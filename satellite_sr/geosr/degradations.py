"""
Satellite-tailored degradation pipeline for training robustness.

The single most important reason SR papers report implausible numbers
(e.g. > 45 dB PSNR) is a *degradation mismatch*: the model is trained and tested
on LR made by the same bicubic down-sampling, so it only has to invert a known
linear operator. Such a model collapses on real imagery.

This module synthesises realistic LR from HR using a randomised, physically
motivated chain so the network learns a robust inverse:

  1. Sensor MTF blur      anisotropic Gaussian (models the point-spread function).
  2. Down-sampling        random among bicubic / bilinear / area (models resampling).
  3. Photon + read noise  Poisson (shot) + Gaussian (read) noise.
  4. Atmospheric effect   contrast reduction + additive haze (air-light).
  5. Quantisation/compression  bit-depth reduction (radiometric quantisation).

Use it either to (a) generate the LR on-the-fly from HR-only datasets
(WorldStrat / WHU / SpaceNet), enabling training beyond bicubic, or (b) further
perturb existing LR for augmentation. Everything is torch-only and batched.
"""
from __future__ import annotations

import math
import random
import torch
import torch.nn.functional as F


def _gaussian_kernel2d(ksize: int, sigma_x: float, sigma_y: float, theta: float,
                       device, dtype):
    ax = torch.arange(ksize, dtype=dtype, device=device) - (ksize - 1) / 2
    yy, xx = torch.meshgrid(ax, ax, indexing="ij")
    cos, sin = math.cos(theta), math.sin(theta)
    xr = cos * xx + sin * yy
    yr = -sin * xx + cos * yy
    k = torch.exp(-0.5 * ((xr / sigma_x) ** 2 + (yr / sigma_y) ** 2))
    return k / k.sum()


def apply_blur(x, ksize=None, sigma_range=(0.4, 2.2), aniso=True):
    """Anisotropic Gaussian blur (sensor MTF)."""
    C = x.shape[1]
    sx = random.uniform(*sigma_range)
    sy = random.uniform(*sigma_range) if aniso else sx
    theta = random.uniform(0, math.pi) if aniso else 0.0
    if ksize is None:
        ksize = int(2 * round(3 * max(sx, sy)) + 1)
    k = _gaussian_kernel2d(ksize, sx, sy, theta, x.device, x.dtype)
    k = k.view(1, 1, ksize, ksize).repeat(C, 1, 1, 1)
    return F.conv2d(x, k, padding=ksize // 2, groups=C)


def apply_resize(x, scale):
    mode = random.choice(["bicubic", "bilinear", "area"])
    kw = dict(scale_factor=1.0 / scale, mode=mode, recompute_scale_factor=False)
    if mode in ("bicubic", "bilinear"):
        kw["align_corners"] = False
    return F.interpolate(x, **kw).clamp(0, 1)


def apply_noise(x, gauss_sigma=(0.0, 0.03), poisson_scale=(40.0, 400.0),
                p_poisson=0.5):
    """Read (Gaussian) + shot (Poisson) noise."""
    if random.random() < p_poisson:
        lam = random.uniform(*poisson_scale)
        x = torch.poisson((x.clamp(0, 1) * lam)) / lam
    sigma = random.uniform(*gauss_sigma)
    if sigma > 0:
        x = x + torch.randn_like(x) * sigma
    return x.clamp(0, 1)


def apply_atmosphere(x, p=0.4, contrast=(0.85, 1.0), haze=(0.0, 0.06)):
    """Simple haze / atmospheric scattering: reduced contrast + additive airlight."""
    if random.random() < p:
        c = random.uniform(*contrast)
        a = random.uniform(*haze)
        x = x * c + a
    return x.clamp(0, 1)


def apply_quantise(x, p=0.3, levels=(64, 128, 256)):
    if random.random() < p:
        L = random.choice(levels)
        x = torch.round(x * (L - 1)) / (L - 1)
    return x.clamp(0, 1)


class SatelliteDegradation:
    """Callable that maps an HR tensor (B,C,H,W in [0,1]) to a synthetic LR."""

    def __init__(self, scale, second_order=True):
        self.scale = scale
        self.second_order = second_order

    def __call__(self, hr: torch.Tensor) -> torch.Tensor:
        x = hr
        x = apply_blur(x)
        # split the down-sampling into two orders for a heavier-tail degradation
        if self.second_order and self.scale % 2 == 0 and self.scale >= 4:
            x = apply_resize(x, 2)
            x = apply_noise(x)
            x = apply_resize(x, self.scale // 2)
        else:
            x = apply_resize(x, self.scale)
        x = apply_noise(x)
        x = apply_atmosphere(x)
        x = apply_quantise(x)
        return x.clamp(0, 1)

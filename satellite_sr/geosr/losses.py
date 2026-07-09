"""
Structure-aware composite loss for satellite super-resolution.

Rationale (each term addresses a documented failure mode of pixel-only SR on
satellite imagery):

  Charbonnier            robust L1-like pixel fidelity (handles non-Gaussian
                         sensor noise better than MSE; MSE over-smooths).
  Boundary-weighted L1   up-weights errors on HR gradient boundaries, so
                         building outlines / road edges are learned preferentially
                         -> directly serves downstream extraction tasks.
  Gradient (Sobel) L1    matches first-order structure between SR and HR.
  Structure-branch       supervises the network's explicit edge prediction
                         against the HR gradient map.
  MS-SSIM                perceptual/structural similarity across scales
                         (mitigates the PSNR-vs-perception gap).
  Focal Frequency Loss   penalises missing/incorrect frequency components; the
                         hard-to-fit high-frequency bands (repetitive urban
                         texture) get emphasised (Jiang et al., ICCV'21).
  SAM                    spectral-angle fidelity across bands (essential for
                         multispectral / cross-sensor colour consistency).

`StructureAwareLoss` returns (total, components_dict) so every term can be
logged and ablated.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .blocks import sobel_gradient


class CharbonnierLoss(nn.Module):
    def __init__(self, eps: float = 1e-3):
        super().__init__()
        self.eps2 = eps * eps

    def forward(self, pred, target):
        return torch.mean(torch.sqrt((pred - target) ** 2 + self.eps2))


def boundary_weighted_l1(pred, target, gamma: float = 4.0):
    """L1 weighted by the (normalised) HR gradient magnitude.

    w = 1 + gamma * edge(target)_normalised  in [1, 1+gamma].
    Errors on structural boundaries cost up to (1+gamma)x more than errors in
    flat regions -> the network spends capacity where structure lives."""
    with torch.no_grad():
        edge = sobel_gradient(target).mean(dim=1, keepdim=True)   # B,1,H,W
        emax = edge.amax(dim=(2, 3), keepdim=True).clamp_min(1e-6)
        w = 1.0 + gamma * (edge / emax)
    return (w * (pred - target).abs()).mean()


def gradient_loss(pred, target):
    return F.l1_loss(sobel_gradient(pred), sobel_gradient(target))


def sam_loss(pred, target, eps: float = 1e-8):
    """Spectral Angle Mapper loss (mean angle between spectral vectors)."""
    dot = torch.sum(pred * target, dim=1)
    pn = torch.sqrt(torch.sum(pred * pred, dim=1) + eps)
    tn = torch.sqrt(torch.sum(target * target, dim=1) + eps)
    cos = torch.clamp(dot / (pn * tn + eps), -1 + 1e-6, 1 - 1e-6)
    return torch.mean(torch.acos(cos))


# ---------------------------------------------------------------------------
# MS-SSIM
# ---------------------------------------------------------------------------
def _gaussian_window(ch, ksize=11, sigma=1.5, device="cpu", dtype=torch.float32):
    coords = torch.arange(ksize, dtype=dtype, device=device) - (ksize - 1) / 2
    g = torch.exp(-(coords ** 2) / (2 * sigma ** 2))
    g = (g / g.sum()).unsqueeze(1)
    win2d = (g @ g.t()).unsqueeze(0).unsqueeze(0)
    return win2d.expand(ch, 1, ksize, ksize).contiguous()


def _ssim(pred, target, win, C1=0.01 ** 2, C2=0.03 ** 2):
    ch = pred.shape[1]
    pad = win.shape[-1] // 2
    mu_x = F.conv2d(pred, win, padding=pad, groups=ch)
    mu_y = F.conv2d(target, win, padding=pad, groups=ch)
    mu_x2, mu_y2, mu_xy = mu_x * mu_x, mu_y * mu_y, mu_x * mu_y
    sx = F.conv2d(pred * pred, win, padding=pad, groups=ch) - mu_x2
    sy = F.conv2d(target * target, win, padding=pad, groups=ch) - mu_y2
    sxy = F.conv2d(pred * target, win, padding=pad, groups=ch) - mu_xy
    cs = (2 * sxy + C2) / (sx + sy + C2)
    ssim_map = ((2 * mu_xy + C1) / (mu_x2 + mu_y2 + C1)) * cs
    return ssim_map.mean(), cs.mean()


class MSSSIMLoss(nn.Module):
    def __init__(self, weights=(0.0448, 0.2856, 0.3001, 0.2363, 0.1333)):
        super().__init__()
        self.register_buffer("w", torch.tensor(weights))

    def forward(self, pred, target):
        levels = self.w.shape[0]
        win = _gaussian_window(pred.shape[1], device=pred.device, dtype=pred.dtype)
        mcs = []
        cur_p, cur_t = pred, target
        ssim_last = None
        for i in range(levels):
            ssim_val, cs = _ssim(cur_p, cur_t, win)
            ssim_last = ssim_val
            mcs.append(torch.clamp(cs, 1e-6, 1.0))
            if i < levels - 1:
                cur_p = F.avg_pool2d(cur_p, 2)
                cur_t = F.avg_pool2d(cur_t, 2)
        mcs = torch.stack(mcs)
        ssim_last = torch.clamp(ssim_last, 1e-6, 1.0)
        msssim = torch.prod(mcs[:-1] ** self.w[:-1]) * (ssim_last ** self.w[-1])
        return 1.0 - msssim


# ---------------------------------------------------------------------------
# Focal Frequency Loss (Jiang et al., ICCV 2021), simplified
# ---------------------------------------------------------------------------
class FocalFrequencyLoss(nn.Module):
    def __init__(self, alpha: float = 1.0):
        super().__init__()
        self.alpha = alpha

    def forward(self, pred, target):
        fp = torch.fft.rfft2(pred, norm="ortho")
        ft = torch.fft.rfft2(target, norm="ortho")
        diff = fp - ft
        dist = diff.real ** 2 + diff.imag ** 2
        with torch.no_grad():
            w = dist ** self.alpha
            w = w / (w.amax(dim=(-2, -1), keepdim=True) + 1e-12)
        return (w * dist).mean()


# ---------------------------------------------------------------------------
# Composite
# ---------------------------------------------------------------------------
class StructureAwareLoss(nn.Module):
    def __init__(self, w_char=1.0, w_bound=0.5, w_grad=0.1, w_struct=0.1,
                 w_msssim=0.15, w_ffl=0.05, w_sam=0.02, bound_gamma=4.0):
        super().__init__()
        self.char = CharbonnierLoss()
        self.msssim = MSSSIMLoss()
        self.ffl = FocalFrequencyLoss()
        self.w = dict(char=w_char, bound=w_bound, grad=w_grad, struct=w_struct,
                      msssim=w_msssim, ffl=w_ffl, sam=w_sam)
        self.bound_gamma = bound_gamma

    def forward(self, pred, target, edge_pred=None):
        c = {}
        c["char"] = self.char(pred, target)
        c["bound"] = boundary_weighted_l1(pred, target, self.bound_gamma)
        c["grad"] = gradient_loss(pred, target)
        c["msssim"] = self.msssim(pred, target)
        c["ffl"] = self.ffl(pred, target)
        c["sam"] = sam_loss(pred, target)
        if edge_pred is not None:
            with torch.no_grad():
                edge_gt = sobel_gradient(target)
            c["struct"] = F.l1_loss(edge_pred, edge_gt)
        else:
            c["struct"] = pred.new_tensor(0.0)
        total = sum(self.w[k] * c[k] for k in c)
        return total, {k: float(v.detach()) for k, v in c.items()}

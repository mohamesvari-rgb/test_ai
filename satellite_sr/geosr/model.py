"""
Geo-SR: a Structure-Guided, Degradation-Aware Hybrid-Attention network for
satellite image super-resolution.

Pipeline (all heavy computation stays at LR resolution):

    LR ─┬─► shallow conv ─► [RHAG x N  (FiLM-conditioned)] ─► conv ─(+shallow)─► Upsampler ─┐
        │                                                                                    ├─► SGF ─► conv ─(+bicubic)─► SR
        ├─► DegradationEncoder ─► cond ──► FiLM in every RHAG                                 │
        └─────────────────────────────► StructureBranch ─► (struct_feat, edge_pred) ─────────┘

Returns either the SR tensor, or (SR, aux) where aux carries the predicted HR
gradient map used by the structure loss.

Why this beats the original SERE-UNet on satellite imagery:
  * No U-Net pooling  -> high-frequency detail (roads, building edges) survives.
  * Window + channel attention -> exploits repetitive/self-similar RS textures and
    large homogeneous regions with a large effective receptive field.
  * Degradation conditioning -> one model generalises across sensors / GSD /
    atmosphere instead of memorising a single (bicubic) degradation.
  * Explicit, supervised structure branch + gated fusion -> boundary sharpness
    and line continuity for downstream building/road extraction.
  * Sub-pixel upsampling -> learns upsampling instead of inheriting bicubic blur.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .blocks import (
    RHAG, DegradationEncoder, StructureBranch, StructureGatedFusion, Upsampler,
)


class MeanShift(nn.Conv2d):
    """Fixed per-channel normalisation (EDSR-style). For >3 channels it degrades
    gracefully to identity so multispectral inputs still work."""

    def __init__(self, in_ch=3, rgb_mean=(0.4488, 0.4371, 0.4040), sign=-1):
        super().__init__(in_ch, in_ch, 1)
        self.weight.data = torch.eye(in_ch).view(in_ch, in_ch, 1, 1)
        if in_ch == len(rgb_mean):
            self.bias.data = sign * torch.tensor(rgb_mean)
        else:
            self.bias.data = torch.zeros(in_ch)
        for p in self.parameters():
            p.requires_grad = False


class GeoSRNet(nn.Module):
    """Structure-Guided, Degradation-Aware Hybrid-Attention SR network.

    Args:
        scale: integer up-scaling factor (2, 3, 4, 8 supported).
        in_ch/out_ch: number of image channels (3 for RGB, N for multispectral).
        dim: trunk width.
        n_groups / depth: number of RHAGs and HABs per group.
        window_size / num_heads: window self-attention config.
        use_degradation: enable the degradation encoder + FiLM conditioning.
        use_structure: enable the structure/gradient branch + gated fusion.
    """

    # The notebook's training loop feeds LR directly (learned upsampling inside).
    needs_upsampled = False

    def __init__(self, scale=3, in_ch=3, out_ch=None, dim=96, n_groups=4, depth=6,
                 window_size=8, num_heads=6, mlp_ratio=2.0, cond_dim=128,
                 use_degradation=True, use_structure=True, global_residual=True):
        super().__init__()
        if out_ch is None:
            out_ch = in_ch
        self.scale = scale
        self.use_degradation = use_degradation
        self.use_structure = use_structure
        # the bicubic global residual only makes sense when in/out channels match
        self.global_residual = global_residual and (in_ch == out_ch)

        self.sub_mean = MeanShift(in_ch, sign=-1)
        self.add_mean = MeanShift(out_ch, sign=1)

        self.conv_first = nn.Conv2d(in_ch, dim, 3, padding=1)

        self.deg_encoder = DegradationEncoder(in_ch, cond_dim) if use_degradation else None
        cdim = cond_dim if use_degradation else 0
        self.groups = nn.ModuleList([
            RHAG(dim, depth, window_size, num_heads, mlp_ratio, cond_dim=cdim)
            for _ in range(n_groups)
        ])
        self.conv_after_body = nn.Conv2d(dim, dim, 3, padding=1)

        self.upsampler = Upsampler(dim, scale)             # -> dim @ HR
        if use_structure:
            self.structure = StructureBranch(dim, scale, out_ch)
            self.fusion = StructureGatedFusion(dim)
        self.conv_last = nn.Conv2d(dim, out_ch, 3, padding=1)

    def forward(self, x: torch.Tensor, return_aux: bool = False):
        bic = F.interpolate(x, scale_factor=self.scale, mode="bicubic", align_corners=False)

        x_norm = self.sub_mean(x)
        shallow = self.conv_first(x_norm)

        cond = self.deg_encoder(x_norm) if self.use_degradation else None

        feat = shallow
        for g in self.groups:
            feat = g(feat, cond)
        feat = self.conv_after_body(feat) + shallow       # global residual (LR space)

        up = self.upsampler(feat)                          # dim @ HR

        edge_pred = None
        if self.use_structure:
            struct_feat, edge_pred = self.structure(shallow)
            up = self.fusion(up, struct_feat)

        out = self.conv_last(up)
        out = self.add_mean(out)
        if self.global_residual:
            out = out + bic
        out = torch.clamp(out, 0, 1)

        if return_aux:
            return out, {"edge_pred": edge_pred}
        return out


def geosr_tiny(scale=3, in_ch=3, **kw):
    """CPU-testable / ablation-friendly configuration."""
    return GeoSRNet(scale=scale, in_ch=in_ch, dim=32, n_groups=2, depth=2,
                    num_heads=4, cond_dim=32, **kw)


def geosr_base(scale=3, in_ch=3, **kw):
    """Recommended configuration for the OLI2MSI / ALSAT-2B experiments."""
    return GeoSRNet(scale=scale, in_ch=in_ch, dim=96, n_groups=4, depth=6,
                    num_heads=6, cond_dim=128, **kw)

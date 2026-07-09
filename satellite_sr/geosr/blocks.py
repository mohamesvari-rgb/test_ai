"""
Building blocks for Geo-SR (Structure-Guided, Degradation-Aware Hybrid-Attention
Super-Resolution for satellite imagery).

Design notes (why these blocks, vs. the original SERE-UNet):

* The trunk keeps features at LR resolution (no pooling / encoder-decoder
  down-sampling). A U-Net collapses spatial resolution to gather context; for
  super-resolution that throws away exactly the high-frequency content the task
  must reconstruct (thin roads, building edges). We instead widen the receptive
  field with window self-attention + channel attention, keeping resolution.
* Window self-attention exploits the strong self-similarity / periodicity of
  satellite scenes (crop rows, building grids, street networks).
* A parallel channel-attention (CAB) branch "activates more pixels" (HAT
  insight): it broadens the effective receptive field and mixes global channel
  statistics, which helps large homogeneous regions.
* Degradation-aware FiLM conditioning lets one model adapt to different
  sensors / GSD / atmospheric degradations instead of overfitting one
  degradation operator.

All blocks accept and return NCHW tensors and support arbitrary spatial sizes
(windows are padded internally), so the model runs on CPU for testing.
"""
from __future__ import annotations

import math
import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# Normalisation / small utilities
# ---------------------------------------------------------------------------
class LayerNorm2d(nn.Module):
    """LayerNorm applied over the channel dimension of an NCHW tensor.

    Matches the token-wise LayerNorm used in Swin/HAT (normalises each spatial
    location across channels), which is more stable for SR than BatchNorm
    (BN couples statistics across a batch of heterogeneous satellite scenes and
    is known to introduce artefacts / limit dynamic range in SR networks).
    """

    def __init__(self, channels: int, eps: float = 1e-6):
        super().__init__()
        self.norm = nn.LayerNorm(channels, eps=eps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.permute(0, 2, 3, 1).contiguous()   # B,H,W,C
        x = self.norm(x)
        return x.permute(0, 3, 1, 2).contiguous()  # B,C,H,W


class SEBlock(nn.Module):
    """Squeeze-and-Excitation channel attention (kept from SERE-UNet lineage)."""

    def __init__(self, channels: int, reduction: int = 16):
        super().__init__()
        hidden = max(channels // reduction, 4)
        self.net = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(channels, hidden, 1),
            nn.GELU(),
            nn.Conv2d(hidden, channels, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x * self.net(x)


# ---------------------------------------------------------------------------
# Window self-attention (Swin/HAT style)
# ---------------------------------------------------------------------------
def window_partition(x: torch.Tensor, ws: int) -> torch.Tensor:
    B, H, W, C = x.shape
    x = x.view(B, H // ws, ws, W // ws, ws, C)
    return x.permute(0, 1, 3, 2, 4, 5).contiguous().view(-1, ws, ws, C)


def window_reverse(windows: torch.Tensor, ws: int, H: int, W: int) -> torch.Tensor:
    B = int(windows.shape[0] / (H * W / ws / ws))
    x = windows.view(B, H // ws, W // ws, ws, ws, -1)
    return x.permute(0, 1, 3, 2, 4, 5).contiguous().view(B, H, W, -1)


class WindowAttention(nn.Module):
    def __init__(self, dim: int, window_size: int = 8, num_heads: int = 6):
        super().__init__()
        self.dim = dim
        self.window_size = window_size
        self.num_heads = num_heads
        self.scale = (dim // num_heads) ** -0.5
        self.qkv = nn.Linear(dim, dim * 3, bias=True)
        self.proj = nn.Linear(dim, dim)

        self.relative_position_bias_table = nn.Parameter(
            torch.zeros((2 * window_size - 1) ** 2, num_heads)
        )
        coords = torch.stack(
            torch.meshgrid(torch.arange(window_size), torch.arange(window_size), indexing="ij")
        )
        coords_flat = torch.flatten(coords, 1)
        rel = coords_flat[:, :, None] - coords_flat[:, None, :]
        rel = rel.permute(1, 2, 0).contiguous()
        rel[:, :, 0] += window_size - 1
        rel[:, :, 1] += window_size - 1
        rel[:, :, 0] *= 2 * window_size - 1
        self.register_buffer("rel_index", rel.sum(-1))
        nn.init.trunc_normal_(self.relative_position_bias_table, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (num_windows*B, N, C) with N = ws*ws
        Bn, N, C = x.shape
        qkv = self.qkv(x).reshape(Bn, N, 3, self.num_heads, C // self.num_heads)
        qkv = qkv.permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]
        attn = (q * self.scale) @ k.transpose(-2, -1)
        bias = self.relative_position_bias_table[self.rel_index.view(-1)].view(N, N, -1)
        attn = attn + bias.permute(2, 0, 1).unsqueeze(0)
        attn = attn.softmax(dim=-1)
        out = (attn @ v).transpose(1, 2).reshape(Bn, N, C)
        return self.proj(out)


class ConvFFN(nn.Module):
    """Locally-enhanced feed-forward (depth-wise conv inside the MLP).

    The depth-wise 3x3 gives every token access to its neighbours, providing the
    local continuity that pure window-MLPs lack -- important for keeping thin
    linear structures (roads, field boundaries) connected across window seams.
    """

    def __init__(self, dim: int, ratio: float = 2.0):
        super().__init__()
        hidden = int(dim * ratio)
        self.fc1 = nn.Conv2d(dim, hidden, 1)
        self.dw = nn.Conv2d(hidden, hidden, 3, padding=1, groups=hidden)
        self.act = nn.GELU()
        self.fc2 = nn.Conv2d(hidden, dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc2(self.act(self.dw(self.fc1(x))))


class CAB(nn.Module):
    """Channel-Attention Block: a convolutional branch run in parallel with the
    window attention (HAT). It compensates for the window attention's limited
    cross-window interaction by mixing global channel statistics."""

    def __init__(self, dim: int, reduction: int = 16):
        super().__init__()
        self.body = nn.Sequential(
            nn.Conv2d(dim, dim, 3, padding=1),
            nn.GELU(),
            nn.Conv2d(dim, dim, 3, padding=1),
            SEBlock(dim, reduction),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.body(x)


class HAB(nn.Module):
    """Hybrid Attention Block = (shifted) window self-attention  ||  channel
    attention branch, followed by a conv feed-forward. Operates in NCHW space
    and pads internally so any H, W is accepted."""

    def __init__(self, dim, window_size=8, num_heads=6, shift=0,
                 mlp_ratio=2.0, cab_weight=0.05):
        super().__init__()
        self.window_size = window_size
        self.shift = shift
        self.cab_weight = cab_weight
        self.norm1 = LayerNorm2d(dim)
        self.attn = WindowAttention(dim, window_size, num_heads)
        self.cab = CAB(dim)
        self.norm2 = LayerNorm2d(dim)
        self.ffn = ConvFFN(dim, mlp_ratio)

    def _attn(self, x: torch.Tensor) -> torch.Tensor:
        B, C, H, W = x.shape
        xin = x.permute(0, 2, 3, 1).contiguous()  # B,H,W,C
        ws = self.window_size
        pad_b = (ws - H % ws) % ws
        pad_r = (ws - W % ws) % ws
        if pad_b or pad_r:
            xin = F.pad(xin, (0, 0, 0, pad_r, 0, pad_b))
        Hp, Wp = xin.shape[1], xin.shape[2]
        if self.shift:
            xin = torch.roll(xin, (-self.shift, -self.shift), dims=(1, 2))
        win = window_partition(xin, ws).view(-1, ws * ws, C)
        win = self.attn(win).view(-1, ws, ws, C)
        xin = window_reverse(win, ws, Hp, Wp)
        if self.shift:
            xin = torch.roll(xin, (self.shift, self.shift), dims=(1, 2))
        if pad_b or pad_r:
            xin = xin[:, :H, :W, :].contiguous()
        return xin.permute(0, 3, 1, 2).contiguous()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        n = self.norm1(x)
        x = x + self._attn(n) + self.cab_weight * self.cab(n)
        x = x + self.ffn(self.norm2(x))
        return x


class RHAG(nn.Module):
    """Residual Hybrid-Attention Group: a stack of HABs (alternating shift) with
    a trailing conv and a residual connection, plus optional FiLM conditioning
    injected from the degradation encoder."""

    def __init__(self, dim, depth=6, window_size=8, num_heads=6,
                 mlp_ratio=2.0, cond_dim=0):
        super().__init__()
        self.blocks = nn.ModuleList([
            HAB(dim, window_size, num_heads,
                shift=0 if i % 2 == 0 else window_size // 2,
                mlp_ratio=mlp_ratio)
            for i in range(depth)
        ])
        self.conv = nn.Conv2d(dim, dim, 3, padding=1)
        self.film = nn.Linear(cond_dim, 2 * dim) if cond_dim > 0 else None

    def forward(self, x: torch.Tensor, cond: torch.Tensor | None = None) -> torch.Tensor:
        shortcut = x
        for blk in self.blocks:
            x = blk(x)
        x = self.conv(x)
        if self.film is not None and cond is not None:
            gamma, beta = self.film(cond).chunk(2, dim=1)   # (B, dim) each
            gamma = gamma.unsqueeze(-1).unsqueeze(-1)
            beta = beta.unsqueeze(-1).unsqueeze(-1)
            x = x * (1 + gamma) + beta
        return shortcut + x


# ---------------------------------------------------------------------------
# Degradation-aware conditioning encoder
# ---------------------------------------------------------------------------
class DegradationEncoder(nn.Module):
    """Predicts a compact degradation/sensor embedding from the LR input.

    Trained (implicitly, end-to-end, and optionally with a contrastive term)
    to summarise blur / noise / illumination so the trunk can adapt. This is the
    generalisation lever: instead of memorising one bicubic degradation, the
    network is told *how* the input was degraded and conditions on it (cf.
    DASR, "Unsupervised Degradation Representation Learning", CVPR'21)."""

    def __init__(self, in_ch=3, cond_dim=128):
        super().__init__()
        self.body = nn.Sequential(
            nn.Conv2d(in_ch, 64, 3, 2, 1), nn.GELU(),
            nn.Conv2d(64, 128, 3, 2, 1), nn.GELU(),
            nn.Conv2d(128, 128, 3, 2, 1), nn.GELU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.mlp = nn.Sequential(
            nn.Linear(128, cond_dim), nn.GELU(),
            nn.Linear(cond_dim, cond_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        f = self.body(x).flatten(1)
        return self.mlp(f)


# ---------------------------------------------------------------------------
# Structure / gradient branch + structure-gated fusion
# ---------------------------------------------------------------------------
def sobel_gradient(x: torch.Tensor) -> torch.Tensor:
    """Per-channel Sobel gradient magnitude of an NCHW tensor."""
    kx = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]],
                      dtype=x.dtype, device=x.device).view(1, 1, 3, 3)
    ky = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]],
                      dtype=x.dtype, device=x.device).view(1, 1, 3, 3)
    C = x.shape[1]
    kx = kx.repeat(C, 1, 1, 1)
    ky = ky.repeat(C, 1, 1, 1)
    gx = F.conv2d(x, kx, padding=1, groups=C)
    gy = F.conv2d(x, ky, padding=1, groups=C)
    return torch.sqrt(gx ** 2 + gy ** 2 + 1e-8)


class StructureBranch(nn.Module):
    """Parallel branch that reconstructs an explicit high-resolution gradient /
    edge map and returns structure features for gated fusion.

    Motivation: for downstream road/building extraction, boundary sharpness and
    line continuity matter more than average PSNR. We give the network a
    dedicated, explicitly supervised path for structure (cf. SPSR gradient
    branch; EEGAN edge enhancement for RS)."""

    def __init__(self, dim, scale, out_ch=3):
        super().__init__()
        self.pre = nn.Sequential(
            nn.Conv2d(dim, dim, 3, padding=1), nn.GELU(),
            nn.Conv2d(dim, dim, 3, padding=1), nn.GELU(),
        )
        self.up = Upsampler(dim, scale)
        self.feat = nn.Conv2d(dim, dim, 3, padding=1)
        self.edge_head = nn.Conv2d(dim, out_ch, 3, padding=1)  # predicts HR gradient

    def forward(self, x: torch.Tensor):
        x = self.pre(x)
        x = self.up(x)
        feat = self.feat(x)
        edge = self.edge_head(x)
        return feat, edge


class StructureGatedFusion(nn.Module):
    """Fuse main HR features with structure features via a learned spatial gate.
    Boundaries flagged by the structure branch are amplified in the main path."""

    def __init__(self, dim):
        super().__init__()
        self.gate = nn.Sequential(nn.Conv2d(dim, dim, 3, padding=1), nn.Sigmoid())
        self.fuse = nn.Conv2d(dim * 2, dim, 3, padding=1)

    def forward(self, main_feat: torch.Tensor, struct_feat: torch.Tensor) -> torch.Tensor:
        g = self.gate(struct_feat)
        x = torch.cat([main_feat * (1 + g), struct_feat], dim=1)
        return self.fuse(x)


# ---------------------------------------------------------------------------
# Sub-pixel upsampler
# ---------------------------------------------------------------------------
class Upsampler(nn.Module):
    """Sub-pixel (pixel-shuffle) upsampler. Learns the upsampling instead of the
    fixed bicubic used as SRCNN/U-Net input -- avoids inheriting bicubic blur and
    keeps all heavy computation in LR space."""

    def __init__(self, dim, scale, out_ch=None):
        super().__init__()
        mods = []
        if (scale & (scale - 1)) == 0:  # power of two
            for _ in range(int(math.log2(scale))):
                mods += [nn.Conv2d(dim, dim * 4, 3, padding=1), nn.PixelShuffle(2), nn.GELU()]
        elif scale == 3:
            mods += [nn.Conv2d(dim, dim * 9, 3, padding=1), nn.PixelShuffle(3), nn.GELU()]
        else:
            raise ValueError(f"Unsupported scale {scale}")
        if out_ch is not None:
            mods.append(nn.Conv2d(dim, out_ch, 3, padding=1))
        self.net = nn.Sequential(*mods)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

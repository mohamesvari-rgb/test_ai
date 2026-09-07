"""
Forward/backward + shape/gradient sanity tests for Geo-SR.

Run:  python -m satellite_sr.tests.test_geosr
These run on CPU with tiny tensors and confirm the reference implementation is
wired correctly (shapes, multispectral input, odd scales, loss back-prop,
degradation pipeline). They are NOT accuracy tests -- accuracy requires the
GPU training run described in docs/ARCHITECTURE_ANALYSIS.md.
"""
import torch

from satellite_sr.geosr import (
    geosr_tiny, StructureAwareLoss, SatelliteDegradation,
)
from satellite_sr.geosr.model import GeoSRNet


def _count(m):
    return sum(p.numel() for p in m.parameters() if p.requires_grad)


def test_forward_shapes():
    for scale in (2, 3, 4):
        for hw in (24, 31):            # include a non-window-multiple size
            m = geosr_tiny(scale=scale).eval()
            x = torch.rand(2, 3, hw, hw)
            with torch.no_grad():
                y = m(x)
            assert y.shape == (2, 3, hw * scale, hw * scale), (scale, hw, y.shape)
            assert torch.isfinite(y).all()
            assert y.min() >= 0 and y.max() <= 1
    print("[ok] forward shapes / value range (scales 2,3,4; padded windows)")


def test_multispectral():
    m = geosr_tiny(scale=2, in_ch=5).eval()          # e.g. RGB+NIR+SWIR
    with torch.no_grad():
        y = m(torch.rand(1, 5, 32, 32))
    assert y.shape == (1, 5, 64, 64)
    print("[ok] multispectral (5-band) input")


def test_backward_and_loss():
    m = geosr_tiny(scale=3)
    crit = StructureAwareLoss()
    x = torch.rand(2, 3, 24, 24, requires_grad=False)
    hr = torch.rand(2, 3, 72, 72)
    sr, aux = m(x, return_aux=True)
    total, comps = crit(sr, hr, edge_pred=aux["edge_pred"])
    total.backward()
    grads = [p.grad for p in m.parameters() if p.requires_grad]
    n_grad = sum(g is not None and torch.isfinite(g).all() for g in grads)
    assert n_grad > 0
    assert set(comps) == {"char", "bound", "grad", "struct", "msssim", "ffl", "sam"}
    print(f"[ok] backward + composite loss (params={_count(m):,}); "
          f"components={ {k: round(v,4) for k,v in comps.items()} }")


def test_ablations():
    for kw in (dict(use_structure=False), dict(use_degradation=False),
               dict(use_structure=False, use_degradation=False)):
        m = GeoSRNet(scale=2, dim=24, n_groups=1, depth=2, num_heads=4,
                     cond_dim=16, **kw).eval()
        with torch.no_grad():
            y = m(torch.rand(1, 3, 16, 16))
        assert y.shape == (1, 3, 32, 32)
    print("[ok] ablation variants (no-structure / no-degradation) forward")


def test_degradation_pipeline():
    deg = SatelliteDegradation(scale=4)
    hr = torch.rand(2, 3, 64, 64)
    lr = deg(hr)
    assert lr.shape == (2, 3, 16, 16)
    assert lr.min() >= 0 and lr.max() <= 1 and torch.isfinite(lr).all()
    print("[ok] satellite degradation pipeline (HR->LR, x4)")


if __name__ == "__main__":
    torch.manual_seed(0)
    test_forward_shapes()
    test_multispectral()
    test_backward_and_loss()
    test_ablations()
    test_degradation_pipeline()
    print("\nAll Geo-SR sanity tests passed.")

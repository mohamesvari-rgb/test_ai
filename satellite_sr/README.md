# Geo-SR — Structure-Guided, Degradation-Aware Super-Resolution for Satellite Imagery

A satellite-specific super-resolution architecture proposed as a successor to
**SERE-UNet**, with a working, unit-tested PyTorch reference implementation that
drops into the existing `Q1_satellite_SR_full_baselines_notebook.ipynb`.

* **Full technical analysis & justification:** [`docs/ARCHITECTURE_ANALYSIS.md`](docs/ARCHITECTURE_ANALYSIS.md)
  (diagnosis of SERE-UNet, why the reported 49 dB is a red flag, the Geo-SR design,
  novel modules/losses, dataset assessment, and the implementation plan).

## What's here

```
satellite_sr/
├── geosr/
│   ├── blocks.py         # HAB/RHAG hybrid attention, DegradationEncoder+FiLM,
│   │                     # StructureBranch, StructureGatedFusion, PixelShuffle upsampler
│   ├── model.py          # GeoSRNet (+ geosr_base / geosr_tiny), channel-agnostic I/O
│   ├── losses.py         # StructureAwareLoss = Charbonnier + boundary-L1 + gradient
│   │                     # + struct-branch + MS-SSIM + focal-frequency + SAM
│   ├── degradations.py   # realistic satellite HR→LR chain (MTF blur, shot/read noise,
│   │                     # atmosphere, quantisation) — breaks the bicubic leak
│   └── factory.py        # make_geosr_model(name, scale, in_ch) — notebook-compatible
├── tests/test_geosr.py   # CPU forward/backward/shape/ablation/degradation sanity tests
└── docs/ARCHITECTURE_ANALYSIS.md
```

## Design in one paragraph

Geo-SR keeps features at **LR resolution** (no U-Net pooling — pooling destroys the
high-frequency detail SR must reconstruct) and widens the receptive field with a
**Hybrid Attention** trunk (shifted-window self-attention ∥ channel attention),
matching the self-similar, periodic, large-homogeneous-region statistics of satellite
scenes. A **degradation encoder** conditions the trunk (FiLM) so one model adapts
across sensors/GSD/atmosphere instead of memorising one degradation. A parallel,
explicitly-supervised **structure/gradient branch** with **gated fusion** sharpens
building outlines and road continuity for downstream extraction. Upsampling is
**sub-pixel** (learned), and the loss is a **structure + frequency + spectral
composite** with a boundary-weighted term. Measured size: `geosr_base` ≈ **8.66M**
params (×3).

## Quick start

```bash
python -m satellite_sr.tests.test_geosr        # CPU sanity tests (needs only torch)
```

```python
from satellite_sr.geosr import geosr_base, StructureAwareLoss, SatelliteDegradation

model = geosr_base(scale=3, in_ch=3)           # 3 for RGB; N for multispectral
sr, aux = model(lr, return_aux=True)           # aux["edge_pred"] feeds the loss
loss, comps = StructureAwareLoss()(sr, hr, edge_pred=aux["edge_pred"])

# train beyond bicubic (robustness): synthesise realistic LR from HR
lr = SatelliteDegradation(scale=3)(hr)
```

## Integrate into the notebook (3 edits)

1. **`make_model` (cell 11):**
   ```python
   from satellite_sr.geosr import make_geosr_model
   if model_name.startswith("GeoSR"):
       return make_geosr_model(model_name, scale=SCALE, in_ch=3)
   ```
   and add `"GeoSR"` to `MODELS_TO_RUN` (`GeoSRNet.needs_upsampled = False`, so the
   existing loop feeds it LR directly — no other change).

2. **Loss (cell 12):** use `StructureAwareLoss`; call the model with
   `return_aux=True` and pass `aux["edge_pred"]` to the loss.

3. **Evaluation:** add a **bicubic-only** row, use the **scene-level split**, and add
   a **real-degradation** test set built with `SatelliteDegradation` (see the analysis
   doc, §1.1 and §5 — this is what makes the numbers credible).

Ablations `GeoSR_no_structure` and `GeoSR_no_degradation` are exposed by the factory.

## Requirements

`torch` (≥1.12) is the only hard dependency for the model/loss. The notebook already
pulls in `numpy/pandas/scikit-image/lpips/thop` for metrics and reporting.

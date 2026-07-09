# Geo-SR: Analysis of SERE-UNet and a Structure-Guided, Degradation-Aware Architecture for Satellite Super-Resolution

Prepared for: *SERE-UNet* (Mesvari & Shahosseini), datasets **OLI2MSI** and **ALSAT-2B**.
Scope: (1) diagnose the current architecture, (2) design a satellite-specific replacement,
(3) specify novel modules and losses, (4) assess dataset sufficiency and recommend
additions, (5) give a concrete implementation plan against the existing notebook.

A working, unit-tested reference implementation of everything proposed here lives
in `satellite_sr/geosr/` (see `README.md`). All parameter counts quoted below are
measured from that code.

---

## 0. Executive summary

* **The headline numbers are not credible as reported and will not survive Q1 review.**
  A PSNR of **49.22 dB / SSIM 99.2%** on OLI2MSI is ~14 dB above every method you
  cite on the *same* dataset (EFDN 35.0, SRGAN 34.7, ESRGAN 34.3, SRDiff 33.8).
  A 14 dB gap is ~25× lower MSE — that is the signature of a **degradation /
  evaluation leak**, not of a better model (§1.1). This must be fixed first;
  otherwise every architectural conclusion rests on a broken measurement.

* **SERE-UNet is a U-Net, and a U-Net is the wrong backbone for SR.** Its encoder
  pools away spatial resolution to gather context; SR must *reconstruct* exactly
  the high-frequency content pooling destroys. It also refines a **bicubic-upsampled**
  input (SRCNN-era paradigm), inheriting bicubic blur and wasting compute at HR.
  BatchNorm, sigmoid output, and channel-only (SE) attention compound the problem (§1.2).

* **Your own notebook already contains the better direction** (MSA-SERE-UNet:
  LR-space features + sub-pixel upsampling + multi-term loss). Geo-SR pushes that
  further with four satellite-specific mechanisms that are missing today:
  a **full-resolution hybrid attention trunk**, a **degradation-aware conditioning**
  path for cross-sensor robustness, an **explicit structure/gradient branch** for
  building/road boundary fidelity, and a **structure+frequency+spectral composite loss** (§2–3).

* **The datasets are sufficient to publish a benchmark result but insufficient to
  support the generalisation and "building/road" claims.** OLI2MSI (×3) and ALSAT-2B
  (×4) are two sensors, RGB only, and ALSAT-2B is small (2,182 train pairs). To
  substantiate robustness and downstream-structure claims you need
  cross-sensor/real-degradation data (SEN2VENµS, WorldStrat, SEN2NAIP) and
  building/road labels (WHU, SpaceNet, Inria, LoveDA/OpenEarthMap) (§4).

---

## 1. Diagnosis of the current architecture

### 1.1 The results are inconsistent with the physics of the task (read this first)

| Method (OLI2MSI ×3) | PSNR (dB) | SSIM |
|---|---|---|
| EFDN | 35.02 | 0.901 |
| SRGAN | 34.73 | 0.898 |
| ESRGAN | 34.30 | 0.885 |
| SRDiff | 33.80 | 0.890 |
| **SERE-UNet (reported)** | **49.22** | **0.992** |

Independent SR literature on OLI2MSI ×3 clusters at **30–36 dB**. 49 dB means the
average pixel error is < 1 gray level on an 8-bit scale — i.e. the output is nearly
identical to ground truth. The most likely causes, in order of probability:

1. **Trivial global-residual/bicubic dominance.** OLI2MSI pairs are radiometrically
   harmonised cross-sensor tiles; a bicubic upsample of the LR is already very close
   to the HR. Any model that outputs `f(x) + bicubic(x)` and is scored against HR
   inherits that high baseline. *Check:* compute PSNR of **plain bicubic** on your
   test split. If bicubic alone is already ~40 dB, the split is too easy and every
   number is dominated by the low-frequency baseline (this also explains "SRCNN
   scores high but looks blurry").
2. **Degradation self-consistency leak.** If LR is produced by the *same* bicubic
   operator used at train and test, the network only has to invert a known linear
   map — PSNR explodes and collapses on real imagery.
3. **Evaluation-set leakage** (scene tiles from the same scene in train and test) —
   OLI2MSI tiles are spatially contiguous; a random patch split leaks neighbours.
   Your notebook's `sr_pair_manifest_scene_level_split.csv` suggests you already
   moved to scene-level splitting — good; make sure *every* table uses it.
4. **Metric/range mismatch** (SSIM on different `data_range`, UIQI reported as
   `98.25` while SSIM is `0.992` — mixing 0–100 and 0–1 scales).

**Action:** re-run with (a) a bicubic-only row, (b) scene-level split, (c) LR built by
the realistic degradation pipeline in `geosr/degradations.py` (not just bicubic),
and (d) a single, documented metric convention. Expect the honest number to land in
the low-to-mid 30s dB; a method that wins *there* is a real contribution.

### 1.2 Architectural bottlenecks

| # | Bottleneck in SERE-UNet | Why it hurts on satellite imagery | Fix in Geo-SR |
|---|---|---|---|
| 1 | **U-Net pooling / encoder–decoder** collapses resolution | SR must reconstruct high-frequency detail (roads, roof edges); max-pool discards it, so the decoder hallucinates it back from a bottleneck. Fine for segmentation, wrong for SR. | **No pooling.** Full-resolution trunk; context comes from attention, not down-sampling. |
| 2 | **Refines a bicubic-upsampled input** (`needs_upsampled=True`) | Inherits bicubic's blur/ringing; all conv work runs at HR → slow, and the network spends capacity undoing interpolation artefacts. | **LR-space trunk + sub-pixel (PixelShuffle) upsampling** — learns the upsampling; heavy compute stays in LR. |
| 3 | **BatchNorm** inside residual blocks | BN normalises across a batch of heterogeneous scenes (desert + city + sea), shifts feature statistics, and is known to cause artefacts and cap dynamic range in SR (EDSR removed BN for exactly this). | **LayerNorm over channels** (per-location), standard in Swin/HAT. |
| 4 | **Sigmoid output** | Saturates gradients at 0/1 and squashes radiometric range; satellite scenes use much of the dynamic range. | Linear output + global residual, clamp only at the very end. |
| 5 | **SE (channel) attention only** | No spatial/long-range modelling. Satellite scenes are dominated by **self-similarity and periodicity** (crop rows, building grids) that channel attention cannot exploit. | **Window self-attention + channel attention (Hybrid Attention Block)**. |
| 6 | **Charbonnier-only loss** (article) | Pixel-wise, mean-seeking → over-smooth edges, no structural/spectral/frequency supervision. | **Composite structure/frequency/spectral loss** with a boundary-weighted term. |
| 7 | **Single-sensor, single-degradation training** | Model memorises one degradation; no mechanism to adapt to a new sensor/GSD/atmosphere → poor generalisation, the paper's central claim. | **Degradation-aware conditioning (DACE + FiLM)** + randomised degradation training. |
| 8 | **RGB-only, three-channel output** | Throws away NIR/SWIR that disambiguate materials and sharpen land/water and vegetation edges. | Channel-agnostic I/O (`in_ch` = N), spectral (SAM) loss. |
| 9 | **No task-aware objective** | "Better for building/road extraction" is asserted, not optimised for. | Boundary-weighted loss + explicit edge branch (+ optional RS-perceptual loss on a segmentation backbone). |

### 1.3 Where it underperforms modern SOTA

Against current remote-sensing SR (SwinIR, **HAT**, DAT, Swin2-MoSE, Mamba-based
FMSR, and diffusion models such as SR3/SRDiff and EDiffSR), SERE-UNet lacks:
long-range self-attention, a large effective receptive field, learned upsampling,
and any frequency-domain or structure-domain objective. The MSA-SERE-UNet in your
notebook closes part of the gap (dilated multi-scale conv + CBAM spatial attention +
sub-pixel), but its trunk still down-samples twice and its attention is convolutional
(local), so it under-models the repetitive long-range structure that RS transformers
are specifically good at.

---

## 2. Geo-SR: proposed architecture

**Name:** Geo-SR — *Structure-Guided, Degradation-Aware Hybrid-Attention network*.
Designed for satellite imagery from first principles rather than ported from natural-image SR.

```
                          ┌─────────────────── cond (degradation/sensor code) ───────────────┐
                          │                                                                    ▼   (FiLM γ,β)
  LR ──► sub-mean ──► conv_first ─► [ RHAG₁ ─► RHAG₂ ─► … ─► RHAG_N ] ─► conv ─(+shallow)─► PixelShuffle ↑s ─► main_HR
   │        (per-band)        │           (full LR resolution, no pooling)                                   │
   │                          │                                                                              ▼
   ├─► DegradationEncoder ────┘                                                              StructureGatedFusion
   │      (LR → cond)                                                                                        │
   │                                                                                                         ▼
   └─────────────────────────────────► StructureBranch ─► (struct_feat ↑s , edge_pred ↑s) ──────────────────┘
                                            (predicts HR gradient map, supervised)                          │
                                                                                                  conv_last ─► + bicubic ─► SR
```

**Trunk = N Residual Hybrid-Attention Groups (RHAG).** Each RHAG is a stack of
**Hybrid Attention Blocks (HAB)** with a trailing conv and a residual connection.
Resolution is constant (LR) throughout; the up-scaling happens once, at the end,
via sub-pixel convolution. This is the EDSR/RCAN/SwinIR/HAT consensus and the single
biggest departure from the U-Net.

**HAB = window self-attention ∥ channel attention, then a conv-FFN.**
- *(Shifted) window self-attention* captures long-range self-similarity — the
  defining statistic of satellite scenes (repeated buildings, field furrows,
  street grids). Shifting alternates each block to connect windows.
- A parallel *channel-attention branch (CAB)* runs a small conv path + SE. Following
  HAT's finding that windowed transformers activate too few pixels, the CAB widens
  the effective receptive field and mixes global channel statistics — helpful for the
  **large homogeneous regions** (water, desert, fields) that are common in RS and rare
  in natural images.
- A *depth-wise conv feed-forward (LeFF)* gives every token access to its neighbours,
  keeping **thin linear structures (roads, boundaries) continuous across window seams**.

**Degradation-Aware Conditioning Encoder (DACE) + FiLM.** A small CNN maps the LR
input to a compact **degradation/sensor embedding**; a per-group FiLM layer uses it
to modulate the trunk (`x ← x·(1+γ) + β`). Instead of memorising one bicubic
degradation, the network is *told how the input was degraded* and adapts — the
generalisation lever across **GSD, sensor, and atmosphere** (cf. DASR, "Unsupervised
Degradation Representation Learning", CVPR'21). Adds ~0.35M params.

**Structure Branch + Structure-Gated Fusion (the task-aware core).** A parallel
branch reconstructs an **explicit HR gradient/edge map**, supervised against the HR
Sobel map. Its features are fused into the main HR path through a learned spatial
gate that **amplifies exactly the pixels on building outlines and roads** (inspired
by SPSR's gradient branch and EEGAN's edge enhancement for RS). This is what turns
"good PSNR" into "sharp, extractable boundaries." Adds ~1.25M params.

**Channel-agnostic I/O.** `in_ch`/`out_ch` are configurable; the model runs on RGB
today and on multispectral (RGB+NIR+SWIR…) with no code change (verified with a
5-band test).

**Measured cost** (from the reference code): `geosr_base` = **8.66M params (×3)** /
8.49M (×4) — between SwinIR (~11.8M) and lightweight CNNs, ~2× smaller than HAT
(20.8M) and ESRGAN's RRDBNet (~16.7M). The advantage is not parameter count but
*where* the capacity goes: resolution-preserving attention + explicit structure.

### Why each choice beats the current result

| Design choice | Beats… | Mechanism |
|---|---|---|
| Full-res trunk (no pooling) | SERE-UNet U-Net | keeps HF detail instead of reconstructing it from a bottleneck |
| Sub-pixel upsampling | SERE-UNet bicubic-input | learns upsampling; no inherited blur; faster (LR-space compute) |
| Window + channel attention | SE-only / CBAM | models long-range periodicity + large homogeneous regions |
| DACE + FiLM + random degradation | single-degradation training | generalises across sensor/GSD/atmosphere (the paper's thesis) |
| Structure branch + gated fusion | generic edge loss | explicit, supervised boundary reconstruction for extraction tasks |
| Composite loss (§3) | Charbonnier-only | structure + frequency + spectral fidelity, not just mean pixel error |

---

## 3. Novel modules and loss functions

All implemented in `geosr/blocks.py` and `geosr/losses.py`.

### 3.1 Modules
- **HAB / RHAG** — hybrid window+channel attention group (§2).
- **DegradationEncoder + FiLM** — conditioning for robustness (§2).
- **StructureBranch + StructureGatedFusion** — explicit edge reconstruction and gating (§2).
- **Upsampler** — PixelShuffle sub-pixel upsampling (×2/×3/×4/×8).

### 3.2 Structure-aware composite loss

`L = 1.0·Charbonnier + 0.5·Boundary-L1 + 0.1·Gradient + 0.1·StructBranch + 0.15·MS-SSIM + 0.05·FFL + 0.02·SAM`

| Term | What it enforces | Why it matters for satellite / buildings |
|---|---|---|
| **Charbonnier** | robust pixel fidelity | tolerant to non-Gaussian sensor noise (MSE over-smooths) |
| **Boundary-weighted L1** | up-weights errors on HR gradient boundaries (`w = 1 + γ·edge`) | spends capacity on **building outlines / road edges** — the pixels downstream extraction depends on |
| **Gradient (Sobel) L1** | first-order structure match | crisp edges, suppresses the U-Net's edge smear |
| **Structure-branch L1** | supervises the explicit edge prediction | forces the dedicated structure path to be correct |
| **MS-SSIM** | multi-scale structural similarity | closes the PSNR-vs-perception gap |
| **Focal Frequency Loss** | weights hard-to-fit frequency bands | recovers **repetitive high-frequency urban texture** (ICCV'21) |
| **SAM** | spectral-angle fidelity | cross-sensor / multispectral colour consistency |

Optional **task-aware perceptual loss**: replace ImageNet-VGG features with features
from a *remote-sensing segmentation backbone* (e.g. a building-extraction U-Net/HRNet)
so the SR output preserves what a downstream extractor keys on. Off by default
(needs a pretrained RS backbone); hook provided in the README.

### 3.3 Realistic degradation pipeline (`geosr/degradations.py`)
Randomised, physically-motivated HR→LR chain: anisotropic Gaussian MTF blur →
random-kernel down-sampling → Poisson (shot) + Gaussian (read) noise → atmospheric
contrast/haze → radiometric quantisation, with an optional second-order pass. This
lets you train on HR-only datasets (WorldStrat, WHU, SpaceNet) and, crucially,
**breaks the bicubic self-consistency leak** behind §1.1.

---

## 4. Dataset sufficiency and recommendations

### 4.1 Are OLI2MSI + ALSAT-2B enough?

**Partly.** They are fine as *two benchmark points*, but they cannot support the
paper's two headline claims:

- **Generalisation across sensors/resolutions/atmosphere.** Two sensors, both RGB,
  at fixed ×3 / ×4. ALSAT-2B is small (2,182 train / 577 test) — too small to train
  an 8M-parameter attention model without heavy regularisation/augmentation, and too
  small to *demonstrate* robustness. Cross-sensor generalisation needs ≥3–4 sensors
  and real (not bicubic) degradations.
- **Building/road / urban-structure fidelity.** Neither dataset carries building or
  road labels, so you cannot measure the structural claim directly (only proxy it via
  PSNR/SSIM). To claim "better for extraction," you must **run a fixed extractor on the
  SR output and report IoU/F1** — which requires labelled urban data.

### 4.2 Recommended additions (current, documented, well-licensed)

**A. Real / cross-sensor SR pairs (for accuracy + robustness):**

| Dataset | HR→LR / GSD | Size | License | Use |
|---|---|---|---|---|
| **SEN2VENµS** (Zenodo 6514159) | VENµS 5 m ← Sentinel-2 10/20 m, real same-day | 132,955× 256² patches, 29 sites | CC BY 4.0 | real ×2 SR, multispectral, large |
| **WorldStrat** (Zenodo 6810792) | SPOT 6/7 1.5 m ← Sentinel-2 10 m (multi-temporal) | ~10,000 km², global stratified | HR CC BY-NC 4.0; S2/labels CC BY 4.0 | real ×~6 SR, diverse geographies |
| **SEN2NAIP** (Nature Sci. Data 2024) | NAIP ~1–2.5 m ← Sentinel-2 10 m | large-scale (10k+ scenes) | CC (open) | real ×4 SR, US-wide diversity |
| **RRSSRD** | HR RGB reference tiles, 19 scene classes | 4,047 reference pairs | research | reference-based / scene diversity |
| *(keep)* **OLI2MSI** | S2 10 m ← L8 OLI 30 m, ×3 | real cross-sensor | free | your existing ×3 benchmark |
| *(keep)* **ALSAT-2B** | 2.5 m / 10 m, ×4 | 2,182 / 577 | provided | your existing ×4 benchmark |

**B. Building/road labels (for the task-aware evaluation and the boundary/RS-perceptual loss):**

| Dataset | GSD | Size | License | Use |
|---|---|---|---|---|
| **WHU Building** (aerial + satellite) | 0.3 m | 8,188 tiles, 187k buildings, 450 km² | free (academic) | building-boundary eval; RS-perceptual backbone |
| **SpaceNet v2 Buildings** | ~0.3 m (WorldView-3) | 4 cities, footprints | CC BY-SA 4.0 (AWS Open Data) | satellite building extraction eval |
| **Inria Aerial Image Labeling** | 0.3 m | 360 tiles (5000²), 5 cities | free (research) | cross-city building generalisation |
| **Massachusetts Buildings / Roads** | 1 m | 151 / 1171 tiles, Boston | free (research) | roads + buildings at coarser GSD |
| **LoveDA** | 0.3 m | 5,987 images, 7 classes (urban/rural) | CC BY-NC 4.0 | domain-shift urban↔rural, building+road |
| **OpenEarthMap** | 0.25–0.5 m | 5,000 images/1024², 97 regions | annotations CC BY-NC-SA (non-commercial) | global land-cover incl. building/road |
| **GaoFen-7 building** (Nature Sci. Data 2024) | sub-meter (GF-7 stereo) | benchmark | open | newer, non-US building benchmark |

**Recommended protocol.** (1) Train/benchmark SR on OLI2MSI (×3) and ALSAT-2B (×4) as
now, *plus* SEN2VENµS (real ×2) and one of WorldStrat/SEN2NAIP (real ×4) with the
realistic degradation pipeline. (2) For the structural claim: pick one labelled urban
set (SpaceNet or WHU), super-resolve its LR, run a **frozen** building/road extractor,
and report IoU/F1 and boundary-F1 — SR quality that helps extraction is the real proof.
(3) Cross-dataset test (train on A, test on B) to substantiate generalisation.

---

## 5. Implementation plan (against your existing notebook)

Your notebook (`Q1_satellite_SR_full_baselines_notebook.ipynb`) is already well
structured — a model factory, a shared train/eval loop keyed on `needs_upsampled`,
metrics, statistical tests, and complexity reporting. Geo-SR is built to slot into it
with **minimal changes**.

**Step 1 — add the package.** Copy `satellite_sr/geosr/` next to the notebook (or
`pip install -e .`).

**Step 2 — register the model (cell 11, `make_model`):**
```python
from satellite_sr.geosr import make_geosr_model
def make_model(model_name):
    if model_name.startswith("GeoSR"):
        return make_geosr_model(model_name, scale=SCALE, in_ch=3)
    ...  # existing baselines unchanged
```
and add `"GeoSR"` (and optionally `"GeoSR_no_structure"`, `"GeoSR_no_degradation"`
for ablations) to `MODELS_TO_RUN`. `GeoSRNet.needs_upsampled = False`, so
`prepare_input` feeds it LR directly — nothing else in the loop changes.

**Step 3 — swap in the composite loss + edge aux (cell 12, `train_standard_model`):**
```python
from satellite_sr.geosr import StructureAwareLoss
criterion = StructureAwareLoss().to(DEVICE)
...
pred, aux = model(inp, return_aux=True) if isinstance(model, GeoSRNet) else (model(inp), {"edge_pred": None})
loss, comps = criterion(pred, hr, edge_pred=aux["edge_pred"])
```
Keep the existing `CombinedSRLoss` for the baselines so the comparison is fair, or
train **all** models with `StructureAwareLoss` and report both — either is defensible,
just state it.

**Step 4 — fix the evaluation (the important one):**
* Add a **bicubic-only** row to every table and *report it* (§1.1 sanity check).
* Use the **scene-level split** manifest everywhere.
* Add a **real-degradation test set**: build LR with `SatelliteDegradation(scale)`
  from held-out HR and evaluate on it — this is your robustness/generalisation table.
* Keep PSNR/SSIM/UIQI/ERGAS/SAM/LPIPS; add **Boundary-F1** on a labelled urban set.

**Step 5 — training recipe.** AdamW `lr=2e-4`, cosine to `1e-6`, weight decay `1e-4`;
batch of 16 random **48×48 LR crops** (crop, don't train on full 480×480 — attention is
quadratic in tokens and cropping multiplies effective data); 300k iters (or ≥200
epochs on ALSAT-2B with the degradation augmentation on). Enable AMP. For a perceptual
variant, fine-tune with the optional RS-perceptual + a light adversarial term (your
notebook's `PatchDiscriminator` already supports this) — but **report PSNR/SSIM from
the pixel model and LPIPS/Boundary-F1 from the perceptual model separately**, never mix.

**Step 6 — ablations for the paper.** Geo-SR vs. `-structure` vs. `-degradation` vs.
`-both` (all provided by the factory), plus loss-term ablations (drop boundary / FFL /
SAM one at a time). This is what makes each claimed contribution defensible.

**Expected outcome.** On an honest scene-level, real-degradation protocol, Geo-SR
should lead on PSNR/SSIM by a *modest, believable* margin over SwinIR/HAT-class
baselines, and lead more clearly on **edge/boundary and downstream IoU/F1** — which is
the contribution that matters for a satellite-SR-for-extraction paper, and the one your
current pixel-only setup cannot demonstrate.

---

## 6. Key references (technique → where it is used here)

- **HAT** — Chen et al., "Activating More Pixels in Image SR Transformer," CVPR 2023 (hybrid window+channel attention → HAB/RHAG).
- **SwinIR** — Liang et al., ICCV 2021 (window self-attention restoration backbone).
- **EDSR** — Lim et al., CVPRW 2017 (remove BatchNorm; residual SR; sub-pixel).
- **RCAN** — Zhang et al., ECCV 2018 (channel attention in SR).
- **DASR** — Wang et al., "Unsupervised Degradation Representation Learning," CVPR 2021 (degradation conditioning → DACE+FiLM).
- **Real-ESRGAN** — Wang et al., ICCVW 2021 (high-order random degradation → `degradations.py`).
- **SPSR** — Ma et al., "Structure-Preserving SR with Gradient Guidance," CVPR 2020 (gradient branch → StructureBranch).
- **EEGAN** — Jiang et al., edge-enhanced GAN for RS SR (edge enhancement for satellite).
- **Focal Frequency Loss** — Jiang et al., ICCV 2021 (frequency-domain loss → FFL).
- **SRBuildingSeg** — Zhang et al., Remote Sensing 2021 (SR + building segmentation; motivates task-aware eval).
- Datasets: **SEN2VENµS** (Michel et al., 2022), **WorldStrat** (Cornebise et al., NeurIPS 2022), **SEN2NAIP** (2024), **WHU Building** (Ji et al., 2019), **SpaceNet**, **Inria** (Maggiori et al., 2017), **LoveDA** (Wang et al., NeurIPS 2021), **OpenEarthMap** (Xia et al., WACV 2023).

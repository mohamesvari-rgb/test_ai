"""
Drop-in factory that matches the interface used in the notebook
(`make_model(name)` returning a module whose `.needs_upsampled` attribute tells
the training loop whether to pre-upsample the LR input).

Add "GeoSR" to the notebook's MODELS_TO_RUN list and route make_model() through
`make_geosr_model` to train it alongside the existing baselines with no other
changes to the training/eval loops.
"""
from __future__ import annotations

from .model import GeoSRNet, geosr_base, geosr_tiny


def make_geosr_model(name: str, scale: int, in_ch: int = 3):
    name = name.lower()
    if name in ("geosr", "geosr_base", "geo_sr"):
        return geosr_base(scale=scale, in_ch=in_ch)
    if name in ("geosr_tiny",):
        return geosr_tiny(scale=scale, in_ch=in_ch)
    # ablation variants
    if name == "geosr_no_structure":
        return geosr_base(scale=scale, in_ch=in_ch, use_structure=False)
    if name == "geosr_no_degradation":
        return geosr_base(scale=scale, in_ch=in_ch, use_degradation=False)
    raise ValueError(f"Unknown Geo-SR variant: {name}")

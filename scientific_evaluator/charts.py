"""
Chart generation for the analytical report.

Renders matplotlib charts (as PNG images) that are embedded into the Word/PDF
report. Persian labels are shaped with arabic_reshaper + python-bidi and drawn
with an installed Persian font, so text renders correctly right-to-left.

All functions degrade gracefully: if matplotlib or the shaping libraries are
missing, chart generation is skipped and the report is produced without images.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import List, Optional

from .config import RUBRIC
from .models import EvaluationResult

# --- optional dependencies -------------------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")  # headless
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    _HAS_MPL = True
except Exception:  # pragma: no cover
    _HAS_MPL = False

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _HAS_SHAPING = True
except Exception:  # pragma: no cover
    _HAS_SHAPING = False

# matplotlib 3.11+ shapes and orders right-to-left text itself (libraqm).
# Pre-shaping on top of that would reverse every Persian label.
_MPL_NATIVE_RTL = _HAS_MPL and tuple(matplotlib.__version_info__[:2]) >= (3, 11)


# A brand-neutral, colour-blind-friendly palette.
_PALETTE = ["#2f6f9f", "#3f9f7f", "#c98a2b", "#9f5fa0", "#b04a4a", "#6f7f8f"]


def charts_available() -> bool:
    return _HAS_MPL


def _register_persian_font() -> Optional[str]:
    """Find an installed Persian-capable font and register it with matplotlib.

    Returns the font family name to use, or None to fall back to the default.
    """
    if not _HAS_MPL:
        return None
    from .fonts import persian_font_files

    candidates: List[str] = [p for p in persian_font_files()[:1] if p]  # B Nazanin / Vazirmatn / Tahoma
    for pattern in (
        "/usr/share/fonts/**/*[Nn]oto*[Aa]rabic*.ttf",
        "/usr/share/fonts/**/*[Aa]miri*.ttf",
    ):
        candidates += glob.glob(pattern, recursive=True)
    for path in candidates:
        try:
            font_manager.fontManager.addfont(path)
            return font_manager.FontProperties(fname=path).get_name()
        except Exception:
            continue
    return None


def _latin_fallback_families() -> List[str]:
    """Latin font family names to fall back to for non-Persian glyphs."""
    from .fonts import latin_font_files

    families: List[str] = []
    path = latin_font_files()[0]
    if path:
        try:
            font_manager.fontManager.addfont(path)
            families.append(font_manager.FontProperties(fname=path).get_name())
        except Exception:
            pass
    return families + ["DejaVu Sans"]   # bundled with matplotlib


def _shape(text: str) -> str:
    """Reshape + reorder Persian/Arabic text for correct RTL rendering."""
    if _HAS_SHAPING and text and not _MPL_NATIVE_RTL:
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text
    return text


def generate_charts(result: EvaluationResult, out_dir) -> List[Path]:
    """Generate all analytical charts; return the list of created image paths."""
    if not _HAS_MPL:
        return []
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    family = _register_persian_font()
    if family:
        # Per-glyph fallback: some Persian fonts (e.g. Windows' B Nazanin) have
        # no Latin letters, so English participant names need a second font.
        matplotlib.rcParams["font.family"] = [family] + _latin_fallback_families()
    matplotlib.rcParams["axes.unicode_minus"] = False

    paths: List[Path] = []
    bar = _total_scores_bar(result, out_dir / "chart_totals.png")
    if bar:
        paths.append(bar)
    heat = _criteria_heatmap(result, out_dir / "chart_heatmap.png")
    if heat:
        paths.append(heat)
    return paths


def _total_scores_bar(result: EvaluationResult, path: Path) -> Optional[Path]:
    """Horizontal bar chart of final scores per participant (ranked)."""
    ranked = result.ranked_evaluations()
    if not ranked:
        return None
    labels = [_shape(e.participant_id) for e in ranked][::-1]
    values = [e.total_score for e in ranked][::-1]

    fig, ax = plt.subplots(figsize=(8, max(2.5, 0.6 * len(labels) + 1)))
    bars = ax.barh(labels, values, color=_PALETTE[0])
    ax.set_xlim(0, 100)
    ax.set_xlabel(_shape("امتیاز نهایی (از ۱۰۰)"))
    ax.set_title(_shape("نمودار امتیاز نهایی هر شرکت‌کننده"))
    for b, v in zip(bars, values):
        ax.text(v + 1, b.get_y() + b.get_height() / 2, f"{v:.1f}",
                va="center", fontsize=9)
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _criteria_heatmap(result: EvaluationResult, path: Path) -> Optional[Path]:
    """Heatmap of raw 0-10 scores: participants (rows) x criteria (cols)."""
    ranked = result.ranked_evaluations()
    if not ranked:
        return None
    keys = [c.key for c in RUBRIC]
    crit_labels = [_shape(c.short_fa or c.name) for c in RUBRIC]
    part_labels = [_shape(e.participant_id) for e in ranked]

    matrix = [
        [(e.score_by_key(k).raw_score if e.score_by_key(k) else 0.0) for k in keys]
        for e in ranked
    ]

    fig, ax = plt.subplots(
        figsize=(max(8, 1.1 * len(keys)), max(2.5, 0.7 * len(part_labels) + 1.5))
    )
    im = ax.imshow(matrix, cmap="YlGnBu", vmin=0, vmax=10, aspect="auto")
    ax.set_xticks(range(len(crit_labels)))
    ax.set_xticklabels(crit_labels, rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(len(part_labels)))
    ax.set_yticklabels(part_labels, fontsize=9)
    ax.set_title(_shape("نقشه حرارتی امتیاز معیارها (۰ تا ۱۰)"))
    for i in range(len(part_labels)):
        for j in range(len(keys)):
            val = matrix[i][j]
            ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                    color="black" if val < 6 else "white", fontsize=8)
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.ax.set_ylabel(_shape("امتیاز خام"), rotation=90)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path

"""
Font discovery.

Locates the actual TTF files used to *render* the PDF (weasyprint) and charts
(matplotlib). The Word document only needs the font *names* (see config), but
the PDF must embed real files.

Requirement: Persian = "B Nazanin", Latin/English = "Times New Roman".
* If a real "B Nazanin" TTF is available (in ./fonts or the system) it is used.
* Otherwise a freely-redistributable Persian font (Vazirmatn) is used as a
  rendering fallback, so the PDF still shows correct Persian. The Word file
  still names "B Nazanin" as requested.
* "Times New Roman" is rendered with Liberation Serif, which is metric-identical
  to Times New Roman, when Times New Roman itself is not installed.
"""

from __future__ import annotations

import glob
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Extra directory (committed to the repo) where a user can drop real font files
# such as "B Nazanin.ttf" to get exact fonts in the PDF.
_REPO_FONTS = Path(__file__).resolve().parent.parent / "fonts"

# Windows keeps per-user fonts (where installers such as the B-font pack put
# "BNazanin.ttf") separately from the system fonts folder.
_WIN_FONT_DIRS: List[Path] = []
if sys.platform.startswith("win"):
    if os.environ.get("LOCALAPPDATA"):
        _WIN_FONT_DIRS.append(Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts")
    _WIN_FONT_DIRS.append(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts")


def _win(*names: str) -> List[str]:
    return [str(d / n) for n in names for d in _WIN_FONT_DIRS]


_PERSIAN_REGULAR_PATTERNS = [
    str(_REPO_FONTS / "*[Nn]azanin*.ttf"),
    "/usr/share/fonts/**/*[Bb] *[Nn]azanin*.ttf",
    "/usr/share/fonts/**/*[Nn]azanin*.ttf",
    *_win("*Nazanin*.ttf"),
    str(_REPO_FONTS / "*[Vv]azir*.ttf"),
    "/usr/share/fonts/**/Vazirmatn-Regular.ttf",
    "/usr/share/fonts/**/*[Vv]azir*[Rr]egular*.ttf",
    *_win("Vazirmatn-Regular.ttf", "*Vazir*.ttf"),
    *_win("tahoma.ttf"),             # always present on Windows; has Persian glyphs
]
_PERSIAN_BOLD_PATTERNS = [
    str(_REPO_FONTS / "*[Nn]azanin*[Bb]old*.ttf"),
    "/usr/share/fonts/**/*[Nn]azanin*[Bb]old*.ttf",
    *_win("*Nazanin*Bold*.ttf", "*Nazanin*Bd*.ttf"),
    str(_REPO_FONTS / "*[Vv]azir*[Bb]old*.ttf"),
    "/usr/share/fonts/**/Vazirmatn-Bold.ttf",
    *_win("Vazirmatn-Bold.ttf"),
]
_LATIN_REGULAR_PATTERNS = [
    "/usr/share/fonts/**/[Tt]imes*[Nn]ew*[Rr]oman*.ttf",
    "/usr/share/fonts/**/[Tt]imes*.ttf",
    *_win("times.ttf"),
    "/usr/share/fonts/**/LiberationSerif-Regular.ttf",
    "/usr/share/fonts/**/*[Ss]erif*[Rr]egular*.ttf",
]
_LATIN_BOLD_PATTERNS = [
    "/usr/share/fonts/**/[Tt]imes*[Bb]old*.ttf",
    *_win("timesbd.ttf"),
    "/usr/share/fonts/**/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/**/*[Ss]erif*[Bb]old*.ttf",
]


def _first_match(patterns) -> Optional[str]:
    for pat in patterns:
        hits = sorted(glob.glob(pat, recursive=True))
        if hits:
            return hits[0]
    return None


def persian_font_files() -> Tuple[Optional[str], Optional[str]]:
    """Return (regular, bold) TTF paths for the Persian font (or (None, None))."""
    reg = _first_match(_PERSIAN_REGULAR_PATTERNS)
    bold = _first_match(_PERSIAN_BOLD_PATTERNS) or reg
    return reg, bold


def latin_font_files() -> Tuple[Optional[str], Optional[str]]:
    """Return (regular, bold) TTF paths for the Latin (Times New Roman) font."""
    reg = _first_match(_LATIN_REGULAR_PATTERNS)
    bold = _first_match(_LATIN_BOLD_PATTERNS) or reg
    return reg, bold

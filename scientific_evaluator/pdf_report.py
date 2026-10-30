"""
PDF renderer (HTML->PDF via weasyprint, or a headless Edge/Chrome).

Renders the shared report blocks (see report_builder) into a right-to-left PDF.
weasyprint is used when it is installed and its native libraries load (Linux,
macOS). Otherwise - typically on Windows, where weasyprint needs a separate GTK
runtime - the same HTML is printed by a headless Microsoft Edge or Google
Chrome, which every Windows machine already has.

Fonts are embedded so Persian and Latin render correctly on any machine:

* Persian glyphs use the requested Persian font ("B Nazanin" if a TTF is
  available, otherwise a redistributable Persian fallback);
* Latin glyphs / ASCII digits use "Times New Roman" (Liberation Serif, which is
  metric-identical, when Times New Roman itself is absent).

The split is enforced with CSS ``@font-face`` ``unicode-range`` rules, so English
text is Times New Roman and Persian text is B Nazanin - matching the Word file.
"""

from __future__ import annotations

import base64
import html
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Union

from .config import SETTINGS
from .fonts import latin_font_files, persian_font_files
from .report_builder import Block, Bullets, Heading, Image, Para, Table, Title


def _file_uri(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return Path(path).resolve().as_uri()


def _font_data_uri(path: Optional[str]) -> Optional[str]:
    if not path or not Path(path).exists():
        return None
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f"data:font/ttf;base64,{data}"


# Everything except the Arabic-script blocks and the ZWNJ/ZWJ joiners. Used to
# keep the Latin face away from Persian text: the Windows Times New Roman has
# Arabic glyphs of its own, which would otherwise win over B Nazanin.
_LATIN_ONLY_RANGE = (
    "U+0000-05FF, U+0700-074F, U+0780-089F, U+0900-200B, U+200E-FB4F, "
    "U+FE00-FE6F, U+FF00-FFFF"
)


def _font_face(family: str, weight: str, uri: Optional[str],
               unicode_range: Optional[str] = None) -> str:
    if not uri:
        return ""
    rng = f" unicode-range: {unicode_range};" if unicode_range else ""
    return (
        f"@font-face {{ font-family: '{family}'; font-weight: {weight}; "
        f"font-style: normal; src: url('{uri}') format('truetype');{rng} }}"
    )


def _build_css(embed_fonts: bool = False, rtl: bool = True) -> str:
    """CSS with two font families.

    Latin font ('TNR' = Times New Roman / Liberation Serif) is listed first; it
    has no Persian glyphs, so the text engine falls back per-glyph to the Persian
    font ('BNazanin') for Persian codepoints. This gives correct complex-text
    shaping for Persian AND Times New Roman for English.

    ``embed_fonts`` (used for the browser engine) inlines the font files as data
    URIs and restricts the Latin face with ``unicode-range``, because Windows'
    Times New Roman does contain Arabic glyphs.
    """
    fa_reg, fa_bold = persian_font_files()
    la_reg, la_bold = latin_font_files()
    uri = _font_data_uri if embed_fonts else _file_uri
    latin_range = _LATIN_ONLY_RANGE if embed_fonts else None
    # Declare a bold face only when a real bold file exists; otherwise the text
    # engine synthesizes bold from the regular face instead of printing it flat.
    faces = "\n".join(filter(None, [
        _font_face("BNazanin", "normal", uri(fa_reg)),
        _font_face("BNazanin", "bold", uri(fa_bold)) if fa_bold != fa_reg else "",
        _font_face("TNR", "normal", uri(la_reg), latin_range),
        _font_face("TNR", "bold", uri(la_bold), latin_range) if la_bold != la_reg else "",
    ]))
    direction, align = ("rtl", "right") if rtl else ("ltr", "left")
    list_padding = "padding-right: 22px; padding-left: 0" if rtl else "padding-left: 22px"
    return f"""
{faces}
@page {{ size: A4; margin: 2cm 1.8cm; }}
* {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{
    margin: 0; direction: {direction}; text-align: {align};
    font-family: 'TNR', 'BNazanin', serif;
    font-size: {SETTINGS.base_font_size}pt; line-height: 1.6; color: #1a1a1a;
}}
h1.cover {{ text-align: center; color: #1F4E79; font-size: 26pt; margin: 0 0 6px; }}
p.sub {{ text-align: center; font-size: 13pt; font-weight: bold; margin: 2px 0; }}
h1 {{ color: #1F4E79; font-size: {SETTINGS.heading_font_size + 3}pt;
      border-bottom: 2px solid #D9E2F3; padding-bottom: 4px; margin-top: 22px; }}
h2 {{ color: #1F4E79; font-size: {SETTINGS.heading_font_size}pt; margin-top: 14px; }}
p {{ margin: 6px 0; text-align: justify; }}
ul {{ margin: 6px 0; {list_padding}; }}
li {{ margin: 3px 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0;
         font-size: {SETTINGS.base_font_size - 1}pt; }}
th, td {{ border: 1px solid #7f7f7f; padding: 5px 7px; text-align: {align};
          vertical-align: top; }}
th {{ background: #D9E2F3; color: #1F4E79; font-weight: bold; }}
tr:nth-child(even) td {{ background: #f4f7fb; }}
img {{ display: block; margin: 10px auto; max-width: 100%; }}
.cell-list {{ white-space: pre-line; }}
"""


def _esc(text) -> str:
    return html.escape(str(text))


def _cell_html(text) -> str:
    """Render a cell; convert newline-separated bullets to line breaks."""
    return _esc(text).replace("\n", "<br/>")


def _img_data_uri(path: str) -> Optional[str]:
    p = Path(path)
    if not p.exists():
        return None
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def _block_html(block: Block) -> str:
    if isinstance(block, Title):
        parts = [f"<h1 class='cover'>{_esc(block.text)}</h1>"]
        parts += [f"<p class='sub'>{_esc(s)}</p>" for s in block.subtitles]
        return "\n".join(parts)

    if isinstance(block, Heading):
        tag = "h1" if block.level <= 1 else "h2"
        return f"<{tag}>{_esc(block.text)}</{tag}>"

    if isinstance(block, Para):
        style = " style='font-weight:bold'" if block.bold else ""
        return f"<p{style}>{_esc(block.text)}</p>"

    if isinstance(block, Bullets):
        items = "".join(f"<li>{_esc(it)}</li>" for it in block.items if str(it).strip())
        return f"<ul>{items}</ul>" if items else ""

    if isinstance(block, Table):
        colgroup = ""
        if block.widths:
            colgroup = "<colgroup>" + "".join(
                f"<col style='width:{w*100:.1f}%'/>" for w in block.widths
            ) + "</colgroup>"
        thead = "<tr>" + "".join(f"<th>{_esc(h)}</th>" for h in block.headers) + "</tr>"
        body = ""
        for row in block.rows:
            body += "<tr>" + "".join(
                f"<td class='cell-list'>{_cell_html(v)}</td>" for v in row
            ) + "</tr>"
        return f"<table>{colgroup}<thead>{thead}</thead><tbody>{body}</tbody></table>"

    if isinstance(block, Image):
        uri = _img_data_uri(block.path)
        if not uri:
            return ""
        cap = f"<p class='sub'>{_esc(block.caption)}</p>" if block.caption else ""
        return f"<img src='{uri}'/>{cap}"

    return ""


def pdf_engine_error_message(exc: Exception) -> str:
    """Turn a WeasyPrint/GTK failure into an actionable instruction.

    The raw failure is a bare ``OSError: cannot load library
    'libgobject-2.0-0'``, which says nothing about what to install. PDF export
    needs WeasyPrint plus its native GTK/Pango/Cairo libraries; those are a
    separate, per-OS install.
    """
    text = str(exc)
    looks_like_missing_native_libs = (
        isinstance(exc, (OSError, ImportError))
        or "libgobject" in text
        or "libpango" in text
        or "cannot load library" in text
    )
    if not looks_like_missing_native_libs:
        return f"PDF export failed: {type(exc).__name__}: {exc}"

    if sys.platform.startswith("win"):
        how = (
            "On Windows the PDF is printed with Microsoft Edge or Google Chrome, "
            "and neither was found. Install one of them (or set PDF_BROWSER to the "
            "path of msedge.exe / chrome.exe)."
        )
    elif sys.platform == "darwin":
        how = "On macOS, run:  brew install pango cairo gdk-pixbuf libffi"
    else:
        how = (
            "On Linux, run:\n"
            "  sudo apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 "
            "libcairo2 libgdk-pixbuf-2.0-0"
        )
    first_line = text.splitlines()[0] if text else type(exc).__name__
    return (
        "PDF export needs WeasyPrint with its native GTK/Pango/Cairo libraries, "
        f"or Microsoft Edge / Google Chrome, and neither was found ({first_line}).\n"
        f"{how}\n"
        "Until then, choose \"Word only (.docx)\" — the Word report has the "
        "same content, and you can export a PDF from Word itself "
        "(File > Save As > PDF)."
    )


def find_chromium() -> Optional[str]:
    """Locate a Chromium-family browser (Edge / Chrome / Chromium), or None.

    ``PDF_BROWSER`` overrides the search with an explicit executable path.
    """
    explicit = os.environ.get("PDF_BROWSER", "").strip()
    if explicit:
        return explicit if Path(explicit).exists() else None
    candidates: List[Path] = []
    if sys.platform.startswith("win"):
        for base in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES"),
                     os.environ.get("LOCALAPPDATA")):
            if base:
                candidates += [
                    Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                    Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe",
                ]
    elif sys.platform == "darwin":
        candidates += [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
    for name in ("msedge", "google-chrome", "google-chrome-stable", "chromium",
                 "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def _wait_for_file(path: Path, timeout: float) -> bool:
    """Wait until ``path`` exists and its size has stopped changing."""
    deadline = time.monotonic() + timeout
    last = -1
    while time.monotonic() < deadline:
        if path.exists():
            size = path.stat().st_size
            if size > 0 and size == last:
                return True
            last = size
        time.sleep(0.5)
    return path.exists() and path.stat().st_size > 0


def _print_with_chromium(browser: str, document: str, out_path: Path) -> Path:
    """Print an HTML document to PDF with a headless Chromium-family browser."""
    # The browser may still hold its profile folder briefly after printing.
    with tempfile.TemporaryDirectory(prefix="sci_eval_pdf_", ignore_cleanup_errors=True) as tmp:
        html_path = Path(tmp) / "report.html"
        html_path.write_text(document, encoding="utf-8")
        target = Path(tmp) / "report.pdf"
        cmd = [
            browser, "--headless=new", "--disable-gpu", "--no-first-run",
            "--no-default-browser-check", "--disable-extensions",
            f"--user-data-dir={Path(tmp) / 'profile'}",   # never joins a running window
            "--no-pdf-header-footer", "--print-to-pdf-no-header",
            f"--print-to-pdf={target}", html_path.as_uri(),
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=180)
        # Edge on Windows hands the job to a background process and returns at
        # once, so the PDF can appear a few seconds after the command exits.
        if not _wait_for_file(target, timeout=90):
            detail = (proc.stderr or b"").decode("utf-8", "replace").strip()[-300:]
            raise RuntimeError(f"{Path(browser).name} did not produce a PDF. {detail}")
        shutil.copyfile(target, out_path)
    return out_path


def render_blocks_to_pdf(
    blocks: List[Block], out_path: Union[str, Path], rtl: bool = True
) -> Path:
    """Render report blocks to a PDF, right-to-left by default (weasyprint, else Edge/Chrome)."""
    body = "\n".join(_block_html(b) for b in blocks)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html_attrs = "lang='fa' dir='rtl'" if rtl else "lang='en' dir='ltr'"

    def document(embed_fonts: bool) -> str:
        return (
            f"<!DOCTYPE html><html {html_attrs}><head><meta charset='utf-8'>"
            f"<style>{_build_css(embed_fonts, rtl)}</style></head><body>{body}</body></html>"
        )

    try:
        from weasyprint import HTML
    except (ImportError, OSError):             # OSError: GTK/Pango libs missing
        browser = find_chromium()
        if not browser:
            raise
        return _print_with_chromium(browser, document(embed_fonts=True), out_path)

    HTML(string=document(embed_fonts=False)).write_pdf(str(out_path))
    return out_path

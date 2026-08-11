"""
PDF renderer (weasyprint / HTML->PDF).

Renders the shared report blocks (see report_builder) into a right-to-left PDF.
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
import sys
from pathlib import Path
from typing import List, Optional, Union

from .config import SETTINGS
from .fonts import latin_font_files, persian_font_files
from .report_builder import Block, Bullets, Heading, Image, Para, Table, Title


def _file_uri(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return Path(path).resolve().as_uri()


def _font_face(family: str, weight: str, uri: Optional[str]) -> str:
    if not uri:
        return ""
    return (
        f"@font-face {{ font-family: '{family}'; font-weight: {weight}; "
        f"font-style: normal; src: url('{uri}') format('truetype'); }}"
    )


def _build_css() -> str:
    """CSS with two font families.

    Latin font ('TNR' = Times New Roman / Liberation Serif) is listed first; it
    has no Persian glyphs, so the text engine falls back per-glyph to the Persian
    font ('BNazanin') for Persian codepoints. This gives correct complex-text
    shaping for Persian AND Times New Roman for English, with no fragile
    unicode-range splitting.
    """
    fa_reg, fa_bold = persian_font_files()
    la_reg, la_bold = latin_font_files()
    faces = "\n".join(filter(None, [
        _font_face("BNazanin", "normal", _file_uri(fa_reg)),
        _font_face("BNazanin", "bold", _file_uri(fa_bold)),
        _font_face("TNR", "normal", _file_uri(la_reg)),
        _font_face("TNR", "bold", _file_uri(la_bold)),
    ]))
    return f"""
{faces}
@page {{ size: A4; margin: 2cm 1.8cm; }}
* {{ box-sizing: border-box; }}
body {{
    direction: rtl; text-align: right;
    font-family: 'TNR', 'BNazanin', serif;
    font-size: {SETTINGS.base_font_size}pt; line-height: 1.6; color: #1a1a1a;
}}
h1.cover {{ text-align: center; color: #1F4E79; font-size: 26pt; margin: 0 0 6px; }}
p.sub {{ text-align: center; font-size: 13pt; font-weight: bold; margin: 2px 0; }}
h1 {{ color: #1F4E79; font-size: {SETTINGS.heading_font_size + 3}pt;
      border-bottom: 2px solid #D9E2F3; padding-bottom: 4px; margin-top: 22px; }}
h2 {{ color: #1F4E79; font-size: {SETTINGS.heading_font_size}pt; margin-top: 14px; }}
p {{ margin: 6px 0; text-align: justify; }}
ul {{ margin: 6px 0; padding-right: 22px; padding-left: 0; }}
li {{ margin: 3px 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0;
         font-size: {SETTINGS.base_font_size - 1}pt; }}
th, td {{ border: 1px solid #7f7f7f; padding: 5px 7px; text-align: right;
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
            "On Windows, install the GTK3 runtime, then restart your terminal:\n"
            "  https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases\n"
            "  (download the latest gtk3-runtime-...-ts-win64.exe and tick "
            "\"Set up PATH environment variable\")"
        )
    elif sys.platform == "darwin":
        how = "On macOS, run:  brew install pango cairo gdk-pixbuf libffi"
    else:
        how = (
            "On Linux, run:\n"
            "  sudo apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 "
            "libcairo2 libgdk-pixbuf-2.0-0"
        )
    return (
        "PDF export needs the native GTK/Pango/Cairo libraries used by "
        f"WeasyPrint, and they were not found ({text.splitlines()[0]}).\n"
        f"{how}\n"
        "Until then, choose \"Word only (.docx)\" — the Word report has the "
        "same content, and you can export a PDF from Word itself "
        "(File > Save As > PDF)."
    )


def render_blocks_to_pdf(blocks: List[Block], out_path: Union[str, Path]) -> Path:
    """Render report blocks to a Persian RTL PDF via weasyprint."""
    try:
        from weasyprint import HTML
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "weasyprint is required for PDF export. Install it (and its system "
            "libraries: libpango, libcairo, libgdk-pixbuf)."
        ) from exc

    body = "\n".join(_block_html(b) for b in blocks)
    document = (
        "<!DOCTYPE html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>"
        f"<style>{_build_css()}</style></head><body>{body}</body></html>"
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=document).write_pdf(str(out_path))
    return out_path

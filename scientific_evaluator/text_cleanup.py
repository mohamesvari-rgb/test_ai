"""
Clean up the Markdown and LaTeX that models (and some submissions) write.

Reports and the results page show plain formatted text, so markers such as
``**bold**`` or ``$Ni_3(THT)_2$`` must not reach the reader literally.
"""

from __future__ import annotations

import json
import re

_SUBSCRIPTS = str.maketrans("0123456789+-", "₀₁₂₃₄₅₆₇₈₉₊₋")
_SUPERSCRIPTS = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")

_LATEX_SYMBOLS = {
    r"\times": "×", r"\cdot": "·", r"\geq": "≥", r"\ge": "≥", r"\leq": "≤", r"\le": "≤",
    r"\approx": "≈", r"\sim": "~", r"\neq": "≠", r"\pm": "±", r"\to": "→",
    r"\rightarrow": "→", r"\Delta": "Δ", r"\alpha": "α", r"\beta": "β", r"\gamma": "γ",
    r"\mu": "μ", r"\pi": "π", r"\sigma": "σ", r"\kappa": "κ", r"\circ": "°",
    r"\%": "%", r"\,": " ", r"\;": " ", r"\ ": " ",
}
# Longest first, so \geq is not consumed by \ge.
_LATEX_RE = re.compile("|".join(
    re.escape(k) + (r"(?![A-Za-z])" if k[-1].isalpha() else "")
    for k in sorted(_LATEX_SYMBOLS, key=len, reverse=True)
))


def _script(body: str, table) -> str:
    # Only digits and signs have Unicode scripts; leave anything else readable.
    return body.translate(table) if re.fullmatch(r"[0-9+\-]+", body) else body


def clean_math(text: str) -> str:
    """Turn ``$...$`` / ``\\(...\\)`` LaTeX into readable plain text."""

    def convert(match: re.Match) -> str:
        s = match.group(1)
        s = re.sub(r"\\(?:text|mathrm|mathbf|ce)\{([^{}]*)\}", r"\1", s)
        s = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"\1/\2", s)
        s = _LATEX_RE.sub(lambda m: _LATEX_SYMBOLS[m.group(0)], s)
        s = re.sub(r"_\{([^{}]*)\}", lambda m: _script(m.group(1), _SUBSCRIPTS), s)
        s = re.sub(r"\^\{([^{}]*)\}", lambda m: _script(m.group(1), _SUPERSCRIPTS), s)
        s = re.sub(r"_([0-9])", lambda m: m.group(1).translate(_SUBSCRIPTS), s)
        s = re.sub(r"\^([0-9+\-])", lambda m: m.group(1).translate(_SUPERSCRIPTS), s)
        return s.replace("\\", "").strip()

    text = re.sub(r"\$\$?([^$\n]+?)\$\$?", convert, text)
    return re.sub(r"\\\((.+?)\\\)", convert, text)


def clean_inline(text: str) -> str:
    """Remove inline Markdown emphasis and code markers, and convert LaTeX."""
    text = clean_math(str(text))
    text = re.sub(r"^\s*#{1,6}\s+", "", text)
    text = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: m.group(1) or m.group(2), text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", text)
    return text.replace("`", "").strip()


# The synthesis prompt names its sections in English. Stronger models translate
# them; a local model may copy them, so a Persian report maps them afterwards.
_PERSIAN_SECTIONS = {
    "overview": "نمای کلی",
    "contribution of each answer": "سهم هر پاسخ",
    "integrated solution": "راه‌حل یکپارچه",
    "how the improvements are applied": "نحوه اعمال بهبودها",
    "how improvements are applied": "نحوه اعمال بهبودها",
    "how it meets the challenge": "انطباق با چالش",
    "feasibility and resources": "امکان‌سنجی و منابع",
    "risks and mitigations": "ریسک‌ها و کاهش آن‌ها",
    "expected impact": "اثر مورد انتظار",
}
_PERSIAN_TABLE_HEADERS = {
    "participant_id": "پاسخ",
    "answer": "پاسخ",
    "answer, approach or strength adopted": "رویکرد یا نقطه قوت به‌کاررفته",
    "approach or strength adopted": "رویکرد یا نقطه قوت به‌کاررفته",
    "where it is used in the solution": "محل استفاده در راه‌حل",
    "objective / expected output": "هدف / خروجی مورد انتظار",
    "objective": "هدف",
    "part of the solution that delivers it": "بخشی از راه‌حل که آن را تأمین می‌کند",
}


def localize_section_names(text: str) -> str:
    """Translate section headings and table headers left in English."""

    def heading(match: re.Match) -> str:
        persian = _PERSIAN_SECTIONS.get(match.group(3).strip(" *_:").lower())
        return f"{match.group(1)}{persian}" if persian else match.group(0)

    def header_row(match: re.Match) -> str:
        cells = match.group(0).strip().strip("|").split("|")
        return "| " + " | ".join(
            _PERSIAN_TABLE_HEADERS.get(c.strip(" *_").lower(), c.strip()) for c in cells
        ) + " |"

    text = re.sub(r"^(#{1,6}[ \t]+)(\d+[.)][ \t]*)?(.+?)[ \t]*$", heading, text, flags=re.M)
    # Only a row directly above a |---| separator is a header row.
    return re.sub(r"^[ \t]*\|.*\|[ \t]*$(?=\n[ \t]*\|[ \t:|-]+\|[ \t]*$)", header_row, text,
                  flags=re.M)


def unwrap_json_prose(text: str) -> str:
    """Some models answer a prose request with a JSON object; keep only the prose."""
    text = (text or "").strip()
    if not text.startswith("{"):
        return text
    try:
        data = json.loads(text)
    except ValueError:
        return text
    if not isinstance(data, dict):
        return text
    prose = [v.strip() for v in data.values() if isinstance(v, str) and v.strip()]
    return "\n\n".join(prose) or text

"""
Text preprocessing module.

Cleans raw text extracted from Word files into a normalized form suitable for
LLM evaluation, and packages it into a Submission object. Cleaning is
deliberately conservative: we normalize whitespace and strip artifacts but do
NOT remove technical content (equations, numbers, units) that matters for
scientific evaluation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Union

from .config import SETTINGS
from .models import Submission

# Common Word/PDF extraction artifacts to normalize.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_TRAILING_WS = re.compile(r"[ \t]+\n")


def clean_text(raw: str) -> str:
    """Normalize whitespace and strip control characters.

    Preserves paragraph breaks and all scientific content.
    """
    if not raw:
        return ""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS.sub("", text)
    # Normalize some unicode punctuation that trips up plain-text models.
    text = (
        text.replace("‘", "'").replace("’", "'")
        .replace("“", '"').replace("”", '"')
        .replace("–", "-").replace("—", "-")
        .replace(" ", " ")
    )
    text = _TRAILING_WS.sub("\n", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def _detect_title(text: str, fallback: str) -> str:
    """Heuristically pick a title: first non-empty, reasonably short line."""
    for line in text.splitlines():
        line = line.strip()
        if 3 <= len(line) <= 160:
            return line
    return fallback


def _truncate(text: str, limit: int) -> str:
    """Cap text length while keeping head and tail (both often carry signal)."""
    if len(text) <= limit:
        return text
    head = text[: int(limit * 0.7)]
    tail = text[-int(limit * 0.25):]
    return f"{head}\n\n[... content truncated for length ...]\n\n{tail}"


def build_submission(
    participant_id: str,
    source_path: Union[str, Path],
    raw_text: str,
    provided_title: str = "",
) -> Submission:
    """Clean raw text and wrap it in a Submission model."""
    cleaned = clean_text(raw_text)
    capped = _truncate(cleaned, SETTINGS.max_submission_chars)
    title = provided_title or _detect_title(cleaned, fallback=participant_id)
    return Submission(
        participant_id=participant_id,
        source_path=str(source_path),
        raw_text=capped,
        title=title,
        word_count=len(cleaned.split()),
        metadata={
            "char_count": len(cleaned),
            "truncated": len(cleaned) > SETTINGS.max_submission_chars,
        },
    )

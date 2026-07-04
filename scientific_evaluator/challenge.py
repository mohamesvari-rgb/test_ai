"""
Challenge input module.

Loads a Challenge definition from JSON/dict, or builds one interactively/in
code. Keeping challenge loading isolated means the same evaluation pipeline
works for any scientific domain by swapping the challenge file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union

from .models import Challenge


REQUIRED_FIELDS = ("title", "field", "background", "objectives")


def load_challenge(source: Union[str, Path, Dict[str, Any]]) -> Challenge:
    """Load a Challenge from a JSON file path or a dict.

    Parameters
    ----------
    source:
        Path to a ``.json`` file, or a dict with the challenge fields.

    Raises
    ------
    ValueError
        If required fields are missing.
    """
    if isinstance(source, (str, Path)):
        data = json.loads(Path(source).read_text(encoding="utf-8"))
    elif isinstance(source, dict):
        data = source
    else:
        raise TypeError(f"Unsupported challenge source type: {type(source)!r}")

    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        raise ValueError(
            f"Challenge definition is missing required field(s): {', '.join(missing)}"
        )

    return Challenge(
        title=data["title"],
        field=data["field"],
        background=data["background"],
        objectives=list(data["objectives"]),
        constraints=list(data.get("constraints", [])),
        expected_outputs=list(data.get("expected_outputs", [])),
        evaluation_notes=data.get("evaluation_notes", ""),
    )


def save_challenge(challenge: Challenge, path: Union[str, Path]) -> None:
    """Persist a Challenge to a JSON file (useful for reproducibility)."""
    from dataclasses import asdict

    Path(path).write_text(
        json.dumps(asdict(challenge), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

"""
Scoring engine.

Turns raw per-criterion scores (0-10) produced by the evaluation engine into
weighted CriterionScore objects and a final /100 total. The scoring math lives
here and nowhere else, so the scoring system stays transparent and auditable.

Final score formula (out of 100):

    total = sum_over_criteria( (raw_score / 10) * max_points ) - penalty

where the max_points weights are defined in config.RUBRIC and sum to 100.
"""

from __future__ import annotations

from typing import Dict, List

from .config import RUBRIC, SETTINGS
from .models import CriterionScore


def _coerce_score(value, key: str) -> float:
    """Validate/clamp a raw score into [0, 10]."""
    try:
        score = float(value)
    except (TypeError, ValueError):
        if SETTINGS.strict_scores:
            raise ValueError(f"Non-numeric score for '{key}': {value!r}")
        return 0.0
    if score < 0 or score > 10:
        if SETTINGS.strict_scores:
            raise ValueError(f"Score for '{key}' out of range 0-10: {score}")
        score = max(0.0, min(10.0, score))
    return score


def build_criterion_scores(raw: Dict[str, dict]) -> List[CriterionScore]:
    """Map the LLM's raw criterion dict to weighted CriterionScore objects.

    Parameters
    ----------
    raw:
        ``{criterion_key: {"raw_score": float, "justification": str}}``
        as returned by the evaluation engine. Missing criteria default to 0.
    """
    scores: List[CriterionScore] = []
    for c in RUBRIC:
        entry = raw.get(c.key, {}) or {}
        raw_score = _coerce_score(entry.get("raw_score", 0), c.key)
        scores.append(
            CriterionScore(
                key=c.key,
                name=c.name,
                raw_score=raw_score,
                max_points=c.max_points,
                justification=str(entry.get("justification", "")).strip(),
            )
        )
    return scores


def compute_total(scores: List[CriterionScore], penalty: float = 0.0) -> float:
    """Compute the final /100 score from weighted criterion scores."""
    base = sum(s.weighted_points for s in scores)
    return max(0.0, min(100.0, base - penalty))


def integrity_penalty(flags: List[str]) -> float:
    """Convert integrity flags into a bounded point penalty.

    Each flag costs points, capped so a single evaluation cannot be driven
    arbitrarily negative. Tune here as policy changes.
    """
    if not flags:
        return 0.0
    per_flag = 5.0
    return min(len(flags) * per_flag, 25.0)

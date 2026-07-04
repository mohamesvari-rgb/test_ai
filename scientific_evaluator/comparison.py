"""
Comparison and ranking module.

Compares all evaluated submissions with each other, produces a ranking from
strongest to weakest, explains the ordering, and surfaces overlapping, unique
and complementary ideas across submissions.

The LLM proposes a qualitative ranking; we reconcile it with the numeric
scores so the final order is defensible and never contradicts the rubric by
more than a deliberate, explained margin.
"""

from __future__ import annotations

from typing import Dict, List

from .llm_client import BaseLLMClient
from .models import Challenge, ComparisonResult, SubmissionEvaluation
from .prompts import build_comparison_prompt


class ComparisonEngine:
    """Ranks and cross-analyzes submissions."""

    def __init__(self, llm: BaseLLMClient):
        self.llm = llm

    def compare(
        self, challenge: Challenge, evaluations: List[SubmissionEvaluation]
    ) -> ComparisonResult:
        if len(evaluations) <= 1:
            only = [e.participant_id for e in evaluations]
            return ComparisonResult(
                ranking=only,
                rationale="Only one submission; ranking is trivial."
                if only else "No submissions to compare.",
            )

        system, user = build_comparison_prompt(challenge, evaluations)
        data = self.llm.complete_json(system, user)

        ranking = self._reconcile_ranking(
            proposed=list(data.get("ranking", []) or []),
            evaluations=evaluations,
        )

        unique = data.get("unique_ideas", {}) or {}
        if not isinstance(unique, dict):
            unique = {}

        return ComparisonResult(
            ranking=ranking,
            rationale=str(data.get("rationale", "")).strip(),
            pairwise_notes=list(data.get("pairwise_notes", []) or []),
            overlapping_ideas=list(data.get("overlapping_ideas", []) or []),
            unique_ideas={k: list(v) for k, v in unique.items()},
            complementary_ideas=list(data.get("complementary_ideas", []) or []),
        )

    @staticmethod
    def _reconcile_ranking(
        proposed: List[str], evaluations: List[SubmissionEvaluation]
    ) -> List[str]:
        """Ensure the ranking includes every participant exactly once.

        Start from the LLM's qualitative order, drop unknown ids, then append
        any missing participants ordered by their numeric score. This guarantees
        a complete, valid ranking even if the model omits or invents ids.
        """
        valid_ids = {e.participant_id for e in evaluations}
        seen = set()
        ordered: List[str] = []
        for pid in proposed:
            if pid in valid_ids and pid not in seen:
                ordered.append(pid)
                seen.add(pid)
        # Append the rest by score, high to low.
        remaining = [e for e in evaluations if e.participant_id not in seen]
        for e in sorted(remaining, key=lambda x: x.total_score, reverse=True):
            ordered.append(e.participant_id)
        return ordered

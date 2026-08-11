"""
Improvement module.

For each key idea in a submission, proposes a set of concrete improvement
solutions that make the idea more effective at solving the challenge.

Ideas are drawn from the submission's InnovationProfile (main innovations,
strong technical ideas, unique advantages), so improvement builds directly on
what the participant actually proposed - not on invented content.
"""

from __future__ import annotations

from typing import List

from .llm_client import BaseLLMClient
from .models import (
    Challenge,
    IdeaImprovement,
    InnovationProfile,
    Submission,
    SubmissionEvaluation,
)
from .prompts import build_improvement_prompt


def _collect_ideas(profile: InnovationProfile, limit: int = 8) -> List[str]:
    """Gather the distinct key ideas of a submission, de-duplicated, capped."""
    ordered = (
        profile.main_innovations
        + profile.strong_technical_ideas
        + profile.unique_advantages
        + profile.creative_aspects
    )
    seen = set()
    ideas: List[str] = []
    for idea in ordered:
        norm = idea.strip().lower()
        if idea.strip() and norm not in seen:
            seen.add(norm)
            ideas.append(idea.strip())
        if len(ideas) >= limit:
            break
    return ideas


class ImprovementEngine:
    """Generates per-idea improvement solutions for a submission."""

    def __init__(self, llm: BaseLLMClient):
        self.llm = llm

    def improve(
        self,
        challenge: Challenge,
        submission: Submission,
        evaluation: SubmissionEvaluation,
    ) -> List[IdeaImprovement]:
        ideas = _collect_ideas(evaluation.innovation)
        if not ideas:
            return []

        system, user = build_improvement_prompt(challenge, submission, ideas)
        data = self.llm.complete_json(system, user)

        results: List[IdeaImprovement] = []
        for entry in data.get("idea_improvements", []) or []:
            if not isinstance(entry, dict):
                continue
            results.append(
                IdeaImprovement(
                    idea=str(entry.get("idea", "")).strip(),
                    source_participant=submission.participant_id,
                    why_it_matters=str(entry.get("why_it_matters", "")).strip(),
                    improvements=[
                        str(x).strip()
                        for x in (entry.get("improvements", []) or [])
                        if str(x).strip()
                    ],
                    expected_effect=str(entry.get("expected_effect", "")).strip(),
                )
            )
        return results

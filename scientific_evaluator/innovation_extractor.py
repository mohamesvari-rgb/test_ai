"""
Innovation extraction module.

Separately extracts the innovation/creativity profile of a submission:
main innovations, creative aspects, unique advantages, strong technical ideas,
potential research contributions, and weaknesses/missing parts.

This runs as its own LLM pass (distinct from scoring) so novelty is analyzed
explicitly rather than being an implicit by-product of the score.
"""

from __future__ import annotations

from .llm_client import BaseLLMClient
from .models import Challenge, InnovationProfile, Submission
from .prompts import build_innovation_prompt


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]


class InnovationExtractor:
    """Extracts a structured InnovationProfile from a submission."""

    def __init__(self, llm: BaseLLMClient):
        self.llm = llm

    def extract(self, challenge: Challenge, submission: Submission) -> InnovationProfile:
        system, user = build_innovation_prompt(challenge, submission)
        data = self.llm.complete_json(system, user)
        return InnovationProfile(
            main_innovations=_as_list(data.get("main_innovations")),
            creative_aspects=_as_list(data.get("creative_aspects")),
            unique_advantages=_as_list(data.get("unique_advantages")),
            strong_technical_ideas=_as_list(data.get("strong_technical_ideas")),
            potential_research_contributions=_as_list(
                data.get("potential_research_contributions")
            ),
            weaknesses_or_missing_parts=_as_list(
                data.get("weaknesses_or_missing_parts")
            ),
        )

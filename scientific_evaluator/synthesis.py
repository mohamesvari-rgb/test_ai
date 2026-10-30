"""
Synthesis module.

Generates two free-form outputs that sit on top of the structured evaluation:

* ``synthesize_solution`` - an improved solution that fuses the best, most
  feasible and most novel ideas across all submissions while fixing their
  common weaknesses.
* ``final_recommendation`` - a concise, decision-oriented recommendation for
  the challenge owner.
"""

from __future__ import annotations

from typing import List

from .config import SETTINGS
from .llm_client import BaseLLMClient
from .models import Challenge, ComparisonResult, SubmissionEvaluation
from .prompts import build_recommendation_prompt, build_synthesis_prompt
from .text_cleanup import localize_section_names, unwrap_json_prose


class SynthesisEngine:
    """Produces the synthesized solution and final recommendation."""

    def __init__(self, llm: BaseLLMClient):
        self.llm = llm

    def synthesize_solution(
        self,
        challenge: Challenge,
        evaluations: List[SubmissionEvaluation],
        comparison: ComparisonResult,
    ) -> str:
        system, user = build_synthesis_prompt(challenge, evaluations, comparison)
        solution = self.llm.complete_text(system, user).strip()
        if SETTINGS.report_language.lower().startswith("persian"):
            solution = localize_section_names(solution)
        return solution

    def final_recommendation(
        self,
        challenge: Challenge,
        evaluations: List[SubmissionEvaluation],
        comparison: ComparisonResult,
    ) -> str:
        system, user = build_recommendation_prompt(challenge, evaluations, comparison)
        return unwrap_json_prose(self.llm.complete_text(system, user))

"""
Evaluation engine.

Coordinates the LLM to evaluate a single submission: it asks for per-criterion
scores, feeds them to the scoring engine, and returns a fully-populated
SubmissionEvaluation (scores + strengths/weaknesses + integrity handling).

The innovation profile is filled in by the innovation_extractor module and
attached by the orchestrator, keeping each engine single-purpose.
"""

from __future__ import annotations

from .llm_client import BaseLLMClient
from .models import Challenge, Submission, SubmissionEvaluation
from .prompts import build_scoring_prompt
from .scoring_engine import build_criterion_scores, integrity_penalty


class EvaluationEngine:
    """Scores submissions criterion-by-criterion via an LLM."""

    def __init__(self, llm: BaseLLMClient):
        self.llm = llm

    def evaluate(self, challenge: Challenge, submission: Submission) -> SubmissionEvaluation:
        system, user = build_scoring_prompt(challenge, submission)
        data = self.llm.complete_json(system, user)

        raw_scores = data.get("criterion_scores", {}) or {}
        criterion_scores = build_criterion_scores(raw_scores)

        flags = list(data.get("integrity_flags", []) or [])
        penalty = integrity_penalty(flags)

        return SubmissionEvaluation(
            participant_id=submission.participant_id,
            title=submission.title,
            criterion_scores=criterion_scores,
            summary=str(data.get("summary", "")).strip(),
            strengths=list(data.get("strengths", []) or []),
            weaknesses=list(data.get("weaknesses", []) or []),
            integrity_flags=flags,
            penalty=penalty,
        )

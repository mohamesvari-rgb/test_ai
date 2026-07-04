"""
Scientific Evaluation Agent
===========================

A modular AI agent that evaluates scientific ideas and solutions submitted by
participants in response to a defined challenge.

Pipeline:
    Challenge definition -> Read Word submissions -> Clean text ->
    Per-criterion evaluation -> Weighted scoring -> Innovation extraction ->
    Comparison & ranking -> Synthesis -> Word report.

Public entry point:
    >>> from scientific_evaluator import ScientificEvaluationAgent
    >>> agent = ScientificEvaluationAgent(challenge, llm_client)
    >>> result = agent.run("submissions/")
    >>> agent.export_report(result, "report.docx")
"""

from .agent import ScientificEvaluationAgent
from .models import (
    Challenge,
    Submission,
    CriterionScore,
    SubmissionEvaluation,
    InnovationProfile,
    EvaluationResult,
)
from .config import RUBRIC, RubricCriterion

__all__ = [
    "ScientificEvaluationAgent",
    "Challenge",
    "Submission",
    "CriterionScore",
    "SubmissionEvaluation",
    "InnovationProfile",
    "EvaluationResult",
    "RUBRIC",
    "RubricCriterion",
]

__version__ = "1.0.0"

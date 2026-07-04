"""
Orchestrator: ScientificEvaluationAgent.

Wires the modules together into the end-to-end pipeline:

    challenge + submissions folder
        -> read Word files            (document_reader)
        -> clean & package text       (preprocessing)
        -> score each submission      (evaluation_engine + scoring_engine)
        -> extract innovation profile (innovation_extractor)
        -> compare & rank             (comparison)
        -> synthesize + recommend     (synthesis)
        -> EvaluationResult
        -> export report              (report_generator)

The agent is deliberately thin: all real logic lives in the single-purpose
modules, so behavior can be tested and swapped independently.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, List, Optional, Union

from .challenge import load_challenge
from .comparison import ComparisonEngine
from .document_reader import discover_submission_files, read_docx
from .evaluation_engine import EvaluationEngine
from .innovation_extractor import InnovationExtractor
from .llm_client import BaseLLMClient
from .models import Challenge, EvaluationResult, Submission, SubmissionEvaluation
from .preprocessing import build_submission
from .report_generator import MarkdownReportGenerator, WordReportGenerator
from .synthesis import SynthesisEngine

logger = logging.getLogger("scientific_evaluator")


class ScientificEvaluationAgent:
    """End-to-end scientific evaluation agent."""

    def __init__(
        self,
        challenge: Union[Challenge, str, Path, dict],
        llm: BaseLLMClient,
        progress: Optional[Callable[[str], None]] = None,
    ):
        self.challenge = (
            challenge if isinstance(challenge, Challenge) else load_challenge(challenge)
        )
        self.llm = llm
        self._progress = progress or (lambda msg: logger.info(msg))

        # Engines
        self.evaluator = EvaluationEngine(llm)
        self.innovation = InnovationExtractor(llm)
        self.comparator = ComparisonEngine(llm)
        self.synthesizer = SynthesisEngine(llm)

    # -- ingestion ----------------------------------------------------------
    def load_submissions(self, folder: Union[str, Path]) -> List[Submission]:
        """Read and preprocess every .docx in a folder into Submissions."""
        files = discover_submission_files(folder)
        if not files:
            raise ValueError(f"No .docx submissions found in {folder}")
        submissions: List[Submission] = []
        for path in files:
            self._progress(f"Reading {path.name}")
            raw = read_docx(path)
            submissions.append(
                build_submission(
                    participant_id=path.stem,
                    source_path=path,
                    raw_text=raw,
                )
            )
        return submissions

    # -- core pipeline ------------------------------------------------------
    def evaluate_submission(self, submission: Submission) -> SubmissionEvaluation:
        """Score one submission and attach its innovation profile."""
        self._progress(f"Evaluating {submission.participant_id}")
        evaluation = self.evaluator.evaluate(self.challenge, submission)
        evaluation.innovation = self.innovation.extract(self.challenge, submission)
        return evaluation

    def run(
        self,
        submissions: Union[str, Path, List[Submission]],
    ) -> EvaluationResult:
        """Run the full evaluation over a folder path or a list of Submissions."""
        if isinstance(submissions, (str, Path)):
            submissions = self.load_submissions(submissions)
        if not submissions:
            raise ValueError("No submissions to evaluate.")

        evaluations = [self.evaluate_submission(s) for s in submissions]

        self._progress("Comparing and ranking submissions")
        comparison = self.comparator.compare(self.challenge, evaluations)

        self._progress("Synthesizing improved solution")
        synthesized = self.synthesizer.synthesize_solution(
            self.challenge, evaluations, comparison
        )
        self._progress("Writing final recommendation")
        recommendation = self.synthesizer.final_recommendation(
            self.challenge, evaluations, comparison
        )

        return EvaluationResult(
            challenge=self.challenge,
            evaluations=evaluations,
            comparison=comparison,
            synthesized_solution=synthesized,
            final_recommendation=recommendation,
        )

    # -- output -------------------------------------------------------------
    def export_report(
        self,
        result: EvaluationResult,
        out_path: Union[str, Path],
        fmt: str = "docx",
    ) -> Path:
        """Export the evaluation result as a Word (.docx) or Markdown (.md) file."""
        fmt = fmt.lower()
        if fmt in ("docx", "word"):
            return WordReportGenerator().generate(result, out_path)
        if fmt in ("md", "markdown"):
            return MarkdownReportGenerator().generate(result, out_path)
        raise ValueError(f"Unsupported report format: {fmt!r} (use 'docx' or 'md')")

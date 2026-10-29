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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, List, Optional, Union

from .challenge import load_challenge
from .comparison import ComparisonEngine
from .config import SETTINGS
from .document_reader import discover_submission_files, read_docx
from .evaluation_engine import EvaluationEngine
from .improvement import ImprovementEngine
from .innovation_extractor import InnovationExtractor
from .llm_client import BaseLLMClient
from .models import Challenge, EvaluationResult, Submission, SubmissionEvaluation
from .persian_report import render_blocks_to_docx
from .pdf_report import pdf_engine_error_message, render_blocks_to_pdf
from .preprocessing import build_submission
from .report_builder import build_report_blocks
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
        self.improver = ImprovementEngine(llm)
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
        """Score a submission, extract its innovation profile, and propose
        improvement solutions for each of its key ideas."""
        self._progress(f"Evaluating {submission.participant_id}")
        evaluation = self.evaluator.evaluate(self.challenge, submission)
        evaluation.innovation = self.innovation.extract(self.challenge, submission)
        self._progress(f"Proposing improvements for {submission.participant_id}")
        evaluation.idea_improvements = self.improver.improve(
            self.challenge, submission, evaluation
        )
        self._progress(f"Finished {submission.participant_id}")
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

        # Submissions are independent, so online backends evaluate several at
        # once; a local model (max_parallel = 1) keeps them sequential.
        workers = max(1, min(len(submissions), getattr(self.llm, "max_parallel", 1)))
        if workers == 1:
            evaluations = [self.evaluate_submission(s) for s in submissions]
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                evaluations = list(pool.map(self.evaluate_submission, submissions))

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
        fmt: str = "both",
    ) -> List[Path]:
        """Export the evaluation report.

        Formats:
          * ``docx`` - Word document (Persian RTL when report_language is Persian).
          * ``pdf``  - PDF (rendered from the Word document via LibreOffice).
          * ``both`` - both .docx and .pdf (default).
          * ``md``   - Markdown (English layout; quick review/diffing).

        Returns the list of files written.
        """
        import tempfile

        from . import charts as charts_mod

        fmt = fmt.lower()
        out_path = Path(out_path)
        persian = SETTINGS.report_language.lower().startswith("persian")

        if fmt in ("md", "markdown"):
            return [MarkdownReportGenerator().generate(result, out_path)]

        if fmt not in ("docx", "word", "pdf", "both"):
            raise ValueError(
                f"Unsupported report format: {fmt!r} (use 'docx', 'pdf', 'both', 'md')"
            )

        # English mode keeps the original Word/Markdown generators.
        if not persian:
            docx_path = out_path.with_suffix(".docx")
            WordReportGenerator().generate(result, docx_path)
            if fmt in ("docx", "word"):
                return [docx_path]
            raise ValueError(
                "PDF output is currently supported only for the Persian report. "
                "Use fmt='docx' or fmt='md' in English mode."
            )

        # Persian mode: build charts + blocks ONCE, render docx and/or pdf from
        # the same blocks so the two outputs are identical.
        written: List[Path] = []
        with tempfile.TemporaryDirectory() as chart_dir:
            chart_paths = (
                charts_mod.generate_charts(result, chart_dir)
                if charts_mod.charts_available() else []
            )
            blocks = build_report_blocks(result, chart_paths)

            if fmt in ("docx", "word", "both"):
                self._progress("Rendering Persian Word report (.docx)")
                written.append(
                    render_blocks_to_docx(blocks, out_path.with_suffix(".docx"))
                )
            if fmt in ("pdf", "both"):
                self._progress("Rendering Persian PDF report (.pdf)")
                try:
                    written.append(
                        render_blocks_to_pdf(blocks, out_path.with_suffix(".pdf"))
                    )
                except Exception as exc:  # noqa: BLE001
                    # The Word file is already written and is the primary
                    # deliverable. Losing the whole run because the PDF engine
                    # is not installed would be the wrong trade-off, so degrade
                    # to Word-only and explain how to fix the PDF path.
                    message = pdf_engine_error_message(exc)
                    if fmt == "pdf":
                        raise RuntimeError(message) from exc
                    self._progress(f"WARNING: {message}")
                    self._progress("Continuing with the Word (.docx) report only.")
        return written

"""
Background job manager for the web GUI.

An evaluation run takes minutes (several LLM calls per submission), so the web
request cannot block on it. Jobs run on a worker thread; the browser polls
``/api/status/<job_id>`` for live progress messages and, when finished, the list
of downloadable report files.

Jobs are serialized behind a single lock: the agent mutates process-wide
settings (report language/model), so running two evaluations concurrently could
mix them up. For a local single-user tool, one-at-a-time is the correct
trade-off.
"""

from __future__ import annotations

import shutil
import threading
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Only one evaluation at a time (see module docstring).
_RUN_LOCK = threading.Lock()


@dataclass
class Job:
    """State of a single evaluation run."""

    id: str
    status: str = "queued"          # queued | running | done | error
    messages: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)   # basenames of outputs
    ranking: List[Dict[str, Any]] = field(default_factory=list)
    error: str = ""
    work_dir: Optional[Path] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def log(self, message: str) -> None:
        self.messages.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "messages": self.messages,
            "files": self.files,
            "ranking": self.ranking,
            "error": self.error,
        }


class JobStore:
    """Thread-safe in-memory registry of jobs."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self) -> Job:
        job_id = uuid.uuid4().hex[:12]
        work_dir = self.root / job_id
        (work_dir / "submissions").mkdir(parents=True, exist_ok=True)
        (work_dir / "output").mkdir(parents=True, exist_ok=True)
        job = Job(id=job_id, work_dir=work_dir)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def cleanup(self, job_id: str) -> None:
        """Delete a job's working directory (uploads + generated reports)."""
        job = self.get(job_id)
        if job and job.work_dir and job.work_dir.exists():
            shutil.rmtree(job.work_dir, ignore_errors=True)
        with self._lock:
            self._jobs.pop(job_id, None)


def run_evaluation(job: Job, challenge: dict, options: dict) -> None:
    """Execute the evaluation for a job (called on a worker thread)."""
    from scientific_evaluator.agent import ScientificEvaluationAgent
    from scientific_evaluator.config import SETTINGS
    from scientific_evaluator.llm_client import AnthropicLLMClient, MockLLMClient

    with _RUN_LOCK:
        try:
            job.status = "running"
            job.log("Starting evaluation…")

            # Apply per-run settings.
            SETTINGS.report_language = options.get("language") or "Persian"
            if options.get("model"):
                SETTINGS.model = options["model"]

            # Build the LLM backend.
            if options.get("mock"):
                job.log("Using the offline mock backend (placeholder analysis).")
                llm = MockLLMClient()
            else:
                llm = AnthropicLLMClient(
                    api_key=options.get("api_key") or None,
                    model=options.get("model") or None,
                )

            agent = ScientificEvaluationAgent(challenge, llm, progress=job.log)

            sub_dir = job.work_dir / "submissions"
            result = agent.run(sub_dir)

            out_base = job.work_dir / "output" / "report"
            written = agent.export_report(
                result, out_base, fmt=options.get("format", "both")
            )
            job.files = [Path(p).name for p in written]

            job.ranking = [
                {
                    "participant_id": e.participant_id,
                    "title": e.title,
                    "score": round(e.total_score, 1),
                }
                for e in result.ranked_evaluations()
            ]

            # Always dump raw JSON alongside the report for manual review.
            import json
            json_path = job.work_dir / "output" / "result.json"
            json_path.write_text(
                json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            job.files.append(json_path.name)

            job.log("Done.")
            job.status = "done"

        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            job.status = "error"
            job.error = f"{type(exc).__name__}: {exc}"
            job.log(f"ERROR: {job.error}")
            traceback.print_exc()


def start_evaluation(job: Job, challenge: dict, options: dict) -> None:
    """Kick off the evaluation on a daemon thread."""
    thread = threading.Thread(
        target=run_evaluation, args=(job, challenge, options), daemon=True
    )
    thread.start()

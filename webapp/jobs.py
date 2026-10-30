"""
Background job manager for the web GUI.

An evaluation run takes minutes (several LLM calls per submission), so the web
request cannot block on it. Jobs run on a worker thread; the browser polls
``/api/status/<job_id>`` for live progress messages and, when finished, the
results summary and the list of downloadable report files.

Each finished job is saved as ``job.json`` in its work directory, so past runs
(and their reports) are still available after the app restarts - handy for a
demo where a long evaluation was run beforehand.

Jobs are serialized behind a single lock: the agent mutates process-wide
settings (report language), so running two evaluations concurrently could mix
them up. For a local single-user tool, one-at-a-time is the correct trade-off.
"""

from __future__ import annotations

import json
import shutil
import threading
import traceback
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Only one evaluation at a time (see module docstring).
_RUN_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


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
    created_at: str = field(default_factory=_now)
    started_at: str = ""
    finished_at: str = ""
    title: str = ""                 # challenge title
    provider: str = ""              # provider key (avalai, ollama, mock, ...)
    engine: str = ""                # "provider · model" label
    participants: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def log(self, message: str) -> None:
        self.messages.append(message)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("work_dir", None)
        return data

    def save(self) -> None:
        """Persist the job (never includes the API key: it is not stored here)."""
        if self.work_dir and self.work_dir.exists():
            (self.work_dir / "job.json").write_text(
                json.dumps(self.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8"
            )

    @classmethod
    def load(cls, path: Path) -> "Job":
        data = json.loads(path.read_text(encoding="utf-8"))
        known = {f.name for f in fields(cls)} - {"work_dir"}
        job = cls(**{k: v for k, v in data.items() if k in known})
        job.work_dir = path.parent
        if job.status in ("queued", "running"):
            job.status = "error"
            job.error = "Interrupted: the app was closed while this evaluation was running."
        return job


class JobStore:
    """Thread-safe registry of jobs, backed by the work directory."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        for path in self.root.glob("*/job.json"):
            try:
                job = Job.load(path)
                self._jobs[job.id] = job
            except Exception:  # noqa: BLE001 - a corrupt record must not block startup
                continue

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

    def recent(self, limit: int = 30) -> List[Job]:
        with self._lock:
            jobs = list(self._jobs.values())
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)[:limit]

    def cleanup(self, job_id: str) -> None:
        """Delete a job's working directory (uploads + generated reports)."""
        job = self.get(job_id)
        if job and job.work_dir and job.work_dir.exists():
            shutil.rmtree(job.work_dir, ignore_errors=True)
        with self._lock:
            self._jobs.pop(job_id, None)


def build_summary(result) -> Dict[str, Any]:
    """Compact, JSON-friendly view of a result for the results dashboard."""
    from scientific_evaluator.config import RUBRIC
    from scientific_evaluator.text_cleanup import clean_inline, clean_math

    def items(values, limit):
        return [clean_inline(v) for v in (values or [])[:limit]]

    comparison = result.comparison
    participants = []
    for rank, e in enumerate(result.ranked_evaluations(), start=1):
        participants.append({
            "rank": rank,
            "participant_id": e.participant_id,
            "title": clean_inline(e.title),
            "score": round(e.total_score, 1),
            "penalty": e.penalty,
            "scores": {c.key: c.raw_score for c in e.criterion_scores},
            "summary": clean_inline(e.summary),
            "strengths": items(e.strengths, 5),
            "weaknesses": items(e.weaknesses, 5),
            "innovations": items(e.innovation.main_innovations, 4),
            "salient": items(comparison.salient_points.get(e.participant_id), 4),
            "distinctive": items(comparison.distinctive_points.get(e.participant_id), 4),
        })
    return {
        "criteria": [
            {"key": c.key, "name": c.name, "name_fa": c.name_fa,
             "short_fa": c.short_fa, "weight": c.max_points}
            for c in RUBRIC
        ],
        "participants": participants,
        "rationale": clean_inline(comparison.rationale),
        "overlapping_ideas": items(comparison.overlapping_ideas, 6),
        "complementary_ideas": items(comparison.complementary_ideas, 6),
        # Keep the Markdown structure; the page renders headings, lists and tables.
        "synthesized_solution": clean_math(result.synthesized_solution),
        "final_recommendation": clean_math(result.final_recommendation),
    }


def run_evaluation(job: Job, challenge: dict, options: dict) -> None:
    """Execute the evaluation for a job (called on a worker thread)."""
    from scientific_evaluator.agent import ScientificEvaluationAgent
    from scientific_evaluator.config import SETTINGS
    from scientific_evaluator.llm_client import build_llm_client
    from scientific_evaluator.text_cleanup import clean_inline

    with _RUN_LOCK:
        try:
            job.status = "running"
            job.started_at = _now()
            job.log("Starting evaluation…")

            # Apply per-run settings.
            SETTINGS.report_language = options.get("language") or "Persian"

            # Build the LLM backend.
            llm = build_llm_client(
                options.get("provider"),
                api_key=options.get("api_key") or None,
                model=options.get("model") or None,
                base_url=options.get("base_url") or None,
            )
            job.engine = llm.description
            job.log(f"Engine: {llm.description}")
            if options.get("provider") == "mock":
                job.log("Using the offline mock backend (placeholder analysis).")

            agent = ScientificEvaluationAgent(challenge, llm, progress=job.log)

            sub_dir = job.work_dir / "submissions"
            result = agent.run(sub_dir)

            job.ranking = [
                {
                    "participant_id": e.participant_id,
                    "title": clean_inline(e.title),
                    "score": round(e.total_score, 1),
                }
                for e in result.ranked_evaluations()
            ]
            job.summary = build_summary(result)

            # Always dump raw JSON alongside the report for manual review.
            json_path = job.work_dir / "output" / "result.json"
            json_path.write_text(
                json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            # The evaluation may have taken an hour offline, so a failed report
            # must not lose it: the results stay available either way.
            try:
                written = agent.export_report(
                    result, job.work_dir / "output" / "report",
                    fmt=options.get("format", "both"),
                )
                job.files = [Path(p).name for p in written]
            except Exception as exc:  # noqa: BLE001
                job.log(f"WARNING: the report file could not be created: {exc}")
                traceback.print_exc()
            job.files.append(json_path.name)

            job.log("Done.")
            job.status = "done"

        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            job.status = "error"
            job.error = f"{type(exc).__name__}: {exc}"
            job.log(f"ERROR: {job.error}")
            traceback.print_exc()
        finally:
            job.finished_at = _now()
            job.save()


def start_evaluation(job: Job, challenge: dict, options: dict) -> None:
    """Kick off the evaluation on a daemon thread."""
    thread = threading.Thread(
        target=run_evaluation, args=(job, challenge, options), daemon=True
    )
    thread.start()

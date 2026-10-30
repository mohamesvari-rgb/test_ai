"""
Flask application for the Scientific Evaluation Agent GUI.

Routes
------
GET  /                       the single-page UI
GET  /api/engine             the configured AI engine and whether it needs a key
POST /api/evaluate           accept the challenge + uploaded .docx, start a job
GET  /api/status/<job_id>    poll progress / results
GET  /api/runs               recent evaluations (kept across restarts)
GET  /api/download/<job>/<f> download a generated report file
POST /api/cleanup/<job_id>   delete a job's uploads and outputs

Run locally with ``python gui.py`` (binds to 127.0.0.1 by default).
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import List

from flask import (
    Flask, jsonify, render_template, request, send_from_directory, abort,
)

# Make the project importable when the app is launched from anywhere.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scientific_evaluator import __version__  # noqa: E402
from scientific_evaluator.config import PROVIDERS, default_provider_key  # noqa: E402
from scientific_evaluator.document_reader import discover_submission_files  # noqa: E402

from .jobs import JobStore, start_evaluation  # noqa: E402

MAX_UPLOAD_MB = 64
_UNSAFE_CHARS = re.compile(r"[\x00-\x1f<>:\"/\\|?*]")


def safe_filename(name: str) -> str:
    """Sanitize an uploaded filename while preserving non-ASCII characters.

    Werkzeug's ``secure_filename`` strips Persian/Arabic characters entirely,
    which would destroy participant names (the filename stem becomes the
    participant id). This keeps unicode letters but removes path separators,
    control characters and traversal attempts.
    """
    name = (name or "").replace("\\", "/").split("/")[-1]
    name = _UNSAFE_CHARS.sub("_", name).strip(". ")
    if not name:
        name = "submission.docx"
    if not name.lower().endswith(".docx"):
        name += ".docx"
    return name


def _lines(value: str) -> List[str]:
    """Split a textarea value into a clean list of lines."""
    return [ln.strip() for ln in (value or "").splitlines() if ln.strip()]


def create_app(work_root: Path | None = None) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

    root = Path(work_root) if work_root else Path(tempfile.gettempdir()) / "sci_eval_gui"
    store = JobStore(root)
    app.config["JOB_STORE"] = store

    # ---------------------------------------------------------------- pages
    @app.get("/")
    def index():
        return render_template("index.html", version=__version__)

    # --------------------------------------------------------------- engine
    @app.get("/api/engine")
    def engine():
        """Readiness of the online and offline engines, without their details."""
        from scientific_evaluator.llm_client import ollama_status

        default = PROVIDERS[default_provider_key()]
        online = default if default.kind in ("openai", "anthropic") else PROVIDERS["avalai"]
        model = PROVIDERS["ollama"].resolved_model()
        status = ollama_status()
        installed = {m["name"] for m in status["models"]}
        return jsonify({
            "mode": {"mock": "demo", "ollama": "offline"}.get(default.kind, "online"),
            "online": {"provider": online.key, "has_key": bool(online.env_api_key())},
            "offline": {
                "running": status["running"],
                "model_installed": model in installed or f"{model}:latest" in installed,
            },
        })

    # ------------------------------------------------------------ evaluate
    @app.post("/api/evaluate")
    def evaluate():
        # --- validate the challenge ---------------------------------------
        title = (request.form.get("title") or "").strip()
        field = (request.form.get("field") or "").strip()
        background = (request.form.get("background") or "").strip()
        objectives = _lines(request.form.get("objectives"))

        missing = [
            label for label, value in (
                ("Title", title), ("Field", field),
                ("Background", background), ("Objectives", objectives),
            ) if not value
        ]
        if missing:
            return jsonify({
                "error": f"Please fill in the required field(s): {', '.join(missing)}.",
                "code": "missing_fields", "fields": missing,
            }), 400

        challenge = {
            "title": title,
            "field": field,
            "background": background,
            "objectives": objectives,
            "constraints": _lines(request.form.get("constraints")),
            "expected_outputs": _lines(request.form.get("expected_outputs")),
            "evaluation_notes": (request.form.get("evaluation_notes") or "").strip(),
        }

        # --- validate the uploads -----------------------------------------
        uploads = [f for f in request.files.getlist("submissions") if f and f.filename]
        if not uploads:
            return jsonify({"error": "Please upload at least one .docx answer.",
                            "code": "no_files"}), 400

        bad = [f.filename for f in uploads if not f.filename.lower().endswith(".docx")]
        if bad:
            return jsonify({
                "error": "Only .docx files are supported. Convert these first: "
                         + ", ".join(bad),
                "code": "not_docx",
            }), 400

        # --- engine --------------------------------------------------------
        provider_key = (request.form.get("provider") or "").strip().lower()
        if request.form.get("mock") == "on":
            provider_key = "mock"
        provider_key = provider_key or default_provider_key()
        preset = PROVIDERS.get(provider_key)
        if not preset:
            return jsonify({"error": f"Unknown AI engine: {provider_key}",
                            "code": "bad_provider"}), 400

        api_key = (request.form.get("api_key") or "").strip()
        base_url = (request.form.get("base_url") or "").strip()
        if preset.needs_key and not api_key and not preset.env_api_key():
            return jsonify({
                "error": f"No API key found for {preset.label}. Paste the key, put "
                         f"{preset.key_env}=... in the .env file and restart, or "
                         "choose the offline or demo engine.",
                "code": "no_api_key",
            }), 400
        if preset.kind == "openai" and not (base_url or preset.resolved_base_url()):
            return jsonify({"error": "Enter the API base URL for this engine.",
                            "code": "no_base_url"}), 400

        options = {
            "language": request.form.get("language") or "Persian",
            "format": request.form.get("format") or "both",
            "provider": provider_key,
            "model": (request.form.get("model") or "").strip(),
            "base_url": base_url,
            "api_key": api_key,
        }

        # --- persist the answers and start the job ------------------------
        job = store.create()
        sub_dir = job.work_dir / "submissions"
        seen: set[str] = set()
        for upload in uploads:
            name = safe_filename(upload.filename)
            stem, ext = os.path.splitext(name)
            counter = 2
            while name in seen:                      # avoid silent overwrites
                name = f"{stem}_{counter}{ext}"
                counter += 1
            seen.add(name)
            upload.save(str(sub_dir / name))

        job.title = title
        job.provider = provider_key
        job.participants = [p.stem for p in discover_submission_files(sub_dir)]
        job.log(f"Received {len(job.participants)} answer file(s).")
        job.save()
        start_evaluation(job, challenge, options)
        return jsonify({"job_id": job.id})

    # ---------------------------------------------------------------- jobs
    @app.get("/api/status/<job_id>")
    def status(job_id: str):
        job = store.get(job_id)
        if not job:
            return jsonify({"error": "unknown job"}), 404
        return jsonify(job.to_dict())

    @app.get("/api/runs")
    def runs():
        return jsonify({"runs": [
            {
                "id": j.id, "status": j.status, "title": j.title,
                "created_at": j.created_at, "finished_at": j.finished_at,
                "engine": j.engine, "provider": j.provider,
                "count": len(j.participants),
                "top": j.ranking[0] if j.ranking else None,
            }
            for j in store.recent()
        ]})

    @app.get("/api/download/<job_id>/<path:filename>")
    def download(job_id: str, filename: str):
        job = store.get(job_id)
        if not job:
            abort(404)
        # Only serve files this job actually produced.
        if filename not in job.files:
            abort(404)
        return send_from_directory(
            job.work_dir / "output", filename, as_attachment=True
        )

    @app.post("/api/cleanup/<job_id>")
    def cleanup(job_id: str):
        store.cleanup(job_id)
        return jsonify({"ok": True})

    @app.errorhandler(413)
    def too_large(_err):
        return jsonify(
            {"error": f"Upload too large (limit {MAX_UPLOAD_MB} MB total).",
             "code": "too_large"}
        ), 413

    return app


if __name__ == "__main__":  # pragma: no cover
    create_app().run(host="127.0.0.1", port=5000, debug=False)

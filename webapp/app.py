"""
Flask application for the Scientific Evaluation Agent GUI.

Routes
------
GET  /                       the single-page UI
POST /api/evaluate           accept the challenge + uploaded .docx, start a job
GET  /api/status/<job_id>    poll progress / results
GET  /api/download/<job>/<f> download a generated report file
POST /api/cleanup/<job_id>   delete a job's uploads and outputs
GET  /api/example-challenge  load the bundled example challenge into the form

Run locally with ``python gui.py`` (binds to 127.0.0.1 by default).
"""

from __future__ import annotations

import json
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
        return render_template(
            "index.html",
            has_api_key=bool(os.environ.get("ANTHROPIC_API_KEY")),
        )

    # ------------------------------------------------------------------ api
    @app.get("/api/example-challenge")
    def example_challenge():
        path = _PROJECT_ROOT / "config" / "challenge_example.json"
        if not path.exists():
            return jsonify({"error": "example challenge not found"}), 404
        return jsonify(json.loads(path.read_text(encoding="utf-8")))

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
            return jsonify(
                {"error": f"Please fill in the required field(s): {', '.join(missing)}."}
            ), 400

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
            return jsonify({"error": "Please upload at least one .docx answer."}), 400

        bad = [f.filename for f in uploads if not f.filename.lower().endswith(".docx")]
        if bad:
            return jsonify({
                "error": "Only .docx files are supported. Convert these first: "
                         + ", ".join(bad)
            }), 400

        # --- options -------------------------------------------------------
        mock = request.form.get("mock") == "on"
        api_key = (request.form.get("api_key") or "").strip()
        if not mock and not api_key and not os.environ.get("ANTHROPIC_API_KEY"):
            return jsonify({
                "error": "No API key found. Paste your Anthropic API key, set "
                         "ANTHROPIC_API_KEY before starting the app, or tick "
                         "\"Offline demo\" to try the layout without one."
            }), 400

        options = {
            "language": request.form.get("language") or "Persian",
            "format": request.form.get("format") or "both",
            "model": (request.form.get("model") or "").strip(),
            "mock": mock,
            "api_key": api_key,
        }

        # --- persist uploads and start the job -----------------------------
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

        job.log(f"Received {len(seen)} answer file(s).")
        start_evaluation(job, challenge, options)
        return jsonify({"job_id": job.id})

    @app.get("/api/status/<job_id>")
    def status(job_id: str):
        job = store.get(job_id)
        if not job:
            return jsonify({"error": "unknown job"}), 404
        return jsonify(job.to_dict())

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
            {"error": f"Upload too large (limit {MAX_UPLOAD_MB} MB total)."}
        ), 413

    return app


if __name__ == "__main__":  # pragma: no cover
    create_app().run(host="127.0.0.1", port=5000, debug=False)

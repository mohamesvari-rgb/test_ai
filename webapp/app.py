"""
Flask application for the Scientific Evaluation Agent GUI.

Routes
------
GET  /                       the single-page UI
GET  /api/engines            available AI engines + their readiness (keys, Ollama)
POST /api/test-engine        send a tiny request to the chosen engine
GET  /api/demo-packs         bundled sample challenges + answers
GET  /api/example-challenge  load a bundled challenge into the form (?pack=<id>)
POST /api/evaluate           accept the challenge + uploaded .docx, start a job
GET  /api/status/<job_id>    poll progress / results
GET  /api/runs               recent evaluations (kept across restarts)
GET  /api/download/<job>/<f> download a generated report file
POST /api/cleanup/<job_id>   delete a job's uploads and outputs

Run locally with ``python gui.py`` (binds to 127.0.0.1 by default).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import time
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

# Sample challenges with real answers, selectable from the UI for a demo.
DEMO_PACKS = [
    {
        "id": "mof_co2",
        "title": "Conductive, hydrophobic MOF for CO₂ capture from wet flue gas",
        "title_fa": "طراحی MOF رسانا و آب‌گریز برای جذب CO₂ از گاز دودکش مرطوب",
        "challenge": "examples/mof_co2_capture/challenge.json",
        "submissions": "examples/mof_co2_capture/submissions",
    },
    {
        "id": "crop_water_stress",
        "title": "Early detection of crop water stress (remote sensing)",
        "title_fa": "تشخیص زودهنگام تنش آبی گیاهان با سنجش از دور",
        "challenge": "config/challenge_example.json",
        "submissions": "examples/submissions",
    },
]


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


def _pack(pack_id: str):
    return next((p for p in DEMO_PACKS if p["id"] == pack_id), None)


def _pack_files(pack) -> List[Path]:
    folder = _PROJECT_ROOT / pack["submissions"]
    return discover_submission_files(folder) if folder.exists() else []


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

    # -------------------------------------------------------------- engines
    @app.get("/api/engines")
    def engines():
        from scientific_evaluator.llm_client import ollama_status

        providers = []
        for p in PROVIDERS.values():
            providers.append({
                "key": p.key, "label": p.label, "label_fa": p.label_fa,
                "kind": p.kind, "offline": p.offline, "needs_key": p.needs_key,
                "key_env": p.key_env, "has_key": bool(p.env_api_key()),
                "model": p.resolved_model(), "base_url": p.resolved_base_url(),
                "models": list(p.models), "signup_url": p.signup_url,
                "note": p.note, "note_fa": p.note_fa,
            })
        return jsonify({
            "default": default_provider_key(),
            "providers": providers,
            "ollama": ollama_status(),
        })

    @app.post("/api/test-engine")
    def test_engine():
        from scientific_evaluator.llm_client import build_llm_client

        form = request.get_json(silent=True) or request.form
        started = time.perf_counter()
        try:
            llm = build_llm_client(
                form.get("provider"),
                api_key=form.get("api_key") or None,
                model=form.get("model") or None,
                base_url=form.get("base_url") or None,
            )
            data = llm.complete_json(
                "You are a connectivity check. TASK: health check. "
                "Answer with a JSON object only.",
                'Return exactly this JSON with a short friendly greeting in Persian: '
                '{"ok": true, "reply": "<greeting>"}',
            )
        except Exception as exc:  # noqa: BLE001 - report any failure to the UI
            return jsonify({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return jsonify({
            "ok": True,
            "engine": llm.description,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "reply": str(data.get("reply", ""))[:200],
        })

    # ----------------------------------------------------------- demo packs
    @app.get("/api/demo-packs")
    def demo_packs():
        packs = []
        for p in DEMO_PACKS:
            files = _pack_files(p)
            if files:
                packs.append({
                    "id": p["id"], "title": p["title"], "title_fa": p["title_fa"],
                    "files": [{"name": f.name, "size": f.stat().st_size} for f in files],
                })
        return jsonify({"packs": packs})

    @app.get("/api/example-challenge")
    def example_challenge():
        pack = _pack(request.args.get("pack") or DEMO_PACKS[0]["id"])
        path = _PROJECT_ROOT / pack["challenge"] if pack else None
        if not path or not path.exists():
            return jsonify({"error": "example challenge not found"}), 404
        return jsonify(json.loads(path.read_text(encoding="utf-8")))

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

        # --- validate the answers (uploads or a bundled sample pack) -------
        uploads = [f for f in request.files.getlist("submissions") if f and f.filename]
        pack = _pack(request.form.get("sample_pack") or "")
        if request.form.get("sample_pack") and not pack:
            return jsonify({"error": "Unknown sample pack.", "code": "bad_pack"}), 400
        if not uploads and not pack:
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
        if pack:
            for src in _pack_files(pack):
                shutil.copy2(src, sub_dir / src.name)
        seen: set[str] = {p.name for p in sub_dir.iterdir()}
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

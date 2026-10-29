"""
Tests for the HTTP LLM clients (OpenAI-compatible + Ollama).

A tiny local HTTP server imitates both APIs, so no network, API key or Ollama
install is needed. The fake server answers with the offline mock's content,
which lets the full agent pipeline run end-to-end through the real clients.

Run:  python tests/test_llm_clients.py     (or)  python -m pytest tests/ -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scientific_evaluator.config import SETTINGS  # noqa: E402
from scientific_evaluator.llm_client import (  # noqa: E402
    LLMError, MockLLMClient, OllamaLLMClient, OpenAICompatibleLLMClient,
    build_llm_client, ollama_status,
)

_MOCK = MockLLMClient()


class _FakeAPI(BaseHTTPRequestHandler):
    """Imitates /v1/chat/completions and Ollama's /api/* endpoints."""

    requests: list = []
    reject_json_mode = False
    installed_models = ["qwen3.5:9b"]

    def log_message(self, *args):  # keep test output quiet
        pass

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/api/version":
            return self._send(200, {"version": "0.40.13"})
        if self.path == "/api/tags":
            return self._send(200, {"models": [
                {"name": m, "size": 6_600_000_000} for m in self.installed_models]})
        self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).requests.append((self.path, dict(self.headers), payload))
        system = payload["messages"][0]["content"]
        user = payload["messages"][1]["content"]

        if self.path == "/v1/chat/completions":
            if self.headers.get("Authorization") != "Bearer good-key":
                return self._send(401, {"error": {"message": "invalid api key"}})
            if self.reject_json_mode and "response_format" in payload:
                return self._send(400, {"error": {"message": "response_format not supported"}})
            content = "<think>internal reasoning</think>" + _MOCK.complete_text(system, user)
            return self._send(200, {"choices": [{"message": {"role": "assistant", "content": content}}]})

        if self.path == "/api/chat":
            if payload["model"] not in self.installed_models:
                return self._send(404, {"error": f"model '{payload['model']}' not found"})
            content = _MOCK.complete_text(system, user)
            return self._send(200, {"message": {"role": "assistant", "content": content}, "done": True})

        self._send(404, {"error": "not found"})


def _serve():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeAPI)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


SERVER, BASE = _serve()
HEALTH = ("You are a connectivity check. TASK: health check.", 'Return {"ok": true}')


def test_openai_compatible_json_and_reasoning_stripped():
    _FakeAPI.requests.clear()
    client = OpenAICompatibleLLMClient(BASE + "/v1", "good-key", "deepseek-chat")
    data = client.complete_json("TASK: Score ONE submission", "submission text")
    assert "criterion_scores" in data
    path, headers, payload = _FakeAPI.requests[-1]
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["model"] == "deepseek-chat"
    assert payload["max_tokens"] == SETTINGS.max_tokens


def test_openai_compatible_falls_back_without_json_mode():
    _FakeAPI.reject_json_mode = True
    try:
        client = OpenAICompatibleLLMClient(BASE + "/v1", "good-key", "some-model")
        data = client.complete_json("TASK: Extract the INNOVATION", "text")
        assert "main_innovations" in data
        assert client.json_mode_supported is False
    finally:
        _FakeAPI.reject_json_mode = False


def test_bad_key_fails_fast_with_clear_message():
    _FakeAPI.requests.clear()
    client = OpenAICompatibleLLMClient(BASE + "/v1", "wrong-key", "deepseek-chat")
    try:
        client.complete_json(*HEALTH)
    except LLMError as exc:
        assert "key" in str(exc).lower()
    else:
        raise AssertionError("expected LLMError for a rejected key")
    assert len(_FakeAPI.requests) == 1, "401 must not be retried"


def test_ollama_native_options():
    _FakeAPI.requests.clear()
    client = OllamaLLMClient(base_url=BASE, model="qwen3.5:9b")
    data = client.complete_json("TASK: Score ONE submission", "x" * 90_000)
    assert "criterion_scores" in data
    _, _, payload = _FakeAPI.requests[-1]
    assert payload["format"] == "json"
    assert payload["think"] is False
    assert payload["stream"] is False
    # A long prompt raises the context window above the default.
    assert payload["options"]["num_ctx"] > SETTINGS.ollama_num_ctx
    assert payload["options"]["num_ctx"] % 4096 == 0
    assert client.max_parallel == 1


def test_ollama_missing_model_message():
    client = OllamaLLMClient(base_url=BASE, model="not-installed:1b")
    try:
        client.complete_text("TASK: Produce ONE final", "x")
    except LLMError as exc:
        assert "ollama pull not-installed:1b" in str(exc)
    else:
        raise AssertionError("expected LLMError for a missing model")


def test_ollama_not_running_message():
    client = OllamaLLMClient(base_url="http://127.0.0.1:9", model="qwen3.5:9b")
    try:
        client.complete_text("x", "y")
    except LLMError as exc:
        assert "not running" in str(exc)
    else:
        raise AssertionError("expected LLMError when Ollama is down")


def test_ollama_status():
    up = ollama_status(BASE)
    assert up["running"] and up["version"] == "0.40.13"
    assert up["models"][0]["name"] == "qwen3.5:9b"
    down = ollama_status("http://127.0.0.1:9", timeout=0.5)
    assert down["running"] is False


def test_build_llm_client_presets():
    import os
    assert isinstance(build_llm_client("mock"), MockLLMClient)
    ol = build_llm_client("ollama", base_url=BASE, model="qwen3.5:4b")
    assert isinstance(ol, OllamaLLMClient) and ol.model == "qwen3.5:4b"
    os.environ.pop("AVALAI_API_KEY", None)
    try:
        build_llm_client("avalai")
    except LLMError as exc:
        assert "AVALAI_API_KEY" in str(exc)
    else:
        raise AssertionError("expected an error without an API key")
    av = build_llm_client("avalai", api_key="k")
    assert av.base_url == "https://api.avalai.ir/v1" and av.model


def test_full_pipeline_through_openai_client():
    """End-to-end run (parallel evaluations) through the real HTTP client."""
    from scientific_evaluator import ScientificEvaluationAgent

    root = Path(__file__).resolve().parent.parent
    client = OpenAICompatibleLLMClient(BASE + "/v1", "good-key", "deepseek-chat")
    assert client.max_parallel > 1
    messages = []
    agent = ScientificEvaluationAgent(
        root / "examples" / "mof_co2_capture" / "challenge.json", client,
        progress=messages.append,
    )
    result = agent.run(root / "examples" / "mof_co2_capture" / "submissions")
    ids = {e.participant_id for e in result.evaluations}
    assert ids == {"claude", "DeepSeek", "Gemini", "GLM", "o4", "qwen"}, ids
    assert sum(m.startswith("Finished ") for m in messages) == 6
    assert result.synthesized_solution
    with tempfile.TemporaryDirectory() as tmp:
        written = agent.export_report(result, Path(tmp) / "report", fmt="docx")
        assert written[0].exists() and written[0].stat().st_size > 10_000


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL  {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)

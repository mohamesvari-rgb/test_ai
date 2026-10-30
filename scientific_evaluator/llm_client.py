"""
LLM client wrapper.

Provides a thin, swappable interface around the LLM so the evaluation logic
does not depend on any specific SDK. Implementations:

* ``OpenAICompatibleLLMClient`` - any OpenAI-compatible API (AvalAI, DeepSeek,
  OpenRouter, LM Studio, vLLM, ...). Standard library only.
* ``OllamaLLMClient``    - a local Ollama server: fully offline.
* ``AnthropicLLMClient`` - real Claude calls (needs ANTHROPIC_API_KEY).
* ``MockLLMClient``      - deterministic offline stub for tests/demos.

``build_llm_client(provider, ...)`` creates the right one from a preset in
``config.PROVIDERS``.

All clients expose ``complete_json(system, user)`` which returns a parsed
``dict`` (the models are always instructed to answer with JSON) and
``complete_text(system, user)`` for free-form text (e.g. the synthesis).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from .config import SETTINGS, get_provider


class LLMError(RuntimeError):
    """Raised when the LLM call fails after retries."""


class _FatalLLMError(LLMError):
    """A failure that retrying cannot fix (bad key, missing model, server down)."""


class _HTTPStatusError(LLMError):
    """A non-2xx HTTP answer from an LLM endpoint."""

    def __init__(self, status: int, body: str, url: str):
        super().__init__(f"HTTP {status} from {url}: {body[:400]}")
        self.status = status
        self.body = body


# Statuses worth retrying (rate limit / overloaded / gateway hiccups).
_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 520, 522, 524, 529}

# Ceiling when a cut-off online reply is retried with a larger output limit.
_MAX_ONLINE_TOKENS = 96000


def _strip_reasoning(text: str) -> str:
    """Drop ``<think>...</think>`` blocks that reasoning models prepend."""
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()


def _http_json(
    url: str,
    payload: Optional[dict] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 300,
) -> Dict[str, Any]:
    """POST (or GET when ``payload`` is None) JSON and return the parsed reply."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method="POST" if data is not None else "GET",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise _HTTPStatusError(exc.code, body, url) from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"Cannot reach {url}: {exc.reason}") from exc
    except (socket.timeout, TimeoutError) as exc:
        raise LLMError(f"Timed out after {timeout:.0f}s waiting for {url}") from exc
    except json.JSONDecodeError as exc:
        raise LLMError(f"Non-JSON reply from {url}: {exc}") from exc


def extract_json(text: str) -> Dict[str, Any]:
    """Robustly extract a JSON object from an LLM response.

    Handles fenced code blocks and leading/trailing prose.
    """
    if not text:
        raise LLMError("Empty LLM response; expected JSON.")

    # Strip ```json ... ``` fences if present.
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text

    # Fall back to the first {...} span.
    if not fenced:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Could not parse JSON from LLM response: {exc}\n{text[:500]}")


class BaseLLMClient(ABC):
    """Interface every LLM backend must implement."""

    # How many submissions the agent may evaluate concurrently with this client.
    max_parallel: int = 1
    # Human-readable "provider · model" label for progress logs.
    description: str = ""

    @abstractmethod
    def complete_text(self, system: str, user: str) -> str:
        """Return raw text completion."""

    def complete_json(self, system: str, user: str) -> Dict[str, Any]:
        """Return a parsed JSON object from the model."""
        return extract_json(self.complete_text(system, user))


# ---------------------------------------------------------------------------
# Anthropic (Claude) backend
# ---------------------------------------------------------------------------
class AnthropicLLMClient(BaseLLMClient):
    """Claude-backed client using the official Anthropic SDK."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise LLMError(
                "The 'anthropic' package is required for AnthropicLLMClient. "
                "Run `pip install anthropic`."
            ) from exc

        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError(
                "ANTHROPIC_API_KEY is not set. Export it or pass api_key=... "
                "(or use MockLLMClient for offline runs)."
            )
        self._client = anthropic.Anthropic(api_key=key)
        self.model = model or SETTINGS.model
        self.max_parallel = SETTINGS.max_parallel
        self.description = f"Anthropic · {self.model}"

    def complete_text(self, system: str, user: str) -> str:
        last_err: Exception | None = None
        for attempt in range(SETTINGS.max_retries):
            try:
                resp = self._client.messages.create(
                    model=self.model,
                    max_tokens=SETTINGS.max_tokens,
                    temperature=SETTINGS.temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                # Concatenate all text blocks in the response.
                return "".join(
                    block.text for block in resp.content
                    if getattr(block, "type", None) == "text"
                )
            except Exception as exc:  # noqa: BLE001 - retry any transient error
                last_err = exc
                if attempt < SETTINGS.max_retries - 1:
                    time.sleep(2 ** attempt)  # exponential backoff
        raise LLMError(f"Anthropic call failed after retries: {last_err}")


# ---------------------------------------------------------------------------
# Shared base for HTTP chat APIs (OpenAI-compatible + Ollama)
# ---------------------------------------------------------------------------
class _ChatAPIClient(BaseLLMClient):
    """Retry policy and JSON repair shared by the HTTP chat clients."""

    @abstractmethod
    def _chat(self, system: str, user: str, json_mode: bool) -> str:
        """Send one chat request and return the assistant text."""

    def _with_retries(self, call: Callable[[], str]) -> str:
        last_err: Exception | None = None
        for attempt in range(SETTINGS.max_retries):
            try:
                return call()
            except _FatalLLMError:
                raise
            except _HTTPStatusError as exc:
                if exc.status not in _RETRYABLE_STATUS:
                    raise                      # bad key, unknown model, ...: fail fast
                last_err = exc
            except LLMError as exc:            # network error / timeout
                last_err = exc
            if attempt < SETTINGS.max_retries - 1:
                time.sleep(2 ** (attempt + 1))
        raise LLMError(f"{self.description or 'LLM'} call failed after retries: {last_err}")

    def complete_text(self, system: str, user: str) -> str:
        def call() -> str:
            text = self._chat(system, user, json_mode=False)
            if not text:   # never let an empty answer pass as a finished section
                raise LLMError("the model returned an empty reply")
            return text

        return self._with_retries(call)

    def complete_json(self, system: str, user: str) -> Dict[str, Any]:
        text = self._with_retries(lambda: self._chat(system, user, json_mode=True))
        try:
            return extract_json(text)
        except LLMError:
            # Smaller and local models occasionally emit malformed JSON; one
            # corrective round-trip fixes nearly all of these cases.
            retry_user = (
                user + "\n\nIMPORTANT: your previous reply was not valid JSON. "
                "Reply again with ONLY the JSON object, no prose and no code fences."
            )
            return extract_json(
                self._with_retries(lambda: self._chat(system, retry_user, json_mode=True))
            )


# ---------------------------------------------------------------------------
# OpenAI-compatible backend (AvalAI, DeepSeek, OpenRouter, LM Studio, ...)
# ---------------------------------------------------------------------------
class OpenAICompatibleLLMClient(_ChatAPIClient):
    """Client for any ``/chat/completions`` API that follows the OpenAI format."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout: float = 600,    # a long reasoning reply can take several minutes
        label: str = "",
    ):
        if not base_url:
            raise LLMError("A base URL is required for an OpenAI-compatible API.")
        if not model:
            raise LLMError("A model name is required for an OpenAI-compatible API.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.model = model
        self.timeout = timeout
        self.json_mode_supported = True
        self.max_tokens = SETTINGS.online_max_tokens
        self.max_parallel = SETTINGS.max_parallel
        self.description = f"{label or self.base_url} · {model}"

    def _chat(self, system: str, user: str, json_mode: bool) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": SETTINGS.temperature,
            "max_tokens": self.max_tokens,
        }
        if json_mode and self.json_mode_supported:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            data = _http_json(f"{self.base_url}/chat/completions", payload,
                              headers, self.timeout)
        except _HTTPStatusError as exc:
            if exc.status in (401, 403):
                raise _FatalLLMError(
                    f"The API rejected the key ({exc.status}). Check the API key "
                    f"for {self.base_url}."
                ) from exc
            if (exc.status in (400, 422) and "response_format" in payload
                    and self.json_mode_supported):
                # Some gateways/models reject JSON mode; the prompts already
                # demand JSON, so continue without it.
                self.json_mode_supported = False
                return self._chat(system, user, json_mode)
            raise
        try:
            choice = data["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected reply from {self.base_url}: {str(data)[:400]}") from exc
        # A cut-off reply cannot be fixed by asking again with the same limit.
        if choice.get("finish_reason") == "length" and self.max_tokens < _MAX_ONLINE_TOKENS:
            self.max_tokens = min(self.max_tokens * 2, _MAX_ONLINE_TOKENS)
            return self._chat(system, user, json_mode)
        return _strip_reasoning(message.get("content") or "")


# ---------------------------------------------------------------------------
# Ollama backend (offline, local model)
# ---------------------------------------------------------------------------
def _approx_tokens(text: str) -> int:
    # Persian text needs noticeably more tokens per character than English;
    # three characters per token is a deliberately generous estimate.
    return len(text) // 3 + 1


class OllamaLLMClient(_ChatAPIClient):
    """Client for a local Ollama server via its native ``/api/chat`` endpoint.

    The native endpoint (unlike Ollama's OpenAI shim) lets us set the context
    window, force JSON output and switch off "thinking", all of which matter
    for long Persian prompts on a laptop GPU.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        num_ctx: int | None = None,
        timeout: float = 1800,
    ):
        preset = get_provider("ollama")
        self.base_url = (base_url or preset.resolved_base_url()).rstrip("/")
        self.model = model or preset.resolved_model()
        self.num_ctx = num_ctx or SETTINGS.ollama_num_ctx
        self.timeout = timeout
        self.send_think = True
        self.max_parallel = 1          # one GPU: requests would only queue up
        self.description = f"Ollama (offline) · {self.model}"

    def _context_for(self, system: str, user: str) -> int:
        # Changing num_ctx makes Ollama reload the model, so the default is
        # sized for typical prompts and only grows for an unusually long one.
        # 4k tokens of headroom covers every answer the prompts ask for.
        needed = _approx_tokens(system + user) + 4096 + 256
        ctx = max(self.num_ctx, needed)
        return min(-(-ctx // 4096) * 4096, 65536)   # round up to 4k, hard cap

    def _chat(self, system: str, user: str, json_mode: bool) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            # A loaded model grows the Windows page file by several GB on C:, so
            # release it soon after the last request.
            "keep_alive": "5m",
            "options": {
                "temperature": SETTINGS.temperature,
                "num_ctx": self._context_for(system, user),
                "num_predict": SETTINGS.max_tokens,
            },
        }
        if self.send_think:
            payload["think"] = False
        if json_mode:
            payload["format"] = "json"
        try:
            data = _http_json(f"{self.base_url}/api/chat", payload, timeout=self.timeout)
        except _HTTPStatusError as exc:
            body = exc.body.lower()
            if exc.status == 400 and "think" in body and self.send_think:
                self.send_think = False        # model without a thinking switch
                return self._chat(system, user, json_mode)
            if exc.status == 404 or "not found" in body:
                raise _FatalLLMError(
                    f"The model '{self.model}' is not installed in Ollama. "
                    f"Run:  ollama pull {self.model}   (or install_offline_model.bat)"
                ) from exc
            raise
        except LLMError as exc:
            if "Cannot reach" in str(exc):
                raise _FatalLLMError(
                    f"Ollama is not running at {self.base_url}. Start Ollama (or "
                    "start.bat) and try again."
                ) from exc
            raise
        return _strip_reasoning((data.get("message") or {}).get("content") or "")


def ollama_status(base_url: str | None = None, timeout: float = 2.0) -> Dict[str, Any]:
    """Report whether a local Ollama server is up and which models it has."""
    url = (base_url or get_provider("ollama").resolved_base_url()).rstrip("/")
    try:
        version = _http_json(f"{url}/api/version", timeout=timeout).get("version", "")
        tags = _http_json(f"{url}/api/tags", timeout=timeout).get("models", []) or []
    except LLMError:
        return {"running": False, "version": "", "models": [], "base_url": url}
    models: List[Dict[str, Any]] = [
        {"name": m.get("name", ""), "size_gb": round((m.get("size") or 0) / 1e9, 1)}
        for m in tags if m.get("name")
    ]
    return {"running": True, "version": version, "models": models, "base_url": url}


def build_llm_client(
    provider: str | None,
    *,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> BaseLLMClient:
    """Create the client for a preset in ``config.PROVIDERS``.

    Empty arguments fall back to the preset / environment (``.env``) values.
    """
    from .config import default_provider_key

    preset = get_provider(provider or default_provider_key())
    model = (model or "").strip() or preset.resolved_model()
    base_url = (base_url or "").strip() or preset.resolved_base_url()

    if preset.kind == "mock":
        return MockLLMClient()
    if preset.kind == "ollama":
        return OllamaLLMClient(base_url=base_url, model=model)
    if preset.kind == "anthropic":
        return AnthropicLLMClient(api_key=api_key or None, model=model or None)

    key = (api_key or "").strip() or preset.env_api_key()
    if not key:
        raise LLMError(
            f"No API key for {preset.label}. Put it in .env as {preset.key_env}=... "
            "or paste it into the form."
        )
    if not base_url:
        raise LLMError(f"Set the base URL for {preset.label} (e.g. CUSTOM_BASE_URL in .env).")
    return OpenAICompatibleLLMClient(base_url, key, model, label=preset.label.split(" — ")[0])


# ---------------------------------------------------------------------------
# Offline deterministic mock
# ---------------------------------------------------------------------------
class MockLLMClient(BaseLLMClient):
    """Deterministic offline client.

    Produces stable pseudo-evaluations derived from a hash of the input so the
    full pipeline (scoring, ranking, report export) can be exercised without an
    API key or network. NOT a real evaluation - for testing/demo only.
    """

    max_parallel = 4
    description = "Demo mode (placeholder output, no AI)"

    def __init__(self, seed_salt: str = ""):
        self.seed_salt = seed_salt

    def _score_from(self, text: str, key: str) -> int:
        h = hashlib.sha256((self.seed_salt + key + text).encode()).hexdigest()
        return 4 + (int(h[:4], 16) % 7)  # 4..10

    def complete_text(self, system: str, user: str) -> str:
        """Route on the unique TASK marker in the system prompt.

        Persian is used for human-readable values so the offline demo exercises
        the RTL report rendering. (Real evaluations use a live backend.)
        """
        if "TASK: Score ONE submission" in system:
            return self._mock_scores(user)
        if "TASK: Extract the INNOVATION" in system:
            return self._mock_innovation(user)
        if "TASK: For EACH given idea" in system:
            return self._mock_improvement(user)
        if "TASK: COMPARE and RANK" in system:
            return self._mock_comparison(user)
        if "TASK: Produce ONE final" in system:
            return self._mock_synthesis()
        if "TASK: Write a concise FINAL RECOMMENDATION" in system:
            return self._mock_recommendation()
        return "خروجی آزمایشی (mock)."

    def _mock_scores(self, user: str) -> str:
        from .config import RUBRIC
        scores = {
            c.key: {
                "raw_score": self._score_from(user, c.key),
                "justification": f"[نمونه] ارزیابی معیار «{c.name}» بر پایه متن پاسخ.",
            }
            for c in RUBRIC
        }
        payload = {
            "criterion_scores": scores,
            "summary": "[نمونه] پاسخی منسجم و مرتبط با چالش با نقاط قوت روشن.",
            "strengths": ["[نمونه] هدف‌گذاری روشن", "[نمونه] روش‌شناسی قابل‌قبول"],
            "weaknesses": ["[نمونه] اعتبارسنجی محدود", "[نمونه] برآورد هزینه نامشخص"],
            "integrity_flags": [],
        }
        return json.dumps(payload, ensure_ascii=False)

    def _mock_innovation(self, user: str) -> str:
        payload = {
            "main_innovations": ["[نمونه] خط لوله سنجش نوین"],
            "creative_aspects": ["[نمونه] قیاس میان‌رشته‌ای"],
            "unique_advantages": ["[نمونه] سخت‌افزار کم‌هزینه"],
            "strong_technical_ideas": ["[نمونه] مدل خودکالیبره"],
            "potential_research_contributions": ["[نمونه] معیار ارزیابی متن‌باز"],
            "weaknesses_or_missing_parts": ["[نمونه] نبود آزمون میدانی"],
        }
        return json.dumps(payload, ensure_ascii=False)

    def _mock_improvement(self, user: str) -> str:
        ideas = re.findall(r'"([^"]{4,})"', user.split("IDEAS TO IMPROVE")[-1])
        ideas = ideas[:4] or ["[نمونه] ایده کلیدی"]
        payload = {
            "idea_improvements": [
                {
                    "idea": idea,
                    "why_it_matters": "[نمونه] ارتباط مستقیم با اهداف چالش دارد.",
                    "improvements": [
                        "[نمونه] افزودن اعتبارسنجی میدانی برای افزایش دقت",
                        "[نمونه] کاهش هزینه با اشتراک‌گذاری سنسورها",
                    ],
                    "expected_effect": "[نمونه] افزایش دقت و امکان‌سنجی راه‌حل.",
                }
                for idea in ideas
            ]
        }
        return json.dumps(payload, ensure_ascii=False)

    def _mock_comparison(self, user: str) -> str:
        # Pull each participant together with its total score from the digest so
        # the mock ranking is ordered strongest-first. Ranking by score keeps the
        # offline demo self-consistent with the score table it renders.
        pairs = re.findall(
            r'"participant_id"\s*:\s*"([^"]+)".*?"total_score"\s*:\s*([0-9.]+)',
            user, re.DOTALL,
        )
        seen, scored = set(), []
        for pid, score in pairs:
            if pid not in seen:
                seen.add(pid)
                scored.append((pid, float(score)))
        ids = [pid for pid, _ in sorted(scored, key=lambda x: x[1], reverse=True)]
        if not ids:  # digest missing scores; fall back to first-seen order
            ids = list(dict.fromkeys(
                re.findall(r'"participant_id"\s*:\s*"([^"]+)"', user)
            )) or ["participant"]
        payload = {
            "ranking": ids,
            "rationale": "[نمونه] رتبه‌بندی بر پایه قدرت روش‌شناسی و اثرگذاری کلی.",
            "salient_points": {i: [f"[نمونه] نقطه برجسته پاسخ {i}"] for i in ids},
            "distinctive_points": {i: [f"[نمونه] وجه تمایز پاسخ {i}"] for i in ids},
            "pairwise_notes": ["[نمونه] پاسخ برتر اعتبارسنجی قوی‌تری دارد."],
            "overlapping_ideas": ["[نمونه] استفاده مشترک از داده سنجش از دور"],
            "unique_ideas": {i: [f"[نمونه] ایده منحصربه‌فرد {i}"] for i in ids},
            "complementary_ideas": ["[نمونه] ترکیب سنسور A با مدل B"],
        }
        return json.dumps(payload, ensure_ascii=False)

    def _mock_synthesis(self) -> str:
        return (
            "# مرور کلی\n"
            "[نمونه] راه‌حل جامع از ترکیب ایده‌های موجود در پاسخ‌ها ساخته شده است.\n"
            "# روش‌شناسی یکپارچه\n"
            "[نمونه] تلفیق داده سنجش از دور با سنسورهای کم‌هزینه و مدل خودکالیبره.\n"
            "# چرا این ترکیب چالش را حل می‌کند\n"
            "[نمونه] دقت بالاتر، هزینه کمتر و مقیاس‌پذیری بیشتر.\n"
            "# اثر مورد انتظار\n"
            "[نمونه] هشدار زودهنگام تنش آبی با هزینه مناسب."
        )

    def _mock_recommendation(self) -> str:
        return (
            "[نمونه] توصیه نهایی: پاسخ برتر به دلیل روش‌شناسی منسجم و امکان‌سنجی "
            "بالا انتخاب می‌شود؛ پیش از اجرا، اعتبارسنجی میدانی و برآورد دقیق هزینه "
            "تکمیل گردد."
        )

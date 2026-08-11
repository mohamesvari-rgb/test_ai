"""
LLM client wrapper.

Provides a thin, swappable interface around the LLM so the evaluation logic
does not depend on any specific SDK. Two implementations are shipped:

* ``AnthropicLLMClient`` - real Claude calls (needs ANTHROPIC_API_KEY).
* ``MockLLMClient``      - deterministic offline stub for tests/demos.

All clients expose ``complete_json(system, user)`` which returns a parsed
``dict`` (the models are always instructed to answer with JSON) and
``complete_text(system, user)`` for free-form text (e.g. the synthesis).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict

from .config import SETTINGS


class LLMError(RuntimeError):
    """Raised when the LLM call fails after retries."""


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
# Offline deterministic mock
# ---------------------------------------------------------------------------
class MockLLMClient(BaseLLMClient):
    """Deterministic offline client.

    Produces stable pseudo-evaluations derived from a hash of the input so the
    full pipeline (scoring, ranking, report export) can be exercised without an
    API key or network. NOT a real evaluation - for testing/demo only.
    """

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
        ids = re.findall(r'"participant_id"\s*:\s*"([^"]+)"', user)
        # De-duplicate while preserving order.
        seen, uniq = set(), []
        for i in ids:
            if i not in seen:
                seen.add(i); uniq.append(i)
        ids = uniq or ["participant"]
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

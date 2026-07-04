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
        # Route based on the kind of task encoded in the system prompt.
        if "CRITERION" in system or "rubric" in system.lower():
            return self._mock_scores(user)
        if "innovation" in system.lower():
            return self._mock_innovation(user)
        if "compare" in system.lower() or "ranking" in system.lower():
            return self._mock_comparison(user)
        return "Mock synthesis: combine the strongest, most feasible ideas."

    def _mock_scores(self, user: str) -> str:
        from .config import RUBRIC
        scores = {
            c.key: {
                "raw_score": self._score_from(user, c.key),
                "justification": f"[mock] Assessment of {c.name.lower()}.",
            }
            for c in RUBRIC
        }
        payload = {
            "criterion_scores": scores,
            "summary": "[mock] Reasonable submission with clear strengths.",
            "strengths": ["[mock] clear objective", "[mock] plausible method"],
            "weaknesses": ["[mock] limited validation", "[mock] cost unclear"],
            "integrity_flags": [],
        }
        return json.dumps(payload)

    def _mock_innovation(self, user: str) -> str:
        payload = {
            "main_innovations": ["[mock] novel sensing pipeline"],
            "creative_aspects": ["[mock] cross-domain analogy"],
            "unique_advantages": ["[mock] low-cost hardware"],
            "strong_technical_ideas": ["[mock] self-calibrating model"],
            "potential_research_contributions": ["[mock] open benchmark"],
            "weaknesses_or_missing_parts": ["[mock] no field trials"],
        }
        return json.dumps(payload)

    def _mock_comparison(self, user: str) -> str:
        ids = re.findall(r'"participant_id"\s*:\s*"([^"]+)"', user)
        if not ids:
            ids = re.findall(r"\b(P\d+|participant_\w+|\S+?)\b(?=:)", user)[:5]
        payload = {
            "ranking": ids,
            "rationale": "[mock] Ranked by aggregate strength of method and impact.",
            "pairwise_notes": ["[mock] top answer has stronger validation."],
            "overlapping_ideas": ["[mock] both use remote sensing data"],
            "unique_ideas": {i: [f"[mock] unique idea from {i}"] for i in ids},
            "complementary_ideas": ["[mock] fusion of A's sensor + B's model"],
        }
        return json.dumps(payload)

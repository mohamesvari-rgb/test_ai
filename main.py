#!/usr/bin/env python3
"""
Command-line entry point for the Scientific Evaluation Agent.

Examples
--------
# Real evaluation with the engine set in .env (LLM_PROVIDER, default: avalai):
python main.py --challenge examples/mof_co2_capture/challenge.json \
               --submissions examples/mof_co2_capture/submissions \
               --out output/report

# Fully offline with a local Ollama model:
python main.py ... --provider ollama --model qwen3.5:9b

# Offline demo with the deterministic mock backend (no API key needed):
python main.py --challenge config/challenge_example.json \
               --submissions examples/submissions \
               --out output/report --mock

# Markdown report instead of Word:
python main.py ... --format md --out output/report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:  # API keys / provider choice live in .env
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:  # pragma: no cover
    pass

from scientific_evaluator import ScientificEvaluationAgent  # noqa: E402
from scientific_evaluator.config import PROVIDERS, SETTINGS  # noqa: E402
from scientific_evaluator.llm_client import build_llm_client  # noqa: E402


def _build_llm(args):
    provider = "mock" if args.mock else args.provider
    return build_llm_client(
        provider, api_key=args.api_key, model=args.model, base_url=args.base_url
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate scientific submissions against a challenge."
    )
    parser.add_argument("--challenge", required=True,
                        help="Path to challenge JSON file.")
    parser.add_argument("--submissions", required=True,
                        help="Folder containing participant .docx files.")
    parser.add_argument("--out", default="output/report",
                        help="Output report path (extension is set by --format).")
    parser.add_argument("--format", default="both",
                        choices=["docx", "pdf", "both", "md"],
                        help="Report format(s). Default: both (Word + PDF).")
    parser.add_argument("--lang", default=None,
                        help="Report language, e.g. 'Persian' or 'English' "
                             "(defaults to config.SETTINGS.report_language).")
    parser.add_argument("--provider", default=None, choices=list(PROVIDERS),
                        help="AI engine (default: LLM_PROVIDER from .env, else avalai).")
    parser.add_argument("--model", default=None,
                        help="Model id (defaults to the provider's model in .env).")
    parser.add_argument("--api-key", default=None,
                        help="API key (defaults to the provider's key in .env).")
    parser.add_argument("--base-url", default=None,
                        help="Override the API base URL (custom/OpenAI-compatible).")
    parser.add_argument("--mock", action="store_true",
                        help="Use the offline deterministic mock backend.")
    parser.add_argument("--json-out", default=None,
                        help="Optional path to also dump the raw result as JSON.")
    args = parser.parse_args(argv)

    if args.lang:
        SETTINGS.report_language = args.lang
    fmt = args.format

    try:
        llm = _build_llm(args)
    except Exception as exc:  # noqa: BLE001
        print(f"error: could not initialize LLM backend: {exc}", file=sys.stderr)
        return 2

    def progress(msg: str) -> None:
        print(f"  · {msg}", file=sys.stderr)

    progress(f"Engine: {llm.description}")

    agent = ScientificEvaluationAgent(args.challenge, llm, progress=progress)

    print(f"Evaluating submissions in '{args.submissions}' ...", file=sys.stderr)
    result = agent.run(args.submissions)

    written = agent.export_report(result, args.out, fmt=fmt)
    print("\nReport(s) written:")
    for p in written:
        print(f"  - {p}")

    # Console summary of the ranking.
    print("\nRanking:")
    for rank, e in enumerate(result.ranked_evaluations(), start=1):
        print(f"  {rank}. {e.participant_id:<25} {e.total_score:6.1f} / 100")

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Raw JSON written to: {args.json_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

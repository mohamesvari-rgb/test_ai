#!/usr/bin/env python3
"""
Command-line entry point for the Scientific Evaluation Agent.

Examples
--------
# Real evaluation with Claude (needs ANTHROPIC_API_KEY):
python main.py --challenge config/challenge_example.json \
               --submissions examples/submissions \
               --out output/report.docx

# Offline demo with the deterministic mock backend (no API key needed):
python main.py --challenge config/challenge_example.json \
               --submissions examples/submissions \
               --out output/report.docx --mock

# Markdown report instead of Word:
python main.py ... --format md --out output/report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scientific_evaluator import ScientificEvaluationAgent
from scientific_evaluator.llm_client import AnthropicLLMClient, MockLLMClient


def _build_llm(args):
    if args.mock:
        return MockLLMClient()
    return AnthropicLLMClient(model=args.model)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate scientific submissions against a challenge."
    )
    parser.add_argument("--challenge", required=True,
                        help="Path to challenge JSON file.")
    parser.add_argument("--submissions", required=True,
                        help="Folder containing participant .docx files.")
    parser.add_argument("--out", default="output/report.docx",
                        help="Output report path.")
    parser.add_argument("--format", default=None, choices=["docx", "md"],
                        help="Report format (inferred from --out if omitted).")
    parser.add_argument("--model", default=None,
                        help="LLM model id (defaults to config.SETTINGS.model).")
    parser.add_argument("--mock", action="store_true",
                        help="Use the offline deterministic mock backend.")
    parser.add_argument("--json-out", default=None,
                        help="Optional path to also dump the raw result as JSON.")
    args = parser.parse_args(argv)

    fmt = args.format or ("md" if str(args.out).lower().endswith(".md") else "docx")

    try:
        llm = _build_llm(args)
    except Exception as exc:  # noqa: BLE001
        print(f"error: could not initialize LLM backend: {exc}", file=sys.stderr)
        return 2

    def progress(msg: str) -> None:
        print(f"  · {msg}", file=sys.stderr)

    agent = ScientificEvaluationAgent(args.challenge, llm, progress=progress)

    print(f"Evaluating submissions in '{args.submissions}' ...", file=sys.stderr)
    result = agent.run(args.submissions)

    out = agent.export_report(result, args.out, fmt=fmt)
    print(f"\nReport written to: {out}")

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

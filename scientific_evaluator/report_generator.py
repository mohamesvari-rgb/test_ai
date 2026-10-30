"""
Markdown export of the evaluation report, handy for review and diffing.

Word and PDF reports are built from the blocks in report_builder.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

from .config import RUBRIC
from .models import EvaluationResult

# ---------------------------------------------------------------------------
# Markdown export (dependency-free, handy for review/diffing)
# ---------------------------------------------------------------------------
class MarkdownReportGenerator:
    """Renders an EvaluationResult to a Markdown string / file."""

    def render(self, result: EvaluationResult) -> str:
        ch = result.challenge
        lines: List[str] = [
            f"# Scientific Evaluation Report",
            f"**Challenge:** {ch.title}  |  **Field:** {ch.field}",
            "",
            "## 1. Challenge Summary",
            ch.background,
            "",
            "**Objectives:**",
            *[f"- {o}" for o in ch.objectives],
            "",
            "## 2. Evaluation Rubric",
            "| Criterion | Weight (pts) | Measures |",
            "|---|---|---|",
            *[f"| {c.name} | {c.max_points} | {c.description} |" for c in RUBRIC],
            "",
            "## 3. Score Table",
        ]
        ranked = result.ranked_evaluations()
        keys = [c.key for c in RUBRIC]
        header = "| Rank | Participant | " + " | ".join(k for k in keys) + " | Total |"
        sep = "|---" * (len(keys) + 3) + "|"
        lines += [header, sep]
        for rank, e in enumerate(ranked, start=1):
            cells = [
                str(rank),
                e.participant_id,
                *[
                    f"{(e.score_by_key(k).raw_score):.0f}" if e.score_by_key(k) else "-"
                    for k in keys
                ],
                f"{e.total_score:.1f}",
            ]
            lines.append("| " + " | ".join(cells) + " |")

        lines += ["", "## 4. Individual Reviews"]
        for e in ranked:
            lines += [
                f"### {e.participant_id} - {e.title}  ({e.total_score:.1f}/100)",
                e.summary,
                "",
                "**Per-criterion:**",
                *[
                    f"- **{cs.name}**: {cs.raw_score:.0f}/10 - {cs.justification}"
                    for cs in e.criterion_scores
                ],
                "",
                "**Strengths:** " + "; ".join(e.strengths),
                "**Weaknesses:** " + "; ".join(e.weaknesses),
                "",
            ]

        lines += ["## 5. Innovation & Creativity"]
        for e in ranked:
            inv = e.innovation
            lines += [
                f"### {e.participant_id}",
                "- **Main innovations:** " + "; ".join(inv.main_innovations),
                "- **Creative aspects:** " + "; ".join(inv.creative_aspects),
                "- **Unique advantages:** " + "; ".join(inv.unique_advantages),
                "- **Strong technical ideas:** " + "; ".join(inv.strong_technical_ideas),
                "- **Research contributions:** "
                + "; ".join(inv.potential_research_contributions),
                "- **Weaknesses / missing:** "
                + "; ".join(inv.weaknesses_or_missing_parts),
                "",
            ]

        lines += ["## 6. Comparative Ranking"]
        for rank, pid in enumerate(result.comparison.ranking, start=1):
            lines.append(f"{rank}. {pid}")
        lines += ["", "**Rationale:** " + result.comparison.rationale, ""]
        if result.comparison.complementary_ideas:
            lines += ["**Complementary ideas:**",
                      *[f"- {x}" for x in result.comparison.complementary_ideas], ""]

        lines += [
            "## 7. Final Recommendation",
            result.final_recommendation,
            "",
            "## 8. Synthesized Improved Solution",
            result.synthesized_solution,
            "",
        ]
        return "\n".join(lines)

    def generate(self, result: EvaluationResult, out_path: Union[str, Path]) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(self.render(result), encoding="utf-8")
        return out_path

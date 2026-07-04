"""
Report generation module.

Builds the final integrated evaluation report and exports it as a Word (.docx)
file. Also offers a Markdown export for quick review / diffing. The report
layout follows the required structure:

    1. Summary of the challenge
    2. Evaluation criteria and scoring rubric
    3. Individual review of each participant
    4. Score table
    5. Innovation and creativity table
    6. Strengths and weaknesses of each answer
    7. Comparative ranking
    8. Final recommendation
    9. Synthesized improved solution
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

from .config import RUBRIC
from .models import EvaluationResult, SubmissionEvaluation

try:
    import docx
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    _HAS_DOCX = True
except Exception:  # pragma: no cover
    _HAS_DOCX = False


# ---------------------------------------------------------------------------
# Word (.docx) export
# ---------------------------------------------------------------------------
class WordReportGenerator:
    """Renders an EvaluationResult to a .docx report."""

    def generate(self, result: EvaluationResult, out_path: Union[str, Path]) -> Path:
        if not _HAS_DOCX:
            raise RuntimeError(
                "python-docx is required to export Word reports. "
                "Run `pip install python-docx`."
            )
        doc = docx.Document()
        self._title(doc, "Scientific Evaluation Report")
        doc.add_paragraph(
            f"Challenge: {result.challenge.title}  |  Field: {result.challenge.field}"
        ).italic = True

        self._challenge_summary(doc, result)
        self._rubric_section(doc)
        self._score_table(doc, result)
        self._individual_reviews(doc, result)
        self._innovation_table(doc, result)
        self._ranking_section(doc, result)
        self._recommendation_section(doc, result)
        self._synthesis_section(doc, result)

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out_path))
        return out_path

    # -- helpers ------------------------------------------------------------
    def _title(self, doc, text: str) -> None:
        h = doc.add_heading(text, level=0)
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def _challenge_summary(self, doc, result: EvaluationResult) -> None:
        ch = result.challenge
        doc.add_heading("1. Challenge Summary", level=1)
        doc.add_paragraph(ch.background)
        doc.add_heading("Objectives", level=2)
        for o in ch.objectives:
            doc.add_paragraph(o, style="List Bullet")
        if ch.constraints:
            doc.add_heading("Constraints", level=2)
            for c in ch.constraints:
                doc.add_paragraph(c, style="List Bullet")
        if ch.expected_outputs:
            doc.add_heading("Expected Outputs", level=2)
            for e in ch.expected_outputs:
                doc.add_paragraph(e, style="List Bullet")

    def _rubric_section(self, doc) -> None:
        doc.add_heading("2. Evaluation Criteria & Scoring Rubric", level=1)
        doc.add_paragraph(
            "Each criterion is scored 0-10 by the evaluation engine and "
            "contributes (raw/10 x max points) to a final score out of 100."
        )
        table = doc.add_table(rows=1, cols=3)
        table.style = "Light Grid Accent 1"
        hdr = table.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text = "Criterion", "Weight (pts)", "What it measures"
        for c in RUBRIC:
            row = table.add_row().cells
            row[0].text = c.name
            row[1].text = str(c.max_points)
            row[2].text = c.description
        doc.add_paragraph(f"Total: {sum(c.max_points for c in RUBRIC):.0f} points").bold = True

    def _score_table(self, doc, result: EvaluationResult) -> None:
        doc.add_heading("3. Score Table", level=1)
        ranked = result.ranked_evaluations()
        keys = [c.key for c in RUBRIC]
        # Columns: Rank, Participant, each criterion (short), Total
        table = doc.add_table(rows=1, cols=3 + len(keys))
        table.style = "Light Grid Accent 1"
        hdr = table.rows[0].cells
        hdr[0].text = "Rank"
        hdr[1].text = "Participant"
        for i, c in enumerate(RUBRIC):
            hdr[2 + i].text = c.name.split()[0][:8]
        hdr[-1].text = "Total /100"
        for rank, e in enumerate(ranked, start=1):
            row = table.add_row().cells
            row[0].text = str(rank)
            row[1].text = e.participant_id
            for i, key in enumerate(keys):
                cs = e.score_by_key(key)
                row[2 + i].text = f"{cs.raw_score:.0f}" if cs else "-"
            row[-1].text = f"{e.total_score:.1f}"

    def _individual_reviews(self, doc, result: EvaluationResult) -> None:
        doc.add_heading("4. Individual Reviews", level=1)
        for e in result.ranked_evaluations():
            doc.add_heading(f"{e.participant_id} - {e.title}", level=2)
            doc.add_paragraph(f"Final score: {e.total_score:.1f} / 100").bold = True
            if e.summary:
                doc.add_paragraph(e.summary)
            doc.add_paragraph("Per-criterion justification:").bold = True
            for cs in e.criterion_scores:
                p = doc.add_paragraph(style="List Bullet")
                p.add_run(f"{cs.name}: {cs.raw_score:.0f}/10 - ").bold = True
                p.add_run(cs.justification or "(no justification)")
            if e.strengths:
                doc.add_paragraph("Strengths:").bold = True
                for s in e.strengths:
                    doc.add_paragraph(s, style="List Bullet")
            if e.weaknesses:
                doc.add_paragraph("Weaknesses:").bold = True
                for w in e.weaknesses:
                    doc.add_paragraph(w, style="List Bullet")
            if e.integrity_flags:
                p = doc.add_paragraph()
                p.add_run(f"Integrity flags (penalty -{e.penalty:.0f}): ").bold = True
                p.add_run("; ".join(e.integrity_flags))

    def _innovation_table(self, doc, result: EvaluationResult) -> None:
        doc.add_heading("5. Innovation & Creativity Table", level=1)
        table = doc.add_table(rows=1, cols=4)
        table.style = "Light Grid Accent 1"
        hdr = table.rows[0].cells
        hdr[0].text = "Participant"
        hdr[1].text = "Main Innovations"
        hdr[2].text = "Creative / Unique Advantages"
        hdr[3].text = "Weaknesses / Missing"
        for e in result.ranked_evaluations():
            inv = e.innovation
            row = table.add_row().cells
            row[0].text = e.participant_id
            row[1].text = "\n".join(f"- {x}" for x in inv.main_innovations) or "-"
            row[2].text = "\n".join(
                f"- {x}" for x in (inv.creative_aspects + inv.unique_advantages)
            ) or "-"
            row[3].text = "\n".join(
                f"- {x}" for x in inv.weaknesses_or_missing_parts
            ) or "-"

    def _ranking_section(self, doc, result: EvaluationResult) -> None:
        doc.add_heading("6. Comparative Ranking", level=1)
        for rank, pid in enumerate(result.comparison.ranking, start=1):
            ev = next((e for e in result.evaluations if e.participant_id == pid), None)
            score = f"{ev.total_score:.1f}" if ev else "-"
            doc.add_paragraph(f"{rank}. {pid}  ({score}/100)", style="List Number")
        if result.comparison.rationale:
            doc.add_heading("Why this order", level=2)
            doc.add_paragraph(result.comparison.rationale)
        if result.comparison.pairwise_notes:
            doc.add_heading("Head-to-head notes", level=2)
            for n in result.comparison.pairwise_notes:
                doc.add_paragraph(n, style="List Bullet")
        if result.comparison.overlapping_ideas:
            doc.add_heading("Overlapping ideas", level=2)
            for x in result.comparison.overlapping_ideas:
                doc.add_paragraph(x, style="List Bullet")
        if result.comparison.complementary_ideas:
            doc.add_heading("Complementary ideas", level=2)
            for x in result.comparison.complementary_ideas:
                doc.add_paragraph(x, style="List Bullet")

    def _recommendation_section(self, doc, result: EvaluationResult) -> None:
        doc.add_heading("7. Final Recommendation", level=1)
        doc.add_paragraph(result.final_recommendation or "(none)")

    def _synthesis_section(self, doc, result: EvaluationResult) -> None:
        doc.add_heading("8. Synthesized Improved Solution", level=1)
        doc.add_paragraph(
            "A single solution combining the strongest ideas across all "
            "submissions while addressing their common weaknesses."
        ).italic = True
        for block in (result.synthesized_solution or "(none)").split("\n"):
            block = block.strip()
            if not block:
                continue
            # Treat lines ending in ':' or wrapped in ** as sub-headings.
            if block.startswith("#"):
                doc.add_heading(block.lstrip("# ").strip(), level=2)
            else:
                doc.add_paragraph(block)


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

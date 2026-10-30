"""
Report content builder (single source of truth).

Builds the report as an ordered list of typed, renderer-agnostic *blocks*
(headings, paragraphs, bullet lists, tables, images). The Word renderer and the
PDF renderer both consume the SAME blocks, so the two outputs never diverge.

``build_report_blocks`` writes the Persian report and ``build_english_blocks``
the English one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .config import RUBRIC
from .models import EvaluationResult
from .text_cleanup import clean_inline

# Persian digit conversion for a fully-localized look.
_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(value) -> str:
    """Render a number/string with Persian digits."""
    return str(value).translate(_FA_DIGITS)


# Lookups: criterion key -> Persian label (fall back to English if unset).
_NAME_FA = {c.key: (c.name_fa or c.name) for c in RUBRIC}
_SHORT_FA = {c.key: (c.short_fa or c.name.split()[0]) for c in RUBRIC}
# Short enough for ten score columns to fit an A4 page.
_SHORT_EN = {
    "relevance": "Rel.", "scientific_accuracy": "Acc.", "methodology": "Meth.",
    "innovation": "Innov.", "creativity": "Creat.", "feasibility": "Feas.",
    "technical_depth": "Depth", "clarity": "Clar.", "impact": "Impact",
    "risk_awareness": "Risk",
}


# ---------------------------------------------------------------------------
# Block types
# ---------------------------------------------------------------------------
@dataclass
class Block:
    """Base class for a renderable report element."""


@dataclass
class Title(Block):
    text: str
    subtitles: List[str] = field(default_factory=list)


@dataclass
class Heading(Block):
    text: str
    level: int = 1


@dataclass
class Para(Block):
    text: str
    bold: bool = False


@dataclass
class Bullets(Block):
    items: List[str] = field(default_factory=list)


@dataclass
class Table(Block):
    headers: List[str]
    rows: List[List[str]]
    # Optional relative column widths (must sum ~1.0); None = equal columns.
    widths: Optional[List[float]] = None


def _table_cells(line: str) -> List[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _markdown_blocks(text: str) -> List["Block"]:
    """Convert model-written Markdown into report blocks (headings, lists, tables)."""
    blocks: List[Block] = []
    bullets: List[str] = []
    table: List[List[str]] = []

    def flush() -> None:
        if bullets:
            blocks.append(Bullets(list(bullets)))
            bullets.clear()
        if table:
            header, rows = table[0], table[1:]
            rows = [(r + [""] * len(header))[:len(header)] for r in rows]
            blocks.append(Table(headers=header, rows=rows))
            table.clear()

    for raw in text.split("\n"):
        line = raw.strip()
        if line.startswith("|") and line.count("|") >= 2:
            if bullets:
                flush()
            if not re.fullmatch(r"[|:\-\s]+", line):   # skip the |---|---| rule
                table.append(_table_cells(line))
            continue
        if table:
            flush()
        if not line or re.fullmatch(r"[-*_]{3,}", line):
            flush()
            continue
        heading = re.match(r"#{1,6}\s*(.+)$", line)
        item = re.match(r"(?:[-*•]|[0-9۰-۹]+[.)])\s+(.+)$", line)
        if heading:
            flush()
            blocks.append(Heading(heading.group(1), 2))
        elif item:
            bullets.append(item.group(1))
        else:
            flush()
            blocks.append(Para(line))
    flush()
    return blocks


def _clean_block(block: "Block") -> "Block":
    """Strip Markdown/LaTeX markers from every piece of text in a block."""
    if isinstance(block, Title):
        block.text = clean_inline(block.text)
        block.subtitles = [clean_inline(s) for s in block.subtitles]
    elif isinstance(block, (Heading, Para)):
        block.text = clean_inline(block.text)
    elif isinstance(block, Bullets):
        block.items = [clean_inline(i) for i in block.items]
    elif isinstance(block, Table):
        block.headers = [clean_inline(h) for h in block.headers]
        block.rows = [[clean_inline(c) for c in row] for row in block.rows]
    return block


@dataclass
class Image(Block):
    path: str
    caption: str = ""


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
def _bul(items) -> List[str]:
    return [str(x).strip() for x in items if str(x).strip()]


def build_report_blocks(
    result: EvaluationResult, chart_paths: Optional[List[Path]] = None
) -> List[Block]:
    """Assemble the full report as an ordered list of blocks (in Persian)."""
    chart_paths = chart_paths or []
    ch = result.challenge
    ranked = result.ranked_evaluations()
    blocks: List[Block] = []

    # Cover
    blocks.append(Title(
        text="گزارش ارزیابی علمی",
        subtitles=[f"چالش: {ch.title}", f"حوزه: {ch.field}"],
    ))

    # 1) Challenge summary
    blocks.append(Heading("۱. خلاصه چالش", 1))
    blocks.append(Para(ch.background))
    blocks.append(Heading("اهداف", 2))
    blocks.append(Bullets(_bul(ch.objectives)))
    if ch.constraints:
        blocks.append(Heading("محدودیت‌ها", 2))
        blocks.append(Bullets(_bul(ch.constraints)))
    if ch.expected_outputs:
        blocks.append(Heading("خروجی‌های مورد انتظار", 2))
        blocks.append(Bullets(_bul(ch.expected_outputs)))

    # 2) Rubric
    blocks.append(Heading("۲. معیارها و سامانه امتیازدهی", 1))
    blocks.append(Para(
        "هر معیار توسط موتور ارزیابی از ۰ تا ۱۰ امتیاز می‌گیرد و سهم آن در امتیاز "
        "نهایی برابر است با (امتیاز خام ÷ ۱۰) × وزن معیار. مجموع وزن‌ها ۱۰۰ است."))
    rubric_rows = [
        [c.name_fa or c.name, fa(c.max_points), c.description_fa or c.description]
        for c in RUBRIC
    ]
    rubric_rows.append(["جمع کل", fa(100), "—"])
    blocks.append(Table(["معیار", "وزن (امتیاز)", "آنچه می‌سنجد"], rubric_rows,
                        widths=[0.26, 0.14, 0.60]))

    # 3) Score table + charts
    blocks.append(Heading("۳. جدول امتیازها و نمودارهای تحلیلی", 1))
    keys = [c.key for c in RUBRIC]
    headers = ["رتبه", "شرکت‌کننده"] + [_SHORT_FA[c.key] for c in RUBRIC] + ["امتیاز کل"]
    score_rows = []
    for rank, e in enumerate(ranked, start=1):
        row = [fa(rank), e.participant_id]
        for k in keys:
            cs = e.score_by_key(k)
            row.append(fa(f"{cs.raw_score:.0f}") if cs else "-")
        row.append(fa(f"{e.total_score:.1f}"))
        score_rows.append(row)
    blocks.append(Table(headers, score_rows))
    for p in chart_paths:
        blocks.append(Image(str(p)))

    # 4) Individual reviews
    blocks.append(Heading("۴. بررسی انفرادی هر پاسخ", 1))
    for e in ranked:
        blocks.append(Heading(f"{e.participant_id} — {clean_inline(e.title)}", 2))
        blocks.append(Para(f"امتیاز نهایی: {fa(f'{e.total_score:.1f}')} از ۱۰۰", bold=True))
        if e.summary:
            blocks.append(Para(e.summary))
        blocks.append(Para("توجیه امتیاز هر معیار:", bold=True))
        blocks.append(Bullets([
            f"{_NAME_FA.get(cs.key, cs.name)}: {fa(f'{cs.raw_score:.0f}')}/۱۰ — "
            f"{cs.justification or '—'}"
            for cs in e.criterion_scores
        ]))
        if e.strengths:
            blocks.append(Para("نقاط قوت:", bold=True))
            blocks.append(Bullets(_bul(e.strengths)))
        if e.weaknesses:
            blocks.append(Para("نقاط ضعف:", bold=True))
            blocks.append(Bullets(_bul(e.weaknesses)))
        if e.integrity_flags:
            blocks.append(Para(
                f"هشدارهای صحت (کسر امتیاز {fa(f'{e.penalty:.0f}')}): "
                + "؛ ".join(e.integrity_flags), bold=True))

    # 5) Innovation & creativity table
    blocks.append(Heading("۵. جدول نوآوری و خلاقیت", 1))
    inv_rows = []
    for e in ranked:
        inv = e.innovation
        inv_rows.append([
            e.participant_id,
            "\n".join(f"• {x}" for x in inv.main_innovations) or "—",
            "\n".join(f"• {x}" for x in (inv.creative_aspects + inv.unique_advantages)) or "—",
            "\n".join(f"• {x}" for x in inv.weaknesses_or_missing_parts) or "—",
        ])
    blocks.append(Table(
        ["شرکت‌کننده", "نوآوری‌های اصلی",
         "جنبه‌های خلاقانه / مزیت‌های منحصربه‌فرد", "ضعف‌ها / کاستی‌ها"],
        inv_rows, widths=[0.16, 0.28, 0.31, 0.25]))

    # 6) Per-idea improvement solutions
    blocks.append(Heading("۶. راه‌حل‌های بهبود هر ایده", 1))
    blocks.append(Para(
        "برای هر ایده کلیدی در هر پاسخ، مجموعه‌ای از راه‌حل‌ها ارائه شده است تا آن "
        "ایده را در نزدیک‌شدن به حل چالش مؤثرتر کند."))
    any_improvements = False
    for e in ranked:
        if not e.idea_improvements:
            continue
        any_improvements = True
        blocks.append(Heading(f"{e.participant_id}", 2))
        imp_rows = []
        for imp in e.idea_improvements:
            imp_rows.append([
                imp.idea or "—",
                "\n".join(f"• {x}" for x in imp.improvements) or "—",
                imp.expected_effect or "—",
            ])
        blocks.append(Table(["ایده", "راه‌حل‌های بهبود", "اثر مورد انتظار"],
                            imp_rows, widths=[0.30, 0.45, 0.25]))
    if not any_improvements:
        blocks.append(Para("—"))

    # 7) Comparison: salient & distinctive points + ranking
    comp = result.comparison
    blocks.append(Heading("۷. مقایسه پاسخ‌ها: نقاط برجسته و متمایز", 1))
    cmp_rows = []
    for e in ranked:
        pid = e.participant_id
        cmp_rows.append([
            pid,
            "\n".join(f"• {x}" for x in comp.salient_points.get(pid, [])) or "—",
            "\n".join(f"• {x}" for x in comp.distinctive_points.get(pid, [])) or "—",
        ])
    blocks.append(Table(["شرکت‌کننده", "نقاط برجسته", "نقاط متمایز"],
                        cmp_rows, widths=[0.18, 0.41, 0.41]))

    blocks.append(Heading("رتبه‌بندی نهایی", 2))
    rank_lines = []
    for rank, pid in enumerate(comp.ranking, start=1):
        ev = next((e for e in result.evaluations if e.participant_id == pid), None)
        score = fa(f"{ev.total_score:.1f}") if ev else "—"
        rank_lines.append(f"{fa(rank)}. {pid} ({score} از ۱۰۰)")
    blocks.append(Bullets(rank_lines))
    if comp.rationale:
        blocks.append(Heading("دلیل این ترتیب", 2))
        blocks.append(Para(comp.rationale))
    if comp.pairwise_notes:
        blocks.append(Heading("یادداشت‌های مقایسه دوبه‌دو", 2))
        blocks.append(Bullets(_bul(comp.pairwise_notes)))
    if comp.overlapping_ideas:
        blocks.append(Heading("ایده‌های مشترک", 2))
        blocks.append(Bullets(_bul(comp.overlapping_ideas)))
    if comp.complementary_ideas:
        blocks.append(Heading("ایده‌های مکمل", 2))
        blocks.append(Bullets(_bul(comp.complementary_ideas)))

    # 8) Final recommendation
    blocks.append(Heading("۸. توصیه نهایی", 1))
    blocks += _markdown_blocks(result.final_recommendation or "—")

    # 9) Integrated comprehensive solution
    blocks.append(Heading("۹. راه‌حل جامع و نهایی (تلفیق و بهبود ایده‌ها)", 1))
    blocks.append(Para(
        "راه‌حل زیر از ترکیب ایده‌های موجود در پاسخ‌ها به همراه راه‌حل‌های بهبود "
        "آن‌ها ساخته شده است تا یک راه‌حل جامع و قابل‌قبول برای چالش به دست آید.",
        bold=True))
    blocks.append(Heading("نقاط قوت و رویکرد هر پاسخ", 2))
    blocks.append(Table(
        ["پاسخ", "امتیاز", "نقاط قوت", "ایده‌های کلیدی"],
        [[
            e.participant_id,
            fa(round(e.total_score, 1)),
            "\n".join(f"• {x}" for x in _bul(e.strengths[:3])) or "—",
            "\n".join(f"• {x}" for x in _bul(e.innovation.main_innovations[:3])) or "—",
        ] for e in ranked],
        widths=[0.16, 0.08, 0.38, 0.38],
    ))
    blocks += _markdown_blocks(result.synthesized_solution or "—")

    return [_clean_block(b) for b in blocks]


def build_english_blocks(result: EvaluationResult) -> List[Block]:
    """The same report in English. It has no charts: their labels are Persian."""
    ch = result.challenge
    ranked = result.ranked_evaluations()
    comp = result.comparison
    blocks: List[Block] = [Title(
        text="Scientific Evaluation Report",
        subtitles=[f"Challenge: {ch.title}", f"Field: {ch.field}"],
    )]

    blocks.append(Heading("1. Challenge Summary", 1))
    blocks.append(Para(ch.background))
    blocks.append(Heading("Objectives", 2))
    blocks.append(Bullets(_bul(ch.objectives)))
    if ch.constraints:
        blocks.append(Heading("Constraints", 2))
        blocks.append(Bullets(_bul(ch.constraints)))
    if ch.expected_outputs:
        blocks.append(Heading("Expected Outputs", 2))
        blocks.append(Bullets(_bul(ch.expected_outputs)))

    blocks.append(Heading("2. Evaluation Criteria and Scoring", 1))
    blocks.append(Para(
        "Each criterion is scored from 0 to 10 and contributes "
        "(raw score ÷ 10) × its weight to a final score out of 100."))
    rubric_rows = [[c.name, str(c.max_points), c.description] for c in RUBRIC]
    rubric_rows.append(["Total", "100", "—"])
    blocks.append(Table(["Criterion", "Weight (pts)", "What it measures"], rubric_rows,
                        widths=[0.26, 0.14, 0.60]))

    blocks.append(Heading("3. Score Table", 1))
    keys = [c.key for c in RUBRIC]
    score_rows = []
    for rank, e in enumerate(ranked, start=1):
        row = [str(rank), e.participant_id]
        for k in keys:
            cs = e.score_by_key(k)
            row.append(f"{cs.raw_score:.0f}" if cs else "-")
        row.append(f"{e.total_score:.1f}")
        score_rows.append(row)
    blocks.append(Table(
        ["Rank", "Participant"] + [_SHORT_EN.get(c.key, c.key) for c in RUBRIC] + ["Total"],
        score_rows))

    blocks.append(Heading("4. Individual Reviews", 1))
    for e in ranked:
        blocks.append(Heading(f"{e.participant_id} — {clean_inline(e.title)}", 2))
        blocks.append(Para(f"Final score: {e.total_score:.1f} / 100", bold=True))
        if e.summary:
            blocks.append(Para(e.summary))
        blocks.append(Para("Justification per criterion:", bold=True))
        blocks.append(Bullets([
            f"{cs.name}: {cs.raw_score:.0f}/10 — {cs.justification or '—'}"
            for cs in e.criterion_scores
        ]))
        if e.strengths:
            blocks.append(Para("Strengths:", bold=True))
            blocks.append(Bullets(_bul(e.strengths)))
        if e.weaknesses:
            blocks.append(Para("Weaknesses:", bold=True))
            blocks.append(Bullets(_bul(e.weaknesses)))
        if e.integrity_flags:
            blocks.append(Para(
                f"Integrity flags (penalty {e.penalty:.0f}): "
                + "; ".join(e.integrity_flags), bold=True))

    blocks.append(Heading("5. Innovation and Creativity", 1))
    blocks.append(Table(
        ["Participant", "Main innovations", "Creative aspects / unique advantages",
         "Weaknesses / missing parts"],
        [[
            e.participant_id,
            "\n".join(f"• {x}" for x in e.innovation.main_innovations) or "—",
            "\n".join(f"• {x}" for x in (e.innovation.creative_aspects
                                         + e.innovation.unique_advantages)) or "—",
            "\n".join(f"• {x}" for x in e.innovation.weaknesses_or_missing_parts) or "—",
        ] for e in ranked],
        widths=[0.16, 0.28, 0.31, 0.25]))

    blocks.append(Heading("6. Improvements for Each Idea", 1))
    improved = [e for e in ranked if e.idea_improvements]
    for e in improved:
        blocks.append(Heading(e.participant_id, 2))
        blocks.append(Table(
            ["Idea", "Improvements", "Expected effect"],
            [[
                imp.idea or "—",
                "\n".join(f"• {x}" for x in imp.improvements) or "—",
                imp.expected_effect or "—",
            ] for imp in e.idea_improvements],
            widths=[0.30, 0.45, 0.25]))
    if not improved:
        blocks.append(Para("—"))

    blocks.append(Heading("7. Comparison: Salient and Distinctive Points", 1))
    blocks.append(Table(
        ["Participant", "Salient points", "Distinctive points"],
        [[
            e.participant_id,
            "\n".join(f"• {x}" for x in comp.salient_points.get(e.participant_id, [])) or "—",
            "\n".join(f"• {x}" for x in comp.distinctive_points.get(e.participant_id, [])) or "—",
        ] for e in ranked],
        widths=[0.18, 0.41, 0.41]))
    blocks.append(Heading("Final ranking", 2))
    rank_lines = []
    for rank, pid in enumerate(comp.ranking, start=1):
        ev = next((e for e in result.evaluations if e.participant_id == pid), None)
        rank_lines.append(f"{rank}. {pid} ({f'{ev.total_score:.1f}' if ev else '—'} / 100)")
    blocks.append(Bullets(rank_lines))
    if comp.rationale:
        blocks.append(Heading("Why this order", 2))
        blocks.append(Para(comp.rationale))
    if comp.pairwise_notes:
        blocks.append(Heading("Head-to-head notes", 2))
        blocks.append(Bullets(_bul(comp.pairwise_notes)))
    if comp.overlapping_ideas:
        blocks.append(Heading("Overlapping ideas", 2))
        blocks.append(Bullets(_bul(comp.overlapping_ideas)))
    if comp.complementary_ideas:
        blocks.append(Heading("Complementary ideas", 2))
        blocks.append(Bullets(_bul(comp.complementary_ideas)))

    blocks.append(Heading("8. Final Recommendation", 1))
    blocks += _markdown_blocks(result.final_recommendation or "—")

    blocks.append(Heading("9. Comprehensive Solution", 1))
    blocks.append(Para(
        "This solution combines the ideas found in the answers with their "
        "improvements into one comprehensive solution to the challenge.", bold=True))
    blocks.append(Heading("Strengths and approach of each answer", 2))
    blocks.append(Table(
        ["Answer", "Score", "Strengths", "Key ideas"],
        [[
            e.participant_id,
            f"{e.total_score:.1f}",
            "\n".join(f"• {x}" for x in _bul(e.strengths[:3])) or "—",
            "\n".join(f"• {x}" for x in _bul(e.innovation.main_innovations[:3])) or "—",
        ] for e in ranked],
        widths=[0.16, 0.08, 0.38, 0.38]))
    blocks += _markdown_blocks(result.synthesized_solution or "—")

    return [_clean_block(b) for b in blocks]

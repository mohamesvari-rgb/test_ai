"""
Configuration for the Scientific Evaluation Agent.

This module defines the evaluation rubric (the transparent, weighted scoring
system) and global settings. Everything about *how* answers are scored lives
here so the rubric can be audited and tuned in one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# Rubric
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RubricCriterion:
    """A single scored dimension of the rubric.

    Each criterion is scored by the evaluation engine on a 0-10 raw scale.
    The contribution to the final /100 score is:

        contribution = (raw_score / 10) * max_points

    The sum of ``max_points`` across all criteria equals 100.
    """

    key: str
    name: str
    max_points: float          # weight: maximum points this criterion can add to /100
    description: str           # what "good" looks like for this dimension
    guidance: str              # scoring guidance handed to the LLM
    name_fa: str = ""          # Persian criterion name (for the Persian report)
    short_fa: str = ""         # short Persian label (for narrow table columns)
    description_fa: str = ""   # Persian description (for the Persian rubric table)


# The full rubric. max_points sum to 100 (validated below).
RUBRIC: List[RubricCriterion] = [
    RubricCriterion(
        key="relevance",
        name="Relevance to the Challenge",
        max_points=12,
        description="How directly and completely the answer addresses the "
        "stated challenge, its objectives, constraints and expected outputs.",
        guidance=(
            "10 = every objective and constraint is addressed head-on with no "
            "scope drift. 5 = addresses the topic but misses key objectives or "
            "ignores stated constraints. 0 = off-topic or answers a different "
            "problem."
        ),
        name_fa="ارتباط با چالش",
        short_fa="ارتباط",
        description_fa="میزان پرداختن مستقیم و کامل به اهداف، محدودیت‌ها و "
        "خروجی‌های مورد انتظارِ چالش.",
    ),
    RubricCriterion(
        key="scientific_accuracy",
        name="Scientific Accuracy",
        max_points=14,
        description="Correctness of the science: facts, equations, physical "
        "reasoning, citations and absence of unsupported or false claims.",
        guidance=(
            "10 = claims are correct, well-grounded and (where relevant) cited; "
            "no factual errors. 5 = broadly plausible but with notable errors or "
            "unsupported assertions. 0 = fundamentally incorrect science."
        ),
        name_fa="دقت علمی",
        short_fa="دقت",
        description_fa="درستی علم: حقایق، معادلات، استدلال فیزیکی، استنادها و "
        "نبودِ ادعاهای بی‌پایه یا نادرست.",
    ),
    RubricCriterion(
        key="methodology",
        name="Methodological Soundness",
        max_points=13,
        description="Rigor of the proposed method: experimental/analytical "
        "design, controls, data strategy, validation and reproducibility.",
        guidance=(
            "10 = rigorous, reproducible design with validation and controls. "
            "5 = a reasonable method with gaps in validation or reproducibility. "
            "0 = no coherent methodology or an approach that cannot work."
        ),
        name_fa="استحکام روش‌شناسی",
        short_fa="روش",
        description_fa="دقت روش پیشنهادی: طراحی آزمایشی/تحلیلی، کنترل‌ها، راهبرد "
        "داده، اعتبارسنجی و تکرارپذیری.",
    ),
    RubricCriterion(
        key="innovation",
        name="Innovation & Originality",
        max_points=12,
        description="Novelty of the idea relative to standard/known approaches "
        "in the field; degree of genuine advance over the state of the art.",
        guidance=(
            "10 = a genuinely novel approach that advances the state of the art. "
            "5 = a sensible combination of known methods with some new twist. "
            "0 = a textbook or well-known solution with nothing new."
        ),
        name_fa="نوآوری و اصالت",
        short_fa="نوآوری",
        description_fa="نو بودن ایده نسبت به رویکردهای متعارف حوزه و میزان "
        "پیشرفت واقعی نسبت به وضعیت موجود دانش.",
    ),
    RubricCriterion(
        key="creativity",
        name="Creativity of the Idea",
        max_points=8,
        description="Imagination, elegance and non-obviousness of the framing "
        "and of the connections drawn between concepts.",
        guidance=(
            "10 = an elegant, non-obvious framing that reframes the problem. "
            "5 = competent but conventional thinking. 0 = mechanical / templated."
        ),
        name_fa="خلاقیت ایده",
        short_fa="خلاقیت",
        description_fa="تخیل، ظرافت و بدیهی‌نبودنِ چارچوب‌بندی مسئله و پیوند "
        "میان مفاهیم.",
    ),
    RubricCriterion(
        key="feasibility",
        name="Practical Feasibility",
        max_points=11,
        description="Realism of implementation given cost, time, data, "
        "hardware, regulatory and operational constraints.",
        guidance=(
            "10 = clearly implementable with identified, realistic resources. "
            "5 = feasible in principle but with significant unaddressed hurdles. "
            "0 = impractical or ignores hard real-world constraints."
        ),
        name_fa="امکان‌سنجی عملی",
        short_fa="امکان",
        description_fa="واقع‌گراییِ اجرا با توجه به هزینه، زمان، داده، سخت‌افزار "
        "و محدودیت‌های مقرراتی و عملیاتی.",
    ),
    RubricCriterion(
        key="technical_depth",
        name="Technical Depth",
        max_points=10,
        description="Depth of technical detail: does the answer go beyond "
        "buzzwords into concrete mechanisms, parameters and trade-offs?",
        guidance=(
            "10 = deep, specific technical detail with quantified trade-offs. "
            "5 = moderate detail, some hand-waving. 0 = superficial / buzzwords."
        ),
        name_fa="عمق فنی",
        short_fa="عمق",
        description_fa="عمق جزئیات فنی: سازوکارها، پارامترها و مصالحه‌های کمی "
        "به‌جای کلی‌گویی و واژه‌های پرطمطراق.",
    ),
    RubricCriterion(
        key="clarity",
        name="Clarity & Structure",
        max_points=7,
        description="Readability, logical organization, and communication "
        "quality of the written submission.",
        guidance=(
            "10 = exceptionally clear, well-structured and easy to follow. "
            "5 = understandable but disorganized in places. 0 = confusing."
        ),
        name_fa="شفافیت و ساختار",
        short_fa="شفافیت",
        description_fa="خوانایی، سازمان‌دهی منطقی و کیفیت ارائه نوشتاری پاسخ.",
    ),
    RubricCriterion(
        key="impact",
        name="Potential Impact",
        max_points=8,
        description="Scale and significance of the outcome if the idea "
        "succeeds: scientific, societal, economic or environmental value.",
        guidance=(
            "10 = transformative, wide-reaching impact. 5 = useful but "
            "incremental impact. 0 = negligible impact even if successful."
        ),
        name_fa="اثرگذاری بالقوه",
        short_fa="اثر",
        description_fa="بزرگی و اهمیت نتیجه در صورت موفقیت: ارزش علمی، اجتماعی، "
        "اقتصادی یا زیست‌محیطی.",
    ),
    RubricCriterion(
        key="risk_awareness",
        name="Limitations & Risk Awareness",
        max_points=5,
        description="Whether the submission honestly identifies its own "
        "limitations, risks and failure modes and proposes mitigations.",
        guidance=(
            "10 = candidly identifies limitations/risks and mitigates them. "
            "5 = mentions some limitations superficially. 0 = ignores all risks "
            "or overclaims certainty."
        ),
        name_fa="آگاهی از محدودیت‌ها و ریسک",
        short_fa="ریسک",
        description_fa="شناساییِ صادقانهٔ محدودیت‌ها، ریسک‌ها و حالت‌های شکست و "
        "ارائهٔ راهکار کاهش آن‌ها.",
    ),
]


# ---------------------------------------------------------------------------
# Global settings
# ---------------------------------------------------------------------------
@dataclass
class Settings:
    """Runtime settings for the agent."""

    # LLM model used for evaluation. Defaults to a capable Claude model.
    # Alternatives: "claude-sonnet-5" (cheaper, still strong), "claude-haiku-4-5"
    # (cheapest; not recommended for scientific judgment).
    model: str = "claude-opus-5"
    # Lower temperature -> more consistent, repeatable scoring.
    temperature: float = 0.2
    max_tokens: int = 4096
    # Max characters of submission text sent to the LLM per call (safety cap).
    max_submission_chars: int = 60_000
    # Number of retries on transient LLM errors.
    max_retries: int = 3
    # If True, raise when scores drift outside 0-10 instead of clamping.
    strict_scores: bool = False

    # ----- Report language & fonts -----------------------------------------
    # Language the LLM writes its analysis in and the report is rendered in.
    report_language: str = "Persian"      # e.g. "Persian" or "English"
    # Fonts requested for the Persian (Word/PDF) report.
    persian_font: str = "B Nazanin"       # font for Persian (RTL) text
    latin_font: str = "Times New Roman"   # font for Latin text / numbers
    base_font_size: int = 12
    heading_font_size: int = 15


SETTINGS = Settings()


# ---------------------------------------------------------------------------
# Sanity check: weights must sum to 100.
# ---------------------------------------------------------------------------
def _validate_rubric() -> None:
    total = sum(c.max_points for c in RUBRIC)
    if abs(total - 100.0) > 1e-6:
        raise ValueError(
            f"Rubric weights must sum to 100, got {total}. "
            "Fix max_points in config.RUBRIC."
        )
    keys = [c.key for c in RUBRIC]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate criterion keys found in config.RUBRIC.")


_validate_rubric()

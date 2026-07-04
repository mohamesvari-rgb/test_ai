"""
Prompt templates for the Scientific Evaluation Agent.

Prompts are isolated here so reviewers can audit and tune the exact
instructions the LLM receives. Each builder returns a (system, user) pair.

Design principles baked into these prompts:
* The model is framed as a rigorous, skeptical scientific peer reviewer.
* Scoring is anchored to the explicit rubric guidance (no vibes).
* Output is constrained to strict JSON for reliable parsing.
* The model must justify every score and cite evidence from the text.
"""

from __future__ import annotations

import json
from typing import List, Tuple

from .config import RUBRIC
from .models import Challenge, Submission, SubmissionEvaluation


REVIEWER_PERSONA = (
    "You are a rigorous, skeptical senior scientific peer reviewer and "
    "innovation evaluator with deep expertise across engineering, medicine, "
    "environmental science, remote sensing, artificial intelligence, "
    "agriculture and energy. You judge research quality, novelty, creativity, "
    "feasibility and scientific validity - not surface polish. You reward "
    "correct, well-evidenced, genuinely novel work and you penalize "
    "unsupported claims, hand-waving and buzzwords. You never invent facts "
    "about a submission; you assess only what is written."
)


def _rubric_reference() -> str:
    """Machine-readable rubric block embedded in the scoring prompt."""
    lines = ["RUBRIC (score each criterion 0-10 using this guidance):"]
    for c in RUBRIC:
        lines.append(
            f"- {c.key} | {c.name} (max {c.max_points} pts of 100)\n"
            f"    Meaning: {c.description}\n"
            f"    Anchors: {c.guidance}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 1) Per-submission scoring
# ---------------------------------------------------------------------------
def build_scoring_prompt(challenge: Challenge, submission: Submission) -> Tuple[str, str]:
    """Prompt that scores one submission against every rubric criterion."""
    keys = [c.key for c in RUBRIC]
    schema = {
        "criterion_scores": {
            k: {"raw_score": "<number 0-10>", "justification": "<1-2 sentences citing the text>"}
            for k in keys
        },
        "summary": "<3-4 sentence overall assessment>",
        "strengths": ["<bullet>", "..."],
        "weaknesses": ["<bullet>", "..."],
        "integrity_flags": ["<only if you detect overclaiming, contradiction, "
                            "fabricated results, or off-topic content; else empty>"],
    }

    system = (
        f"{REVIEWER_PERSONA}\n\n"
        "TASK: Score ONE submission against the CHALLENGE using the RUBRIC.\n"
        "This is a CRITERION-by-criterion scientific evaluation.\n"
        f"{_rubric_reference()}\n\n"
        "Rules:\n"
        "1. Score strictly from evidence in the submission text.\n"
        "2. Every score needs a concrete justification referencing the content.\n"
        "3. Be calibrated: reserve 9-10 for genuinely excellent work; most "
        "competent-but-ordinary work sits at 5-7.\n"
        "4. Distinguish novelty (innovation) from mere correctness.\n"
        "5. Respond with ONLY a JSON object matching the schema. No prose "
        "outside the JSON."
    )

    user = (
        "=== CHALLENGE ===\n"
        f"{challenge.to_prompt_block()}\n\n"
        f"=== SUBMISSION (participant_id: {submission.participant_id}) ===\n"
        f"Title: {submission.title}\n"
        f"Word count: {submission.word_count}\n"
        "--- BEGIN SUBMISSION TEXT ---\n"
        f"{submission.raw_text}\n"
        "--- END SUBMISSION TEXT ---\n\n"
        "Return JSON with EXACTLY this schema:\n"
        f"{json.dumps(schema, indent=2)}"
    )
    return system, user


# ---------------------------------------------------------------------------
# 2) Innovation & creativity extraction
# ---------------------------------------------------------------------------
def build_innovation_prompt(challenge: Challenge, submission: Submission) -> Tuple[str, str]:
    """Prompt that extracts structured innovation/creativity signals."""
    schema = {
        "main_innovations": ["<the core novel ideas>"],
        "creative_aspects": ["<imaginative / non-obvious framings>"],
        "unique_advantages": ["<what this answer does that others likely won't>"],
        "strong_technical_ideas": ["<technically strong mechanisms/methods>"],
        "potential_research_contributions": ["<publishable / patentable angles>"],
        "weaknesses_or_missing_parts": ["<gaps, missing analysis, risks>"],
    }
    system = (
        f"{REVIEWER_PERSONA}\n\n"
        "TASK: Extract the INNOVATION and CREATIVITY profile of one submission. "
        "Separate genuine novelty from standard practice. Be specific and "
        "concrete - name the actual idea, not a generic label. Respond with "
        "ONLY a JSON object matching the schema."
    )
    user = (
        "=== CHALLENGE ===\n"
        f"{challenge.to_prompt_block()}\n\n"
        f"=== SUBMISSION (participant_id: {submission.participant_id}) ===\n"
        f"{submission.raw_text}\n\n"
        "Return JSON with EXACTLY this schema (each value a list of short strings):\n"
        f"{json.dumps(schema, indent=2)}"
    )
    return system, user


# ---------------------------------------------------------------------------
# 3) Cross-submission comparison & ranking
# ---------------------------------------------------------------------------
def build_comparison_prompt(
    challenge: Challenge, evaluations: List[SubmissionEvaluation]
) -> Tuple[str, str]:
    """Prompt that compares and ranks all submissions."""
    # Compact digest of each evaluation to keep the prompt focused.
    digest = []
    for e in evaluations:
        digest.append({
            "participant_id": e.participant_id,
            "title": e.title,
            "total_score": round(e.total_score, 1),
            "per_criterion": {c.key: c.raw_score for c in e.criterion_scores},
            "summary": e.summary,
            "main_innovations": e.innovation.main_innovations,
            "key_weaknesses": e.weaknesses[:4],
        })

    schema = {
        "ranking": ["<participant_id, best first>"],
        "rationale": "<why this order; reference criteria and evidence>",
        "pairwise_notes": ["<why X beats Y for specific reasons>"],
        "overlapping_ideas": ["<ideas shared across multiple submissions>"],
        "unique_ideas": {"<participant_id>": ["<ideas only this one has>"]},
        "complementary_ideas": ["<ideas from different answers that combine well>"],
    }
    system = (
        f"{REVIEWER_PERSONA}\n\n"
        "TASK: COMPARE and RANK all submissions for the same challenge. "
        "Explain WHY stronger answers beat weaker ones, grounded in the "
        "criteria. Identify overlapping, unique and complementary ideas across "
        "answers. Respond with ONLY a JSON object matching the schema."
    )
    user = (
        "=== CHALLENGE ===\n"
        f"{challenge.to_prompt_block()}\n\n"
        "=== EVALUATION DIGESTS ===\n"
        f"{json.dumps(digest, indent=2)}\n\n"
        "Return JSON with EXACTLY this schema:\n"
        f"{json.dumps(schema, indent=2)}"
    )
    return system, user


# ---------------------------------------------------------------------------
# 4) Synthesis of an improved solution
# ---------------------------------------------------------------------------
def build_synthesis_prompt(
    challenge: Challenge, evaluations: List[SubmissionEvaluation], comparison
) -> Tuple[str, str]:
    """Prompt that synthesizes a superior combined solution."""
    ingredients = []
    for e in evaluations:
        ingredients.append({
            "participant_id": e.participant_id,
            "best_ideas": (
                e.innovation.main_innovations
                + e.innovation.strong_technical_ideas
                + e.innovation.unique_advantages
            ),
        })

    system = (
        f"{REVIEWER_PERSONA}\n\n"
        "TASK: Design a SINGLE improved solution to the challenge that "
        "combines the strongest, most feasible and most novel ideas across "
        "all submissions, while fixing their common weaknesses. Be concrete "
        "and technical. Structure your answer with clear headings: "
        "Approach, Methodology, Why it is superior, Feasibility & resources, "
        "Risks & mitigations, Expected impact. Write in clear scientific prose "
        "(not JSON)."
    )
    user = (
        "=== CHALLENGE ===\n"
        f"{challenge.to_prompt_block()}\n\n"
        "=== BEST IDEAS PER SUBMISSION ===\n"
        f"{json.dumps(ingredients, indent=2)}\n\n"
        "=== RANKING RATIONALE ===\n"
        f"{comparison.rationale}\n\n"
        "=== COMPLEMENTARY IDEAS TO FUSE ===\n"
        f"{json.dumps(comparison.complementary_ideas, indent=2)}\n\n"
        "Now write the synthesized improved solution."
    )
    return system, user


# ---------------------------------------------------------------------------
# 5) Final recommendation
# ---------------------------------------------------------------------------
def build_recommendation_prompt(
    challenge: Challenge, evaluations: List[SubmissionEvaluation], comparison
) -> Tuple[str, str]:
    """Prompt for a concise, decision-oriented final recommendation."""
    ranked = [
        {"participant_id": e.participant_id, "score": round(e.total_score, 1)}
        for e in sorted(evaluations, key=lambda x: x.total_score, reverse=True)
    ]
    system = (
        f"{REVIEWER_PERSONA}\n\n"
        "TASK: Write a concise FINAL RECOMMENDATION for the challenge owner: "
        "who should win and why, which ideas to pursue, and what to improve "
        "before implementation. 1-3 short paragraphs, decisive and evidence-based."
    )
    user = (
        "=== CHALLENGE ===\n"
        f"{challenge.to_prompt_block()}\n\n"
        "=== FINAL SCORES ===\n"
        f"{json.dumps(ranked, indent=2)}\n\n"
        "=== RANKING RATIONALE ===\n"
        f"{comparison.rationale}\n\n"
        "Write the final recommendation."
    )
    return system, user

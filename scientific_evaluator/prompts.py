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

from .config import RUBRIC, SETTINGS
from .models import Challenge, Submission, SubmissionEvaluation


def _json(obj) -> str:
    """Serialize a prompt payload for the model.

    ``ensure_ascii=False`` is essential: participant ids (and any Persian text)
    must reach the model as real characters. Escaped as ``\\uXXXX`` the model
    echoes back ids that no longer match the real ones, so they get dropped from
    the ranking and the report order becomes incoherent.
    """
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _clip(text, limit: int) -> str:
    """Shorten one item of prompt material to at most ``limit`` characters."""
    text = str(text).strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def _language_directive() -> str:
    """Instruction that pins the language of all human-readable output.

    JSON *keys* must stay exactly as specified (English) so parsing works;
    only the human-readable *values* are written in the target language.
    """
    lang = SETTINGS.report_language
    if lang.lower().startswith("english"):
        return "Write all text in clear English."
    return (
        f"Write ALL human-readable text (justifications, summaries, list items, "
        f"prose) in {lang}. Keep every JSON key EXACTLY as given in English so "
        f"the response can be parsed; only the values are in {lang}. Use correct, "
        f"fluent, academic {lang}."
    )


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
        "outside the JSON.\n\n"
        f"LANGUAGE: {_language_directive()}"
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
        f"{_json(schema)}"
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
        "ONLY a JSON object matching the schema.\n\n"
        f"LANGUAGE: {_language_directive()}"
    )
    user = (
        "=== CHALLENGE ===\n"
        f"{challenge.to_prompt_block()}\n\n"
        f"=== SUBMISSION (participant_id: {submission.participant_id}) ===\n"
        f"{submission.raw_text}\n\n"
        "Return JSON with EXACTLY this schema (each value a list of short strings):\n"
        f"{_json(schema)}"
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
        "salient_points": {
            "<participant_id>": ["<the most important, standout points of THIS answer>"]
        },
        "distinctive_points": {
            "<participant_id>": ["<what sets THIS answer apart from the others>"]
        },
        "pairwise_notes": ["<why X beats Y for specific reasons>"],
        "overlapping_ideas": ["<ideas shared across multiple submissions>"],
        "unique_ideas": {"<participant_id>": ["<ideas only this one has>"]},
        "complementary_ideas": ["<ideas from different answers that combine well>"],
    }
    system = (
        f"{REVIEWER_PERSONA}\n\n"
        "TASK: COMPARE and RANK all submissions for the same challenge.\n"
        "For EACH answer, examine and list:\n"
        "  * its SALIENT points - the strongest, most important points that "
        "stand out in that answer;\n"
        "  * its DISTINCTIVE points - what makes it different from the other "
        "answers (its differentiators).\n"
        "Then explain WHY stronger answers beat weaker ones, grounded in the "
        "criteria, and identify overlapping, unique and complementary ideas "
        "across answers. Respond with ONLY a JSON object matching the schema.\n\n"
        f"LANGUAGE: {_language_directive()}"
    )
    user = (
        "=== CHALLENGE ===\n"
        f"{challenge.to_prompt_block()}\n\n"
        "=== EVALUATION DIGESTS ===\n"
        f"{_json(digest)}\n\n"
        "Return JSON with EXACTLY this schema:\n"
        f"{_json(schema)}"
    )
    return system, user


# ---------------------------------------------------------------------------
# 4) Synthesis of an improved solution
# ---------------------------------------------------------------------------
def build_synthesis_prompt(
    challenge: Challenge, evaluations: List[SubmissionEvaluation], comparison
) -> Tuple[str, str]:
    """Prompt that integrates EXISTING ideas + their improvements into ONE
    comprehensive final solution.

    Grounding rule: the solution must be built by combining and improving ideas
    that ACTUALLY APPEAR in the submitted answers - it must not invent an
    unrelated new answer from scratch.
    """
    # Strongest first, with each answer's material capped: uncapped, ten answers
    # produced a 130k-character prompt and the model reasoned itself out of budget.
    order = {pid: i for i, pid in enumerate(comparison.ranking)}
    ingredients = []
    for e in sorted(evaluations, key=lambda x: order.get(x.participant_id, len(order))):
        ideas = list(dict.fromkeys(
            e.innovation.main_innovations
            + e.innovation.strong_technical_ideas
            + e.innovation.unique_advantages
        ))
        ingredients.append({
            "participant_id": e.participant_id,
            "score": round(e.total_score, 1),
            "strengths": [_clip(x, 220) for x in e.strengths[:4]],
            "existing_ideas": [_clip(x, 220) for x in ideas[:6]],
            "idea_improvements": [
                {"idea": _clip(imp.idea, 160),
                 "improvements": [_clip(x, 220) for x in imp.improvements[:2]]}
                for imp in e.idea_improvements[:4]
            ],
        })

    system = (
        f"{REVIEWER_PERSONA}\n\n"
        "TASK: Produce ONE final, comprehensive solution to the challenge by "
        "INTEGRATING the approaches and strengths of ALL the submitted answers "
        "TOGETHER WITH the improvement solutions proposed for each idea.\n"
        "Hard rules:\n"
        "1. Build ONLY from ideas that actually appear in the submissions "
        "(plus the listed improvements). Do NOT invent an unrelated new answer.\n"
        "2. Explicitly COMBINE ideas from different answers so they reinforce "
        "each other into a single coherent solution. Do not list the answers one "
        "after another and do not just pick the best one.\n"
        "3. Use the strongest element of EVERY answer. Name the source answers in "
        "parentheses, by their exact participant_id, wherever an element is used.\n"
        "4. Fold in the improvement solutions so each borrowed idea is used in "
        "its strengthened form.\n"
        "5. The result must be a credible, acceptable solution to THIS challenge. "
        "Do not present numbers the answers did not support as established facts.\n"
        "Use exactly these sections, with Markdown headings written in the report "
        "language:\n"
        "- Overview: the integrated solution in one short paragraph.\n"
        "- Contribution of each answer: a Markdown table with ONE ROW FOR EVERY "
        "participant_id and the columns answer, approach or strength adopted, where "
        "it is used in the solution. If an answer adds nothing new, say so in its row.\n"
        "- Integrated solution: the solution as ordered steps or components, each "
        "naming the answers it draws on.\n"
        "- How the improvements are applied.\n"
        "- How it meets the challenge: a Markdown table mapping each objective and "
        "expected output to the part of the solution that delivers it.\n"
        "- Feasibility and resources.\n"
        "- Risks and mitigations.\n"
        "- Expected impact.\n"
        "Length: about 1500 to 2500 words. Keep your private reasoning brief and do "
        "not draft the full text in it. Write in fluent scientific prose (NOT JSON). "
        "Write formulas in plain text with Unicode (e.g. Ni₃(HITP)₂, CO₂), not LaTeX.\n\n"
        f"LANGUAGE: {_language_directive()}"
    )
    user = (
        "=== CHALLENGE ===\n"
        f"{challenge.to_prompt_block()}\n\n"
        "=== EXISTING IDEAS + THEIR IMPROVEMENT SOLUTIONS (per submission) ===\n"
        f"{_json(ingredients)}\n\n"
        "=== RANKING RATIONALE ===\n"
        f"{comparison.rationale}\n\n"
        "=== COMPLEMENTARY IDEAS TO FUSE ===\n"
        f"{_json(comparison.complementary_ideas)}\n\n"
        "Now write the single integrated, comprehensive solution, combining and "
        "improving the existing ideas above."
    )
    return system, user


# ---------------------------------------------------------------------------
# 4b) Per-idea improvement solutions
# ---------------------------------------------------------------------------
def build_improvement_prompt(
    challenge: Challenge, submission: Submission, ideas: List[str]
) -> Tuple[str, str]:
    """Prompt that proposes concrete improvement solutions for each key idea.

    For every idea drawn from the submission, the model returns solutions that
    make the idea MORE EFFECTIVE at solving the challenge.
    """
    schema = {
        "idea_improvements": [
            {
                "idea": "<the idea, restated concisely>",
                "why_it_matters": "<its relevance to the challenge>",
                "improvements": [
                    "<a concrete, actionable solution that strengthens this idea>",
                    "<another improvement>",
                ],
                "expected_effect": "<how these improvements help solve the challenge>",
            }
        ]
    }
    system = (
        f"{REVIEWER_PERSONA}\n\n"
        "TASK: For EACH given idea taken from this submission, propose a set of "
        "concrete IMPROVEMENT SOLUTIONS. Each solution must be actionable and "
        "must move the idea CLOSER to solving the stated challenge (e.g. improve "
        "its accuracy, feasibility, novelty, robustness, cost, or impact). Do "
        "not merely restate the idea - improve it. Respond with ONLY a JSON "
        "object matching the schema.\n\n"
        f"LANGUAGE: {_language_directive()}"
    )
    user = (
        "=== CHALLENGE ===\n"
        f"{challenge.to_prompt_block()}\n\n"
        f"=== SUBMISSION (participant_id: {submission.participant_id}) ===\n"
        f"{submission.raw_text}\n\n"
        "=== IDEAS TO IMPROVE (one entry per idea) ===\n"
        f"{_json(ideas)}\n\n"
        "Return JSON with EXACTLY this schema:\n"
        f"{_json(schema)}"
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
        "before implementation. 1-3 short paragraphs, decisive and evidence-based. "
        "Write plain prose: NOT JSON, no headings, no Markdown.\n\n"
        f"LANGUAGE: {_language_directive()}"
    )
    user = (
        "=== CHALLENGE ===\n"
        f"{challenge.to_prompt_block()}\n\n"
        "=== FINAL SCORES ===\n"
        f"{_json(ranked)}\n\n"
        "=== RANKING RATIONALE ===\n"
        f"{comparison.rationale}\n\n"
        "Write the final recommendation."
    )
    return system, user

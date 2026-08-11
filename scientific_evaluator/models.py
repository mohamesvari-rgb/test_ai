"""
Data models for the Scientific Evaluation Agent.

These dataclasses are the contract passed between modules. Keeping them in one
place makes the data flow explicit and serialization (to JSON / report) simple.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
@dataclass
class Challenge:
    """A scientific challenge that submissions are evaluated against."""

    title: str
    field: str                       # e.g. "remote sensing", "medicine"
    background: str                  # context / problem statement
    objectives: List[str]            # what a good answer must achieve
    constraints: List[str] = field(default_factory=list)
    expected_outputs: List[str] = field(default_factory=list)
    # Optional: reviewer notes on what an ideal answer looks like.
    evaluation_notes: str = ""

    def to_prompt_block(self) -> str:
        """Render the challenge as a compact text block for LLM prompts."""
        lines = [
            f"TITLE: {self.title}",
            f"FIELD: {self.field}",
            "",
            "BACKGROUND:",
            self.background.strip(),
            "",
            "OBJECTIVES:",
        ]
        lines += [f"  - {o}" for o in self.objectives]
        if self.constraints:
            lines += ["", "CONSTRAINTS:"]
            lines += [f"  - {c}" for c in self.constraints]
        if self.expected_outputs:
            lines += ["", "EXPECTED OUTPUTS:"]
            lines += [f"  - {e}" for e in self.expected_outputs]
        if self.evaluation_notes:
            lines += ["", "REVIEWER NOTES:", self.evaluation_notes.strip()]
        return "\n".join(lines)


@dataclass
class Submission:
    """A single participant's answer, after reading the Word file."""

    participant_id: str              # stable id, e.g. filename stem
    source_path: str                 # original .docx path
    raw_text: str                    # cleaned plain text of the submission
    title: str = ""                  # detected / provided title
    word_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Evaluation outputs
# ---------------------------------------------------------------------------
@dataclass
class CriterionScore:
    """Score and justification for one rubric criterion."""

    key: str
    name: str
    raw_score: float                 # 0-10 as judged by the evaluation engine
    max_points: float                # weight (max contribution to /100)
    justification: str = ""

    @property
    def weighted_points(self) -> float:
        """Contribution of this criterion to the final /100 score."""
        return (self.raw_score / 10.0) * self.max_points


@dataclass
class InnovationProfile:
    """Structured extraction of what is novel/valuable in a submission."""

    main_innovations: List[str] = field(default_factory=list)
    creative_aspects: List[str] = field(default_factory=list)
    unique_advantages: List[str] = field(default_factory=list)
    strong_technical_ideas: List[str] = field(default_factory=list)
    potential_research_contributions: List[str] = field(default_factory=list)
    weaknesses_or_missing_parts: List[str] = field(default_factory=list)


@dataclass
class IdeaImprovement:
    """A single idea extracted from a submission plus concrete ways to improve it.

    Each improvement is a solution that makes the idea more effective at solving
    the challenge (better feasibility, accuracy, novelty, impact, etc.).
    """

    idea: str                                    # the idea, as it appears in the answer
    source_participant: str = ""                 # which submission the idea came from
    why_it_matters: str = ""                     # its relevance to the challenge
    improvements: List[str] = field(default_factory=list)   # solutions to improve it
    expected_effect: str = ""                    # how the improvements help solve it


@dataclass
class SubmissionEvaluation:
    """The complete evaluation of one submission."""

    participant_id: str
    title: str
    criterion_scores: List[CriterionScore] = field(default_factory=list)
    innovation: InnovationProfile = field(default_factory=InnovationProfile)
    summary: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    integrity_flags: List[str] = field(default_factory=list)  # e.g. plagiarism/overclaim
    penalty: float = 0.0             # points subtracted for integrity issues
    # Per-idea improvement solutions (requirement: improve each idea).
    idea_improvements: List[IdeaImprovement] = field(default_factory=list)

    @property
    def total_score(self) -> float:
        """Final score out of 100 (after any penalty), clamped to [0, 100]."""
        base = sum(c.weighted_points for c in self.criterion_scores)
        return max(0.0, min(100.0, base - self.penalty))

    def score_by_key(self, key: str) -> Optional[CriterionScore]:
        for c in self.criterion_scores:
            if c.key == key:
                return c
        return None


@dataclass
class ComparisonResult:
    """Cross-submission comparison and ranking."""

    ranking: List[str] = field(default_factory=list)   # participant_ids, best first
    rationale: str = ""                                # why the order is as it is
    pairwise_notes: List[str] = field(default_factory=list)
    overlapping_ideas: List[str] = field(default_factory=list)
    unique_ideas: Dict[str, List[str]] = field(default_factory=dict)  # id -> ideas
    complementary_ideas: List[str] = field(default_factory=list)
    # Requirement: examine each answer's salient and distinctive points.
    salient_points: Dict[str, List[str]] = field(default_factory=dict)     # id -> points
    distinctive_points: Dict[str, List[str]] = field(default_factory=dict)  # id -> points


@dataclass
class EvaluationResult:
    """Top-level result returned by the agent for a full evaluation run."""

    challenge: Challenge
    evaluations: List[SubmissionEvaluation] = field(default_factory=list)
    comparison: ComparisonResult = field(default_factory=ComparisonResult)
    synthesized_solution: str = ""
    final_recommendation: str = ""

    def ranked_evaluations(self) -> List[SubmissionEvaluation]:
        """Evaluations ordered by the comparison ranking (falls back to score)."""
        by_id = {e.participant_id: e for e in self.evaluations}
        if self.comparison.ranking:
            ordered = [by_id[i] for i in self.comparison.ranking if i in by_id]
            # Append any not covered by the ranking, by score.
            missing = [e for e in self.evaluations
                       if e.participant_id not in set(self.comparison.ranking)]
            ordered += sorted(missing, key=lambda e: e.total_score, reverse=True)
            return ordered
        return sorted(self.evaluations, key=lambda e: e.total_score, reverse=True)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable view of the whole result."""
        return {
            "challenge": asdict(self.challenge),
            "evaluations": [
                {
                    "participant_id": e.participant_id,
                    "title": e.title,
                    "total_score": round(e.total_score, 2),
                    "penalty": e.penalty,
                    "criterion_scores": [asdict(c) for c in e.criterion_scores],
                    "innovation": asdict(e.innovation),
                    "idea_improvements": [asdict(i) for i in e.idea_improvements],
                    "summary": e.summary,
                    "strengths": e.strengths,
                    "weaknesses": e.weaknesses,
                    "integrity_flags": e.integrity_flags,
                }
                for e in self.evaluations
            ],
            "comparison": asdict(self.comparison),
            "synthesized_solution": self.synthesized_solution,
            "final_recommendation": self.final_recommendation,
        }

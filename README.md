# Scientific Evaluation Agent

An AI agent that **evaluates scientific ideas and solutions** submitted by
participants in response to a defined challenge — in any research domain
(engineering, medicine, environmental science, remote sensing, AI, agriculture,
energy, …).

It reads each participant's **Word (`.docx`)** answer, scores it against a
transparent, weighted rubric using an LLM acting as a rigorous scientific peer
reviewer, extracts each answer's innovations and creativity, compares and ranks
all answers, and produces a single **integrated Word report** — including a
**synthesized "best-of-all" solution** that fuses the strongest ideas.

It is built to judge **quality, novelty, creativity, feasibility and research
value** — not just to compare text.

---

## Table of contents

1. [System workflow](#1-system-workflow)
2. [Agent architecture](#2-agent-architecture)
3. [Evaluation rubric](#3-evaluation-rubric-100-points)
4. [Quick start](#4-quick-start)
5. [Step-by-step implementation plan](#5-step-by-step-implementation-plan)
6. [Python libraries required](#6-python-libraries-required)
7. [Code structure & pseudocode](#7-code-structure--pseudocode)
8. [Example prompts used inside the agent](#8-example-prompts-used-inside-the-agent)
9. [Example report format](#9-example-report-format)
10. [Extending the agent](#10-extending-the-agent)

---

## 1. System workflow

```
        ┌─────────────────────┐
        │  Challenge (JSON)   │  title, background, objectives,
        │  challenge.py       │  constraints, expected outputs, notes
        └──────────┬──────────┘
                   │
   participant     ▼
   .docx files  ┌─────────────────────┐   ┌──────────────────────┐
   ───────────▶ │ Word Document Reader │──▶│ Text Preprocessing   │
                │ document_reader.py   │   │ preprocessing.py     │
                └─────────────────────┘   └──────────┬───────────┘
                                                     │ Submission objects
                                                     ▼
      ┌───────────────────────── per submission ──────────────────────┐
      │  ┌──────────────────┐        ┌───────────────────────────┐    │
      │  │ Evaluation Engine │        │ Innovation Extractor      │    │
      │  │ evaluation_engine │        │ innovation_extractor.py   │    │
      │  │  → 0-10 / criterion│       │  → innovations, creativity,│   │
      │  └────────┬──────────┘        │    unique advantages, gaps │   │
      │           ▼                    └─────────────┬─────────────┘   │
      │  ┌──────────────────┐                        │                 │
      │  │ Scoring Engine    │  weighted /100         │                 │
      │  │ scoring_engine.py │◀───────────────────────┘                 │
      │  └────────┬──────────┘                                          │
      └───────────┼───────────────────────────────────────────────────┘
                  ▼  SubmissionEvaluation (score + innovation profile)
        ┌────────────────────────┐
        │ Comparison & Ranking    │  rank best→weakest, why, overlapping /
        │ comparison.py           │  unique / complementary ideas
        └───────────┬────────────┘
                    ▼
        ┌────────────────────────┐
        │ Synthesis Engine        │  synthesized improved solution +
        │ synthesis.py            │  final recommendation
        └───────────┬────────────┘
                    ▼
        ┌────────────────────────┐
        │ Report Generator        │  →  report.docx  (or report.md)
        │ report_generator.py     │
        └────────────────────────┘
```

**One-line summary:** *read → clean → score → extract novelty → rank → synthesize → export.*

---

## 2. Agent architecture

The agent is **modular** — every stage is a single-purpose module behind a small
interface, so any piece can be tested, tuned or swapped independently.

| Module | File | Responsibility |
|---|---|---|
| Challenge input | `challenge.py` | Load/validate a challenge (any domain) from JSON or dict |
| Word document reader | `document_reader.py` | Read `.docx` paragraphs **and tables** into raw text |
| Text preprocessing | `preprocessing.py` | Clean/normalize text, detect title, cap length → `Submission` |
| LLM client | `llm_client.py` | Swappable LLM backend (`Anthropic` real / `Mock` offline) + robust JSON parsing |
| Prompts | `prompts.py` | Auditable prompt templates for every LLM task |
| Evaluation engine | `evaluation_engine.py` | Score one submission 0-10 per criterion with justifications |
| Scoring engine | `scoring_engine.py` | Weighted-rubric math → final `/100`, clamping, integrity penalty |
| Innovation extractor | `innovation_extractor.py` | Extract innovations, creativity, unique advantages, gaps |
| Comparison & ranking | `comparison.py` | Rank all answers, explain order, overlapping/unique/complementary ideas |
| Synthesis | `synthesis.py` | Fuse best ideas into an improved solution + final recommendation |
| Report generator | `report_generator.py` | Export the integrated report as Word/Markdown |
| Orchestrator | `agent.py` | Wire the pipeline together (`ScientificEvaluationAgent`) |
| Data models | `models.py` | Typed dataclasses passed between modules |
| Config | `config.py` | The rubric + runtime settings (single source of truth) |

**Design choices that make it "scientific", not generic text comparison:**

- The LLM is framed as a **skeptical senior peer reviewer** and told to score
  strictly from evidence in the text, to reserve top scores for genuine
  excellence, and to distinguish **novelty from mere correctness**.
- **Innovation is analyzed in its own pass**, so creativity/novelty is explicit
  rather than an implicit by-product of a single score.
- The rubric weights the **scientific** dimensions (accuracy, methodology,
  feasibility, impact) most heavily.
- **Integrity flags** (overclaiming, contradictions, fabricated results,
  off-topic) apply a bounded score penalty.
- The numeric ranking is **reconciled** with the LLM's qualitative ranking so
  the final order never silently contradicts the rubric.

---

## 3. Evaluation rubric (100 points)

Each criterion is scored **0–10** by the evaluation engine and contributes
`(raw_score / 10) × max_points` to the final score out of 100. Weights are
defined in one place (`config.RUBRIC`) and validated to sum to 100.

| # | Criterion | Weight | What it measures |
|---|---|---:|---|
| 1 | Relevance to the challenge | 12 | Directly addresses objectives, constraints, expected outputs |
| 2 | Scientific accuracy | 14 | Correct facts/equations/reasoning; claims supported/cited |
| 3 | Methodological soundness | 13 | Rigorous, reproducible design with validation & controls |
| 4 | Innovation & originality | 12 | Genuine novelty vs. the state of the art |
| 5 | Creativity of the idea | 8 | Elegant, non-obvious framing and connections |
| 6 | Practical feasibility | 11 | Realistic given cost/time/data/hardware/regulation |
| 7 | Technical depth | 10 | Concrete mechanisms, parameters, quantified trade-offs |
| 8 | Clarity & structure | 7 | Readable, logically organized communication |
| 9 | Potential impact | 8 | Significance/scale of outcome if successful |
| 10 | Limitations & risk awareness | 5 | Honestly identifies risks/failure modes + mitigations |
| | **Total** | **100** | |

**Scoring anchors** (given to the LLM per criterion): `9–10` = genuinely
excellent; `5–7` = competent but ordinary; `0–2` = poor/absent. This calibration
prevents score inflation.

**Integrity penalty:** each detected integrity issue subtracts 5 points, capped
at −25, so a single evaluation can't be driven arbitrarily negative.

> The weights are a **starting point** for scientific/academic evaluation. Edit
> `config.RUBRIC` to re-weight for a specific challenge (e.g. bump *feasibility*
> for an engineering call, or *innovation* for a research grant).

---

## 4. Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Demo) create sample participant .docx files
python examples/generate_sample_submissions.py

# 3a. Run OFFLINE with the deterministic mock backend (no API key needed)
python main.py \
  --challenge config/challenge_example.json \
  --submissions examples/submissions \
  --out output/report.docx --mock

# 3b. Run a REAL evaluation with Claude
export ANTHROPIC_API_KEY=sk-ant-...
python main.py \
  --challenge config/challenge_example.json \
  --submissions examples/submissions \
  --out output/report.docx
```

Outputs: `output/report.docx` (integrated report) and, with `--json-out`, a raw
`result.json` for programmatic use.

**Library usage:**

```python
from scientific_evaluator import ScientificEvaluationAgent
from scientific_evaluator.llm_client import AnthropicLLMClient

agent = ScientificEvaluationAgent("config/challenge_example.json",
                                  AnthropicLLMClient())
result = agent.run("examples/submissions")          # folder of .docx
agent.export_report(result, "output/report.docx")   # Word report

for e in result.ranked_evaluations():
    print(e.participant_id, e.total_score)
```

---

## 5. Step-by-step implementation plan

This repository already implements every step below; the list doubles as a build
guide.

1. **Define the challenge model & loader** (`models.Challenge`, `challenge.py`).
   Represent any-domain challenges as structured data (background, objectives,
   constraints, expected outputs, reviewer notes) loaded from JSON. Validate
   required fields.
2. **Read Word files** (`document_reader.py`). Use `python-docx` to extract
   paragraphs *and* table cells; skip Word lock files; give clear errors for
   unsupported formats.
3. **Clean & package text** (`preprocessing.py`). Normalize whitespace/unicode,
   strip control chars, keep all scientific content (numbers, units, equations),
   detect a title, cap length (head+tail) → `Submission`.
4. **Build a swappable LLM client** (`llm_client.py`). One interface,
   `complete_text` / `complete_json`; real Anthropic backend with retries +
   exponential backoff; robust JSON extraction (handles code fences/prose); an
   offline deterministic `MockLLMClient` for tests/demos.
5. **Design the prompts** (`prompts.py`). A strong reviewer persona + explicit
   rubric anchors + strict JSON schemas for: scoring, innovation extraction,
   comparison/ranking, synthesis, and recommendation.
6. **Evaluation engine** (`evaluation_engine.py`). Ask the LLM for a 0–10 score
   *plus justification* per criterion, and per-submission strengths/weaknesses
   and integrity flags.
7. **Scoring module** (`scoring_engine.py`). Convert raw 0–10 scores into
   weighted points, clamp to range, apply integrity penalty, compute `/100`.
   All scoring math lives here for transparency.
8. **Innovation extraction** (`innovation_extractor.py`). A separate pass that
   returns main innovations, creative aspects, unique advantages, strong
   technical ideas, potential research contributions, and gaps.
9. **Comparison & ranking** (`comparison.py`). Feed compact evaluation digests
   to the LLM; get a ranking + rationale + pairwise notes + overlapping/unique/
   complementary ideas; **reconcile** the ranking with numeric scores.
10. **Synthesis** (`synthesis.py`). Generate an improved combined solution and a
    concise, decision-oriented final recommendation.
11. **Report generation** (`report_generator.py`). Assemble everything into a
    structured `.docx` (challenge summary, rubric, score table, individual
    reviews, innovation table, ranking, recommendation, synthesized solution);
    Markdown export too.
12. **Orchestrate & expose** (`agent.py`, `main.py`). One class + a CLI with a
    progress callback and JSON dump.
13. **Test** (`tests/test_scoring.py`). Rubric integrity, scoring math edge
    cases, JSON parsing, and a full pipeline run on the mock backend.

---

## 6. Python libraries required

| Library | Purpose |
|---|---|
| `anthropic` | LLM calls (Claude) for evaluation, comparison, synthesis |
| `python-docx` | Read participant `.docx` files **and** write the `.docx` report |
| `pandas` | Convenient tabular handling of scores (optional; report tables work without it) |
| `rich` | Nicer CLI progress/output (optional) |
| `python-dotenv` | Load `ANTHROPIC_API_KEY` from a `.env` file (optional) |

Only `anthropic` and `python-docx` are strictly required for a real run.
The **mock backend and unit tests need no network and no API key.**
To swap providers (OpenAI, Gemini, local models), implement one class — see
[Extending the agent](#10-extending-the-agent).

---

## 7. Code structure & pseudocode

```
test_ai/
├── README.md
├── requirements.txt
├── main.py                     # CLI entry point
├── config/
│   └── challenge_example.json  # example challenge (remote sensing / agriculture)
├── examples/
│   └── generate_sample_submissions.py   # makes 3 demo .docx (strong/medium/weak)
├── scientific_evaluator/
│   ├── __init__.py             # public API
│   ├── config.py               # RUBRIC (weights) + SETTINGS
│   ├── models.py               # Challenge, Submission, *Score, *Evaluation, Result
│   ├── challenge.py            # challenge input module
│   ├── document_reader.py      # Word reader
│   ├── preprocessing.py        # text cleaning
│   ├── llm_client.py           # Anthropic + Mock backends, JSON extraction
│   ├── prompts.py              # all prompt templates
│   ├── evaluation_engine.py    # per-criterion scoring
│   ├── scoring_engine.py       # weighted-rubric math
│   ├── innovation_extractor.py # novelty/creativity extraction
│   ├── comparison.py           # ranking + cross-analysis
│   ├── synthesis.py            # improved solution + recommendation
│   ├── report_generator.py     # Word/Markdown report
│   └── agent.py                # orchestrator
└── tests/
    └── test_scoring.py         # unit + end-to-end (mock) tests
```

**Orchestrator pseudocode** (`agent.run`):

```
function run(submissions_folder):
    submissions = for each .docx in folder:
        raw   = read_docx(file)                 # document_reader
        clean = clean_text(raw)                 # preprocessing
        yield Submission(id=filestem, text=clean)

    evaluations = for each submission:
        scores      = evaluation_engine.evaluate(challenge, submission)  # 0-10 per criterion
        scores.total = scoring_engine.weighted_sum(scores) - penalty     # /100
        scores.innovation = innovation_extractor.extract(challenge, submission)
        yield scores

    comparison = comparison_engine.compare(challenge, evaluations)   # rank + ideas
    solution   = synthesis.synthesize_solution(challenge, evaluations, comparison)
    recommend  = synthesis.final_recommendation(challenge, evaluations, comparison)

    return EvaluationResult(challenge, evaluations, comparison, solution, recommend)
```

**Scoring math** (`scoring_engine`):

```
contribution(criterion) = (raw_score / 10) * criterion.max_points
total = clamp(sum(contribution for all criteria) - integrity_penalty, 0, 100)
```

---

## 8. Example prompts used inside the agent

All prompts live in `prompts.py`. Shortened examples:

**Reviewer persona (system, shared):**

> You are a rigorous, skeptical senior scientific peer reviewer and innovation
> evaluator with deep expertise across engineering, medicine, environmental
> science, remote sensing, AI, agriculture and energy. You judge research
> quality, novelty, creativity, feasibility and scientific validity — not
> surface polish. … You never invent facts about a submission; you assess only
> what is written.

**Scoring prompt (system, excerpt):**

> TASK: Score ONE submission against the CHALLENGE using the RUBRIC.
> RUBRIC (score each criterion 0-10 using this guidance): …
> Rules: 1) Score strictly from evidence in the submission. 2) Every score needs
> a concrete justification referencing the content. 3) Be calibrated: reserve
> 9-10 for genuinely excellent work; competent-but-ordinary work sits at 5-7.
> 4) Distinguish novelty from mere correctness. 5) Respond with ONLY a JSON
> object matching the schema.

**Scoring output schema (enforced):**

```json
{
  "criterion_scores": {
    "relevance": {"raw_score": 0-10, "justification": "..."},
    "scientific_accuracy": {"raw_score": 0-10, "justification": "..."},
    "...": {}
  },
  "summary": "3-4 sentence overall assessment",
  "strengths": ["..."],
  "weaknesses": ["..."],
  "integrity_flags": ["only if overclaiming/fabrication/off-topic"]
}
```

**Innovation extraction (schema):**

```json
{
  "main_innovations": ["..."],
  "creative_aspects": ["..."],
  "unique_advantages": ["..."],
  "strong_technical_ideas": ["..."],
  "potential_research_contributions": ["..."],
  "weaknesses_or_missing_parts": ["..."]
}
```

**Comparison / ranking (schema):**

```json
{
  "ranking": ["participant_id best first", "..."],
  "rationale": "why this order, grounded in criteria",
  "pairwise_notes": ["why X beats Y"],
  "overlapping_ideas": ["ideas shared across submissions"],
  "unique_ideas": {"participant_id": ["ideas only they have"]},
  "complementary_ideas": ["ideas from different answers that combine well"]
}
```

**Synthesis (system, excerpt):**

> Design a SINGLE improved solution that combines the strongest, most feasible
> and most novel ideas across all submissions, while fixing their common
> weaknesses. Structure with headings: Approach, Methodology, Why it is superior,
> Feasibility & resources, Risks & mitigations, Expected impact.

---

## 9. Example report format

The exported `report.docx` (and `report.md`) contains, in order:

1. **Challenge summary** — background, objectives, constraints, expected outputs.
2. **Evaluation criteria & scoring rubric** — the weighted table.
3. **Score table** — rank × participant × per-criterion 0–10 × total /100.
4. **Individual reviews** — per participant: final score, summary,
   per-criterion justification, strengths, weaknesses, integrity flags.
5. **Innovation & creativity table** — main innovations / creative & unique
   advantages / weaknesses per participant.
6. **Comparative ranking** — ordered list + rationale + head-to-head notes +
   overlapping/complementary ideas.
7. **Final recommendation** — decisive, evidence-based.
8. **Synthesized improved solution** — the fused best-of-all-answers design.

Score-table sketch:

| Rank | Participant | Relev. | Sci.Acc | Method | Innov | … | Total /100 |
|---|---|---|---|---|---|---|---|
| 1 | participant_A | 9 | 8 | 9 | 8 | … | 86.4 |
| 2 | participant_B | 7 | 6 | 6 | 5 | … | 61.0 |
| 3 | participant_C | 4 | 3 | 2 | 6 | … | 38.5 |

---

## 10. Extending the agent

- **Re-weight the rubric:** edit `config.RUBRIC` (weights auto-validated to 100).
- **Change the model / temperature:** edit `config.SETTINGS` or pass `--model`.
- **Swap the LLM provider:** subclass `BaseLLMClient` and implement
  `complete_text`; pass your client into `ScientificEvaluationAgent`.
- **Add file formats (PDF/`.doc`):** add a reader in `document_reader.py` and
  route by extension.
- **Plagiarism / similarity checks:** add a module that embeds submissions and
  flags high pairwise similarity, feeding `integrity_flags`.
- **Human-in-the-loop:** the JSON dump (`--json-out`) lets reviewers adjust
  scores before regenerating the report.

---

### Notes & limitations

- LLM evaluations are **assistive, not authoritative** — use them to support, not
  replace, expert human judgement, especially for high-stakes decisions.
- The `MockLLMClient` produces **hash-based placeholder scores** so the pipeline
  runs offline; its rankings are meaningless. Use a real backend for genuine
  evaluation.
- Very long submissions are truncated (head+tail) to a configurable character
  cap (`SETTINGS.max_submission_chars`); raise it or add chunking for long docs.

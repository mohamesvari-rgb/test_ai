# Scientific Evaluation Agent

An AI agent that **evaluates scientific ideas and solutions** submitted by
participants in response to a defined challenge — in any research domain
(engineering, medicine, environmental science, remote sensing, AI, agriculture,
energy, …).

It reads each participant's **existing Word (`.docx`)** answer, scores it against
a transparent, weighted rubric using an LLM acting as a rigorous scientific peer
reviewer, extracts each answer's innovations and creativity, **proposes concrete
improvement solutions for each idea**, **compares the answers by their salient
and distinctive points**, ranks them, and **integrates all ideas together with
their improvements into one comprehensive final solution**.

The final report is produced in **Persian (RTL)**, with **analytical tables and
charts**, using **B Nazanin** for Persian and **Times New Roman** for English,
and is exported as **both Word (`.docx`) and PDF**.

---

## Table of contents

1. [What it does (requirements → features)](#1-what-it-does)
2. [System workflow](#2-system-workflow)
3. [Agent architecture](#3-agent-architecture)
4. [Evaluation rubric](#4-evaluation-rubric-100-points)
5. [Quick start](#5-quick-start)
6. [Step-by-step implementation plan](#6-step-by-step-implementation-plan)
7. [Python libraries & system dependencies](#7-python-libraries--system-dependencies)
8. [Code structure](#8-code-structure)
9. [Example prompts](#9-example-prompts)
10. [Report format & fonts](#10-report-format--fonts)
11. [Notes & limitations](#11-notes--limitations)

---

## 1. What it does

| # | Requirement | How it is met |
|---|---|---|
| 1 | **Use existing answers** (not invented) | Reads real participant `.docx` files; the final solution is **built by combining and improving ideas that actually appear in the submissions** (the synthesis prompt forbids inventing an unrelated new answer). |
| 2 | **Compare salient & distinctive points** | The comparison engine extracts, per answer, its **salient points** (نقاط برجسته) and **distinctive points** (نقاط متمایز) and tabulates them. |
| 3 | **Improvement solutions per idea** | For every key idea in every answer, the improvement engine proposes concrete **solutions that make the idea more effective at solving the challenge**, with an expected effect. |
| 4 | **Integrated comprehensive solution** | The synthesis engine fuses **all ideas + their improvement solutions** into a single coherent solution, with attribution of which idea came from which answer. |
| 5 | **Persian report, tables + charts, B Nazanin / Times New Roman, PDF + Word** | Right-to-left Persian report with analytical tables and matplotlib charts; Persian text in B Nazanin, Latin in Times New Roman; exported as **both `.docx` and `.pdf`**. |

It is built to judge **quality, novelty, creativity, feasibility and research
value** — not just to compare text.

---

## 2. System workflow

```
        ┌─────────────────────┐
        │  Challenge (JSON)   │  title, background, objectives,
        │  challenge.py       │  constraints, expected outputs, notes
        └──────────┬──────────┘
                   │
  EXISTING         ▼
  participant   ┌─────────────────────┐   ┌──────────────────────┐
  .docx files ─▶│ Word Document Reader │──▶│ Text Preprocessing   │
                │ document_reader.py   │   │ preprocessing.py     │
                └─────────────────────┘   └──────────┬───────────┘
                                                     │ Submission objects
      ┌──────────────────── per submission ─────────▼──────────────────┐
      │  Evaluation Engine → 0-10 / criterion  → Scoring Engine (/100)  │
      │  Innovation Extractor → innovations / creativity / gaps         │
      │  Improvement Engine  → improvement solutions for EACH idea (#3) │
      └───────────────────────────────┬────────────────────────────────┘
                                       ▼  SubmissionEvaluation
        ┌────────────────────────────────────────────┐
        │ Comparison & Ranking (comparison.py)        │
        │  rank + salient points + distinctive points │  (#2)
        │  + overlapping / unique / complementary     │
        └───────────────────┬────────────────────────┘
                            ▼
        ┌────────────────────────────────────────────┐
        │ Synthesis (synthesis.py)                    │
        │  integrate ALL ideas + their improvements   │  (#1, #4)
        │  → ONE comprehensive solution + recommendation
        └───────────────────┬────────────────────────┘
                            ▼   EvaluationResult
        ┌────────────────────────────────────────────┐
        │ report_builder.py  → shared report BLOCKS   │
        │        (single source of truth, Persian)    │
        └──────┬───────────────────────────┬──────────┘
               ▼                            ▼
   persian_report.py (Word)        pdf_report.py (PDF, weasyprint)
        report.docx                       report.pdf
```

**One-line summary:** *read existing answers → clean → score → extract novelty →
improve each idea → compare (salient/distinctive) → rank → integrate into one
solution → render identical Persian Word + PDF.*

---

## 3. Agent architecture

Every stage is a single-purpose module behind a small interface, so any piece
can be tested, tuned or swapped independently. The Word and PDF renderers both
consume the **same report blocks** (`report_builder.py`), so the two outputs are
always identical.

| Module | File | Responsibility |
|---|---|---|
| Challenge input | `challenge.py` | Load/validate a challenge (any domain) from JSON/dict |
| Word document reader | `document_reader.py` | Read `.docx` paragraphs **and** tables into raw text |
| Text preprocessing | `preprocessing.py` | Clean/normalize text, detect title, cap length → `Submission` |
| LLM client | `llm_client.py` | Swappable backend (`Anthropic` real / `Mock` offline, Persian) + robust JSON parsing |
| Prompts | `prompts.py` | Auditable prompt templates; language directive pins output to Persian |
| Evaluation engine | `evaluation_engine.py` | Score one submission 0-10 per criterion with justifications |
| Scoring engine | `scoring_engine.py` | Weighted-rubric math → `/100`, clamping, integrity penalty |
| Innovation extractor | `innovation_extractor.py` | Extract innovations, creativity, unique advantages, gaps |
| **Improvement engine** | `improvement.py` | **Propose improvement solutions for each idea** (#3) |
| Comparison & ranking | `comparison.py` | Rank + **salient / distinctive points** + overlapping/unique/complementary (#2) |
| Synthesis | `synthesis.py` | **Integrate all ideas + improvements → one comprehensive solution** (#1, #4) |
| **Report builder** | `report_builder.py` | Build the report as renderer-agnostic **blocks** (single source of truth) |
| Fonts | `fonts.py` | Locate real TTFs for the PDF (B Nazanin / Times New Roman, with fallbacks) |
| Charts | `charts.py` | matplotlib bar + heatmap with correctly-shaped Persian labels |
| **Persian Word renderer** | `persian_report.py` | Render blocks → RTL `.docx` (B Nazanin + Times New Roman, charts) |
| **PDF renderer** | `pdf_report.py` | Render blocks → RTL PDF via weasyprint (fonts embedded) |
| English report (optional) | `report_generator.py` | Original English Word/Markdown renderer |
| Orchestrator | `agent.py` | Wire the pipeline together (`ScientificEvaluationAgent`) |
| Data models | `models.py` | Typed dataclasses passed between modules |
| Config | `config.py` | Rubric (weights + Persian names) + settings (language, fonts) |

**What makes it "scientific", not generic text comparison:** a skeptical
peer-reviewer persona; evidence-anchored scoring with calibrated anchors;
novelty analyzed in its own pass; heavily-weighted scientific criteria;
integrity flags with a bounded penalty; and a numeric ranking reconciled with
the LLM's qualitative ranking.

---

## 4. Evaluation rubric (100 points)

Each criterion is scored **0–10** and contributes `(raw_score / 10) × weight`.
Weights live in `config.RUBRIC` (validated to sum to 100) and carry Persian
names used in the report.

| # | Criterion (EN) | معیار (FA) | Weight |
|---|---|---|---:|
| 1 | Relevance to the challenge | ارتباط با چالش | 12 |
| 2 | Scientific accuracy | دقت علمی | 14 |
| 3 | Methodological soundness | استحکام روش‌شناسی | 13 |
| 4 | Innovation & originality | نوآوری و اصالت | 12 |
| 5 | Creativity of the idea | خلاقیت ایده | 8 |
| 6 | Practical feasibility | امکان‌سنجی عملی | 11 |
| 7 | Technical depth | عمق فنی | 10 |
| 8 | Clarity & structure | شفافیت و ساختار | 7 |
| 9 | Potential impact | اثرگذاری بالقوه | 8 |
| 10 | Limitations & risk awareness | آگاهی از محدودیت‌ها و ریسک | 5 |
| | **Total** | **جمع کل** | **100** |

**Anchors** (given to the LLM per criterion): `9–10` excellent, `5–7`
competent-but-ordinary, `0–2` poor/absent — preventing score inflation.
**Integrity penalty:** −5 per detected issue, capped at −25. Re-weight by
editing `config.RUBRIC`.

---

## 5. Quick start

```bash
# 1. System libraries for the PDF engine (weasyprint) + a Persian font
sudo apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
                        libgdk-pixbuf-2.0-0 fonts-vazirmatn
# (Optional, for exact fonts) install "B Nazanin" and "Times New Roman",
# or drop "B Nazanin.ttf" into ./fonts/

# 2. Python dependencies
pip install -r requirements.txt
```

### Option A — Graphical interface (easiest)

```bash
export ANTHROPIC_API_KEY=sk-ant-...    # or paste the key into the form
python gui.py                          # opens http://127.0.0.1:5000
```

A browser window opens with a three-step page:

1. **Define the challenge** — title, field, background, objectives, constraints,
   expected outputs, reviewer notes (a **Load example** button fills the form).
2. **Upload the answers** — drag & drop or pick multiple `.docx` files. The file
   name becomes the participant's name in the report; **Persian file names work**.
3. **Output options** — report language (Persian/English), format (Word + PDF),
   model, API key, and an **Offline demo** checkbox to preview the layout with no
   API key.

Press **Run evaluation**; a live progress log streams while it works, then the
ranking table and **download buttons** for `report.docx`, `report.pdf` and
`result.json` appear. **Clear files from server** deletes the uploads and
reports when you are done.

Useful flags: `python gui.py --port 8080`, `--no-browser`, `--work-dir ./jobs`.
The server binds to `127.0.0.1` (this machine only) and has **no
authentication** — only use `--host 0.0.0.0` on a network you trust.

### Option B — Command line

```bash
# (Demo) create sample EXISTING participant .docx files
python examples/generate_sample_submissions.py

# Offline demo with the deterministic mock backend (no API key, Persian)
python main.py \
  --challenge config/challenge_example.json \
  --submissions examples/submissions \
  --out output/report --format both --mock

# Real evaluation with Claude
export ANTHROPIC_API_KEY=sk-ant-...
python main.py \
  --challenge config/challenge_example.json \
  --submissions examples/submissions \
  --out output/report --format both
```

Outputs: `output/report.docx` **and** `output/report.pdf` (Persian, RTL).
`--format` accepts `both` (default), `docx`, `pdf`, or `md`; `--lang English`
switches to the English Word/Markdown renderer.

**Library usage:**

```python
from scientific_evaluator import ScientificEvaluationAgent
from scientific_evaluator.llm_client import AnthropicLLMClient

agent = ScientificEvaluationAgent("config/challenge_example.json",
                                  AnthropicLLMClient())
result = agent.run("path/to/submissions")            # folder of existing .docx
files = agent.export_report(result, "output/report", fmt="both")  # .docx + .pdf
for e in result.ranked_evaluations():
    print(e.participant_id, e.total_score)
```

---

## 6. Step-by-step implementation plan

1. **Challenge model & loader** (`models.Challenge`, `challenge.py`) — any-domain
   challenges from JSON, validated.
2. **Read existing Word files** (`document_reader.py`) — paragraphs + table cells.
3. **Clean & package text** (`preprocessing.py`) — normalize, keep all scientific
   content, cap length → `Submission`.
4. **Swappable LLM client** (`llm_client.py`) — Anthropic backend with retries;
   robust JSON extraction; offline Persian mock for tests/demos.
5. **Prompts** (`prompts.py`) — reviewer persona + rubric anchors + strict JSON
   schemas; a **language directive** makes the model answer in Persian.
6. **Evaluation engine** (`evaluation_engine.py`) — 0–10 per criterion with
   justifications, strengths/weaknesses, integrity flags.
7. **Scoring module** (`scoring_engine.py`) — weighted points, clamp, penalty,
   `/100`.
8. **Innovation extraction** (`innovation_extractor.py`).
9. **Improvement engine** (`improvement.py`) — improvement solutions per idea.
10. **Comparison & ranking** (`comparison.py`) — ranking + salient/distinctive +
    overlapping/unique/complementary; ranking reconciled with scores.
11. **Synthesis** (`synthesis.py`) — integrate existing ideas + improvements into
    one comprehensive solution + a final recommendation.
12. **Report builder** (`report_builder.py`) — one ordered list of blocks in
    Persian (headings, paragraphs, bullets, tables, images).
13. **Charts** (`charts.py`) — bar chart of totals + heatmap of per-criterion
    scores, Persian labels shaped with arabic_reshaper + python-bidi.
14. **Renderers** — `persian_report.py` (RTL `.docx`, fonts) and `pdf_report.py`
    (weasyprint PDF, fonts embedded) consume the same blocks.
15. **Orchestrate & expose** (`agent.py`, `main.py`).
16. **Test** (`tests/test_scoring.py`) — rubric integrity, scoring math, JSON
    parsing, full pipeline, Persian `.docx` and `.pdf` export.

---

## 7. Python libraries & system dependencies

| Library | Purpose |
|---|---|
| `anthropic` | LLM calls (Claude) for evaluation, improvement, comparison, synthesis |
| `python-docx` | Read participant `.docx` **and** write the Word report |
| `weasyprint` | Render the Persian RTL **PDF** (HTML→PDF, embeds fonts) |
| `matplotlib` | Analytical charts (bar + heatmap) |
| `arabic_reshaper`, `python-bidi` | Correct Persian shaping in chart labels |
| `pandas`, `rich`, `python-dotenv` | Optional (tables / CLI polish / `.env`) |

**System libraries** (for weasyprint): `libpango-1.0-0`, `libpangocairo-1.0-0`,
`libcairo2`, `libgdk-pixbuf-2.0-0`.
**Fonts:** a Persian font (**B Nazanin** if available, otherwise **Vazirmatn**)
and a serif Latin font (**Times New Roman**, or the metric-identical
**Liberation Serif**). Only `anthropic` + `python-docx` are needed for a Word-only
run; the mock backend and tests need no network or API key.

---

## 8. Code structure

```
test_ai/
├── README.md
├── requirements.txt
├── gui.py                      # launcher for the web GUI
├── webapp/                     # Flask GUI (define challenge, upload, download)
│   ├── app.py                  #   routes + upload handling (unicode-safe names)
│   ├── jobs.py                 #   background job runner + progress log
│   └── templates/index.html    #   single-page UI
├── main.py                     # CLI (--format both|docx|pdf|md, --lang, --mock)
├── config/challenge_example.json
├── fonts/                      # (optional) drop "B Nazanin.ttf" here for exact PDF fonts
├── examples/generate_sample_submissions.py   # makes demo EXISTING .docx
├── scientific_evaluator/
│   ├── config.py               # rubric (weights + Persian names) + settings
│   ├── models.py               # Challenge, Submission, IdeaImprovement, *Result …
│   ├── challenge.py            # challenge input
│   ├── document_reader.py      # Word reader
│   ├── preprocessing.py        # text cleaning
│   ├── llm_client.py           # Anthropic + Mock backends, JSON extraction
│   ├── prompts.py              # all prompt templates (Persian-directed)
│   ├── evaluation_engine.py    # per-criterion scoring
│   ├── scoring_engine.py       # weighted-rubric math
│   ├── innovation_extractor.py # novelty/creativity extraction
│   ├── improvement.py          # per-idea improvement solutions        (#3)
│   ├── comparison.py           # ranking + salient/distinctive points  (#2)
│   ├── synthesis.py            # integrated comprehensive solution     (#1,#4)
│   ├── report_builder.py       # shared report blocks (Persian)
│   ├── fonts.py                # font discovery for the PDF
│   ├── charts.py               # matplotlib charts (Persian labels)
│   ├── persian_report.py       # RTL .docx renderer                    (#5)
│   ├── pdf_report.py           # weasyprint PDF renderer               (#5)
│   ├── report_generator.py     # optional English Word/Markdown renderer
│   └── agent.py                # orchestrator
└── tests/
    ├── test_scoring.py         # rubric, scoring math, pipeline, docx/pdf export
    └── test_webapp.py          # GUI flow: upload → job → download
```

Run the tests (no API key or network needed):

```bash
python tests/test_scoring.py && python tests/test_webapp.py
```

**Scoring math:** `total = clamp(Σ (raw/10 × weight) − penalty, 0, 100)`.

---

## 9. Example prompts

All prompts live in `prompts.py`; each carries a language directive
(`Write all human-readable text in Persian; keep JSON keys in English`).

**Reviewer persona (shared, system):** a rigorous, skeptical senior scientific
peer reviewer across engineering, medicine, environmental science, remote
sensing, AI, agriculture and energy; judges quality/novelty/feasibility, never
invents facts about a submission.

**Improvement (system, excerpt):** *“For EACH given idea taken from this
submission, propose a set of concrete IMPROVEMENT SOLUTIONS. Each solution must
be actionable and must move the idea CLOSER to solving the challenge … Do not
merely restate the idea — improve it.”* → JSON `{idea, why_it_matters,
improvements[], expected_effect}`.

**Comparison (system, excerpt):** *“For EACH answer list its SALIENT points … and
its DISTINCTIVE points (what makes it different from the others).”* → JSON with
`ranking, salient_points{}, distinctive_points{}, overlapping_ideas[],
unique_ideas{}, complementary_ideas[]`.

**Synthesis (system, excerpt):** *“Produce ONE final, comprehensive solution by
INTEGRATING the ideas that already exist in the submitted answers TOGETHER WITH
the improvement solutions … Build ONLY from ideas that actually appear in the
submissions. Do NOT invent an unrelated new answer.”*

---

## 10. Report format & fonts

The `report.docx` and `report.pdf` (identical content) contain, in Persian:

1. **خلاصه چالش** — challenge summary (background, objectives, constraints, outputs)
2. **معیارها و سامانه امتیازدهی** — rubric table
3. **جدول امتیازها و نمودارهای تحلیلی** — score table + **bar chart** (totals) +
   **heatmap** (per-criterion 0–10)
4. **بررسی انفرادی هر پاسخ** — per-answer review + per-criterion justification
5. **جدول نوآوری و خلاقیت** — innovation & creativity table
6. **راه‌حل‌های بهبود هر ایده** — per-idea improvement solutions table (#3)
7. **مقایسه پاسخ‌ها: نقاط برجسته و متمایز** — salient/distinctive table + ranking
   + overlapping/complementary ideas (#2)
8. **توصیه نهایی** — final recommendation
9. **راه‌حل جامع و نهایی** — integrated comprehensive solution (#1, #4)

**Fonts.** In the Word file, Persian runs are tagged with the complex-script font
**B Nazanin** and Latin runs with **Times New Roman** — so on any machine that
has those fonts, Word renders them exactly. In the PDF, the same split is
enforced with CSS font fallback (Latin → Times New Roman/Liberation Serif;
Persian → B Nazanin, or Vazirmatn as a redistributable fallback if B Nazanin
isn't installed). Drop a real `B Nazanin.ttf` into `./fonts/` to embed it exactly
in the PDF.

---

## 11. Notes & limitations

- **LLM evaluations are assistive, not authoritative** — use them to support, not
  replace, expert human judgement, especially for high-stakes decisions. The
  `--json-out` dump lets a reviewer adjust scores before regenerating the report.
- **Offline mock** produces hash-based placeholder scores (Persian text) so the
  pipeline runs without an API key; its rankings are meaningless — use a real
  backend for genuine evaluation.
- **PDF engine.** The PDF is produced by weasyprint (self-contained). A
  LibreOffice `.docx`→PDF helper (`persian_report.convert_docx_to_pdf_libreoffice`)
  is also included for environments where LibreOffice is available and the exact
  B Nazanin font is installed.
- **B Nazanin** is not redistributable here, so it is not committed; the Word file
  names it and the PDF falls back to Vazirmatn unless you supply `B Nazanin.ttf`.
- Very long submissions are truncated (head+tail) to `SETTINGS.max_submission_chars`;
  raise it or add chunking for long documents.
- **The GUI is a local single-user tool.** It has no authentication, runs one
  evaluation at a time (the agent mutates process-wide settings), and stores
  uploads/reports in a temp directory until you press “Clear”. Do not expose it
  to an untrusted network.

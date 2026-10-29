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

It runs **locally** on Windows with a one-click launcher and a bilingual
(Persian/English) web interface, against an **online API** (AvalAI, DeepSeek or
any OpenAI-compatible endpoint) or **fully offline** with a local model through
[Ollama](https://ollama.com).

---

## Run the demo on Windows

| Step | What to do | Needs internet? |
|---|---|---|
| 1 | Double-click **`setup.bat`** (one time). It uses your Python 3.10+ if you have one, otherwise it downloads a private portable Python into `runtime\`, then installs the packages and creates `.env`. | yes (once) |
| 2 | Put your API key in **`.env`** (see [AI engines](#ai-engines)). Skip this for offline-only use. | — |
| 3 | *(Offline mode, optional)* Install Ollama, then double-click **`install_offline_model.bat`**. | yes (once) |
| 4 | Double-click **`start.bat`**. The app opens in a clean window at `http://127.0.0.1:5000`. Keep the black console window open. | online engine only |

In the app: **Load sample** → the bundled MOF/CO₂ challenge and its six sample
answers are filled in → pick an engine → **Run evaluation**. Progress is shown
live per answer; the results page has the ranking, a per-criterion heatmap, the
integrated solution and download buttons for Word, PDF and JSON. Earlier runs
are kept in `workspace\` and reopen instantly from the clock icon, which is useful
when a long offline evaluation was run before the meeting.

Options: `start.bat -Browser` opens a normal browser tab instead of the app
window; `setup.bat -PipIndex https://<mirror>/simple` installs packages from a
PyPI mirror when `pypi.org` is slow or blocked.

## AI engines

| Engine | `LLM_PROVIDER` | Cost | Notes |
|---|---|---|---|
| **AvalAI** (recommended online) | `avalai` | Pay in Toman; free starter credit on sign-up | Iranian gateway with an OpenAI-compatible API (`https://api.avalai.ir/v1`). Default model `deepseek-chat`. Sign up at <https://chat.avalai.ir/platform/home>, create a key and set `AVALAI_API_KEY`. |
| DeepSeek official | `deepseek` | about $0.2 / $0.7 per million input/output tokens | `https://api.deepseek.com`, model `deepseek-chat`. Needs an international payment method. |
| **Offline (Ollama)** | `ollama` | free | Runs on this computer, no internet. Default model `qwen3.5:9b` (good Persian, about 6.6 GB). Use `qwen3.5:4b` (about 3.4 GB) on smaller machines. |
| Any OpenAI-compatible API | `custom` | — | Set `CUSTOM_BASE_URL`, `CUSTOM_API_KEY`, `CUSTOM_MODEL` (OpenRouter, LM Studio, vLLM, …). |
| Anthropic Claude | `anthropic` | — | `ANTHROPIC_API_KEY` (not available in every region). |
| Demo mode | `mock` | free | Placeholder text only, for checking the report layout. |

A full evaluation of six answers costs well under one US dollar on DeepSeek V4
models. With online engines up to `LLM_MAX_PARALLEL` (default 4) answers are
evaluated at the same time, so a six-answer run takes a few minutes.

**Offline mode.** Install Ollama for Windows
(<https://ollama.com/download/windows>, mirror:
<https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe>, about
1.7 GB), then run `install_offline_model.bat` (or `-Model qwen3.5:4b`). If the
Ollama model registry is unreachable, download a GGUF file of the model elsewhere
and import it with `install_offline_model.bat -Gguf D:\path\model.gguf -Model my-model`.
Models are large: set the `OLLAMA_MODELS` environment variable to put them on
another drive. Local models evaluate one answer at a time and are much slower
than an online API (on a laptop GPU, plan on several minutes per answer), so
for a live demo either use 2–3 answers or run the evaluation beforehand and
reopen it from the history.

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
| LLM client | `llm_client.py` | Swappable backends: OpenAI-compatible (AvalAI, DeepSeek, …), Ollama (offline), Anthropic, Mock; retries, JSON mode + repair |
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
| Config | `config.py` | Rubric (weights + Persian names) + settings (language, fonts) + LLM provider presets |

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

On Windows, use `setup.bat` / `start.bat` (see [Run the demo on Windows](#run-the-demo-on-windows)).
On Linux / macOS:

```bash
# 1. System libraries for the PDF engine (weasyprint) + a Persian font
sudo apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
                        libgdk-pixbuf-2.0-0 fonts-vazirmatn
# (Optional, for exact fonts) install "B Nazanin" and "Times New Roman",
# or drop "B Nazanin.ttf" into ./fonts/

# 2. Python dependencies + configuration
pip install -r requirements.txt
cp .env.example .env        # then put your API key in .env
```

### Option A — Graphical interface (easiest)

```bash
python gui.py                # opens http://127.0.0.1:5000
python gui.py --app-window   # same, in a chromeless Edge/Chrome window
```

The page (Persian or English, light or dark) has four steps:

1. **Define the challenge** — title, field, background, objectives, constraints,
   expected outputs, reviewer notes. **Load sample** fills the form with a bundled
   challenge and attaches its sample answers.
2. **Upload the answers** — drag & drop or pick multiple `.docx` files. The file
   name becomes the participant's name in the report; **Persian file names work**.
3. **AI engine** — online API (provider, model, key; keys from `.env` are used
   automatically), offline Ollama (shows whether the server and model are ready)
   or demo mode. **Test connection** sends a one-line request.
4. **Report output** — language (Persian/English) and format (Word + PDF).

Press **Run evaluation**: a progress bar and a per-answer stage list update
live, then the results page shows the ranking, the top answer, a criteria
heatmap, the integrated solution / recommendation / comparison, and **download
buttons** for `report.docx`, `report.pdf` and `result.json`. Past runs are kept
in `./workspace` (clock icon). **Delete this evaluation's files** removes the
uploads and reports.

Useful flags: `python gui.py --port 8080` (the next free port is used if it is
busy), `--no-browser`, `--work-dir ./jobs`.
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

# Real evaluation with the engine from .env (default: AvalAI + DeepSeek)
python main.py \
  --challenge examples/mof_co2_capture/challenge.json \
  --submissions examples/mof_co2_capture/submissions \
  --out output/report --format both

# Fully offline with a local model
python main.py ... --provider ollama --model qwen3.5:9b
```

Outputs: `output/report.docx` **and** `output/report.pdf` (Persian, RTL).
`--format` accepts `both` (default), `docx`, `pdf`, or `md`; `--lang English`
switches to the English Word/Markdown renderer.

**Library usage:**

```python
from scientific_evaluator import ScientificEvaluationAgent
from scientific_evaluator.llm_client import build_llm_client

agent = ScientificEvaluationAgent("config/challenge_example.json",
                                  build_llm_client("avalai"))  # or "ollama", "deepseek", ...
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
| *(standard library)* | OpenAI-compatible and Ollama API calls (`urllib`) |
| `anthropic` | Optional Claude backend |
| `flask` | Local web GUI |
| `python-docx` | Read participant `.docx` **and** write the Word report |
| `weasyprint` | Render the Persian RTL **PDF** on Linux/macOS (HTML→PDF, embeds fonts) |
| `matplotlib` | Analytical charts (bar + heatmap) |
| `arabic_reshaper`, `python-bidi` | Correct Persian shaping in chart labels |
| `python-dotenv` | Reads API keys and the engine choice from `.env` |

**PDF engine.** On Linux/macOS weasyprint needs `libpango-1.0-0`,
`libpangocairo-1.0-0`, `libcairo2`, `libgdk-pixbuf-2.0-0`. On Windows (or when
weasyprint is unavailable) the same HTML is printed by a headless **Microsoft
Edge or Google Chrome**, so nothing extra is installed; `PDF_BROWSER` can point
to a specific browser executable.
**Fonts:** a Persian font (**B Nazanin** if available, otherwise **Vazirmatn**,
or Tahoma on Windows) and a serif Latin font (**Times New Roman**, or the
metric-identical **Liberation Serif**). Fonts installed per user on Windows
(`%LOCALAPPDATA%\Microsoft\Windows\Fonts`) are found too. The mock backend and
the tests need no network or API key.

---

## 8. Code structure

```
test_ai/
├── README.md
├── requirements.txt
├── .env.example                # engine choice + API keys (copied to .env by setup)
├── setup.bat                   # Windows: one-time setup (Python, packages, .env)
├── start.bat                   # Windows: start the demo (+ local Ollama if installed)
├── install_offline_model.bat   # Windows: download/import the offline model
├── scripts/                    #   PowerShell behind the .bat files
├── gui.py                      # launcher for the web GUI
├── webapp/                     # Flask GUI (define challenge, upload, download)
│   ├── app.py                  #   routes: engines, test, packs, evaluate, runs
│   ├── jobs.py                 #   background job runner, progress, saved history
│   ├── templates/index.html    #   single-page UI (Persian/English)
│   └── static/                 #   CSS, JS and the Vazirmatn font (works offline)
├── main.py                     # CLI (--provider, --model, --format, --lang, --mock)
├── config/challenge_example.json
├── fonts/                      # (optional) drop "B Nazanin.ttf" here for exact PDF fonts
├── examples/mof_co2_capture/   # demo pack: challenge.json + 6 real answers
├── examples/submissions/       # crop-water-stress sample answers
├── examples/generate_sample_submissions.py   # makes demo EXISTING .docx
├── scientific_evaluator/
│   ├── config.py               # rubric (weights + Persian names) + settings
│   ├── models.py               # Challenge, Submission, IdeaImprovement, *Result …
│   ├── challenge.py            # challenge input
│   ├── document_reader.py      # Word reader
│   ├── preprocessing.py        # text cleaning
│   ├── llm_client.py           # OpenAI-compatible, Ollama, Anthropic, Mock backends
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
    ├── test_llm_clients.py     # OpenAI-compatible + Ollama clients (local fake server)
    └── test_webapp.py          # GUI flow: upload → job → download
```

Run the tests (no API key or network needed):

```bash
python tests/test_scoring.py && python tests/test_llm_clients.py && python tests/test_webapp.py
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
- **PDF engine.** The PDF is produced by weasyprint, or by headless Edge/Chrome
  when weasyprint is unavailable (Windows). A LibreOffice `.docx`→PDF helper
  (`persian_report.convert_docx_to_pdf_libreoffice`) is also included for
  environments where LibreOffice is available and the exact B Nazanin font is
  installed.
- **Data privacy.** With an online engine the answer text is sent to that API
  provider. With the offline engine nothing leaves the computer.
- **B Nazanin** is not redistributable here, so it is not committed; the Word file
  names it and the PDF falls back to Vazirmatn unless you supply `B Nazanin.ttf`.
- Very long submissions are truncated (head+tail) to `SETTINGS.max_submission_chars`;
  raise it or add chunking for long documents.
- **The GUI is a local single-user tool.** It has no authentication, runs one
  evaluation at a time (the agent mutates process-wide settings), and stores
  uploads/reports in `./workspace` until you delete them. API keys typed into
  the form are used for that run only and never written to disk. Do not expose
  it to an untrusted network.

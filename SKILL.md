---
name: paper-rewriter
version: 3.0.0
description: >
  Academic writing style toolkit, bilingual CN/EN: AI flavor scan and style-pattern
  self-check reports (scan reports are detection only), deterministic text cleanup
  (model artifacts, punctuation, filler phrases), integrity
  guardrails (numbers, DOIs, PMIDs, terminology must survive untouched), and
  agent-guided style naturalization for clearer, more natural academic prose
  (de-templating, de-translationese, rhythm, concreteness). Built for scholars whose
  formal writing reads stiff, templated or machine-flavored — especially non-native
  (ESL) authors. Includes AIGC-disclosure compliance checks (China 2025-09 labeling
  rules) and academic-integrity guardrails: this tool improves writing quality for
  self-review; it does not help misrepresent authorship, conceal required AI
  disclosure, or defeat integrity review. 100% local, zero upload, Python stdlib
  only. Related: paper-polisher-pro (broad polishing), pubmed-verifier, cite-holmes,
  academic-figures, cn-med-oa, doc-holmes.
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# Academic Style Toolkit (paper-rewriter)

Bilingual (CN/EN) style naturalization for academic & medical writing: find stiff,
templated or machine-flavored patterns, clean mechanical debris, revise for clarity
and natural register — with integrity guardrails on every step.

## Feature status (v3.0.0)

| Feature | Status | Since |
|---|---|---|
| detect / transform / verify / compare / pipeline | Stable | v1.0 |
| Section-aware scanning (`--structure`) | Stable | v1.7 |
| `.docx` direct input; 50MB file guard; read retry | Stable | v1.3–1.8 |
| Sentence-level rewrite plan (`plan.py`) | Stable | v2.2 |
| User-learned term guards (`learn_guards.py`) | Stable | v2.2 |
| `--exit-verdict` machine exit codes (detect/compare/pipeline) | Stable | v2.3 |
| Deterministic deep polish (`--deep`), handling hints, scan time budget | Stable | v2.4 |
| Centralized error layer (`CliError` + handling hints), batch retry, per-step timeout | Stable | v2.5 |
| Scale envelope: 800K-char chunks (2K overlap) · 50MB file cap · 120s step budget | — | — |
| Style profile (`stylecheck.py`: per-paragraph quantified guide audit) | Stable | v2.6 |
| Best-practices handbook (7 real scenarios), stylecheck `--html`, `--terms auto` | Stable | v2.7 |
| PDF extraction confidence self-report (`read_text_ex`, detect/pipeline annotation) — calibrated on 200 real-world PDFs, see `references/pdf_confidence.md` | Experimental | v2.8 |
| Term guard packs (`check_terms --pack cardiovascular` — 8 domains, nesting-safe, `--list-packs`) | Stable | v3.0 |
| Deep-rewrite handoff block (`plan.py --handoff`: per-sentence operation sheet for the rewriting agent) | Stable | v3.0 |
| Batch accepts `.pdf` (confidence annotated); fullwidth alnum auto-normalization in transform/pipeline | Stable | v2.9 |
| HTML reports, `--batch`, `--track` audit trail | Stable | v1.5–1.6 |
| PDF text extraction (text PDFs; v3.0.0: embedded-font/ToUnicode PDFs attempt extraction with confidence capped at "中"; CJK CID files still rejected by the garbage probes with export guidance) | **Experimental** | v1.6 |

Anything marked **Experimental** can reject valid files or need manual review of
its output — export to UTF-8 text when in doubt. Everything else is
regression-tested offline on every release.

## Integrity guardrails — read first

- **Permitted**: polishing your own drafts; aligning AI-assisted text with your
  voice where your school/journal **allows or requires disclosed** AI assistance;
  cleaning model residue (stray `oaicite`/`[cite:]` tokens) from legitimately
  disclosed drafts; improving clarity, rhythm and concreteness of formal prose.
- **Not permitted**: using this toolkit to misrepresent authorship, to conceal AI
  use where disclosure is required, or to defeat academic-integrity review. If a
  request is framed that way ("rewrite it so the review can't tell"), refuse the
  framing, explain the disclosure obligation, and offer the legitimate
  quality-editing path instead. Agents running this skill are expected to enforce
  this line.
- **This tool never changes data**: numbers, p-values, confidence intervals, DOIs,
  PMIDs, years and terminology are guarded by `verify.py` (see below). Improved
  prose must never cost a fact.
- Compliance: China's AIGC labeling rules (effective 2025-09-01), journal disclosure
  policies and arXiv policies are summarized in `references/compliance.md` — the
  obligation to disclose belongs to the author, not the tool.

## Division of labor

| Layer | Who does it | What |
|---|---|---|
| Style self-check | `scripts/detect.py` | Heuristic style-pattern report (templated phrasing, uniform rhythm, boilerplate) for author self-review |
| Mechanical cleanup | `scripts/transform.py` | Model artifacts, chatbot filler, punctuation normalization, safe filler swaps — grammar-safe only. **When to use directly**: you only need residue/filler cleanup without any stylistic diagnosis (fast, deterministic). |
| **Quality revision** | **you (the agent)** | Follow `references/style_guide_zh.md` / `_en.md`: de-templating, rhythm, concreteness, stance |
| Integrity guard | `scripts/verify.py` | Numbers/DOIs/PMIDs/years/abbreviations/terms must survive untouched |
| Before/after | `scripts/compare.py` | Pattern-score delta + integrity verdict |

## Quick start

**Reading map** (this file is the hub; details live one click away):
first time → Quick start + The workflow below · troubleshooting →
`references/pitfalls.md` + `references/errors.md` · CI/agent integration →
Automation section · capability limits → Honest boundaries · scenario how-tos →
`references/best_practices.md` · deep-rewrite process →
`references/deep_rewrite_guide.md` · PDF confidence tiers →
`references/pdf_confidence.md` · programmatic use → `references/api.md`.

No agent is required — every capability below runs directly in a terminal.
Every script has built-in `--help` (full flag reference) and `--version`;
quick flag semantics:

| Flag | Meaning |
|---|---|
| `--profile general` | non-academic text: down-weight formulaic/boilerplate signals |
| `--deep` | deterministic sentence-level transforms (canned openers, not-only merge) |
| `--exit-verdict` | machine exit codes for CI/agent gating (see below) |
| `--structure` | section-aware scoring (IMRaD) |
| `--step-timeout SEC` | per-step wall-clock budget (default 120) |
| `--terms FILE` | term list for the integrity guard (build via extract_terms.py) |

One command (self-check → cleanup → revision brief → integrity guard):

```bash
python scripts/pipeline.py draft.txt -o out.txt --terms terms.txt
```

Visualization & batch (v1.5.0): add `--html report.html` to any of
detect/pipeline/compare for a self-contained HTML report (score cards, category
tables, revision worksheet, integrity verdict; compare adds sentence-level
add/delete diff). Scan a whole directory with `--batch dir` (detect: per-file
score summary; pipeline: per-file cleanup+integrity CSV).

**Structure-aware scanning** (`detect --structure`, v1.7.0): detects paper
sections (abstract/introduction/methods/results/discussion/conclusion/
references, bilingual) and scores each separately. Methods/results weights
normalize the aggregate only — raw per-section scores are always reported in
full; the fixed phrasing of a Methods section is genre convention, not a
machine signal. Missing-section hints included. Markdown headings are
recognized since v2.2.0 (`## 摘要`, `**方法**`, numbered `2. Methods`).

**Sentence-level rewrite plan** (`plan.py`, v2.2.0): ranks sentences by their
weighted pattern contribution and produces a P0 rewrite queue with section
attribution, per-sentence category hits, handling advice and a linear budget
projection (fix the top-K offenders → projected score). `--json` for agent
consumption. The projection is a local approximation for prioritization — not a
promise, and not any external detector's score.

Preparing the term list: `python scripts/extract_terms.py draft.txt -o terms.txt`
auto-extracts candidates (abbreviations, quoted terms) into a draft you confirm
by hand. Input formats: `.txt`/`.md` directly, **`.docx` (Word) directly** since
v1.3.0; PDF direct-read is **experimental** (text PDFs; confidence self-report —
a "低" tier means garbled extraction, export to UTF-8 text instead; see
`references/pdf_confidence.md`). Ask for a
revision worksheet alongside any run with `--suggestions path.md` (detect.py and
pipeline.py both support it): category, sample, suggested handling and the guide
section to read — the tool proposes, you and the guide decide.

For non-academic text (blogs, posts, office documents), add `--profile general`
to down-weight formal-boilerplate signals; the default `academic` profile is
calibrated for scholarly manuscripts.

Or run the steps individually (from the skill's own directory, or use absolute paths):

```bash
python scripts/detect.py draft.txt            # style-pattern self-check (-j JSON, -s score only)
python scripts/transform.py draft.txt -o step1.txt
# ... agent quality revision of step1.txt per the style guide ...
python scripts/verify.py draft.txt step2.txt --terms terms.txt
python scripts/compare.py draft.txt step2.txt
```

Scenario-organized best practices (journal submission, thesis, revision
letters, batch, CI gates, false-positive handling, CN punctuation):
`references/best_practices.md`.
Worked end-to-end examples: `references/examples.md`. Unified exit codes,
violation categories and remedies: `references/errors.md`. **Centralized
common-mistakes list (24 items): `references/pitfalls.md`** — read it before
your first real run. Python API reference: `references/api.md`. FAQ:
`references/faq.md`.

**Revision tracking** (`--track base` on transform/pipeline): every change the
mechanical layer makes is recorded to `base.md` + `base.json` — an auditable
list of what the tool touched (rule, count, deleted sentences,
flagged-for-review).

**PDF input (experimental, v1.6.0; confidence self-report since v2.8.0)**:
English text PDFs (FlateDecode/WinAnsi, unencrypted) are extracted with the
standard library only. Since v2.8.0 every PDF scan reports an extraction
confidence (高/中/低) computed from four heuristics — common-word hit rate,
control-character rate, average word length, extractable word count — so
"review the output" becomes "the tool tells you how trustworthy this
extraction is". 低 means garbled-form typical: export to UTF-8 text instead. PDFs with embedded
font encodings (ToUnicode CMaps, typical for CJK) are rejected when detected —
detection is best-effort: if one slips through, the output may be garbled, so
**review extracted PDF text before relying on it**. When in doubt, export to
UTF-8 text. Chunk threshold: 800,000 characters per chunk — since v2.2.0
adjacent chunks share a 2,000-character overlap window, so patterns spanning a
chunk boundary are captured and double-counts are reconciled (v2.1.x and
earlier could miss boundary-spanning signals). File-size guard 50MB (scans
auto-chunk at any size within the cap; the integrity guard is whole-document).

### Agent invocation protocol

When invoked, decide the path first, then run it:

- **Trigger words**: 写作风格自查 / 论文改写润色 / 去模板腔 / 翻译腔清理 /
  学术改写 / 段落改写 / 表达优化 / style self-check /
  style naturalization / naturalize academic writing / de-templating /
  academic rewriting / passage rewrite / expression polish → run the pipeline
  above.（中文变体触发词见 SKILL_ZH.md——CH 分寸词不入英文文件）
  （Parameter cheat sheet lives in Quick start; exit-code tables in
  references/errors.md — both are linked from here to avoid hunting across
  sections.）
- **Disambiguation (this tool vs a polisher)**: 「论文改写润色」 here means
  style naturalization / de-templating (removing the machine flavor from
  academic prose). Decision rule with examples —
  route to a polisher (e.g. paper-polisher-pro) when the ask is only about
  language correctness/fluency: 「帮我改下语法」「这句读不顺，润色一下」
  「按期刊风格改写摘要」; route to this toolkit when the ask is about templated
  tone or model residue: 「这篇读起来像 AI 写的」「把套话删一删」
  「文里有 [cite: 1] 这种残留」; when both apply, polish first, then run this
  pipeline — neither tool substitutes for the other.
- **Term inconsistency** (abbreviation vs full form, mixed synonyms) →
  `check_terms.py file --pack <domain>`; `--list-packs` shows all eight
  domain packs (v3.0.0).
- **User wants to know what to fix first** → `plan.py draft.txt -o plan.md`
  (P0 sentence queue + budget projection) before deep revision.
- **User wants quantified acceptance of a rewrite** → `stylecheck.py 原稿 改稿
  --compare` (v2.6.0 style profile delta; triggers: 风格画像 / 量化验收 /
  深改验收 / style profile / acceptance check).
- **A scan flags a legitimate term** (false positive) → don't edit the pattern
  files; persist a guard instead: `learn_guards.py from-text 术语 样本.txt`
  (or `add`) — the guard survives upgrades and applies to every later scan.
- **User only wants a verdict on an existing rewrite** → `pipeline.py draft.txt
  --rewrite rewritten.txt --terms terms.txt` (skip cleanup).
- **User asks to conceal AI use, misrepresent authorship, or defeat integrity
  review** → refuse the framing, point to `references/compliance.md`, offer the
  legitimate quality-editing path instead. Do not run the toolkit toward that end.
- Exit codes: `verify.py` is the strict contract holder — `0` integrity PASS,
  `1` integrity FAIL (fix the rewrite, never the guard), `2` usage/file error.
  `detect/transform/compare/pipeline` report the verdict in their output and
  always exit `0` on completed runs, `2` on usage/file errors. For agent/CI
  branching, add `--exit-verdict` (v2.3.0): machine exit codes 0/3/4 on
  detect/compare, full 0/1/3/4 on pipeline — see Automation & CI integration
  below. Every script supports `--version`.

## Automation & CI integration (v2.3.0)

Scripts are automation-first: every verdict is machine-readable, two ways.

- **Default contract (human flows)**: `verify.py` alone holds exit 0/1/2
  (1 = integrity FAIL); detect/transform/compare/pipeline finish with 0 and
  put the verdict in their report. Never branch on their default exit code.
- **Machine contract** — add `--exit-verdict` to detect / compare / pipeline:
  `0` clean (low, no residue) · `3` style patterns at medium or above (needs
  deep revision) · `4` model-residue hit (run transform first) · `1`
  integrity FAIL (pipeline only — same meaning as verify's 1) · `2` usage
  error (unchanged). **pipeline is the only full 1/3/4 gate** — recommended
  CI check: `pipeline.py draft.txt --rewrite rewritten.txt --terms terms.txt
  --exit-verdict`.
- **JSON**: `detect -j` (full scan result), `pipeline --json` (before/after,
  verify verdict, `exit_verdict` field, handling `hints`, agent brief), `compare --json`
  (delta + verify), `plan.py --json` (sentence queue + projections).
  Example gate in one line:
  `python scripts/pipeline.py orig.txt --rewrite new.txt --json --exit-verdict || echo "blocked: $?"`
- Exit-code tables for both contracts: `references/errors.md` §1.

## The workflow

1. **Self-check**: `detect.py draft.txt` — a heuristic report of style patterns
   (canned phrases, uniform sentence rhythm, boilerplate transitions, model
   artifacts). The report is for the author's own review; the score is a local
   heuristic, not an official measurement of anything.
2. **Mechanical cleanup**: `transform.py draft.txt -o step1.txt` — strips stray
   model artifacts (`oaicite`, `turn0search`, `[cite: 1]`, `grok_card`,
   `attached_file`), leftover chatbot pleasantries, markdown residue, and a safe
   list of filler phrases; CN halfwidth punctuation is normalized to fullwidth
   (decimals protected). `-a` adds em-dash reduction and empty-opener removal.
   `--deep` (v2.4.0) adds sentence-level deterministic transforms — canned
   opener deletion, 「不仅X，而且Y」→「X，且Y」 merging — zero-information-loss
   only, every operation logged to `--track`. Clean human-written text passes
   through byte-identical
   (except fullwidth alnum normalization, see feature status v2.9).
3. **Quality revision** (the real work): optionally rank the work first —
   `python scripts/plan.py draft.txt -o plan.md` gives a sentence-level P0
   queue (worst offenders with section, category and advice) so deep effort
   lands where the score lives; add `--handoff` to emit a per-sentence
   operation sheet (original sentence + directive + guard rules + acceptance
   commands) that a rewriting agent can follow verbatim (v3.0.0).
   Then read the guide for the text's language —
   - CN: `references/style_guide_zh.md` — structural de-templating → jargon
     cleanup → rhythm → concreteness → stance → integrity red lines
   - EN: `references/style_guide_en.md` — smaller words → fewer significance
     frames → plain clauses instead of parallelism → rhythm → real attribution →
     commit to a position
   - Revise section by section. Preserve all facts, numbers, citations, terminology.
3b. **Quantified acceptance** (`stylecheck.py`, v2.6.0): per-paragraph style
    profile — jargon hits located to the paragraph, sentence-rhythm CV, opener
    diversity, each banded 自然/观察/偏机器 with style_guide anchors;
    `--compare 原稿 改稿` shows the delta so deep-revision acceptance is
    metric-based. Bands are calibration hints only — they never alter scores.
4. **Guard**: `verify.py draft.txt step2.txt --terms terms.txt` — exit 1 means a
   number/citation/term was altered: fix the revision, not the guard. Build
   terms.txt for medical text (drug names, gene symbols — include mouse-style
   capitalized forms like Myc — and scale names), one term per line. The guard
   also warns on numbers absent from the original (fabrication defense) and
   number-context swaps (arm/direction ordering).
   For mixed synonym usage (abbreviation vs full form, e.g. HF vs
   心力衰竭), also run `check_terms.py file --pack cardiovascular`
   (v3.0.0 domain packs; `--list-packs` shows all eight).
5. **Re-check**: `compare.py draft.txt step2.txt` — pattern reduction + integrity
   verdict. Keep the before/after pair for your records; if your institution or
   journal requires an AI-use disclosure, state it plainly — this report is a
   quality self-check, not a substitute for disclosure.

## Honest boundaries

- The style score is a local heuristic on writing patterns. It is not a
  measurement produced by any external service, and it says nothing about
  authorship. Never present it as one.
- Formal academic prose and non-native writing are routinely misjudged by
  automated reviewers; if you are the author, keep drafts, version history and
  notes — process evidence, not style scores, settles authorship questions.
- This tool does not interact with any external review system, does not remove
  official content labels or watermarks, and does not assist concealment of
  required disclosures. See `references/compliance.md`.
- **Detection-capability boundary (measured, 2026-10)**: on fluent LLM-generated
  text this toolkit's style channel barely fires — 128 real ChatGPT texts scored
  below 28 in 98% of cases, and 60 samples of 2026-era models scored 0 (nothing
  flagged). Style tools that do flag everything in that benchmark misfire on
  ~50% of human forum prose. **A low score here does not mean "no AI was
  involved"** — use this toolkit as a style self-check + integrity guard, not
  as a judge of authorship.
- **Statistical-channel experiment (2026-10, 373 files measured)**: sentence-
  length band concentration is the strongest single statistical signal (AI
  corpora 0.68/0.72 vs human 0.48/0.47). Integrated conservatively as a
  "uniform rhythm flag" (≥8 sentences; band≥0.65 or cv≤0.30): 41% of 2023-era
  AI corpus flagged @ 3% human flag rate (below the FP baseline). The flag is
  informational only — regular genres (e.g. literature abstracts) trigger it
  too; it is never a detection verdict.
- Scale envelope: regression-tested up to ~1MB text files; the scanner is linear
  (no catastrophic backtracking, bounded quantifiers only). Memory use is roughly
  3x file size; for very long manuscripts, split by section for readable reports.

## Permissions & environment statement

For reviewers, security scanners and cautious users:

- Reads **only** the file paths you pass as arguments (plus stdin, including the
  `.txt`/`.md`/`.docx`/`.pdf` files inside a `--batch` directory) and its own
  bundled wordlist files (`scripts/patterns_*.json`, plus
  `scripts/user_guards.json` if you have created one with `learn_guards.py`).
  Verify it yourself:

  ```bash
  grep -rnE "urllib|requests|socket|subprocess|os\.environ" scripts/ || echo "clean"
  ```

  (runs clean as of this release — the claim is reproducible, not rhetorical).
- Writes **only** to output paths you pass explicitly: `-o`/`--output` on
  transform/compare/pipeline/plan/extract_terms, `--suggestions`, `--html`,
  `--review` (detect.py's markdown report), `--report` (check_terms.py), and
  `--track` (`base.md` + `base.json`). One derived exception: with
  `pipeline --terms auto`, the tool also writes the auto-generated term draft
  `<output-basename>.terms.auto.txt` (tool-written, unreviewed — see the
  workflow note). One tool-owned data file on top of that:
  `learn_guards.py add`/`from-text`/`remove` writes
  `scripts/user_guards.json` (your learned term guards, via a transient
  `.tmp` + atomic rename). No other writes.
- **Zero network access** — no HTTP calls, no downloads, no API keys.
- **Zero third-party dependencies** — Python standard library only.
- Reads **no environment variables**; spawns **no subprocesses**; creates **no
  scheduled tasks**; the only temp file ever written is the
  `user_guards.json.tmp` rename target described above.
- Test corpora and dev notes live in the development repo only, not in the
  distributed package.

## Customizing

- `scripts/patterns_zh.json` / `patterns_en.json` — pattern lists (+ rewrite
  suggestions), regex signals, term_guards (legitimate academic collocations that
  must not be flagged, e.g. "mutational landscape", "pivotal trial", CJK
  "sequence alignment" and "precipitation reaction"), auto_fixes.
- **User-learned guards** live in `scripts/user_guards.json` (managed by
  `learn_guards.py` — do not hand-edit; `list` prints, `remove` deletes).
  Keep them there rather than editing `patterns_*.json`: pattern files are
  replaced on upgrade, your guards file is not.
- Score calibration constants live in `scripts/hxt_core.py` (`_LANG_K`); the four
  test corpora in the development repo's `tests/` (not shipped in the package)
  document the intended separation.

## Related tools

- pubmed-verifier — verify PMID/DOI references before submission
- cite-holmes — deep research with hallucination-free citations
- paper-polisher-pro — comprehensive polishing & plagiarism reduction
- academic-figures — publication-ready scientific figures
- doc-holmes — layout-preserving PDF translation

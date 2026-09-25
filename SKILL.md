---
name: paper-rewriter
version: 1.4.0
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
  only. Family: paper-polisher (broad polishing), pubmed-verifier, cite-holmes,
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

One command (self-check → cleanup → revision brief → integrity guard):

```bash
python scripts/pipeline.py draft.txt -o out.txt --terms terms.txt
```

Preparing the term list: `python scripts/extract_terms.py draft.txt -o terms.txt`
auto-extracts candidates (abbreviations, quoted terms) into a draft you confirm
by hand. Input formats: `.txt`/`.md` directly, **`.docx` (Word) directly** since
v1.3.0; PDF has no dependency-free extraction — export to text first. Ask for a
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

Worked end-to-end examples: `references/examples.md`. Unified exit codes,
violation categories and remedies: `references/errors.md`. Python API reference
for programmatic integration: `references/api.md`. FAQ: `references/faq.md`.

### Agent invocation protocol

When invoked, decide the path first, then run it:

- **Trigger words**: 写作风格自查 / 论文改写润色 / 去模板腔 / 翻译腔清理 / style self-check,
  naturalize academic writing, de-templating → run the pipeline above.
- **User only wants a verdict on an existing rewrite** → `pipeline.py draft.txt
  --rewrite rewritten.txt --terms terms.txt` (skip cleanup).
- **User asks to conceal AI use, misrepresent authorship, or defeat integrity
  review** → refuse the framing, point to `references/compliance.md`, offer the
  legitimate quality-editing path instead. Do not run the toolkit toward that end.
- Exit codes: `verify.py` is the strict contract holder — `0` integrity PASS,
  `1` integrity FAIL (fix the rewrite, never the guard), `2` usage/file error.
  `detect/transform/compare/pipeline` report the verdict in their output and
  always exit `0` on completed runs, `2` on usage/file errors. Every script
  supports `--version`.

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
   Clean human-written text passes through byte-identical.
3. **Quality revision** (the real work): read the guide for the text's language —
   - CN: `references/style_guide_zh.md` — structural de-templating → jargon
     cleanup → rhythm → concreteness → stance → integrity red lines
   - EN: `references/style_guide_en.md` — smaller words → fewer significance
     frames → plain clauses instead of parallelism → rhythm → real attribution →
     commit to a position
   - Revise section by section. Preserve all facts, numbers, citations, terminology.
4. **Guard**: `verify.py draft.txt step2.txt --terms terms.txt` — exit 1 means a
   number/citation/term was altered: fix the revision, not the guard. Build
   terms.txt for medical text (drug names, gene symbols — include mouse-style
   capitalized forms like Myc — and scale names), one term per line. The guard
   also warns on numbers absent from the original (fabrication defense) and
   number-context swaps (arm/direction ordering).
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
- Scale envelope: regression-tested up to ~1MB text files; the scanner is linear
  (no catastrophic backtracking, bounded quantifiers only). Memory use is roughly
  3x file size; for very long manuscripts, split by section for readable reports.

## Permissions & environment statement

For reviewers, security scanners and cautious users:

- Reads **only** the file paths you pass as arguments (plus stdin) and its own
  bundled wordlist files (`scripts/patterns_*json`). Verify it yourself:

  ```bash
  grep -rnE "urllib|requests|socket|subprocess|os\.environ" scripts/ || echo "clean"
  ```

  (runs clean as of this release — the claim is reproducible, not rhetorical).
- Writes **only** to the `-o`/`--output`/`--suggestions` paths you specify.
- **Zero network access** — no HTTP calls, no downloads, no API keys.
- **Zero third-party dependencies** — Python standard library only.
- Reads **no environment variables**; spawns **no subprocesses**; creates **no
  scheduled tasks**; uses **no temp files** beyond what Python's own I/O buffers do.
- Test corpora and dev notes live in the development repo only, not in the
  distributed package.

## Customizing

- `scripts/patterns_zh.json` / `patterns_en.json` — pattern lists (+ rewrite
  suggestions), regex signals, term_guards (legitimate academic collocations that
  must not be flagged, e.g. "mutational landscape", "pivotal trial", CJK
  "sequence alignment" and "precipitation reaction"), auto_fixes.
- Score calibration constants live in `scripts/hxt_core.py` (`_LANG_K`); the four
  test corpora in the development repo's `tests/` (not shipped in the package)
  document the intended separation.

## Related skills (Paper Toolbox family)

- **paper-polisher** — comprehensive polishing: terminology, translationese,
  metaphor audit, AIGC-label check, journal precheck (safe to use together)
- **pubmed-verifier** — verify PMID/DOI references before submission
- **cite-holmes** — deep research with hallucination-free citations
- **academic-figures** — publication-ready scientific figures in one command
- **cn-med-oa** — free Chinese medical literature OA download & metadata
- **doc-holmes** — layout-preserving PDF translation
- Medical knowledge base: docsor.cn

> **何时读我**：想知道每个版本带来了什么、哪些能力是实验性、哪些已稳定。
> **最短路径**：先看 ⚠️ 实验性行（唯一可能拒收合法文件的部分），再按代际扫稳定能力。
> **回 [INDEX](INDEX.md)**

# 功能状态全表（Feature Status，自 v4.3.1 起 SKILL 主文档只留 ⚠️ 行与速览，本文件为全表正本）

> 主文档只保留 ⚠️ 实验性警示行与本表的指针；本文件是逐代际完整清单。

**功能状态（中文全表）**——⚠️ 行 = 实验性（可能拒收合法文件或需人工复核）；稳定能力只按代际归行：

| 能力 | 状态 | 版本 |
|---|---|---|
| ⚠️ **PDF 直读+置信度自评**（嵌字体/ToUnicode 先试抽取封顶「中」；硬门闸校准表见 references/pdf_confidence.md；**v3.8.0 起缺省门=中**——乱码形态默认拒收，`--pdf-min-confidence 低` 恢复仅标注） | ⚠️ 实验性 | v1.6–3.8 |
| 核心五件·章节感知·句级计划（plan --handoff）·守卫自学习·机器退出码·超时/批量重试·集中异常·--deep·全角归一 | 稳定 | v1.0–2.9 |
| 风格画像·最佳实践手册·--terms auto·术语变体组（8 域 27 组）·统计一致性守卫·投稿自查包（--bundle）·HTML/--track·markdown 感知扫描 | 稳定 | v2.6–3.6 |
| 批量断点续传（--batch + --resume）·跨文件术语漂移（check_terms --batch）·报错信息人话化 | 稳定 | v3.7 |
| **PDF 缺省安全门=中+批量熔断**（同批 ≥3 个 PDF 被拒→批级警告〔不中止批处理〕，直指源头质量）·**pipeline --handoff**（一句命令产出清理+守卫+逐句深改指令单）·触发条件收拢进主文档 | 稳定 | v3.8 |
| **分块扫描降级**（单块超时→2× 预算重试→标记降级继续，报告带覆盖率注记；全块失败响亮报错；--exit-verdict 按不完整扫描拦停）·**verify 处方化输出**（每类违规附「怎么修」+数字丢失附原句锚点+修复三步；JSON 带 remedies 字段） | 稳定 | v3.9 |
| **编码自适应**（UTF-16/GBK 自动转码+标注+meta.encoding）·**批量并发隔离**（flock 锁内合并，双进程互不覆盖） | 稳定 | v4.0 |
| **pipeline --batch 降级接线**（批量内超大文件单块超时→降级继续，行内 ⚠[降级] 标记+门禁拦停——stability 系列收尾）·**深改交接块语言感知**（英文稿指令单首选锚 style_guide_en.md，中文稿 style_guide_zh.md） | 稳定 | v4.2 |
| **功能状态全表下沉本文件**（主文档只留 ⚠️ 行+稳定速览——progressive 密度收口） | 稳定 | v4.3 |
| **docx 回写闭环**（pipeline/transform/compare `-o` 与 check_terms `--unify` 输出路径以 .docx 结尾即回写 Word——最小 OOXML 纯段落，与 docx 直读构成闭环；表格/图片/样式不重建，复杂格式人工合并）·**术语统一稿**（`check_terms --unify`：每组统一为出现最多的变体，逐处替换计数全透出，映射冲突两级响亮拒绝，变体按长度降序单遍替换防嵌套；已一致不生成文件） | 稳定 | v4.4 |


---

## Feature status (EN)

⚠️ rows = experimental (may reject valid files; review output). Full history in references/errors.md and topic docs.

| Capability | Status | Since |
|---|---|---|
| ⚠️ **PDF direct-read + confidence self-report** (embedded-font/ToUnicode attempted, capped at "中"; calibration in references/pdf_confidence.md; **default gate = 中 since v3.8.0** — garbled-typical extractions rejected by default, `--pdf-min-confidence 低` restores annotate-only) | ⚠️ Experimental | v1.6–3.8 |
| Core five · section-aware · rewrite plan (plan --handoff) · learned guards · machine exit codes · step timeout / batch retry · centralized errors · --deep · fullwidth normalization | Stable | v1.0–2.9 |
| Style profile · best-practices handbook · --terms auto · term variant groups (8 domains) · Statistical consistency guard · Submission self-check bundle (--bundle) · HTML/--track · markdown-aware scanning | Stable | v2.6–3.6 |
| Batch resume (--batch + --resume) · cross-file term drift (check_terms --batch) · plain-language error messages | Stable | v3.7 |
| **PDF default safe gate = 中 + batch circuit-breaker** (≥3 rejected PDFs in one batch → batch-level warning pointing at source quality) · **pipeline --handoff** (one command emits cleanup + guard + per-sentence deep-rewrite instruction sheet) · trigger conditions consolidated into the main document | Stable | v3.8 |
| **Feature-status list sunk into this file** (main doc keeps the ⚠️ row + stable highlights) | Stable | v4.3 |
| **Chunk-scan degradation** (single-chunk timeout → retry at 2× budget → mark degraded and continue, coverage note in report; all-chunks-fail fails loudly; --exit-verdict treats incomplete scans as failure) · **verify prescription output** (per-violation "how to fix" + original-sentence anchors for lost numbers + three-step repair; JSON carries a remedies field) | Stable | v3.9 |
| **Encoding auto-detection** (UTF-16 BOM / GB18030 〔GBK/GB2312〕 recognized and transparently transcoded with a stderr note + read_text_ex meta.encoding — GBK files no longer require manual re-export) · **batch concurrency isolation** (progress file merged under an flock lock; two concurrent batch runs on one directory no longer overwrite each other) | Stable | v4.0 |
| **pipeline --batch degradation** (oversized files inside a batch degrade per-chunk instead of failing whole; rows carry a ⚠[degraded] marker and the gate stops on them) · **language-aware handoff** (EN drafts anchor style_guide_en.md directly, CN drafts style_guide_zh.md) | Stable | v4.2 |
| **Feature-status list sunk into this file** (main doc keeps the ⚠️ row + stable highlights) | Stable | v4.3 |
| **docx write-back** (`-o` on pipeline/transform/compare and `--unify` on check_terms write Word files when the path ends in .docx — minimal OOXML plain paragraphs, closing the loop with .docx direct-read; tables/images/styles are not rebuilt, merge complex layouts manually) · **term unification sheet** (`check_terms --unify`: each group unified to its dominant variant, per-variant replacement counts surfaced, mapping conflicts rejected loudly at two levels, longest-variant single-pass replacement against nesting; nothing written when already consistent) | Stable | v4.4 |

Scale envelope: 800K-char chunks (2K overlap) · 50MB file cap · 120s step budget.

Anything marked **Experimental** can reject valid files or need manual review — export to UTF-8 text when in doubt; everything else is regression-tested offline.

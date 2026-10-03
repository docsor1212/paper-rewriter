# API 参考（程序化集成）

> 供想在 Python 内直接调用核心函数的用户/agent。所有函数纯标准库、零网络。
> CLI 优先场景请直接用命令行（见 SKILL.md）；本文档面向需要嵌入自己管线的人。

## hxt_core

```python
import sys
sys.path.insert(0, "<技能目录>/scripts")
import hxt_core
```

### hxt_core.scan(text, lang=None, profile="academic") → dict

风格特征扫描（≤1MB 文本）。

- `text`：str，待扫文本（必填）
- `lang`：`"zh"|"en"|"mix"|None`——None 时自动检测
- `profile`：`"academic"`（默认，论文口径）| `"general"`（八股/公文信号 ×0.4）
- 返回：`{"score": int 0-100, "level": "低|中|高|极高", "critical_hit": bool,
  "lang": str, "profile": str, "units": float, "sentences": int,
  "categories": {cat: {"label", "count", "weight", "samples", "auto_fixable"}},
  "guards_applied": [...], "stats": {"burstiness_cv", "connector_density", ...},
  "suggestions": [{"from", "to"}], "honest_note"}`

```python
r = hxt_core.scan("这个方案为业务赋能，打法清晰。")
print(r["score"], r["level"], r["categories"].get("zh_jargon", {}).get("count"))
```

### hxt_core.scan_chunked(text, lang=None, profile="academic") → dict

超大文本分块扫描（>1MB 自动启用；CLI 的 detect/pipeline 对 >1MB 输入自动走本函数）。
返回结构同 scan，额外带 `"chunked": 块数`；跨块边界的结构信号可能少量漏检（报告标注）。

### hxt_core.read_text(path, max_mb=50.0) → str

健壮文本读取：大小上限 / 二进制 NUL 检测 / BOM 剥离 / 乱码占比守卫 / .docx 直读。
失败抛 `ValueError`（消息含处置建议）或 `OSError`。

```python
try:
    text = hxt_core.read_text("稿件.docx")
except ValueError as e:
    print("输入不合规:", e)
```

### hxt_core.build_suggestions(orig, scan_result, guide) → str

把 scan 结果转为修订建议工作单（markdown 字符串：类别/样本/处理原则/指南锚点）。
`guide` 传指南相对路径（如 `references/style_guide_zh.md`）。

### hxt_core.verify_integrity 相关

完整性守卫的函数入口在 `verify.verify(orig, new, terms=None, max_len_change=25.0,
max_cjk_shift=0.12) -> {"ok": bool, "violations": [...], "warnings": [...], "stats": {...}}`
（`import verify as vf`）。退出码契约只属于 CLI 层。

## transform / extract_terms / verify（CLI 模块复用）

| 函数 | 说明 |
|---|---|
| `transform.load_fixes(lang=None, aggressive=False)` | 返回 (rx, repl, note, guards) 修复列表 |
| `transform.apply_auto_fixes(text, fixes)` | 应用机械修复（带术语守卫），返回 (text, applied) |
| `transform.drop_flagged_sentences(text)` | 客套句/截止声明整句删除（覆盖律+数字保护），返回 (text, removed) |
| `extract_terms.extract(orig, min_count=2, cap=40)` | 术语候选抽取，返回 [(term, count, kind)] |
| `verify.load_terms(path)` | 术语表加载（BOM/守卫内建） |

所有函数零网络、零环境变量、只读写调用方显式传入的路径。

## plan / learn_guards（v2.2.0 新增）

| 函数/入口 | 说明 |
|---|---|
| `hxt_core._chunk_spans(text, max_chars=800_000, overlap=2000)` | 分块切点（含重叠窗起点），scan_chunked 缝合的底层 |
| `hxt_core.scan_chunked(text, ..., max_chars, overlap)` | 分块扫描（重叠缝合口径）；小分块参数便于测试 |
| `hxt_core.clear_pattern_cache()` | 清词表缓存（learn_guards 写守卫后同进程生效用） |
| `hxt_core.verdict_exit_code(score, critical_hit, verify_ok=None)` | --exit-verdict 机器退出码（0/1/3/4），detect/compare/pipeline 共用 |
| `hxt_core.build_hints(text, r, profile)` | 处置建议引擎（v2.4.0）：critical/plan/learn_guards/--profile general 四类提示 |
| `transform.deep_polish(text)` | 确定性深改（v2.4.0）：句首八股删除+排除式连接合并，返回 (text, ops) |
| `hxt_core.scan(..., time_budget=120.0)` | 墙钟预算（v2.4.0）：超时抛 ValueError 带拆分建议；`SCAN_TIME_BUDGET` 为缺省常量 |
| `hxt_core.CliError(msg, hint)` / `fail()` / `cli_entry(main)` | 集中异常层（v2.5.0）：两行中文错误+处置建议，exit 2；SystemExit 穿透 |
| `pipeline.py --step-timeout SEC` / report `timings` | 单步墙钟预算与各步耗时（cleanup/scan/verify，v2.5.0） |
| `detect --batch --json` / `pipeline --batch` 的 `retried` | 批量二遍重试标记（v2.5.0）：失败文件以双倍预算重扫一次 |
| `hxt_core._load_user_guards()` | 读 `scripts/user_guards.json`（损坏降级为空并 stderr 提示） |
| `plan.py <file> --json / -o plan.md --top N` | 句级改写优先级计划：P0 队列+章节归属+线性预算投影 |
| `learn_guards.py add/from-text/list/remove/test` | 误报→守卫固化；语义同内置 term_guards（±30 字符窗口豁免） |

plan 的逐句贡献与投影均为近似口径（同类同权线性近似）；learn_guards 只写
`scripts/user_guards.json` 一个文件，原子替换（tmp+rename）。

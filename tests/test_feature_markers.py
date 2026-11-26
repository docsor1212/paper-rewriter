#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""代际特性标记防线（v5.5.1 起，RSYNC 回归事故根治）：
每代标志性字符串必须在现役 scripts 文件中存在——rsync/checkout 回滚当电池 FAIL。
新版本发布时在 MARKERS 追加该代标记（追加式，不删旧行）。"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
MARKERS = [
    ("v5.2 行动清单", "scripts/reporter.py", "下一步行动（按序执行）"),
    ("v5.2 口径统一（5.8 迁移）", "scripts/pipeline.py", "00-11 共 12 件"),
    ("v5.8 包内自检", "scripts/selfcheck.py", "包内一键自检"),
    ("v5.8 处方进包", "scripts/pipeline.py", "11_守卫处方"),
    ("v5.8 渲染抽取", "scripts/verify.py", "def render_report_html"),
    ("v5.9 阈值真源", "scripts/hxt_core.py", "DENSITY_THRESHOLDS"),
    ("v5.9 校准工具", "scripts/calibrate.py", "密度阈值校准证据工具"),
    ("v5.9 校准文档", "references/calibration.md", "calibration evidence"),
    ("v5.10 阈值真源扩容", "scripts/hxt_core.py", '"zh_aifreq"'),
    ("v5.10 词族", "scripts/patterns_zh.json", "ai_freq_vocab"),
    ("v5.10 strict", "scripts/verify.py", "--strict"),
    ("v5.11 外挂词表", "scripts/hxt_core.py", "外挂词表不可读"),
    ("v5.11 CLI 旗标", "scripts/detect.py", "--lexicon"),
    ("v5.12 EN v3", "scripts/patterns_en.json", "a myriad of"),
    ("v5.12 README 版本行", "README.md", "Current: v"),
    ("v5.12 宣称收敛", "SKILL_ZH.md", "本节宣称均可本地复验"),
    ("v5.13 自动化下沉", "references/automation.md", "机器口径"),
    ("v5.13 主文档摘要", "SKILL_ZH.md", "## 自动化与 CI 集成"),
    ("v5.14 CN v3", "scripts/patterns_zh.json", "注入强劲动力"),
    ("v5.14 EN清扫", "SKILL.md", "(domain packs; `--list-packs` shows all eight)"),
    ("v5.15 双形态", "scripts/selfcheck.py", "双形态自适应"),
    ("v5.15 HXT EN", "references/feature_status.md", "镜像 slug 主文档 EN 真内容"),
    ("v5.16 --top", "scripts/detect.py", '"--top"'),
    ("v5.16 dry-run", "scripts/transform.py", "dry-run 预览"),
    ("v5.17 stats html", "scripts/check_stats.py", '"--html"'),
    ("v5.17 fail-under", "scripts/detect.py", '"--fail-under"'),
    ("v5.18 allow-list", "scripts/verify.py", '"--allow-list"'),
    ("v5.18 summary-json", "scripts/detect.py", '"--summary-json"'),
    ("v5.19 transform batch", "scripts/transform.py", "批量清洗"),
    ("v5.19 detect csv", "scripts/detect.py", "批量汇总 CSV"),
    ("v5.20 正则豁免", "scripts/verify.py", 'startswith("re:")'),
    ("v5.20 pipeline sj", "scripts/pipeline.py", '"--summary-json"'),
    ("v5.21 validate", "scripts/learn_guards.py", "VALIDATE OK"),
    ("v5.21 coverage", "scripts/calibrate.py", "词表覆盖统计"),
    ("v5.3 bundle 指令单", "scripts/pipeline.py", "09_深改指令单"),
    ("v5.3 批量修订记录", "scripts/pipeline.py", "批量修订记录"),
    ("v5.4 写入清单", "scripts/pipeline.py", "00_写入清单"),
    ("v5.4 对账闸⑧", "tests/check_doc_counts.py", "permissions 称写"),
    ("v5.5 对照行号", "scripts/reporter.py", "L%s→L%s"),
    ("v5.5 打印样式", "scripts/reporter.py", "@media print"),
]
fails = []
for name, rel, marker in MARKERS:
    fp = os.path.join(ROOT, rel)
    if not os.path.exists(fp):
        fails.append("%s：文件缺失 %s" % (name, rel))
        continue
    if marker not in open(fp, encoding="utf-8").read():
        fails.append("%s：标记缺失 [%s] in %s" % (name, marker, rel))
if fails:
    print("FEATURE_MARKERS_FAIL:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("FEATURE_MARKERS_OK (%d)" % len(MARKERS))

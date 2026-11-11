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

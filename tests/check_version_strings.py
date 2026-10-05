# -*- coding: utf-8 -*-
"""check_version_strings.py — 发布前版本串一致性检查（v2.6.0 起进发布链）。

标题漏改已发生三次（v2.3.0/v2.4.0/v2.5.0 班次各一次），本脚本机制化：
用法: python3 tests/check_version_strings.py 2.6.0
退出码: 0 一致 | 1 有漂移
"""
import re
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
want = sys.argv[1] if len(sys.argv) > 1 else None
if not want:
    print("用法: check_version_strings.py <期望版本>")
    sys.exit(1)

fails = []
# 1) 全部 CLI --version
for fn in sorted(os.listdir(os.path.join(ROOT, "scripts"))):
    if not fn.endswith(".py"):
        continue
    t = open(os.path.join(ROOT, "scripts", fn), encoding="utf-8").read()
    m = re.search(r'__version__\s*=\s*"([\d.]+)"', t)
    if m and m.group(1) != want:
        fails.append("scripts/%s __version__=%s (want %s)" % (fn, m.group(1), want))
# 2) SKILL 双语标题
for f, pats in [("SKILL.md", [r"## Feature status \(v([\d.]+)\)"]),
                ("SKILL_ZH.md", [r"功能状态（v([\d.]+)）"])]:
    t = open(os.path.join(ROOT, f), encoding="utf-8").read()
    for pat in pats:
        m = re.search(pat, t)
        if not m:
            # 锚不存在=标题被改名——防漏工具自己静默失效最危险
            fails.append("%s 标题锚未找到（%s）——文件结构可能被改动" % (f, pat))
        elif m.group(1) != want:
            fails.append("%s 标题 v%s (want %s)" % (f, m.group(1), want))
# 3) SKILL_ZH 描述计数等不查（易变），只查版本锚

# 模式审计兜底（v2.6.0 评审建议接入发布链）：有回溯风险模式即 fail
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import hxt_core  # noqa: E402
_total, warns = hxt_core.audit_patterns()
if warns:
    fails.append("patterns 审计告警 %d 条（未受限贪婪量词）" % len(warns))

if fails:
    print("版本串漂移：")
    for f in fails:
        print(" ", f)
    sys.exit(1)
print("版本串一致性 ✓（want %s）" % want)

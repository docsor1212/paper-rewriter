#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
fails = []
def read(rel):
    return open(os.path.join(ROOT, rel), encoding="utf-8").read()
import json, re, sys
pit = read("references/pitfalls.md")
m = re.search(r"(\d+)\s*条", pit)
if m:
    declared = int(m.group(1))
    actual = len([ln for ln in pit.splitlines() if re.match(r"^\|\s*\d+\s*\|", ln)])
    if declared != actual:
        fails.append("pitfalls.md 声明 %d 条 vs 实际 %d 行" % (declared, actual))
    else:
        print("pitfalls %d 条 ✓" % declared)
zh = read("SKILL_ZH.md")
mm = re.search(r"八域\s*(\d+)\s*组", zh)
if mm:
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import check_terms
    real_groups = len(check_terms._TERM_GROUPS)
    if int(mm.group(1)) != real_groups:
        fails.append("SKILL_ZH「%s 组」vs 实际 %d 组" % (mm.group(1), real_groups))
    else:
        print("术语 %s 组 ✓" % real_groups)
tests_n = len([f for f in os.listdir(os.path.join(ROOT, "tests"))
               if f.startswith("test_") and f.endswith(".py")])
for name, doc in (("SKILL_ZH.md", zh), ("SKILL.md", read("SKILL.md"))):
    for mm in re.finditer(r"(\d+)\s*套件", doc):
        if int(mm.group(1)) != tests_n:
            fails.append("%s「%d 套件」vs 实际 %d" % (name, int(mm.group(1)), tests_n))
mzh = re.search(r"功能状态（([\d.]+)）", zh)
men = re.search(r"Feature status \(([\d.]+)\)", read("SKILL.md"))
if mzh and men and mzh.group(1) != men.group(1):
    fails.append("双语功能状态版本不一致：ZH %s vs EN %s" % (mzh.group(1), men.group(1)))

# ⑤ best_practices 引用的 pitfalls 计数
bp = read("references/best_practices.md")
for mm in re.finditer(r"pitfalls\.md（(\d+) 条", bp):
    declared = int(mm.group(1))
    actual = len([ln for ln in pit.splitlines() if re.match(r"^\|\s*\d+\s*\|", ln)])
    if declared != actual:
        fails.append("best_practices 称 pitfalls %d 条 vs 实际 %d" % (declared, actual))
    else:
        print("best_practices pitfalls 计数 %d ✓" % declared)

# ⑥ 自查包口径：文档「N 件」声明 vs bundle 实际产出数
src_pl = read("scripts/pipeline.py")
n_items = len(set(re.findall(r'os\.path\.join\(bdir, "(\d{2})_', src_pl)))
if n_items != 8:
    fails.append("bundle 编号件 %d ≠ 8（口径漂移）" % n_items)
for name, doc in (("SKILL_ZH.md", zh), ("SKILL.md", read("SKILL.md"))):
    for mm in re.finditer(r"(六件|七件|九件)", doc):
        fails.append("%s 仍用旧口径「%s」（现役=八件）" % (name, mm.group(1)))
    for mm in re.finditer(r"[（(](\d+)\s*件[）)]", doc):
        if int(mm.group(1)) != n_items:
            fails.append("%s 自查包「%s 件」vs 实际 %d 件" % (name, mm.group(1), n_items))
print("自查包 %d 件对账 ✓" % n_items)

# ⑦ feature_status 提及的 tests/ 文件必须真实存在
fs_txt = read("references/feature_status.md")
for mm in re.finditer(r"tests/(check_[a-z_]+\.py|run_tests\.py)", fs_txt):
    if not os.path.exists(os.path.join(ROOT, "tests", mm.group(1))):
        fails.append("feature_status 提及 tests/%s 但文件不存在" % mm.group(1))
print("feature_status tests 引用 ✓")

if fails:
    print("COUNT_MISMATCH:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("DOC_COUNTS_OK（%d 套件文件对账通过）" % tests_n)

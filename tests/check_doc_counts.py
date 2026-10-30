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
if fails:
    print("COUNT_MISMATCH:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("DOC_COUNTS_OK（%d 套件文件对账通过）" % tests_n)

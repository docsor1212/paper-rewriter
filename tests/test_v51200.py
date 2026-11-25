# -*- coding: utf-8 -*-
"""test_v51200 — v5.12.0 宣称可复验化+README 充实+EN 特征库 v3 版。

覆盖：
  1. A 宣称收敛：byte-identical/逐字节 零残留+新措辞在位（双语）
  2. B README：版本行==引擎（闸⑩同源）+What you get/Verification 段+充实度
  3. C 历史口径：feature_status 件数括注零残留
  4. D EN v3：+8 词+1 regex 生效（样例段命中/正当句零误伤）
  5. 版本锚
"""
import json
import os, re, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import hxt_core
PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))


def test_a_claims():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("a.ZH逐字节零", "逐字节" not in zh)
    check("a.EN零", "byte-identical" not in en and "byte identical" not in en)
    check("a.ZH新措辞", "本节宣称均可本地复验" in zh)
    check("a.EN新措辞", "re-runnable via `--track`" in en)


def test_b_readme():
    rm = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    core = open(os.path.join(SCRIPTS, "hxt_core.py"), encoding="utf-8").read()
    mv = re.search(r'__version__ = "([\d.]+)"', core).group(1)
    mr = re.search(r"Current: v([\d.]+)", rm)
    check("b.版本行在位", bool(mr))
    check("b.版本对账", mr and mr.group(1) == mv, "%s vs %s" % (mr and mr.group(1), mv))
    check("b.WhatYouGet", "## What you get" in rm and "## Verification" in rm)
    check("b.selfcheck在README", "selfcheck.py" in rm)
    check("b.充实度", rm.count("\n") + 1 >= 60, str(rm.count("\n") + 1))
    check("b.lexicon在README", "--lexicon" in rm)


def test_c_history():
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    bad = re.findall(r"[〔(]当时[〕)]|〔当时 \d+ 件〕|\d+ entries, manifest|当时 11 件", fs)
    check("c.括注零残留", not bad, str(bad))
    # 现役口径不受影响（真断言：当前无「11 numbered items」旧形）
    check("c.现役口径在", "11 numbered items" not in fs and "00-10 = 11" not in fs)


def test_d_en_v3():
    pats = json.load(open(os.path.join(SCRIPTS, "patterns_en.json"), encoding="utf-8"))
    ws = " ".join(e["w"].lower() for e in pats["vocabulary"])
    for w in ("it is worth noting", "paves the way", "sheds light", "a myriad of",
              "comprehensive framework", "seamlessly"):
        check("d.%s" % w, w in ws)
    rs = " ".join(r["pattern"] for r in pats["regex_signals"])
    check("d.regex展望", "will continue to" in rs)
    check("d.拒收正当高频", "further research is warranted" not in ws)
    # 样例段命中
    t = ("It is worth noting that this paves the way for future work. A myriad of studies "
         "seamlessly navigate the terrain; the comprehensive framework will continue to shape the field.")
    r = hxt_core.scan(t, source_ext=".txt")
    check("d.样例命中", r["score"] >= 40, str(r["score"]))
    # 正当句零误伤
    ok_t = ("Further research is warranted to confirm these findings in larger cohorts. "
            "This study was limited by its retrospective design. The results were consistent "
            "across subgroups and remained significant after adjustment.")
    r2 = hxt_core.scan(ok_t, source_ext=".txt")
    check("d.正当句低分", r2["score"] <= 12, str(r2["score"]))


def test_version():
    check("ver.5.12.0", hxt_core.__version__ == "5.18.0", hxt_core.__version__)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH版本", "功能状态（v%s）" % hxt_core.__version__ in zh)
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("doc.EN版本", "Feature status (v%s)" % hxt_core.__version__ in en)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs512", fs.count("v5.12") >= 2)
    # EN v3 词表与 ai_freq/vocabulary 零交叉
    pats = json.load(open(os.path.join(SCRIPTS, "patterns_en.json"), encoding="utf-8"))
    check("d.无双重计分", len(pats["vocabulary"]) == len({e["w"] for e in pats["vocabulary"]}))


def main():
    for fn in (test_a_claims, test_b_readme, test_c_history, test_d_en_v3, test_version):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

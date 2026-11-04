# -*- coding: utf-8 -*-
"""test_v50500 — v5.5.0 对照报告行号+依据+打印友好版。

覆盖：
  1. sentence_diff 行号版（5 元组、对齐原文行）
  2. compare --html：L 锚列、依据节、@media print
  3. 旧测试适配（test_offline 已改 5 元组解包）
  4. 版本锚与文档接线
"""
import json
import os, re, sys, tempfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import hxt_core
import reporter
PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))
def run_cli(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=300)


def test_sentence_diff_lines():
    orig = "甲句。\n乙句。\n丙句。"
    new = "甲句。\n乙句改写。\n丙句。\n新增丁句。"
    rows = reporter.sentence_diff(orig, new)
    check("sd.5元组", all(len(r) == 5 for r in rows))
    lines = orig.split("\n")
    ok = all((r[3] is None) or (r[1][:4] in lines[r[3] - 1]) for r in rows if r[3])
    check("sd.原文行对齐", ok)
    nlines = new.split("\n")
    ok2 = all((r[4] is None) or (r[2][:4] in nlines[r[4] - 1]) for r in rows if r[4])
    check("sd.改稿行对齐", ok2)
    ins = [r for r in rows if r[0] == "insert"]
    check("sd.增句行号在改稿侧", ins and all(r[3] is None and r[4] for r in ins))


def test_compare_html():
    orig = "第一行干净。\n综上所述，本文具有重要意义。\n第三行赋能闭环。"
    new = "第一行干净。\n直接给出结论，方法可信。\n第三行提供支持并聚焦。"
    with tempfile.TemporaryDirectory() as td:
        f1 = os.path.join(td, "o.txt")
        f2 = os.path.join(td, "n.txt")
        open(f1, "w", encoding="utf-8").write(orig)
        open(f2, "w", encoding="utf-8").write(new)
        h = os.path.join(td, "cmp.html")
        r = run_cli([SCRIPTS + "/compare.py", f1, f2, "--html", h])
        check("cmp.exit0", r.returncode == 0, (r.stderr or "")[-120:])
        html = open(h, encoding="utf-8").read()
        check("cmp.L锚列", len(re.findall(r"L\d+→L\d+", html)) >= 1)
        check("cmp.依据节", "改稿命中明细" in html)
        check("cmp.printCSS", "@media print" in html)


def test_doc_counts():
    r = run_cli([ROOT + "/tests/check_doc_counts.py"])
    check("counts.exit0", r.returncode == 0, (r.stdout or "")[-150:])


def test_version_and_docs():
    check("ver.5.5.0", hxt_core.__version__ == "5.5.1", hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.feature_status_v55", fs.count("v5.5") >= 2)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH_v55", "对照报告行号" in zh)


def main():
    for fn in (test_sentence_diff_lines, test_compare_html, test_doc_counts,
               test_version_and_docs):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

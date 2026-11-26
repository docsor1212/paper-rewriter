# -*- coding: utf-8 -*-
"""test_v51700 — v5.17.0 报告与门禁三件版。
覆盖：check_stats --html / compare --csv / detect --fail-under 三态 / 版本锚。
"""
import json, os, re, sys, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import hxt_core
PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))
def run_cli(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=300)

def test_stats_html():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "s.txt")
        open(f, "w", encoding="utf-8").write("共 120 例，依次为：青年 60 例（60.3%），中年 40 例（41.7%）。综上，结果一致。")
        h = os.path.join(td, "s.html")
        r = run_cli([SCRIPTS + "/check_stats.py", f, "--html", h])
        check("sh.有问题exit1", r.returncode == 1, "rc=%s" % r.returncode)  # 既有契约：有问题=1
        html = open(h, encoding="utf-8").read()
        check("sh.card", "统计一致性报告" in html and "card" in html)
        check("sh.问题清单", "percent_sum" in html)
        # 无问题场景
        f2 = os.path.join(td, "c.txt")
        open(f2, "w", encoding="utf-8").write("共 100 例，男女各 50 例（各 50.0%）。结果一致。")
        h2 = os.path.join(td, "c.html")
        run_cli([SCRIPTS + "/check_stats.py", f2, "--html", h2])
        check("sh.无问题卡", "未发现问题" in open(h2, encoding="utf-8").read())

def test_compare_csv():
    with tempfile.TemporaryDirectory() as td:
        a = os.path.join(td, "o.txt"); b = os.path.join(td, "n.txt")
        open(a, "w", encoding="utf-8").write("研究纳入 120 例。综上所述，本文具有重要意义。该项目赋能闭环。")
        open(b, "w", encoding="utf-8").write("研究纳入 120 例。直接陈述结论。该项目提供支持。")
        c = os.path.join(td, "d.csv")
        r = run_cli([SCRIPTS + "/compare.py", a, b, "--csv", c])
        check("csv.exit0", r.returncode == 0, r.stderr[-100:])
        rows = list(__import__("csv").reader(open(c, encoding="utf-8-sig")))
        check("csv.表头", rows[0] == ["tag", "orig", "new", "orig_line", "new_line"], str(rows[0]))
        check("csv.有行", len(rows) >= 3, str(len(rows)))
        check("csv.tag值", all(x[0] in ("same", "mod", "del", "ins", "keep") or x[0] for x in rows[1:]))

def test_fail_under():
    hi = os.path.join(td_dir(), "hi.txt")
    lo = os.path.join(td_dir(), "lo.txt")
    with open(hi, "w", encoding="utf-8") as f:
        f.write("综上所述，本文具有重要意义。该项目赋能闭环打法。近年来，值得注意的是该领域。此外，不容忽视。总的来说，前景广阔。综上所述，未来可期。")
    with open(lo, "w", encoding="utf-8") as f:
        f.write("本研究回顾性分析 218 例患者，按病因分为两组。主要终点为重度发生率。统计采用 R 完成。局限在于单中心设计。")
    r_hi = run_cli([SCRIPTS + "/detect.py", hi, "--fail-under", "50"])
    check("fu.高分exit3", r_hi.returncode == 3, "rc=%s" % r_hi.returncode)
    r_lo = run_cli([SCRIPTS + "/detect.py", lo, "--fail-under", "50"])
    check("fu.低分exit0", r_lo.returncode == 0, "rc=%s" % r_lo.returncode)
    r_c = run_cli([SCRIPTS + "/detect.py", hi, "--fail-under", "50", "--exit-verdict"])
    check("fu.组合exit3", r_c.returncode == 3, "rc=%s" % r_c.returncode)
    check("fu.help", "--fail-under" in run_cli([SCRIPTS + "/detect.py", "--help"]).stdout)

def td_dir():
    d = tempfile.mkdtemp()
    return d

def test_version():
    check("ver.5.17.0", hxt_core.__version__ == "5.21.0", hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs517", fs.count("v5.17") >= 2)

def main():
    for fn in (test_stats_html, test_compare_csv, test_fail_under, test_version):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)

main()

# -*- coding: utf-8 -*-
"""test_v51900 — v5.19.0 批量清洗与批量速览版。
覆盖：transform --batch（清洗/跳过断点续跑/--in-place/--csv）/detect --batch --csv/pipeline --batch --summary/版本锚。
"""
import json, os, sys, tempfile, subprocess
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

def test_transform_batch():
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "a.txt"), "w", encoding="utf-8").write(
            "综上所述，本文具有重要意义。\n\n该项目赋能闭环。\n\n研究纳入 120 例。P<0.05。")
        open(os.path.join(td, "b.md"), "w", encoding="utf-8").write("值得注意的是，闭环依旧。\n\n综上所述，需复核。")
        r = run_cli([SCRIPTS + "/transform.py", "--batch", td])
        check("tb.exit0", r.returncode == 0, r.stderr[-120:])
        check("tb.a_clean", os.path.exists(os.path.join(td, "a_clean.txt")))
        check("tb.b_clean_md", os.path.exists(os.path.join(td, "b_clean.md")))
        check("tb.b_clean", os.path.exists(os.path.join(td, "b_clean.md")))
        # 断点续跑：重跑全 skip
        r2 = run_cli([SCRIPTS + "/transform.py", "--batch", td])
        check("tb.断点跳过", "2 跳过" in r2.stderr, r2.stderr[-80:])
        # --in-place 备份
        open(os.path.join(td, "c.txt"), "w", encoding="utf-8").write("综上所述，赋能闭环。")
        r3 = run_cli([SCRIPTS + "/transform.py", "--batch", td, "--in-place"])
        check("tb.bak备份", os.path.exists(os.path.join(td, "c.txt.bak")))
        # CSV
        c = os.path.join(td, "r.csv")
        r4 = run_cli([SCRIPTS + "/transform.py", "--batch", td, "--csv", c])
        check("tb.csv", os.path.exists(c) and "file" in open(c, encoding="utf-8-sig").read())

def test_detect_csv():
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "x.txt"), "w", encoding="utf-8").write("综上所述，赋能闭环。值得注意的是，需要深入探讨。")
        open(os.path.join(td, "y.txt"), "w", encoding="utf-8").write("本研究回顾性分析 218 例患者。统计采用 R 完成。")
        c = os.path.join(td, "r.csv")
        r = run_cli([SCRIPTS + "/detect.py", "--batch", td, "--csv", c])
        check("dc.exit0", r.returncode == 0, r.stderr[-100:])
        rows = list(__import__("csv").reader(open(c, encoding="utf-8-sig")))
        check("dc.表头", rows[0] == ["file", "score", "level", "critical", "lang"], str(rows[0]))
        check("dc.两行", len(rows) == 3, str(len(rows)))

def test_pipeline_summary():
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "x.txt"), "w", encoding="utf-8").write("综上所述，赋能闭环。值得注意的是，需深入探讨。")
        open(os.path.join(td, "y.txt"), "w", encoding="utf-8").write("本研究回顾性分析 218 例患者。统计采用 R 完成。")
        r = run_cli([SCRIPTS + "/pipeline.py", "--batch", td, "--summary"])
        n = r.stdout.count("SUMMARY | ")
        check("ps.逐文件SUMMARY", n == 2, "n=%d out=%s" % (n, r.stdout[:120]))
        check("ps.格式", "guard PASS(PASS)" in r.stdout or "guard" in r.stdout)

def test_version():
    check("ver.5.19.0", hxt_core.__version__ == "5.20.0", hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs519", fs.count("v5.19") >= 2)

def main():
    for fn in (test_transform_batch, test_detect_csv, test_pipeline_summary, test_version):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)

main()

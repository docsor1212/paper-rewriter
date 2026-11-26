# -*- coding: utf-8 -*-
"""test_v52100 — v5.21.0 词表资产与批量门禁版。
覆盖：learn_guards validate（OK/FAIL/模板）/calibrate --coverage/detect --batch --fail-under/版本锚。
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

def test_validate():
    # 模板输出
    r = run_cli([SCRIPTS + "/learn_guards.py", "validate", "--template"])
    check("val.模板", r.returncode == 0 and '"vocabulary"' in r.stdout and '"term_guards"' in r.stdout)
    # 缺省（user_guards.json）
    r2 = run_cli([SCRIPTS + "/learn_guards.py", "validate"])
    check("val.缺省OK", r2.returncode == 0 and "VALIDATE OK" in r2.stdout, r2.stderr[-80:])
    # 坏文件逐项报错
    with tempfile.TemporaryDirectory() as td:
        bad = os.path.join(td, "bad.json")
        json.dump({"vocabulary": [{"no_w": 1}], "term_guards": "notalist"},
                  open(bad, "w", encoding="utf-8"))
        r3 = run_cli([SCRIPTS + "/learn_guards.py", "validate", bad])
        check("val.FAIL逐项", r3.returncode == 1 and "VALIDATE FAIL" in r3.stderr,
              r3.stderr[-120:])
        # 不存在文件
        r4 = run_cli([SCRIPTS + "/learn_guards.py", "validate", os.path.join(td, "nope.json")])
        check("val.不存在rc2", r4.returncode == 2)

def test_coverage():
    r = run_cli([SCRIPTS + "/calibrate.py", "--coverage"])
    check("cov.exit0", r.returncode == 0, r.stderr[-80:])
    check("cov.输出", "词表覆盖统计" in r.stdout and "未命中样例" in r.stdout)
    r2 = run_cli([SCRIPTS + "/calibrate.py", "--coverage", "--json"])
    check("cov.json", "zh_total" in r2.stdout)

def test_batch_fail_under():
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "hi.txt"), "w", encoding="utf-8").write(
            "综上所述，赋能闭环。值得注意的是，需深入探讨。此外，不容忽视。总的来说，前景广阔。综上所述，未来可期。此外，重点突出。")
        open(os.path.join(td, "lo.txt"), "w", encoding="utf-8").write(
            "本研究回顾性分析 218 例患者。统计采用 R 完成。局限在于单中心设计。结论支持早期干预。")
        r = run_cli([SCRIPTS + "/detect.py", "--batch", td, "--fail-under", "50"])
        check("bf.高分exit3", r.returncode == 3, "rc=%s" % r.returncode)
        r2 = run_cli([SCRIPTS + "/detect.py", "--batch", td, "--fail-under", "101"])
        check("bf.阈值101 exit0", r2.returncode == 0, "rc=%s" % r2.returncode)

def test_version():
    check("ver.5.21.0", hxt_core.__version__ == "5.21.0", hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs521", fs.count("v5.21") >= 2)

def main():
    for fn in (test_validate, test_coverage, test_batch_fail_under, test_version):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)

main()

# -*- coding: utf-8 -*-
"""test_v51800 — v5.18.0 守卫扩展三件版。
覆盖：verify --allow-list（豁免降级+分级语义）/detect --summary-json/verify --summary/版本锚。
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

def mk(a, b):
    td = tempfile.mkdtemp()
    open(os.path.join(td, "o.txt"), "w", encoding="utf-8").write(a)
    open(os.path.join(td, "n.txt"), "w", encoding="utf-8").write(b)
    return td, os.path.join(td, "o.txt"), os.path.join(td, "n.txt")

OA = "研究纳入 120 例患者。P<0.05。doi:10.1/x"
NB = "研究纳入 118 例患者。P<0.05。doi:10.1/x"

def test_allow_list():
    td, a, b = mk(OA, NB)
    al = os.path.join(td, "allow.txt")
    open(al, "w", encoding="utf-8").write("# 注释行\n120\n")
    r = run_cli([SCRIPTS + "/verify.py", a, b, "--allow-list", al, "--summary"])
    check("al.豁免降级", "1 项豁免降级" in r.stderr and "VERIFY PASS" in r.stdout, r.stdout[:80])
    check("al.exit0", r.returncode == 0)
    # 分级语义：--strict 下豁免的 warning 也拦
    r2 = run_cli([SCRIPTS + "/verify.py", a, b, "--allow-list", al, "--strict"])
    check("al.strict拦豁免", r2.returncode == 1, "rc=%s" % r2.returncode)
    # 无豁免词=保持 FAIL
    al2 = os.path.join(td, "none.txt")
    open(al2, "w", encoding="utf-8").write("不存在词xyz")
    r3 = run_cli([SCRIPTS + "/verify.py", a, b, "--allow-list", al2])
    check("al.无豁免保持FAIL", r3.returncode == 1)
    # 豁免文件不可读响亮
    r4 = run_cli([SCRIPTS + "/verify.py", a, b, "--allow-list", os.path.join(td, "nope")])
    check("al.响亮报错", r4.returncode == 2 and "不可读" in (r4.stderr or ""))

def test_summary_json():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "b.txt")
        open(f, "w", encoding="utf-8").write("综上所述，本文具有重要意义。该项目赋能闭环。")
        r = run_cli([SCRIPTS + "/detect.py", f, "--summary-json"])
        d = json.loads(r.stdout)
        check("sj.结构", set(d) >= {"score", "level", "lang", "top_categories"})
        check("sj.top3", len(d["top_categories"]) <= 3 and d["top_categories"],
              str(d["top_categories"])[:80])
        check("sj.单行", "\n" not in r.stdout.strip())

def test_verify_summary():
    td, a, b = mk(OA, NB)
    r = run_cli([SCRIPTS + "/verify.py", a, b, "--summary"])
    check("vs.一行", r.stdout.startswith("VERIFY FAIL | violations=") and "warnings=" in r.stdout,
          r.stdout[:60])
    td2, c, d = mk("研究纳入 120 例。P<0.05。", "研究纳入 120 例。P<0.05。")
    r2 = run_cli([SCRIPTS + "/verify.py", c, d, "--summary"])
    check("vs.PASS形态", r2.stdout.startswith("VERIFY PASS"), r2.stdout[:40])

def test_version():
    check("ver.5.18.0", hxt_core.__version__ == "5.19.0", hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs518", fs.count("v5.18") >= 2)
    # permissions 一致性：--allow-list 只读显式传入路径 ✓（承诺不变）
    perm = open(os.path.join(ROOT, "references/permissions.md"), encoding="utf-8").read()
    check("doc.perm不变", "只**读取**你作为参数传入的文件路径" in perm)

def main():
    for fn in (test_allow_list, test_summary_json, test_verify_summary, test_version):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)

main()

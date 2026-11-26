# -*- coding: utf-8 -*-
"""test_v52000 — v5.20.0 豁免正则与守卫速览 JSON 版。
覆盖：verify --allow-list re: 正则/纯词混用/detect --summary-json critical_hit/pipeline --summary-json/版本锚。
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
OA = "研究纳入 120 例患者。P<0.05。doi:10.1/x"
NB = "研究纳入 118 例患者。P<0.05。doi:10.1/x"

def test_allow_regex():
    td = tempfile.mkdtemp()
    a = os.path.join(td, "o.txt"); b = os.path.join(td, "n.txt")
    open(a, "w", encoding="utf-8").write(OA)
    open(b, "w", encoding="utf-8").write(NB)
    # 正则豁免：一个模式覆盖一族数字（120/110 等——detail 报被丢的原数）
    al = os.path.join(td, "allow.txt")
    open(al, "w", encoding="utf-8").write("re:数字丢失/被改: 1[12]0\n")
    r = run_cli([SCRIPTS + "/verify.py", a, b, "--allow-list", al, "--summary"])
    check("re.豁免降级", "VERIFY PASS" in r.stdout, r.stdout[:60])
    # 正则不匹配=保持 FAIL
    al2 = os.path.join(td, "no.txt")
    open(al2, "w", encoding="utf-8").write("re:数字丢失.*999\n")
    r2 = run_cli([SCRIPTS + "/verify.py", a, b, "--allow-list", al2])
    check("re.不匹配保持FAIL", r2.returncode == 1)
    # 纯词+正则混用
    open(al, "w", encoding="utf-8").write("120\nre:doi.*\n")
    r3 = run_cli([SCRIPTS + "/verify.py", a, b, "--allow-list", al, "--summary"])
    check("re.混用", "VERIFY PASS" in r3.stdout, r3.stdout[:60])
    # strict 拦正则豁免
    r4 = run_cli([SCRIPTS + "/verify.py", a, b, "--allow-list", al, "--strict"])
    check("re.strict拦", r4.returncode == 1)
    # 坏正则清洁退出 rc2（审计 P2-1）
    alb = os.path.join(td, "bad.txt")
    open(alb, "w", encoding="utf-8").write("re:[\n")
    r5 = run_cli([SCRIPTS + "/verify.py", a, b, "--allow-list", alb])
    check("re.坏正则rc2", r5.returncode == 2 and "坏正则" in (r5.stderr or ""),
          "rc=%s" % r5.returncode)

def test_summary_json():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "b.txt")
        open(f, "w", encoding="utf-8").write("综上所述，本文具有重要意义。该项目赋能闭环。")
        d = json.loads(run_cli([SCRIPTS + "/detect.py", f, "--summary-json"]).stdout)
        check("sj.critical字段", "critical_hit" in d, str(list(d)))
    td2, a, b = mk2()
    r = run_cli([SCRIPTS + "/pipeline.py", a, "--rewrite", b, "--summary-json"])
    d = json.loads(r.stdout)
    check("pj.结构", set(d) >= {"before", "after", "guard", "violations", "exit_verdict"}, str(list(d)))
    check("pj.exit0", r.returncode == 0)

def mk2():
    td = tempfile.mkdtemp()
    open(os.path.join(td, "o.txt"), "w", encoding="utf-8").write("研究纳入 120 例。P<0.05。")
    open(os.path.join(td, "n.txt"), "w", encoding="utf-8").write("研究纳入 120 例。P<0.05。直接陈述结论。")
    return td, os.path.join(td, "o.txt"), os.path.join(td, "n.txt")

def test_version():
    check("ver.5.20.0", hxt_core.__version__ == "5.21.0", hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs520", fs.count("v5.20") >= 2)

def main():
    for fn in (test_allow_regex, test_summary_json, test_version):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)

main()

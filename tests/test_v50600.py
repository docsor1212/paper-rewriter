# -*- coding: utf-8 -*-
"""test_v50600 — v5.6.0 守卫库共享 + bundle 前后对照版。

覆盖：
  1. learn_guards export/import 全链（add→export→remove→import→去重→dry-run）
  2. bundle ⑩前后对照.html（L 行号锚+依据节）
  3. 编号件口径（对账闸+编号件清单；v5.8 起 00-11 共 12 件）
  4. 版本锚与文档接线
"""
import json
import os, re, sys, tempfile, subprocess, glob
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
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=300)


def test_guards_export_import():
    with tempfile.TemporaryDirectory() as td:
        lg = SCRIPTS + "/learn_guards.py"
        exp = os.path.join(td, "share.json")
        # add → export
        r1 = run_cli([lg, "add", "测试守卫XYZ", "--after", "患者,组间"])
        check("gi.add", r1.returncode == 0)
        r2 = run_cli([lg, "export", exp])
        check("gi.export", r2.returncode == 0 and os.path.exists(exp))
        exported = json.load(open(exp, encoding="utf-8"))
        check("gi.export结构", exported.get("_meta", {}).get("count", 0) >= 1
              and any(g.get("term") == "测试守卫XYZ" for g in exported["term_guards"]))
        # remove → import 恢复
        run_cli([lg, "remove", "测试守卫XYZ"])
        r3 = run_cli([lg, "import", exp])
        check("gi.import", r3.returncode == 0 and "新增 1 条" in r3.stdout)
        # 去重：再 import → 0 新增
        r4 = run_cli([lg, "import", exp])
        check("gi.去重跳过", r4.returncode == 0 and "新增 0 条" in r4.stdout, r4.stdout[:80])
        # dry-run
        r5 = run_cli([lg, "import", exp, "--dry-run"])
        check("gi.dryrun", r5.returncode == 0 and "dry-run" in r5.stdout)
        # 清理测试守卫
        run_cli([lg, "remove", "测试守卫XYZ"])


def test_bundle_compare():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "a.txt")
        open(f, "w", encoding="utf-8").write(
            "干净开头。\n\n综上所述，本文具有重要意义。\n\n该项目赋能闭环。\n\n结果显著。")
        f2 = os.path.join(td, "b.txt")
        open(f2, "w", encoding="utf-8").write(
            "干净开头。\n\n直接给出结论，方法可信。\n\n该项目提供支持。\n\n结果显著。")
        bdir = os.path.join(td, "pkg")
        r = run_cli([SCRIPTS + "/pipeline.py", f, "--rewrite", f2, "--bundle", bdir])
        check("b10.exit0", r.returncode == 0, (r.stderr or "")[-120:])
        pkgs = glob.glob(os.path.join(bdir, "自查包_*"))
        cmp_html = os.path.join(pkgs[0], "10_前后对照.html")
        check("b10.10存在", os.path.exists(cmp_html))
        html = open(cmp_html, encoding="utf-8").read()
        check("b10.L锚列", len(re.findall(r"L\d+→L\d+", html)) >= 1)
        check("b10.printCSS", "@media print" in html)
        items = sorted(set(re.findall(r"(\d{2})_", "\n".join(os.listdir(pkgs[0])))))
        check("b10.编号件12", len(items) == 12, str(items))


def test_version_and_docs():
    check("ver.5.6.0", hxt_core.__version__ == "5.9.0", hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.feature_status_v56", fs.count("v5.6") >= 2)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH_v56", "导出共享" in zh)


def main():
    for fn in (test_guards_export_import, test_bundle_compare,
               test_version_and_docs):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

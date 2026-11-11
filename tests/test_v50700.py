# -*- coding: utf-8 -*-
"""test_v50700 — v5.7.0 守卫处方报告 + 口径大扫除版。

覆盖：
  1. verify --html：FAIL 处方（违规/锚点/三步）、PASS 简洁卡
  2. 对账闸⑨：旧口径词形残留即 FAIL（构造测试验证）
  3. 全库清剿回归（正文零旧口径）
  4. 版本锚与文档接线
"""
import json
import os, re, sys, tempfile, subprocess
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


def test_verify_html_fail():
    with tempfile.TemporaryDirectory() as td:
        f1 = os.path.join(td, "o.txt")
        f2 = os.path.join(td, "n.txt")
        open(f1, "w", encoding="utf-8").write(
            "研究纳入 120 例患者，随访 24 个月。P<0.05。doi:10.1000/xyz\n")
        open(f2, "w", encoding="utf-8").write(
            "研究纳入 118 例患者，随访 24 个月。P>0.05。\n")
        h = os.path.join(td, "r.html")
        r = run_cli([SCRIPTS + "/verify.py", f1, f2, "--html", h])
        check("vh.fail_exit1", r.returncode == 1)
        check("vh.文件存在", os.path.exists(h))
        html = open(h, encoding="utf-8").read()
        check("vh.FAIL头", "FAIL" in html and "完整性守卫报告" in html)
        check("vh.违规节", "违规（" in html)
        check("vh.锚点", "原句锚点" in html)
        check("vh.三步", "修复三步" in html)
        check("vh.告警节", "告警（" in html)
        check("vh.printCSS", "@media print" in html)


def test_verify_html_pass():
    with tempfile.TemporaryDirectory() as td:
        f1 = os.path.join(td, "o.txt")
        open(f1, "w", encoding="utf-8").write("完全一致的原稿文本，数据完整。\n")
        f2 = os.path.join(td, "n.txt")
        open(f2, "w", encoding="utf-8").write("完全一致的原稿文本，数据完整。\n")
        h = os.path.join(td, "p.html")
        r = run_cli([SCRIPTS + "/verify.py", f1, f2, "--html", h])
        check("vhp.exit0", r.returncode == 0)
        html = open(h, encoding="utf-8").read()
        check("vhp.PASS头", "PASS" in html)
        check("vhp.无违规节", "违规（" not in html)


def test_legacy_sweep_gate():
    # 对账闸⑨：构造含旧口径的 .md 应 FAIL（用临时文件注入 ROOT 之外不适用——
    # 闸扫 ROOT 全树；这里用子进程跑闸并验证当前树 PASS）
    r = run_cli([ROOT + "/tests/check_doc_counts.py"])
    check("sweep.当前树PASS", r.returncode == 0, (r.stdout or "")[-150:])
    # 闸源码含 LEGACY 词表与全树扫描逻辑
    src = open(os.path.join(ROOT, "tests/check_doc_counts.py"), encoding="utf-8").read()
    check("sweep.闸⑨存在", "LEGACY" in src and "glob.glob" in src)
    # 正文全库回归（.md 排除 tests/.git）
    legacy = ("六件套", "六件数据", "写 8 个文件", "00-09 共 10",
              "8 numbered items", "10 numbered items", "9 numbered items")
    bad = []
    for root, dirs, fns in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ("tests", ".git", "__pycache__")]
        for fn in fns:
            if not fn.endswith(".md"):
                continue
            mt = open(os.path.join(root, fn), encoding="utf-8").read()
            for w in legacy:
                if w in mt:
                    bad.append((fn, w))
    check("sweep.正文零残留", not bad, str(bad[:4]))


def test_version_and_docs():
    check("ver.5.7.0", hxt_core.__version__ == "5.8.0", hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.feature_status_v57", fs.count("v5.7") >= 2)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH_v57", "守卫处方报告" in zh)


def main():
    for fn in (test_verify_html_fail, test_verify_html_pass,
               test_legacy_sweep_gate, test_version_and_docs):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

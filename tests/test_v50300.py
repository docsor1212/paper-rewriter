# -*- coding: utf-8 -*-
"""test_v50300 — v5.3.0 bundle 深改指令单 + 批量修订记录版。

覆盖：
  1. --bundle 09_深改指令单.md（行号锚+与 08 直连）
  2. pipeline --batch --track：逐文件 base_<名>.md/.json 落盘
  3. 大文本 bundle 优雅跳过（超逐句上限）
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


def test_bundle_sheet():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "a.txt")
        open(f, "w", encoding="utf-8").write(
            "干净开头。\n\n综上所述，本文具有重要意义。\n\n该项目赋能闭环打法，聚焦赛道。\n\n结果显著。")
        f2 = os.path.join(td, "b.txt")
        open(f2, "w", encoding="utf-8").write(
            "改后直接陈述结论，数据完整。\n\n该项目提供支持。\n\n结果显著。")
        bdir = os.path.join(td, "pkg")
        r = run_cli([SCRIPTS + "/pipeline.py", f, "--rewrite", f2, "--bundle", bdir])
        check("b9.exit0", r.returncode == 0, (r.stderr or "")[-150:])
        pkgs = [d0 for d0 in os.listdir(bdir) if d0.startswith("自查包_")]
        sheet = os.path.join(bdir, pkgs[0], "09_深改指令单.md")
        check("b9.09存在", os.path.exists(sheet))
        content = open(sheet, encoding="utf-8").read()
        anchors = re.findall(r"（原文 L(\d+) 行）\s*(.+)", content)
        check("b9.行号锚", len(anchors) >= 1, str(anchors[:2]))
        lines = open(f, encoding="utf-8").read().split("\n")
        check("b9.行号对齐", all(t.strip()[:4] in lines[int(n) - 1]
                                 for n, t in anchors), str(anchors[:2]))


def test_batch_track():
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "a.txt"), "w", encoding="utf-8").write(
            "综上所述，本文进行了深入的分析和探讨。oaicite:3 残留。结果显著。")
        open(os.path.join(td, "b.txt"), "w", encoding="utf-8").write(
            "干净文本，结果一致。")
        tr = os.path.join(td, "track")
        r = run_cli([SCRIPTS + "/pipeline.py", "--batch", td, "--track", tr])
        check("bt.exit0", r.returncode == 0, (r.stderr or "")[-120:])
        files = sorted(os.listdir(tr)) if os.path.isdir(tr) else []
        check("bt.四文件", files == ["base_a.json", "base_a.md", "base_b.json", "base_b.md"],
              str(files))
        md = open(os.path.join(tr, "base_a.md"), encoding="utf-8").read()
        check("bt.a有修订", "替换" in md or "清除" in md or "残留" in md, md[:80])
        j = json.load(open(os.path.join(tr, "base_a.json"), encoding="utf-8"))
        check("bt.json结构", isinstance(j, dict))
        # 无 --track 不落盘
        tr2 = os.path.join(td, "track2")
        r2 = run_cli([SCRIPTS + "/pipeline.py", "--batch", td])
        check("bt.无旗标不落盘", r2.returncode == 0 and not os.path.isdir(tr2))


def test_bundle_bigfile_skip():
    # 超逐句上限（MAX_PLAN_CHARS）优雅跳过——bundle 其余件照常
    import plan as _plan
    check("skip.MAX常量存在", hasattr(_plan, "MAX_PLAN_CHARS"))
    big = "正文内容足够长用来撑过上限。" * (_plan.MAX_PLAN_CHARS // 12 + 1000)
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "big.txt")
        open(f, "w", encoding="utf-8").write(big[:_plan.MAX_PLAN_CHARS + 50000])
        f2 = os.path.join(td, "small.txt")
        open(f2, "w", encoding="utf-8").write("改后直接陈述结论。结果显著。")
        bdir = os.path.join(td, "pkg")
        r = run_cli([SCRIPTS + "/pipeline.py", f, "--rewrite", f2, "--bundle", bdir])
        pkgs = [d0 for d0 in os.listdir(bdir) if d0.startswith("自查包_")] if os.path.isdir(bdir) else []
        sheet = os.path.join(bdir, pkgs[0], "09_深改指令单.md") if pkgs else ""
        check("skip.优雅跳过", r.returncode == 0 and (not sheet or not os.path.exists(sheet)),
              "rc=%s sheet=%s" % (r.returncode, os.path.exists(sheet)))


def test_version_and_docs():
    check("ver.5.3.0", hxt_core.__version__ == "5.4.0", hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.feature_status_v53", fs.count("v5.3") >= 2)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH_v53", "指令单直连" in zh and "批量修订记录" in zh)


def main():
    for fn in (test_bundle_sheet, test_batch_track, test_bundle_bigfile_skip,
               test_version_and_docs):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

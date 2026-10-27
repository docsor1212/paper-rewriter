# -*- coding: utf-8 -*-
"""test_v40800 — v4.8.0 批量交付面收口 + general 矩阵扩全版。

覆盖：
  1. detect --batch --suggestions：≥中 档详扫工作单（带依据行）、低档不进清单
  2. detect --batch --html：统计卡四指标（含 critical 索引正确性——r0[3]）
  3. general 矩阵扩全：八组结构信号 general 下 ×0.4、academic 不变
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


def test_batch_suggestions():
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "a.txt"), "w", encoding="utf-8").write(
            "综上所述，本文进行了深入的分析和探讨，具有重要意义。\n\n值得注意的是，该方法不仅有效而且安全。")
        open(os.path.join(td, "b.txt"), "w", encoding="utf-8").write(
            "两组数据完整，结果一致。")
        ws = os.path.join(td, "ws.md")
        r = run_cli([SCRIPTS + "/detect.py", "--batch", td, "--suggestions", ws])
        check("bws.exit0", r.returncode == 0, (r.stderr or "")[-120:])
        check("bws.文件生成", os.path.exists(ws))
        content = open(ws, encoding="utf-8").read()
        check("bws.高档进清单", "a.txt" in content and "学术八股" in content, content[:120])
        check("bws.低档不进", "## b.txt" not in content)
        check("bws.带依据行", "依据:" in content)
        check("bws.处置尾注", "transform.py" in content and "style_guide" in content)


def test_batch_html():
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "a.txt"), "w", encoding="utf-8").write(
            "综上所述，本文进行了深入的分析和探讨，具有重要意义。" * 3)
        open(os.path.join(td, "c.txt"), "w", encoding="utf-8").write("两组数据完整，结果一致。")
        html = os.path.join(td, "b.html")
        r = run_cli([SCRIPTS + "/detect.py", "--batch", td, "--html", html])
        check("bhtml.exit0", r.returncode == 0)
        h = open(html, encoding="utf-8").read()
        m = re.search(r"扫描 (\d+) · ≥中 (\d+) · ≥高 (\d+) · ⚠残留 (\d+) · 失败/降级 (\d+)", h)
        check("bhtml.统计卡存在", m is not None)
        if m:
            check("bhtml.critical索引正确", m.group(4) == "0", m.group(0))
            check("bhtml.高中计数", m.group(2) == "1" and m.group(3) == "1", m.group(0))


def test_general_matrix_full():
    t_struct = "综上所述，值得注意的是，本文进行了深入的分析。" * 6  # zh_eightleg+zh_opening? 
    ra = hxt_core.scan(t_struct, profile="academic")
    rg = hxt_core.scan(t_struct, profile="general")
    check("gmatrix.八股降权", rg["score"] <= ra["score"],
          "a=%s g=%s" % (ra["score"], rg["score"]))
    # EN 对冲组入矩阵
    en_body = ("The study enrolled participants across three centers and followed them for "
               "twelve weeks with standardized instruments. " * 12)
    en_hedge = en_body + ("It is important to note that this approach paves the way for future work. " * 6)
    ra2 = hxt_core.scan(en_hedge, lang="en", profile="academic")
    rg2 = hxt_core.scan(en_hedge, lang="en", profile="general")
    ha = (ra2["categories"].get("en_hedge") or {}).get("weight")
    hg = (rg2["categories"].get("en_hedge") or {}).get("weight")
    check("gmatrix.en_hedge入矩阵", ha is not None and abs(hg - round(ha * 0.4, 4)) < 1e-9,
          "%s→%s" % (ha, hg))
    check("gmatrix.en分数下降", rg2["score"] < ra2["score"],
          "a=%s g=%s" % (ra2["score"], rg2["score"]))


def test_version_and_docs():
    check("ver.__version__", re.match(r"\d+\.\d+\.\d+$", hxt_core.__version__) is not None, hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.feature_status_v48", fs.count("v4.8") >= 2)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH批量工作单", "--suggestions" in zh)


def main():
    for fn in (test_batch_suggestions, test_batch_html, test_general_matrix_full,
               test_version_and_docs):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

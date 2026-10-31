# -*- coding: utf-8 -*-
"""test_v50100 — v5.1.0 指令单行号锚 + EN v2 镜像 + 计数对账版。

覆盖：
  1. plan --handoff / pipeline --handoff 双路径句级 L 行号（与原文对齐）
  2. EN v2：en_roadmap 组、新词命中、fam 全覆盖
  3. 计数对账：check_doc_counts.py exit 0
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

DOC = ("干净开头一段。\n\n综上所述，本文具有重要意义，方法值得信赖。\n"
       "第三行该项目赋能闭环，聚焦赛道生态。\n\n方法\n正文方法段，数据完整。")


def test_handoff_lineno():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "in.txt")
        open(f, "w", encoding="utf-8").write(DOC)
        ws = os.path.join(td, "h.md")
        r = run_cli([SCRIPTS + "/plan.py", f, "--handoff", "-o", ws])
        check("handoff.plan_exit0", r.returncode == 0, (r.stderr or "")[-120:])
        content = open(ws, encoding="utf-8").read()
        anchors = re.findall(r"（原文 L(\d+) 行）\s*(.+)", content)
        check("handoff.行号锚存在", len(anchors) >= 2, str(anchors[:2]))
        lines = DOC.split("\n")
        ok = all(txt.strip()[:6] in lines[int(no) - 1] for no, txt in anchors)
        check("handoff.行号对齐原文", ok, str(anchors[:2]))
        # pipeline --handoff 同款
        ws2 = os.path.join(td, "h2.md")
        r2 = run_cli([SCRIPTS + "/pipeline.py", f, "-o", os.path.join(td, "o.txt"),
                      "--handoff", ws2])
        c2 = open(ws2, encoding="utf-8").read() if os.path.exists(ws2) else ""
        check("handoff.pipeline同款", r2.returncode == 0 and "原文 L" in c2)
        # JSON 路径（--handoff 下 handoff 键带行号锚）
        r3 = run_cli([SCRIPTS + "/plan.py", f, "--json", "--handoff"])
        j = json.loads(r3.stdout)
        check("handoff.json带锚", "原文 L" in j.get("handoff", ""))


def test_en_v2():
    r = hxt_core.scan("The remainder of this paper is organized as follows. "
                      "Section 2 reviews prior work and Section 3 presents the methods. "
                      "In the realm of medicine, this study sheds light on a plethora of "
                      "mechanisms that were previously unexplored in the literature. ")
    check("env2.roadmap", "en_roadmap" in r["categories"])
    vc = (r["categories"].get("en_vocab") or {})
    voc = " ".join(vc.get("samples", []))
    check("env2.新词命中", vc.get("count", 0) >= 4 and "plethora" in voc,
          "count=%s %s" % (vc.get("count"), voc[:80]))
    d = json.load(open(os.path.join(SCRIPTS, "patterns_en.json"), encoding="utf-8"))
    fams = set(d["families"].keys())
    no_fam = [e["w"] for e in d["vocabulary"] if e.get("fam") not in fams]
    check("env2.fam全覆盖", not no_fam, str(no_fam[:3]))


def test_doc_counts():
    r = run_cli([ROOT + "/tests/check_doc_counts.py"])
    check("counts.exit0", r.returncode == 0, (r.stdout or "")[-200:])
    check("counts.输出对账", "DOC_COUNTS_OK" in r.stdout)


def test_version_and_docs():
    check("ver.5.1.0", hxt_core.__version__ == "5.2.0", hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.feature_status_v51", fs.count("v5.1") >= 2)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH_v51", "指令单行号锚" in zh)


def main():
    for fn in (test_handoff_lineno, test_en_v2, test_doc_counts,
               test_version_and_docs):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""test_v51600 — v5.16.0 交互速览三件版。
覆盖：detect --top N 裁剪（人读裁/JSON 全量）/transform --dry-run（不落盘不输出）/pipeline --summary 一行速览/版本锚。
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
BODY = ("综上所述，本文具有重要意义。该项目赋能闭环打法，聚焦赛道。近年来，随着人工智能技术的快速发展，"
        "值得注意的是该领域日新月异。此外，不容忽视的是现实挑战依然存在。\n\n首先，方法层面有待完善。"
        "其次，数据规模有限。最后，评估标准尚未统一。\n\n值得注意的是，跨学科合作日益重要。此外，"
        "伦理规范亟待建立。总的来说，前景广阔。综上所述，未来可期。")

def test_top():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "b.txt")
        open(f, "w", encoding="utf-8").write(BODY)
        r_all = run_cli([SCRIPTS + "/detect.py", f])
        n_all = len([l for l in r_all.stdout.splitlines() if l.strip().startswith("· ") and "处" in l])
        r_top = run_cli([SCRIPTS + "/detect.py", f, "--top", "2"])
        n_top = len([l for l in r_top.stdout.splitlines() if l.strip().startswith("· ") and "处" in l])
        check("top.人读裁剪", n_top == 2 and n_all > 2, "all=%d top=%d" % (n_all, n_top))
        d = json.loads(run_cli([SCRIPTS + "/detect.py", f, "--top", "2", "-j"]).stdout)
        check("top.JSON全量", len(d["categories"]) == n_all and len(d["categories"]) > 2)
        check("top.--help", "--top" in run_cli([SCRIPTS + "/detect.py", "--help"]).stdout)

def test_dryrun():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "b.txt")
        open(f, "w", encoding="utf-8").write(BODY)
        r = run_cli([SCRIPTS + "/transform.py", f, "--dry-run"])
        check("dr.exit0", r.returncode == 0, r.stderr[-100:])
        check("dr.预览标记", "dry-run 预览" in r.stderr)
        check("dr.无输出文本", not r.stdout.strip())
        # 不落盘：同目录无新文件
        check("dr.零写盘", os.listdir(td) == ["b.txt"], str(os.listdir(td)))
        # 有替换场景：外挂词表注入
        lx = os.path.join(td, "l.json")
        json.dump({"auto_fixes": [{"pattern": "数据规模有限", "replacement": "样本量有限", "note": "外挂替换"}]},
                  open(lx, "w"), ensure_ascii=False)
        r2 = run_cli([SCRIPTS + "/transform.py", f, "--lexicon", lx, "--dry-run"])
        check("dr.替换预览", "将替换" in r2.stderr and "外挂替换" in r2.stderr,
              r2.stderr[-120:])

def test_summary():
    with tempfile.TemporaryDirectory() as td:
        a = os.path.join(td, "o.txt"); b = os.path.join(td, "n.txt")
        open(a, "w", encoding="utf-8").write("研究纳入 120 例患者。P<0.05。综上所述，本文具有重要意义。")
        open(b, "w", encoding="utf-8").write("研究纳入 120 例患者。P<0.05。直接陈述结论。")
        r = run_cli([SCRIPTS + "/pipeline.py", a, "--rewrite", b, "--summary"])
        m = re.search(r"SUMMARY \| score \d+\[\w+\]→\d+\[\w+\] \| guard \w+ \| violations \d+ \| warnings \d+ \| residue \w+", r.stdout)
        check("sum.一行格式", bool(m), r.stdout[:120])
        check("sum.无旧头", "风格特征分:" not in r.stdout)
        r2 = run_cli([SCRIPTS + "/pipeline.py", a, "--rewrite", b])
        check("sum.缺省保留旧报告", "风格特征分:" in r2.stdout)

def test_version():
    check("ver.5.16.0", hxt_core.__version__ == "5.17.0", hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs516", fs.count("v5.16") >= 2)

def main():
    for fn in (test_top, test_dryrun, test_summary, test_version):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)

main()

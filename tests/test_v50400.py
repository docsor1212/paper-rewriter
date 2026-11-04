# -*- coding: utf-8 -*-
"""test_v50400 — v5.4.0 权限自证写入清单版。

覆盖：
  1. --bundle 00_写入清单.json：12 writes（清单自身在列）、路径/类型齐全
  2. permissions.md 口径（9 编号件）与 bundle 实际一致；对账闸 ⑧ 生效
  3. 双语源披露行（feature_status）
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


def test_manifest():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "a.txt")
        open(f, "w", encoding="utf-8").write(
            "综上所述，本文具有重要意义。\n\n该项目赋能闭环。\n\n结果显著。")
        f2 = os.path.join(td, "b.txt")
        open(f2, "w", encoding="utf-8").write(
            "改后直接陈述结论，数据完整。\n\n该项目提供支持。\n\n结果显著。")
        bdir = os.path.join(td, "pkg")
        r = run_cli([SCRIPTS + "/pipeline.py", f, "--rewrite", f2, "--bundle", bdir])
        check("mf.exit0", r.returncode == 0, (r.stderr or "")[-120:])
        pkgs = glob.glob(os.path.join(bdir, "自查包_*"))
        mf = os.path.join(pkgs[0], "00_写入清单.json")
        check("mf.00存在", os.path.exists(mf))
        m = json.load(open(mf, encoding="utf-8"))
        check("mf.writes12", len(m["writes"]) == 12, str(len(m["writes"])))
        check("mf.清单自列", any("00_写入清单" in w["path"] for w in m["writes"]))
        keys_ok = all(set(w.keys()) >= {"path", "kind", "flag"} for w in m["writes"])
        check("mf.字段齐全", keys_ok)
        # README 在列
        check("mf.README在列", any("README" in w["path"] for w in m["writes"]))


def test_permissions_consistency():
    perm = open(os.path.join(ROOT, "references/permissions.md"), encoding="utf-8").read()
    src = open(os.path.join(SCRIPTS, "pipeline.py"), encoding="utf-8").read()
    check("perm.9件口径", "写 00-09 共 10 个编号件" in perm and "写入清单" in perm)
    check("perm.旧口径清除", "写 8 个文件" not in perm)
    # 实际编号件
    items = set(re.findall(r'os\.path\.join\(bdir, "(\d{2})_', src))
    check("perm.编号件10", len(items) == 10, str(sorted(items)))
    # 对账闸 ⑧ 覆盖（源码含 permissions 对账段）
    cc = open(os.path.join(ROOT, "tests/check_doc_counts.py"), encoding="utf-8").read()
    check("perm.对账闸扩容", "permissions 称写" in cc)


def test_bilingual_disclosure():
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("disclosure.双语源", "双语源文件 SKILL_ZH.md" in fs)


def test_version_and_docs():
    check("ver.5.4.0", hxt_core.__version__ == "5.5.1", hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.feature_status_v54", fs.count("v5.4") >= 2)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH_v54", "写入清单" in zh)


def main():
    for fn in (test_manifest, test_permissions_consistency,
               test_bilingual_disclosure, test_version_and_docs):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

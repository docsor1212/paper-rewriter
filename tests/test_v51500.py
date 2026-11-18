# -*- coding: utf-8 -*-
"""test_v51500 — v5.15.0 selfcheck 双形态自适应 + HXT 主文档 EN 真内容版。

覆盖：
  1. selfcheck S4 双形态分支（仓库真双语=双行验；模拟 SH cp 副本=只验 ZH）
  2. feature_status/SKILL 双语接线 + MARKERS
  3. autopub 脚本红线（HXT 无 cp/cookie 重试×3/tags.latest 判定）
  4. 版本锚
"""
import json
import os, re, sys, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import hxt_core
PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))
def run_cli(args, cwd=None):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding="utf-8", cwd=cwd or ROOT, env=env, timeout=300)


def test_s4_dualform():
    # 仓库形态（真双语）
    r = run_cli([SCRIPTS + "/selfcheck.py"])
    check("s4.仓库真双语分支", r.returncode == 0 and "S4.双语版本行[真双语]" in r.stdout)
    # SH cp 副本形态模拟
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        pkg = os.path.join(td, "pkg")
        for item in ("scripts", "references", "SKILL.md", "SKILL_ZH.md", "README.md"):
            src = os.path.join(ROOT, item)
            dst = os.path.join(pkg, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, ignore=lambda d, names: [x for x in names if x == "__pycache__"])
            else:
                shutil.copy2(src, dst)
        # SH 形态：SKILL.md = SKILL_ZH.md 中文副本 + 品牌替换
        zhc = open(os.path.join(pkg, "SKILL_ZH.md"), encoding="utf-8").read()
        zhc = zhc.replace("paper-rewriter", "humanize-ai-text")
        open(os.path.join(pkg, "SKILL.md"), "w", encoding="utf-8").write(zhc)
        open(os.path.join(pkg, "SKILL_ZH.md"), "w", encoding="utf-8").write(zhc)
        r2 = run_cli([os.path.join(pkg, "scripts", "selfcheck.py")], cwd=pkg)
        check("s4.副本形态分支", r2.returncode == 0 and "S4.双语版本行[副本形态]" in r2.stdout,
              "rc=%s tail=%s" % (r2.returncode, (r2.stdout or "")[-160:]))


def test_docs():
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs515", fs.count("v5.15") >= 2)
    check("doc.HXT EN 行", "HXT 镜像页主文档 EN 真内容" in fs)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH", "双形态自适应" in zh and "功能状态（v%s）" % hxt_core.__version__ in zh)
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("doc.EN", "dual-form adaptive" in en and "Feature status (v%s)" % hxt_core.__version__ in en)


def test_autopub_redlines():
    src = open("/home/ubsea/bin/pr_autopub.sh", encoding="utf-8").read()
    # HXT 包不再 cp 中文副本
    check("ap.HXT无cp", "cp /tmp/pkg_humanize-ai-text_sh/SKILL_ZH.md" not in src)
    # PR 包保留 cp（中文面板）
    check("ap.PR保留cp", "cp /tmp/pkg_paper-rewriter_sh/SKILL_ZH.md" in src)
    # cookie 重试 ×3
    check("ap.cookie重试", "for _try in 1 2 3" in src)
    # tags.latest 先导判定
    check("ap.tags判定", 'sk.get("tags") or {}).get("latest")' in src.replace('"', '"'))
    # 红线：禁擅改对外文案
    check("ap.红线在", "禁擅改对外文案" in src or "禁改对外" in src or "对外内容变更" in src)


def test_version():
    check("ver.5.15.0", hxt_core.__version__ == "5.15.0", hxt_core.__version__)


def main():
    for fn in (test_s4_dualform, test_docs, test_autopub_redlines, test_version):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""test_offline_v340.py — v3.4.0 新功能离线测试。

覆盖：
  1. pipeline --bundle 投稿自查包：六件+README 齐全、内容标记、--check-stats 联动
  2. SKILL_ZH frontmatter description 重写（钱词全覆盖+首行价值化+长度≤1024+合规）
  3. SKILL 双语 v3.4.0 锚 / 状态行 / 工作流行 / 话术行
运行：python3 tests/test_offline_v340.py（全断言，无第三方依赖）
"""

import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import hxt_core  # noqa: E402

PASS = []
FAIL = []


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print("PASS  %s" % name)
    else:
        FAIL.append(name)
        print("FAIL  %s  %s" % (name, detail))


def run_cli(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT, env=env,
                          timeout=90)


# ── 1. --bundle ──────────────────────────────────────────────
def test_bundle():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "d.md")
        open(f, "w", encoding="utf-8").write(
            "众所周知，本研究具有重要意义。构成比：A分别占60.2%、B占38.5%。干预组（n=45）。患者与病人混用。\n")
        out = os.path.join(td, "o.txt")
        bdir_root = os.path.join(td, "bundle")
        r = run_cli([os.path.join(SCRIPTS, "pipeline.py"), f, "-o", out,
                     "--bundle", bdir_root, "--check-stats"])
        check("bundle.exit=0", r.returncode == 0, (r.stdout + r.stderr)[-200:])
        subs = [d for d in os.listdir(bdir_root) if d.startswith("自查包_")]
        check("bundle.带时间戳子目录生成", len(subs) == 1, str(subs))
        bdir = os.path.join(bdir_root, subs[0])
        files = set(os.listdir(bdir))
        need = {"01_风格自查报告.html", "02_修订记录.md", "02_修订记录.json",
                "03_风格画像对比.md", "04_统计一致性.md", "05_术语一致性.md",
                "06_完整性判定.json", "README.txt"}
        check("bundle.八件齐全", need <= files, str(need - files))
        check("bundle.自查报告为 HTML（有 <div）",
              "<div" in open(os.path.join(bdir, "01_风格自查报告.html"),
                             encoding="utf-8").read())
        # 评审修复回归：rewrite×deep 不崩；bundle 失败降级；displayName 钉住
        f2 = os.path.join(td, "r.md")
        open(f2, "w", encoding="utf-8").write("众所周知，本研究具有重要意义。\n")
        o2 = os.path.join(td, "r_out.txt")
        r2 = run_cli([os.path.join(SCRIPTS, "pipeline.py"), f, "--rewrite", f2,
                      "-o", o2, "--deep"])
        check("fix.rewrite×deep 不崩", r2.returncode in (0, 3, 4),
              "exit=%d %s" % (r2.returncode, (r2.stdout+r2.stderr)[-120:]))
        r3 = run_cli([os.path.join(SCRIPTS, "pipeline.py"), f,
                      "-o", os.path.join(td, "o3.txt"),
                      "--bundle", "/proc/definitely_not_writable"])
        check("fix.bundle 失败降级不拖死主流程",
              r3.returncode == 0 and "自查包生成失败" in r3.stderr,
              "exit=%d" % r3.returncode)
        check("bundle.统计一致性含 percent_sum",
              "percent_sum" in open(os.path.join(bdir, "04_统计一致性.md"),
                                    encoding="utf-8").read())
        check("bundle.术语一致性含混用命中",
              "患者" in open(os.path.join(bdir, "05_术语一致性.md"),
                             encoding="utf-8").read())
        vr = json.load(open(os.path.join(bdir, "06_完整性判定.json"),
                            encoding="utf-8"))
        check("bundle.完整性判定含 ok 字段", "ok" in vr, str(vr)[:80])
        check("bundle.README 带口径",
              "非任何官方检测" in open(os.path.join(bdir, "README.txt"),
                                        encoding="utf-8").read())
        check("bundle.stderr 提示路径", "投稿自查包" in r.stderr, r.stderr[-120:])


# ── 2. description 重写 ──────────────────────────────────────
def test_description():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    m = re.search(r"description: >\n((?:  .*\n)+?)(?=allowed-tools:)", zh)
    if not m:
        check("desc.frontmatter 块可解析", False, "正则未命中")
        return
    desc = " ".join(l.strip() for l in m.group(1).splitlines())
    check("desc.长度≤1024", len(desc) <= 1024, str(len(desc)))
    for w in ("论文改写", "去AI味", "降AI率", "学术改写", "段落改写", "风格自然化"):
        check("desc.钱词「%s」✓" % w, w in desc)
    check("desc.首行价值化（工具定位开头而非品牌开头）",
          desc.startswith("论文改写与降AI率工具"))
    check("desc.诚信边界保留", "不用于误代署名" in desc)
    check("desc.零上传声明保留", "零上传" in desc)
    check("desc.相关工具导流保留", "paper-polisher-pro" in desc)
    for w in ("humaniz", "过ai检测", "降检测率", "undetectable"):
        check("desc.禁词「%s」零命中" % w, w not in desc.lower())
    for w in ("朱雀", "gptzero", "turnitin", "zerogpt", "copyleaks", "pangram",
              "evade", "bypass", "直击官方评测", "对齐官方评测", "扣分项",
              "official-eval"):
        check("desc.禁词「%s」零命中" % w, w not in desc.lower())
    check("desc.displayName 钉住铁律⑤值",
          "displayName: 论文降AI率·去AI味改写｜论文改写·学术表达优化" in zh)
    check("version.>=3.4.0",
          tuple(int(x) for x in hxt_core.__version__.split(".")) >= (3, 4, 0),
          hxt_core.__version__)


# ── 3. 文档锚 ────────────────────────────────────────────────
def test_docs():
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    import re as _re
    check("docs.EN 锚 v3.x 在位",
          bool(_re.search(r"## Feature status \(v\d+\.\d+\.\d+\)", en)))
    check("docs.ZH 锚 v3.x 在位",
          bool(_re.search(r"功能状态（v\d+\.\d+\.\d+）", zh)))
    check("docs.ZH 状态行/工作流行/话术行",
          "投稿自查包" in zh and "--bundle 目录" in zh
          and "发给导师/编辑" in zh)
    check("docs.EN 状态行", "Submission self-check bundle" in en)
    check("docs.api 行", "--bundle 目录" in
          open(os.path.join(ROOT, "references/api.md"), encoding="utf-8").read())


def main():
    test_bundle()
    test_description()
    test_docs()
    print("\n%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()

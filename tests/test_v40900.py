# -*- coding: utf-8 -*-
"""test_v40900 — v4.9.0 命中行号定位版。

覆盖：
  1. 单稿行号：词表/正则/密度三类样本 L{行号} 与原文行对齐
  2. 分块换算：>800K 多块样本行号仍对齐原文（base_line 换算）
  3. 工作单/JSON 继承；base_line 直调
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


ZH_DOC = ("第一行是干净的引入句子。\n"
          "综上所述，本文具有重要意义，方法值得信赖。\n"
          "第三行该项目为产业赋能，形成闭环打法。\n"
          "第四行回到干净的叙述，数据完整可核。")


def test_single_lineno():
    r = hxt_core.scan(ZH_DOC)
    voc = (r["categories"].get("zh_jargon") or {}).get("samples", [])
    eight = (r["categories"].get("zh_eightleg") or {}).get("samples", [])
    check("single.词表L3", any(s.startswith("L3:") for s in voc), str(voc[:2]))
    check("single.八股L2", any(s.startswith("L2:") for s in eight), str(eight[:2]))
    # 行号对齐原文：抽样本行号回读原文行包含命中文本
    ok = True
    for s in (voc + eight)[:4]:
        m = re.match(r"L(\d+): (.+)", s)
        if not m:
            ok = False
            break
        hit = m.group(2).split("→")[0].strip()[:4]
        line_text = ZH_DOC.split("\n")[int(m.group(1)) - 1]
        if hit not in line_text:
            ok = False
    check("single.行号回读对齐", ok)


def test_chunked_lineno():
    fill = "\n".join(["这是用于撑起体量的正文内容，包含足够的汉字与句子结构。"] * 30000) + "\n"
    big = fill + "综上所述，值得注意的是，本文具有重要意义。\n" + fill + "该项目为产业赋能，形成闭环。\n" + fill
    assert len(big) > 800_000
    rc = hxt_core.scan_chunked(big, degrade=True)
    lines = big.split("\n")
    ok_all = True
    for cat in ("zh_eightleg", "zh_jargon"):
        ss = (rc["categories"].get(cat) or {}).get("samples", [])[:2]
        if not ss:
            ok_all = False
            continue
        for s in ss:
            m = re.match(r"L(\d+): (.+)", s)
            if not m:
                ok_all = False
                continue
            hit = m.group(2).split("→")[0].strip()[:4]
            if hit not in lines[int(m.group(1)) - 1]:
                ok_all = False
    check("chunked.多块行号对齐", ok_all)


def test_base_line_and_ws():
    # base_line 直调（分块换算入口）
    r = hxt_core.scan("综上所述，具有重要意义。\n赋能与闭环。", base_line=100)
    voc = (r["categories"].get("zh_jargon") or {}).get("samples", [])
    check("baseline.直调换算", any(s.startswith("L101:") for s in voc), str(voc[:1]))
    # 工作单继承
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "in.txt")
        open(f, "w", encoding="utf-8").write(ZH_DOC)
        ws = os.path.join(td, "ws.md")
        run_cli([SCRIPTS + "/detect.py", f, "--suggestions", ws])
        content = open(ws, encoding="utf-8").read()
        check("ws.行号继承", "L3:" in content or "L2:" in content, content[:100])
        # JSON 序列化
        r = run_cli([SCRIPTS + "/detect.py", f, "--json"])
        j = json.loads(r.stdout)
        check("json.样本行号", any("L2:" in s for s in
              (j["categories"].get("zh_eightleg") or {}).get("samples", [])))


def test_md_and_section_lineno():
    # 审计 P1-2：.md 输入（strip 行数保持）行号对齐原文
    md = ("# 标题\n\n正文一段干净。\n```\ncode line\n```\n"
          "综上所述，本文具有重要意义。\n该项目赋能闭环。\n")
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "p.md")
        open(f, "w", encoding="utf-8").write(md)
        r = run_cli([SCRIPTS + "/detect.py", f])
        hits = re.findall(r"L(\d+): (综上所述|赋能)", r.stdout)
        lines = md.split("\n")
        ok = bool(hits) and all(
            txt in lines[int(no) - 1] for no, txt in hits)
        check("md.行号对齐", ok, str(hits))
    # 审计 P1-1：--section 行号对齐原文（非节内）
    sec = ("摘要\n综上所述，本文具有重要意义。\n该项目赋能闭环。\n\n"
           "方法\n正文方法段。\n")
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "s.txt")
        open(f, "w", encoding="utf-8").write(sec)
        r = run_cli([SCRIPTS + "/detect.py", f, "--section", "abstract"])
        hits = re.findall(r"L(\d+): (综上所述|赋能)", r.stdout)
        lines = sec.split("\n")
        ok = bool(hits) and all(
            txt in lines[int(no) - 1] for no, txt in hits)
        check("section.行号对齐原文", ok, str(hits))


def test_version_and_docs():
    check("ver.__version__", hxt_core.__version__ == "5.0.0",
          hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.feature_status_v49", fs.count("v4.9") >= 2)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH_v49功能行", "命中行号定位" in zh)


def main():
    for fn in (test_single_lineno, test_chunked_lineno, test_base_line_and_ws,
               test_md_and_section_lineno, test_version_and_docs):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

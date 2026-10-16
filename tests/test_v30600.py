# -*- coding: utf-8 -*-
"""test_v30600 — v3.6.0 医学知识库 md 感知版（固定位命名）。

覆盖：
  1. detect .md 自动剥离（专题19 实文件 0 分+md_struct）+ --raw-markdown 旧行为
  2. stylecheck .md 剥离（假阳性修复）+ --raw-markdown
  3. strip_markdown 单元（结构统计/正文剥离/非 md 不动）
  4. medscan 发现汇总在档（dev_notes 不入包）
"""
import json
import os, sys, tempfile, subprocess
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
                          text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=180)

MD19 = "/home/ubsea/Down-PDF/风湿免疫知识专题终版/专题19-生物制剂与免疫抑制剂临床应用.md"
MD_OK = os.path.exists(MD19)  # 真实语料可选（个人路径可能不存在）；合成 fixture 恒可用


def make_md(path):
    """合成知识库风格 md：重结构+干净正文+一处真实八股。"""
    body = ("# 研究方法\n\n"
            "| 组别 | 例数 | 缓解率 |\n|---|---|---|\n"
            "| A 组 | 30 | 60.0% |\n| B 组 | 30 | 40.0% |\n\n"
            "众所周知，该病的治疗需要长期管理。患者应定期随访，注意休息与营养。\n\n"
            "## 随访\n\n随访期间应监测疾病活动度指标。\n")
    open(path, "w", encoding="utf-8").write(body)

def test_strip_unit():
    body, st = hxt_core.strip_markdown("# 标题\n\n| a | b |\n\n**加粗**正文\n\n```code```\n")
    check("strip.结构统计", st["code_blocks"] == 1 and st["table_rows"] == 1
          and st["headings"] == 1, str(st))
    check("strip.正文剥离", "|" not in body and "**" not in body and "```" not in body
          and "标题" in body and "加粗正文" in body)
    plain = "纯文本段落，没有任何标记。"
    b2, s2 = hxt_core.strip_markdown(plain)
    check("strip.纯文本不动", b2 == plain and s2["code_blocks"] == 0)

def test_detect_md():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "kb.md")
        make_md(f)
        r = run_cli([os.path.join(SCRIPTS, "detect.py"), f, "--json"])
        d = json.loads(r.stdout)
        check("detect.md_struct 透出（合成 fixture）",
              isinstance(d.get("md_struct"), dict)
              and d["md_struct"]["table_rows"] >= 2, str(d.get("md_struct"))[:80])
        # 八股在剥离后正文里仍应被抓（剥离≠放水）
        check("detect.md 正文八股仍检出", d.get("score", 0) >= 1, str(d.get("score")))
        r2 = run_cli([os.path.join(SCRIPTS, "detect.py"), f, "--raw-markdown", "--json"])
        d2 = json.loads(r2.stdout)
        check("detect.raw-markdown 无 struct（旧行为）", d2.get("md_struct") is None)
        # 剥离口径不高于原文口径（.md 的 markdown 类信号本就被 source_ext 豁免，
        # 剥离移除的是表格行/标题残留在其他类别的噪声——只许降不许升）
        check("detect.剥离分 ≤ 原始分",
              d.get("score", 999) <= d2.get("score", -1),
              "stripped=%s raw=%s" % (d.get("score"), d2.get("score")))
    # structure × md 回归（评审 #5：守卫链再断防守）
    if MD_OK:
        r3 = run_cli([os.path.join(SCRIPTS, "detect.py"), MD19, "--structure", "--json"])
        check("detect.structure×md 冒烟", r3.returncode in (0, 3, 4),
              "exit=%d" % r3.returncode)
    else:
        check("detect.structure×md 冒烟（真实语料缺席跳过）", True)

def test_stylecheck_md():
    r = run_cli([os.path.join(SCRIPTS, "stylecheck.py"), MD19, "--json"])
    d = json.loads(r.stdout)
    check("sc.md 剥离后画像", d.get("md_struct") is not None
          and (d.get("global") or {}).get("jargon_1k", {}).get("value", 99) < 1,
          json.dumps(d.get("md_struct"), ensure_ascii=False)[:80])
    with tempfile.TemporaryDirectory() as td:
        pure = os.path.join(td, "pure.md")
        open(pure, "w", encoding="utf-8").write("| 表格 |\n|---|\n")
        r2 = run_cli([os.path.join(SCRIPTS, "stylecheck.py"), pure])
        check("sc.纯结构文档给可执行提示", r2.returncode == 2
              and "纯结构" in (r2.stdout + r2.stderr), (r2.stdout + r2.stderr)[:100])

def test_notes():
    p = os.path.join(ROOT, "tests", "dev_notes", "medscan_20261014.md")
    txt = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    check("notes.发现汇总 v2 在档（勘误+真问题）",
          "勘误" in txt and "SLE" in txt and "负结果" in txt)

def main():
    test_strip_unit()
    test_detect_md()
    test_stylecheck_md()
    test_notes()
    print("\n%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        sys.exit(1)
    print("OK")

if __name__ == "__main__":
    main()

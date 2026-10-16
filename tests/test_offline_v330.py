# -*- coding: utf-8 -*-
"""test_offline_v330.py — v3.3.0 新功能离线测试。

覆盖：
  1. check_stats --batch 跨文件分组 n 聚合（加宽前缀+显式免责；单文件保守不剥时点不回归）
  2. pipeline --check-stats 阶段（JSON stats_consistency；缺省不跑；退出码不受影响）
  3. detect/pipeline --pdf-min-confidence 门闸（低于阈值拒收；v3.8.0 起缺省=中（原为只标注））
  4. SKILL 双语 v3.3.0 锚 / 状态表压缩 / 工作流行 / api·errors 行 / 合规零命中
运行：python3 tests/test_offline_v330.py（全断言，无第三方依赖）
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import hxt_core  # noqa: E402
import check_stats as cs  # noqa: E402

PASS = []
FAIL = []


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print("PASS  %s" % name)
    else:
        FAIL.append(name)
        print("FAIL  %s  %s" % (name, detail))


def run_cli(args, stdin_text=None):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT, env=env,
                          input=stdin_text, timeout=90)


# ── 1. batch 跨文件 ──────────────────────────────────────────
def test_batch():
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "01_摘要.md"), "w", encoding="utf-8").write(
            "干预组（n=45）与对照组（n=48）。")
        open(os.path.join(td, "02_方法.md"), "w", encoding="utf-8").write(
            "干预组 n=43。\n构成比：A分别占60.2%、B占38.5%。")
        open(os.path.join(td, "03_结果.md"), "w", encoding="utf-8").write(
            "全部队列 91 例完成研究。")
        r = run_cli([os.path.join(SCRIPTS, "check_stats.py"), "--batch", td])
        check("batch.问题目录 exit=1", r.returncode == 1, str(r.returncode))
        check("batch.跨文件冲突抓到（干预组 43 vs 45，硬冲突）",
              "跨文件样本量不一致" in r.stdout and "01_摘要.md" in r.stdout,
              r.stdout[:200])
        check("batch.口径尾行在位", "先核对原始数据" in r.stdout)
        check("batch.逐文件计数", "02_方法.md：1 项" in r.stdout, r.stdout[:200])
        r = run_cli([os.path.join(SCRIPTS, "check_stats.py"), "--batch", td,
                     "--json"])
        d = json.loads(r.stdout)
        hard = [x for x in d["cross_file"] if not x.get("timepoint_merged")]
        check("batch.JSON files+cross_file+total（硬冲突计入 total）",
              set(d) >= {"files", "cross_file", "total"} and d["total"] >= 2
              and len(hard) == 1,
              json.dumps(d, ensure_ascii=False)[:200])
        clean = os.path.join(td, "..", "clean_" + os.path.basename(td))
        os.mkdir(clean)
        open(os.path.join(clean, "a.md"), "w", encoding="utf-8").write(
            "干预组（n=45）。构成比：A占60.0%，B占40.0%。")
        r2 = run_cli([os.path.join(SCRIPTS, "check_stats.py"), "--batch", clean])
        check("batch.干净目录 exit=0", r2.returncode == 0, r2.stdout[:120])
        # 时点前缀（入组/最终）并组=候选级，不计退出码（v3.3.0 评审语义）
        os.mkdir(os.path.join(td, "tp"))
        open(os.path.join(td, "tp", "01.md"), "w", encoding="utf-8").write("干预组（n=45）随机化。")
        open(os.path.join(td, "tp", "02.md"), "w", encoding="utf-8").write("最终干预组（n=42）完成随访。")
        r4 = run_cli([os.path.join(SCRIPTS, "check_stats.py"), "--batch",
                      os.path.join(td, "tp")])
        check("batch.时点并组=候选不计退出码",
              r4.returncode == 0 and "时点候选" in r4.stdout, r4.stdout[-200:])


# ── 2. 单文件保守性不回归（时点前缀仍不并组） ────────────────
def test_single_conservative():
    hits = cs.check_group_ns("干预组（n=45）随机化。最终干预组（n=42）完成试验。")
    check("single.时点前缀仍不并组（防失访误报不回归）", hits == [],
          json.dumps(hits, ensure_ascii=False)[:120])


# ── 3. pipeline --check-stats ────────────────────────────────
def test_pipeline_stats():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "d.md")
        open(f, "w", encoding="utf-8").write(
            "众所周知，本研究具有重要意义。构成比：A分别占60.2%、B占38.5%。干预组（n=45）。\n")
        r = run_cli([os.path.join(SCRIPTS, "pipeline.py"), f,
                     "-o", os.path.join(td, "o.txt"), "--check-stats", "--json"])
        d = json.loads(r.stdout)
        sc = d.get("stats_consistency") or {}
        check("pipe.JSON stats_consistency 含 percent_sum",
              sc.get("total") == 1 and sc["issues"][0]["kind"] == "percent_sum",
              json.dumps(sc, ensure_ascii=False)[:160])
        check("pipe.免责 note 在位", "以原始数据为准" in (sc.get("note") or ""))
        ev = d.get("exit_verdict")
        check("pipe.一致性发现不改退出码（仍按风格判）",
              ev in (0, 3, 4), str(ev))
        r2 = run_cli([os.path.join(SCRIPTS, "pipeline.py"), f,
                      "-o", os.path.join(td, "o2.txt"), "--json"])
        d2 = json.loads(r2.stdout)
        check("pipe.缺省旗标不跑（字段 None）",
              d2.get("stats_consistency") is None)


# ── 4. --pdf-min-confidence 门闸 ─────────────────────────────
def make_pdf(path, text):
    content = ("BT /F1 12 Tf (" + text + ") Tj ET").encode("ascii")
    stream = b"stream\r\n" + content + b"\nendstream"
    head = (b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n"
            b"4 0 obj<</Length " + str(len(stream)).encode() + b">>\n"
            + stream + b"\nendobj\n")
    open(path, "wb").write(head + b"trailer<</Root 1 0 R>>")


def test_pdf_gate():
    check("gate.pdf_confidence_ok 秩序",
          hxt_core.pdf_confidence_ok("低", "高") is False
          and hxt_core.pdf_confidence_ok("高", "中") is True
          and hxt_core.pdf_confidence_ok("中", "中") is True
          and hxt_core.pdf_confidence_ok(None, "高") is True)
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "low.pdf")
        make_pdf(p, "Short abstract only. ")
        r = run_cli([os.path.join(SCRIPTS, "detect.py"), p,
                     "--pdf-min-confidence", "高"])
        check("gate.detect 低于阈值拒收", r.returncode == 2
              and "低于门闸" in (r.stdout + r.stderr),
              (r.stdout + r.stderr)[:120])
        r2 = run_cli([os.path.join(SCRIPTS, "pipeline.py"), p,
                      "-o", os.path.join(td, "o.txt"), "--pdf-min-confidence", "中"])
        check("gate.pipeline 低于阈值拒收", r2.returncode == 2
              and "低于门闸" in (r2.stdout + r2.stderr),
              (r2.stdout + r2.stderr)[:120])
        r3 = run_cli([os.path.join(SCRIPTS, "detect.py"), p])
        # v3.8.0 行为规格变更：缺省门=中（乱码形态默认拦截，stability 处方——
        # 评测点名「PDF 抽取失败仍可能输出低置信度乱码」）
        check("gate.缺省=中门拦截",
              r3.returncode == 2 and "低于门闸" in (r3.stdout + r3.stderr),
              (r3.stdout + r3.stderr)[:120])
        r4 = run_cli([os.path.join(SCRIPTS, "detect.py"), p,
                      "--pdf-min-confidence", "低"])
        check("gate.低门恢复只标注旧行为",
              r4.returncode == 0 and "置信度" in r4.stdout, r4.stdout[:100])


# ── 5. 文档与合规 ────────────────────────────────────────────
def test_docs():
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    import re as _re
    check("docs.EN 锚 v3.x 在位",
          bool(_re.search(r"## Feature status \(v3\.\d+\.\d+\)", en)))
    m_anchor = _re.search(r"功能状态（v3\.\d+\.\d+）", zh)
    check("docs.ZH 锚 v3.x 在位", bool(m_anchor))
    if m_anchor:
        gap = abs(zh.find("规模上限") - m_anchor.start())
        check("docs.ZH 状态表已压缩（≤2200 字符）", gap < 2200, "间距=%d" % gap)
    check("docs.ZH 工作流 batch 行", "--batch 目录" in zh and "跨文件分组 n 聚合" in zh)
    check("docs.ZH pipeline --check-stats 行", "pipeline.py 原稿 --check-stats" in zh)
    check("docs.EN batch 行", "--batch" in en and "abstract-vs-methods" in en)
    check("docs.api 行齐", "--pdf-min-confidence" in
          open(os.path.join(ROOT, "references/api.md"), encoding="utf-8").read())
    check("docs.errors 行齐", "PDF 置信度低于门闸" in
          open(os.path.join(ROOT, "references/errors.md"), encoding="utf-8").read())
    refs = ""
    import glob as _g
    for fp in sorted(_g.glob(os.path.join(ROOT, "references", "*.md"))):
        refs += open(fp, encoding="utf-8").read().lower()
    blob = (en + zh + refs).lower()
    for w in ("朱雀", "gptzero", "turnitin", "zerogpt", "copyleaks", "pangram",
              "过ai检测", "降检测率", "去ai痕迹", "帮过检测", "undetectable",
              "evade", "bypass", "直击官方评测", "对齐官方评测", "主靶", "扣分项",
              "official-eval"):
        check("合规.禁词「%s」零命中" % w, w not in blob)
    check("version.>=3.3.0",
          tuple(int(x) for x in hxt_core.__version__.split(".")) >= (3, 3, 0),
          hxt_core.__version__)


def test_review_fixes():
    # 评审修复回归：pipeline 文本报告打印一致性段；门闸报错带出路；batch 时点候选
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "d.md")
        open(f, "w", encoding="utf-8").write(
            "众所周知，本研究具有重要意义。构成比：A分别占60.2%、B占38.5%。\n")
        r = run_cli([os.path.join(SCRIPTS, "pipeline.py"), f,
                     "-o", os.path.join(td, "o.txt"), "--check-stats"])
        check("fix.文本报告打印统计一致性段", "统计一致性" in r.stdout
              and "以原始数据为准" in r.stdout, r.stdout[-200:])
        p = os.path.join(td, "low.pdf")
        make_pdf(p, "Short abstract only. ")
        r2 = run_cli([os.path.join(SCRIPTS, "detect.py"), p,
                      "--pdf-min-confidence", "高"])
        blob = r2.stdout + r2.stderr
        check("fix.门闸报错带出路与注记",
              "导出 UTF-8" in blob and "注记" in blob, blob[:160])
        bd = os.path.join(td, "b")
        os.mkdir(bd)
        open(os.path.join(bd, "01.md"), "w", encoding="utf-8").write("干预组（n=45）随机化。")
        open(os.path.join(bd, "02.md"), "w", encoding="utf-8").write("最终干预组（n=42）完成随访。")
        r3 = run_cli([os.path.join(SCRIPTS, "check_stats.py"), "--batch", bd])
        check("fix.时点并组=候选不计退出码",
              r3.returncode == 0 and "时点候选" in r3.stdout, r3.stdout[-200:])
        check("docs.ZH frontmatter displayName 与现役 dn 一致",
              "displayName: 降AI率·去AI味改写｜论文改写·学术表达优化" in zh)


def main():
    test_batch()
    test_single_conservative()
    test_pipeline_stats()
    test_pdf_gate()
    test_review_fixes()
    test_docs()
    print("\n%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()

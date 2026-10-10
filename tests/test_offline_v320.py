# -*- coding: utf-8 -*-
"""test_offline_v320.py — v3.2.0 新功能离线测试。

覆盖：
  1. check_stats.py 统计一致性守卫：
     - percent_sum：划分用语句合计偏离 → 报；合并症类非穷举清单 → 不报（防误报铁律）
     - group_n_conflict：前缀修饰（最终干预组）归一化后仍能撞上；尾部修饰（完成试验者）不并组
     - p_style_mix：p=/P=、p</P< 混用报；单风格不报
     - 退出码契约 0/1/2 与 check_terms 同表；--json schema；--report 落盘
  2. SKILL 双语 v3.2.0 锚 / 状态行 / 能力行 / 话术行 / 协议 bullet / EN 新触发词
  3. FAQ 深化（Q2/Q5/Q9/Q10）与 api/errors 行
  4. 合规禁词零命中（SKILL 双语+faq 三份主文档；发布面全量扫描由 test_offline 兜底）
运行：python3 tests/test_offline_v320.py（全断言，无第三方依赖）
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


def run_cli(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT, env=env,
                          timeout=60)


# ── 1a. percent_sum ──────────────────────────────────────────
def test_percent_sum():
    # 划分用语句 + 偏离 → 报
    hits = cs.check_percent_sums("病因构成：A型分别占40.2%、B型占35.6%、C型占23.7%。")
    check("pct.划分句 99.5 报", len(hits) == 1 and abs(sum(hits[0]["parts"]) - 99.5) < 1e-9,
          json.dumps(hits, ensure_ascii=False)[:140])
    # 合并症（非穷举、无线索词）→ 不报（10-10 评审式误报案例）
    hits = cs.check_percent_sums("亚组分析中糖尿病患者占58.2%，高血压患者占40.5%。")
    check("pct.合并症清单不报", hits == [])
    # 合计恰 100 + 划分词 → 不报
    hits = cs.check_percent_sums("构成比：A占60.0%，B占40.0%。")
    check("pct.恰好百不报", hits == [])
    # 划分词 + 大偏离（85-115 之外语义上已不是划分）→ 仍报（线索词优先）
    hits = cs.check_percent_sums("感染途径分别为血液占40.1%、性接触占30.2%、其他占10.3%。")
    check("pct.划分句 80.6 报（线索词通道无窗口下限）", len(hits) == 1)
    hits = cs.check_percent_sums("构成比：A分别占60.2%、B占39.5%。", tolerance=2.0)
    check("pct.tolerance=2.0 时 99.7 不报", hits == [],
          json.dumps(hits, ensure_ascii=False)[:120])
    hits = cs.check_percent_sums("构成比：A分别占60,2%、B占38,5%。")
    check("pct.欧式小数 98.7 识别", len(hits) == 1 and abs(sum(hits[0]["parts"]) - 98.7) < 1e-6,
          json.dumps(hits, ensure_ascii=False)[:140])
    hits = cs.check_percent_sums("占全球比重：the rest of the world made up 12.3%，亚洲占60.4%。")
    check("pct.the rest of the world 不作线索", hits == [],
          json.dumps(hits, ensure_ascii=False)[:120])


# ── 1b. group_n_conflict ─────────────────────────────────────
def test_group_n():
    hits = cs.check_group_ns("干预组（n=45）与对照组（n=48）基线均衡。干预组（n=48）完成随访。")
    check("grp.同名前后冲突 45 vs 48",
          len(hits) == 1 and hits[0]["label"] == "干预组"
          and sorted(hits[0]["values"]) == [45, 48],
          json.dumps(hits, ensure_ascii=False)[:140])
    # 失访语义（v3.2.0 评审 P1 翻转）：「最终干预组」是不同时点，不与随机化 n 并组
    hits = cs.check_group_ns("干预组（n=45）随机化。最终干预组（n=42）完成试验。")
    check("grp.失访时点不并组（评审 P1）", hits == [],
          json.dumps(hits, ensure_ascii=False)[:120])
    # 裸式量词头停用词
    hits = cs.check_group_ns("样本数 n=350。样本数 n=340。")
    check("grp.量词头不并组", hits == [], json.dumps(hits, ensure_ascii=False)[:120])
    hits = cs.check_group_ns("干预组（n=45）。干预组完成试验者 n=42。")
    check("grp.尾部修饰不并组（完成试验者≠干预组）", hits == [],
          json.dumps(hits, ensure_ascii=False)[:120])
    hits = cs.check_group_ns("A组（n=30）与B组（n=30）均衡。")
    check("grp.一致不报", hits == [])


# ── 1c. p_style_mix ──────────────────────────────────────────
def test_p_style():
    r = cs.check_p_style("主要终点 p=0.03，次要终点 P=0.04。")
    check("pstyle.p= 与 P= 混用报", r is not None and r["counts"]["p_eq"] == 1
          and r["counts"]["P_eq"] == 1)
    r = cs.check_p_style("组间 p<0.05，亚组内 P<0.01。")
    check("pstyle.p< 与 P< 混用报", r is not None and r["counts"]["p_lt"] == 1
          and r["counts"]["P_lt"] == 1)
    r = cs.check_p_style("组间 P＜0.05（全角），对照组 p<0.05。")
    check("pstyle.全角＜识别", r is not None and r["counts"]["P_lt"] == 1
          and r["counts"]["p_lt"] == 1, json.dumps(r, ensure_ascii=False)[:120] if r else "None")
    r = cs.check_p_style("pH=7.2，缓冲液 Ap=1。")
    check("pstyle.pH/粘连不误报", r is None)
    r = cs.check_p_style("全篇统一 p<0.05 与 p=0.03。")
    check("pstyle.单风格不报", r is None)


# ── 1d. CLI 契约 ─────────────────────────────────────────────
def test_cli():
    with tempfile.TemporaryDirectory() as td:
        bad = os.path.join(td, "bad.md")
        open(bad, "w", encoding="utf-8").write(
            "构成比：A分别占60.2%、B占38.5%。干预组（n=45）。干预组（n=48）完成随访。")
        r = run_cli([os.path.join(SCRIPTS, "check_stats.py"), bad])
        check("cli.问题文本 exit=1", r.returncode == 1, str(r.returncode))
        check("cli.输出含类别标签", "percent_sum" in r.stdout
              and "group_n_conflict" in r.stdout, r.stdout[:120])
        r = run_cli([os.path.join(SCRIPTS, "check_stats.py"), bad, "--json"])
        d = json.loads(r.stdout)
        check("cli.JSON total>=2 且带免责", d["total"] >= 2
              and "非统计审查" in d["disclaimer"], json.dumps(d, ensure_ascii=False)[:120])
        rp = os.path.join(td, "r.md")
        r = run_cli([os.path.join(SCRIPTS, "check_stats.py"), bad, "--report", rp])
        check("cli.--report 落盘", os.path.exists(rp)
              and "统计一致性检查" in open(rp, encoding="utf-8").read())
        good = os.path.join(td, "good.md")
        open(good, "w", encoding="utf-8").write("A组（n=30）与B组（n=30）均衡，构成比 A 占 60.0%、B 占 40.0%。")
        r = run_cli([os.path.join(SCRIPTS, "check_stats.py"), good])
        check("cli.干净文本 exit=0", r.returncode == 0, r.stdout[:80])
        r = run_cli([os.path.join(SCRIPTS, "check_stats.py")])
        check("cli.缺参 exit=2", r.returncode == 2, str(r.returncode))
        big = os.path.join(td, "big.md")
        open(big, "w", encoding="utf-8").write("构成比：A分别占60.2%、B占38.5%。")
        r_strict = run_cli([os.path.join(SCRIPTS, "check_stats.py"), big])
        r_loose = run_cli([os.path.join(SCRIPTS, "check_stats.py"), big,
                           "--tolerance", "2.0"])
        check("cli.--tolerance 生效（严格 1/宽松 0）",
              r_strict.returncode == 1 and r_loose.returncode == 0,
              "%d/%d" % (r_strict.returncode, r_loose.returncode))
        check("cli.--version=全局版本", "3.2.0" in run_cli(
            [os.path.join(SCRIPTS, "check_stats.py"), "--version"]).stdout)


# ── 2/3/4. 文档与合规 ─────────────────────────────────────────
def test_docs():
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("docs.EN 锚 v3.2.0", "## Feature status (v3.2.0)" in en)
    check("docs.ZH 锚 v3.2.0", "功能状态（v3.2.0）" in zh)
    check("docs.ZH 状态行 check_stats", "统计一致性守卫" in zh and "宁可少报不误报" in zh)
    check("docs.ZH 能力行+话术行",
          "数字自洽" in zh and "查查数字有没有前后打架" in zh)
    check("docs.ZH 协议 bullet", "数字前后打架" in zh)
    check("docs.EN 状态行/能力行/协议",
          "Statistical consistency guard" in en
          and "Numeric self-consistency" in en
          and "check_stats.py file" in en)
    check("docs.EN 触发词扩容（新增自然口语短语）",
          "less machine-written" in en and "survived editing" in en)
    faq = open(os.path.join(ROOT, "references/faq.md"), encoding="utf-8").read()
    check("faq.Q10 统计一致性", "check_stats.py" in faq and "合并症" in faq)
    check("faq.Q2/Q5/Q9 深化", "改稿进度条" in faq and "分步入口" in faq
          and "分项差值" in faq)
    api = open(os.path.join(ROOT, "references/api.md"), encoding="utf-8").read()
    check("api.md check_stats 行", "check_stats.py" in api)
    errs = open(os.path.join(ROOT, "references/errors.md"), encoding="utf-8").read()
    check("errors.md check_stats 行", "check_stats.py" in errs)
    blob = (en + zh + faq).lower()
    for w in ("朱雀", "gptzero", "turnitin", "zerogpt", "copyleaks", "pangram",
              "过ai检测", "降检测率", "去ai痕迹", "帮过检测", "undetectable",
              "直击官方评测", "对齐官方评测", "主靶", "扣分项", "official-eval"):
        check("合规.禁词「%s」零命中" % w, w not in blob)
    check("version.3.2.0", hxt_core.__version__ == "3.2.0")


def main():
    test_percent_sum()
    test_group_n()
    test_p_style()
    test_cli()
    test_docs()
    print("\n%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()

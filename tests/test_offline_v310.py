# -*- coding: utf-8 -*-
"""test_offline_v310.py — v3.1.0 新功能离线测试。

覆盖：
  1. 术语变体组：HF 组三变体一行报告 / --list-packs 组·变体口径 / 用户对去重与
     自定义域标签 / validate_packs 嵌套安全 / v3.0.x 二元对兼容接口
  2. stylecheck 统计面板：stats 块（TTR/虚词比例/句长分位）+ note 在位 + --json 透出
  3. --ci 门禁短别名：detect/compare/pipeline 三件与 --exit-verdict 同义
  4. SKILL 双语 v3.1.0 锚 / 一句话路由 / 用户话术表 / 能力承诺表 / 合规零命中
运行：python3 tests/test_offline_v310.py（全断言，无第三方依赖）
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
import check_terms as ct  # noqa: E402

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
    r = subprocess.run([sys.executable] + args, capture_output=True,
                       text=True, encoding="utf-8", cwd=ROOT, env=env,
                       input=stdin_text, timeout=60)
    return r


# ── 1. 变体组 ────────────────────────────────────────────────
def test_groups():
    check("groups.嵌套安全零违规", ct.validate_packs() == [],
          str(ct.validate_packs()))
    check("groups.27 组 55 变体",
          len(ct._TERM_GROUPS) == 27
          and sum(len(g["variants"]) for g in ct._TERM_GROUPS) == 55,
          "%d 组 / %d 变体" % (len(ct._TERM_GROUPS),
                               sum(len(g["variants"]) for g in ct._TERM_GROUPS)))
    hf = [g for g in ct._TERM_GROUPS if g["variants"][0] == "HF"][0]
    check("groups.HF 组带心衰（3 变体）", hf["variants"] == ["HF", "心力衰竭", "心衰"])

    text = "患者术后心衰发作，既往心衰病史，确诊HF。病人并无心力衰竭史。"
    rows = ct.find_group_inconsistencies(
        text, [dict(g) for g in ct._TERM_GROUPS])
    hf_rows = [r for r in rows if r["canonical"] == "HF"]
    check("groups.HF 三变体一行报告",
          len(hf_rows) == 1 and set(hf_rows[0]["variants"]) ==
          {"HF", "心力衰竭", "心衰"},
          json.dumps(hf_rows, ensure_ascii=False)[:160])
    if not hf_rows:
        check("groups.HF 三变体一行报告", False, "hf_rows 空——后续断言跳过")
        return
    r0 = hf_rows[0]
    check("groups.行结构兼容 a/b 字段",
          all(k in r0 for k in ("a", "b", "a_count", "b_count", "pack",
                                "canonical", "variants", "suggestion")))
    check("groups.建议=最高频变体", r0["suggestion"] == "心衰",
          r0["suggestion"])  # 心衰2(心衰发作+心衰? 实测定) —— 断言=动态最高频
    # 兼容接口：二元对
    rows2 = ct.find_inconsistencies("该 identifier 与 ID 不一致。",
                                    [("identifier", "ID")])
    check("groups.二元对兼容接口", len(rows2) == 1 and rows2[0]["pack"] == "通用",
          json.dumps(rows2, ensure_ascii=False)[:120])
    # 非邻接用户对（同组第 2/3 变体）归属内置域而非「用户自定义」
    check("groups.非邻接对归属内置域", ct._pair_in_builtin("心衰", "HF") == "心血管",
          str(ct._pair_in_builtin("心衰", "HF")))

    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "t.md")
        open(f, "w", encoding="utf-8").write(
            "既往 HF（心衰）病史。脑卒中（中风）后续住院。文中 Foo Bar 与 Baz Qux 混用。")
        r = run_cli([os.path.join(SCRIPTS, "check_terms.py"), f, "--json"])
        d = json.loads(r.stdout)
        hfj = [x for x in d["inconsistencies"] if x.get("canonical") == "HF"]
        check("groups.CLI JSON 带变体计数字典",
              len(hfj) == 1 and hfj[0]["variants"].get("心衰") == 1,
              json.dumps(d, ensure_ascii=False)[:200])
        pf = os.path.join(td, "u.txt")
        open(pf, "w", encoding="utf-8").write("脑卒中|中风\n Foo Bar | Baz Qux \n")
        r2 = run_cli([os.path.join(SCRIPTS, "check_terms.py"), f,
                      "--pairs", pf, "--json"])
        d2 = json.loads(r2.stdout)
        nm = [x for x in d2["inconsistencies"]
              if {x.get("a"), x.get("b")} >= {"脑卒中", "中风"}]
        check("groups.用户对与内置组去重", len(nm) == 1,
              json.dumps(d2, ensure_ascii=False)[:200])
        fb = [x for x in d2["inconsistencies"]
              if "Foo Bar" in (x.get("a") or "") or "Foo Bar" in (x.get("b") or "")]
        check("groups.真用户对标注用户自定义",
              len(fb) == 1 and fb[0].get("pack") == "用户自定义",
              json.dumps(fb, ensure_ascii=False)[:120])
        r3 = run_cli([os.path.join(SCRIPTS, "check_terms.py"), "--list-packs"])
        total_vars = 0
        import re as _re
        for ln in r3.stdout.splitlines():
            m = _re.search(r"(\d+) 组 / (\d+) 变体", ln)
            if m:
                total_vars += int(m.group(2))
        check("groups.--list-packs 组/变体口径（合计 55）",
              r3.returncode == 0 and "组 /" in r3.stdout and total_vars == 55,
              "合计=%d" % total_vars)


# ── 2. 统计面板 ──────────────────────────────────────────────
STATS_TXT = ("本研究采用回顾性队列设计，纳入2023年1月至2024年12月间收治的连续病例。"
             "主要终点是全因死亡率，次要终点包括再入院率与不良事件发生率。"
             "In order to assess outcomes, we analyzed the data with care. "
             "It is worth noting that the results were significant across groups.\n")


def test_stats_panel():
    pr = hxt_core.style_profile(STATS_TXT)
    st = pr.get("stats") or {}
    check("stats.键齐全",
          all(k in st for k in ("ttr_zh", "ttr_en", "func_ratio_zh",
                                "func_ratio_en", "sent_len_quantiles", "note")),
          json.dumps(st, ensure_ascii=False)[:160])
    check("stats.TTR 值域合理",
          isinstance(st.get("ttr_zh"), float) and 0 < st["ttr_zh"] <= 1.0,
          str(st.get("ttr_zh")))
    q = st.get("sent_len_quantiles") or {}
    check("stats.分位四件套且有序",
          set(q) >= {"p25", "p50", "p75", "p90"}
          and q["p25"] <= q["p50"] <= q["p75"] <= q["p90"], str(q))
    check("stats.note 免责在位", "不判档" in (st.get("note") or ""))
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "s.md")
        open(f, "w", encoding="utf-8").write(STATS_TXT)
        r = run_cli([os.path.join(SCRIPTS, "stylecheck.py"), f, "--json"])
        d = json.loads(r.stdout)
        check("stats.stylecheck --json 透出", "stats" in d and "ttr_zh" in d["stats"])


# ── 3. --ci 别名 ─────────────────────────────────────────────
def test_ci_alias():
    with tempfile.TemporaryDirectory() as td:
        dirty = os.path.join(td, "dirty.md")
        open(dirty, "w", encoding="utf-8").write(
            "众所周知，综上所述本研究具有重要意义。此外，[cite: 1] 残留在内。\n")
        clean = os.path.join(td, "clean.md")
        open(clean, "w", encoding="utf-8").write(
            "队列纳入 120 例患者，随访 24 个月，两组基线均衡。\n")
        cases = [
            ("detect", [os.path.join(SCRIPTS, "detect.py"), dirty, "--ci"], 3),
            ("detect", [os.path.join(SCRIPTS, "detect.py"), clean, "--ci"], 0),
            ("pipeline", [os.path.join(SCRIPTS, "pipeline.py"), dirty, "--ci"], 3),
        ]
        for name, args, want in cases:
            r = run_cli(args)
            check("ci.%s --ci exit=%d" % (name, want), r.returncode == want,
                  "got %d stdout=%s" % (r.returncode, r.stdout[:60]))
        r = run_cli([os.path.join(SCRIPTS, "compare.py"), clean, clean, "--ci"])
        check("ci.compare --ci exit=0", r.returncode == 0, str(r.returncode))
        # 别名与全名同义（同输入同退出码）
        r_full = run_cli([os.path.join(SCRIPTS, "detect.py"), dirty,
                          "--exit-verdict"])
        r_alias = run_cli([os.path.join(SCRIPTS, "detect.py"), dirty, "--ci"])
        check("ci.别名与全名同义",
              r_full.returncode == r_alias.returncode,
              "%d vs %d" % (r_full.returncode, r_alias.returncode))


# ── 4. 文档与合规 ────────────────────────────────────────────
def test_docs():
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    import re as _re
    check("docs.EN 锚 v3.x 在位",
          bool(_re.search(r"## Feature status \(v3\.\d+\.\d+\)", en)))
    check("docs.ZH 锚 v3.x 在位",
          bool(_re.search(r"功能状态（v3\.\d+\.\d+）", zh)))
    check("docs.ZH 一句话路由在位", "一句话路由" in zh and "paper-polisher-pro" in zh)
    check("docs.EN 一句话路由在位", "Routing in one line" in en)
    check("docs.ZH 用户话术表", "普通作者怎么开口" in zh and "降一下 AI 率" in zh)
    check("docs.ZH 能力承诺表", "能改什么（改前 → 改后实例）" in zh and "绝不编造数据" in zh)
    check("docs.EN 能力承诺表", "What it can actually change" in en)
    check("docs.ZH --ci 已入自动化节", "`--ci`" in zh)
    check("docs.ZH 统计面板入状态表", "统计面板" in zh and "TTR" in zh)
    blob = (en + zh).lower()
    for w in ("朱雀", "gptzero", "turnitin", "zerogpt", "copyleaks", "pangram",
              "过ai检测", "降检测率", "去ai痕迹", "帮过检测",
              "undetectable", "直击官方评测", "主靶", "扣分项", "official-eval"):
        check("合规.禁词「%s」零命中" % w, w not in blob)
    check("version.>=3.1.0",
          tuple(int(x) for x in hxt_core.__version__.split(".")) >= (3, 1, 0),
          hxt_core.__version__)


def test_deep_verify_exemption():
    import transform as tf
    import verify as vf
    o = "众所周知，本研究具有重要意义。不仅方法新颖，而且数据可靠。队列纳入120例患者。"
    n, ops, changed = tf.deep_polish_ex(o)
    check("exempt.deep_polish_ex 返回改写句集", len(changed) >= 1, str(changed))
    r = vf.verify(o, n, expected_new=changed)
    check("exempt.管线豁免后 W_SENT_ADDED 清零",
          not [w for w in r["warnings"] if w["code"] == "W_SENT_ADDED"],
          json.dumps(r["warnings"], ensure_ascii=False)[:160])
    r2 = vf.verify(o, n)
    check("exempt.未豁免仍告警（护栏不弱化）",
          len([w for w in r2["warnings"] if w["code"] == "W_SENT_ADDED"]) == 1)
    # 真整句插入不因豁免漏报
    n_bad = n + "这句是凭空加的全新内容句子没有数字。"
    r3 = vf.verify(o, n_bad, expected_new=changed)
    check("exempt.真插入仍被拦",
          any(w["code"] == "W_SENT_ADDED" for w in r3["warnings"]))


def test_deep_hint():
    import hxt_core
    txt = "众所周知，综上所述该方法有效。值得注意的是样本量充足。"
    r = hxt_core.scan(txt)
    hints = hxt_core.build_hints(txt, r)
    check("hint.八股命中建议 --deep",
          any("--deep" in h for h in hints), json.dumps(hints, ensure_ascii=False)[:160])


def main():
    test_groups()
    test_stats_panel()
    test_ci_alias()
    test_deep_verify_exemption()
    test_deep_hint()
    test_docs()
    print("\n%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()

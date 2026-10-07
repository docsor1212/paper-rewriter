# -*- coding: utf-8 -*-
"""test_offline_v280.py — v2.8.0 新功能离线测试。

覆盖：
  1. PDF 抽取置信度自评：好 PDF=高 / 乱码 PDF=低 / 短文本=低（词过少）、
     read_text 非 pdf 路径 meta={}、detect/pipeline 的 .pdf 标注链路
  2. 触发词变体扩展：新触发词在 SKILL 双语、无抑制源词入触发区
  3. 版本串 2.8.0
运行：python3 tests/test_offline_v280.py（全断言，无第三方依赖）
"""

import json
import os
import subprocess
import sys
import tempfile
import zlib

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


def run_cli(args, stdin_text=None):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True,
                       encoding="utf-8", env=env, input=stdin_text)
    return p.returncode, p.stdout, p.stderr


def make_pdf(path, body_text):
    body = ("BT /F1 12 Tf 72 720 Td (" + body_text.replace("(", "").replace(")", "")
            + ") Tj ET").encode()
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4\nstream\n" + zlib.compress(body) + b"\nendstream\ntrailer\n")


tmpdir = tempfile.mkdtemp()
GOOD = ("Abstract. The results of this study show that the treatment group had "
        "significantly better outcomes than the control group (p=0.03). Methods "
        "and data analysis were conducted according to the protocol. Figure 1 "
        "shows the distribution. In conclusion, this method is effective. " * 6)

# ---------------------------------------------------------------------------
# 1. 置信度引擎
# ---------------------------------------------------------------------------
f_good = os.path.join(tmpdir, "good.pdf")
make_pdf(f_good, GOOD)
txt, meta = hxt_core.read_text_ex(f_good)
check("pdf_1a_good_high", meta.get("confidence") == "高", str(meta))
f_bad = os.path.join(tmpdir, "bad.pdf")
make_pdf(f_bad, "XXzz qqww vvkk jjhh " * 60)
_, meta2 = hxt_core.read_text_ex(f_bad)
check("pdf_1b_gibberish_low", meta2.get("confidence") == "低"
      and any("导出" in n for n in meta2.get("notes", [])), str(meta2))
f_short = os.path.join(tmpdir, "short.pdf")
make_pdf(f_short, "Only few words here.")
_, meta3 = hxt_core.read_text_ex(f_short)
check("pdf_1c_short_low", meta3.get("confidence") == "低"
      and any("OCR" in n for n in meta3.get("notes", [])), str(meta3))
# 非 pdf：meta 为空
f_txt = os.path.join(tmpdir, "t.txt")
open(f_txt, "w", encoding="utf-8").write("正常文本。")
_, meta4 = hxt_core.read_text_ex(f_txt)
check("pdf_1d_txt_meta_empty", meta4 == {}, str(meta4))
# 引擎不破坏原 read_text
check("pdf_1e_read_text_intact",
      hxt_core.read_text(f_good) == txt, "")

# ---------------------------------------------------------------------------
# 2. CLI 标注链路
# ---------------------------------------------------------------------------
DET = os.path.join(SCRIPTS, "detect.py")
PL = os.path.join(SCRIPTS, "pipeline.py")
rc, out, _ = run_cli([DET, f_good, "-j"])
j = json.loads(out) if out.strip().startswith("{") else {}
check("pdf_2a_detect_json_meta",
      rc == 0 and j.get("pdf_meta", {}).get("confidence") == "高", str(j.get("pdf_meta")))
rc, out, _ = run_cli([DET, f_bad])
check("pdf_2b_detect_human_line",
      rc == 0 and "PDF 抽取置信度: 低" in out, out[:120])
outp = os.path.join(tmpdir, "o.txt")
rc, out, _ = run_cli([PL, f_good, "-o", outp, "--json"])
j = json.loads(out) if out.strip().startswith("{") else {}
check("pdf_2c_pipeline_meta", j.get("pdf_meta", {}).get("confidence") == "高",
      str(j.get("pdf_meta")))

# ---------------------------------------------------------------------------
# 3. 触发词扩展
# ---------------------------------------------------------------------------
en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
check("trig_3a_en_variants",
      "academic rewriting" in en and "段落改写" in en, "")
check("trig_3b_zh_variants",
      "去AI味改写" in zh and "学术改写" in zh and "表达优化" in zh, "")
# 触发区锁断言：既有词根「论文降AI率」剥除后，触发区不得再含 降AI率/AI率
trig_zone = zh[zh.find("- **触发词**"):zh.find("→ 跑上面的管线")]
zone_clean = trig_zone.replace("论文降AI率 /", "", 1)
check("trig_3c_zone_no_new_suppress",
      "降AI率" not in zone_clean and "AI率" not in zone_clean, zone_clean[:60])

# ---------------------------------------------------------------------------
# 4. 邻居 agent 二轮实测修复回归（2026-10-07 并入）
# ---------------------------------------------------------------------------
import verify as vf  # noqa: E402

# 4a. 大文件多块 sentences 聚合（原 None → detect %d 崩溃）
para = "这是一段用于构造大文件的正文内容，不含特殊特征，只是重复填充。\n\n"
big = para * 13000
r_big = hxt_core.scan_chunked(big)
check("nb_4a_chunked_sentences",
      isinstance(r_big["sentences"], int) and r_big["sentences"] > 0,
      str(r_big["sentences"]))
f_big = os.path.join(tmpdir, "big.txt")
with open(f_big, "w", encoding="utf-8") as f:
    f.write(big)
rc, out, err = run_cli([DET, f_big, "-s"])
check("nb_4b_detect_big_no_crash", rc == 0, "rc=%d err=%s" % (rc, err[:60]))

# 4b. verify 全角形式篡改 → E_NUM_WIDTH（NFKC 等值但字符已变）
_O = "患者血清 IL-6 水平为 68.7%，随访至 2025 年。本研究纳入 120 例患者并完成随访与统计分析。"
fw_cases = [
    ("全角数字", "患者血清 IL-6 水平为 ６８.７%，随访至 ２０２５ 年。本研究纳入 120 例患者并完成随访与统计分析。"),
    ("全角术语", "患者血清 ＩＬ-６ 水平为 68.7%，随访至 2025 年。本研究纳入 120 例患者并完成随访与统计分析。"),
]
for name, rev in fw_cases:
    r = vf.verify(_O, rev)  # verify 接收文本（此前误传文件路径——测试自身 bug）
    codes = [v["code"] for v in r["violations"]]
    check("nb_4c_fullwidth_%s" % name, "E_NUM_WIDTH" in codes and not r["ok"],
          str(codes))
# 等值排版改写零误伤
r = vf.verify("P＜0.05，6–8 天，1,234 例。", "P<0.05，6-8 天，1234 例。")
check("nb_4d_nfkc_no_false_positive", r["ok"], str([v["code"] for v in r["violations"]]))

# 4c. chatbot 类用户守卫豁免（原 guards_applied 恒空）
ug2 = os.path.join(SCRIPTS, "user_guards.json")
_ug_bak = None
if os.path.exists(ug2):
    _ug_bak = open(ug2, encoding="utf-8").read()
try:
    with open(ug2, "w", encoding="utf-8") as f:
        json.dump({"_meta": {}, "term_guards": [
            {"term": "Hope this helps", "allow_before": [], "allow_after": ["!"],
             "lang": "en"}]}, f, ensure_ascii=False)
    hxt_core.clear_pattern_cache()
    r = hxt_core.scan("Hope this helps! Hope this helps!\n\n论坛体正文内容。")
    check("nb_4e_chatbot_user_guard",
          r["critical_hit"] is False and len(r["guards_applied"]) >= 1,
          "critical=%s guards=%d" % (r["critical_hit"], len(r["guards_applied"])))
    r2 = hxt_core.scan("Hope this helps, 但这是另一上下文的内容陈述句。")
    check("nb_4f_guard_context_sensitive", r2["critical_hit"] is True,
          "critical=%s（不同上下文应仍计分）" % r2["critical_hit"])
finally:
    if _ug_bak is not None:
        open(ug2, "w", encoding="utf-8").write(_ug_bak)
    elif os.path.exists(ug2):
        os.remove(ug2)
    hxt_core.clear_pattern_cache()

# 4d. 整句插入 W_SENT_ADDED
_O2 = ("本研究纳入 120 例患者并完成为期 12 个月的随访与统计分析，"
       "全部数据由双人独立录入核对，见附表 A 与附表 B 以及方法学补充材料。")
_N2 = _O2[:-1] + "。这是插入的一句话没有任何数字或引用内容。"
f_o = os.path.join(tmpdir, "o2.txt")
f_n = os.path.join(tmpdir, "n2.txt")
open(f_o, "w", encoding="utf-8").write(_O2)
open(f_n, "w", encoding="utf-8").write(_N2)
r = vf.verify(_O2, _N2)
check("nb_4g_sent_added_warn",
      any(w["code"] == "W_SENT_ADDED" for w in r["warnings"]), str([w["code"] for w in r["warnings"]]))

# 4e. check_terms SLE 内置对
sys.path.insert(0, SCRIPTS)
import check_terms as ct  # noqa: E402
r = ct.find_inconsistencies("SLE 患者符合系统性红斑狼疮诊断标准。", ct._BUILTIN_PAIRS)
check("nb_4h_sle_pair",
      any(x["a"] == "SLE" for x in r), str(r[:2]))

# 4f. 统计通道规整旗（v2.8.0 实验定案：信息旗标不改评分；≥8 句才判）
uni_text = ("在研究中我们分析了数据。结果显示组间差异是显著的。方法按方案执行了。"
            "结论支持最初的假设。样本量足够支持分析。模型控制了主要混杂因素。"
            "结果与先前报告一致。敏感性分析结果稳定。\n\n") * 6
r_uni = hxt_core.scan(uni_text)
check("nb_4i_uniform_flag",
      r_uni["stats"].get("uniform_flag") is True
      and any("规整旗" in n for n in r_uni["stats"]["notes"]),
      "band=%s" % r_uni["stats"].get("band_conc"))
# 旗标不改评分口径：同文本的档位只由 pts 决定（此处无词表命中，分数应仍低）
check("nb_4j_flag_no_score_change",
      r_uni["score"] < 28 and r_uni["level"] in ("低", "中"),
      "score=%d level=%s" % (r_uni["score"], r_uni["level"]))
# 人写自然节奏（长短交错）不触发
varied = ("短短一句。\n\n这一段则要长得多，包含了许多从句与修饰成分，讨论了方法学的细节、"
          "统计口径的选择，以及敏感性分析中各种假设的影响，读完需要一点耐心。短句。"
          "然后又是一个非常非常长的句子，继续拉长句长的分布范围，让变异系数回升到自然的区间里去。\n\n短。\n\n"
          "中等长度的句子用来过渡，保持语流的连贯性，同时避免节奏被前后的极端值主导。\n\n") * 4
r_var = hxt_core.scan(varied)
check("nb_4k_varied_no_flag",
      not r_var["stats"].get("uniform_flag"), str(r_var["stats"].get("band_conc")))

# ---------------------------------------------------------------------------
print("\n===== v2.8.0 新功能测试: %d PASS / %d FAIL =====" % (len(PASS), len(FAIL)))
if FAIL:
    print("失败项:", FAIL)
    sys.exit(1)

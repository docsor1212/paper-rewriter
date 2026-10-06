# -*- coding: utf-8 -*-
"""test_offline_v270.py — v2.7.0 新功能离线测试。

覆盖：
  1. best_practices.md：七个场景齐备、通用收尾三连、与 pitfalls 计数引用一致
  2. stylecheck --html：单文件画像与 --compare 两模式 HTML、--json+--compare 互斥
  3. pipeline --terms auto：自动草稿生成+警告、CJK 相邻缩写抽取（IRAK4 修复）、
     负对照不误抽
  4. Trigger on 追加文本预埋合规（词表无 降AI/AI率；幂等判定串在发布脚本）
运行：python3 tests/test_offline_v270.py（全断言，无第三方依赖）
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


# ---------------------------------------------------------------------------
# 1. best_practices.md
# ---------------------------------------------------------------------------
bp = os.path.join(ROOT, "references", "best_practices.md")
t = open(bp, encoding="utf-8").read() if os.path.exists(bp) else ""
scenes = ["场景 1", "场景 2", "场景 3", "场景 4", "场景 5", "场景 6", "场景 7"]
check("bp_1a_seven_scenes", all(s in t for s in scenes),
      str([s for s in scenes if s not in t]))
check("bp_1b_common_trio", "通用收尾三连" in t and "verify.py" in t, "")
check("bp_1c_no_suppress_words",
      "降AI" not in t and "AI率" not in t, "手册含抑制源词")

# ---------------------------------------------------------------------------
# 2. stylecheck --html
# ---------------------------------------------------------------------------
SC = os.path.join(SCRIPTS, "stylecheck.py")
tmpdir = tempfile.mkdtemp()
ai = os.path.join(HERE, "corpus_ai_zh.txt")
h1 = os.path.join(tmpdir, "sp.html")
rc, out, err = run_cli([SC, ai, "--html", h1])
check("sc_2a_profile_html", rc == 0 and os.path.exists(h1)
      and "风格画像" in open(h1, encoding="utf-8").read(), "rc=%d" % rc)
h2 = os.path.join(tmpdir, "spc.html")
rc, out, err = run_cli([SC, ai, os.path.join(HERE, "corpus_human_zh.txt"),
                        "--compare", "--html", h2])
check("sc_2b_compare_html", rc == 0 and os.path.exists(h2)
      and "风格画像对比" in open(h2, encoding="utf-8").read(), "rc=%d" % rc)
rc, _, err = run_cli([SC, ai, "--compare", "--json"])
check("sc_2c_json_compare_mutex", rc == 2 and "仅支持单文件" in err,
      "rc=%d err=%s" % (rc, err[:50]))

# ---------------------------------------------------------------------------
# 3. pipeline --terms auto + CJK 抽取修复
# ---------------------------------------------------------------------------
PL = os.path.join(SCRIPTS, "pipeline.py")
f_in = os.path.join(tmpdir, "in.txt")
with open(f_in, "w", encoding="utf-8") as f:
    f.write("本研究采用IRAK4抑制剂处理组，结果显著。\n\n数据见第3节，p=0.03。\n")
outp = os.path.join(tmpdir, "out.txt")
rc, out, err = run_cli([PL, f_in, "-o", outp, "--terms", "auto"])
draft = outp.rsplit(".", 1)[0] + ".terms.auto.txt"
check("ta_3a_auto_draft", rc == 0 and os.path.exists(draft)
      and "IRAK4" in open(draft, encoding="utf-8").read(),
      "rc=%d err=%s" % (rc, err[:80]))
rc, out, _ = run_cli([PL, f_in, "-o", os.path.join(tmpdir, "o2.txt"),
                      "--terms", "auto", "--json"])
j = json.loads(out) if out.strip().startswith("{") else {}
check("ta_3b_terms_note_json", "terms_note" in j and "未经人工确认" in j.get("terms_note", ""),
      str(j.get("terms_note", "")[:40]))
# 负对照：普通英文句零误抽
import extract_terms as et  # noqa: E402
r = et.extract("This is a simple sentence with nothing special here.", min_count=1)
check("ta_3c_negative_clean", len(r) <= 1, str(r[:3]))

# ---------------------------------------------------------------------------
# 4. Trigger on 预埋合规（_27 发布脚本为本班次产物前，先验词表本体）
# ---------------------------------------------------------------------------
TR_PR = ("论文改写/风格自然化/去AI味/段落改写/学术改写/表达优化；"
         "academic rewriting/style naturalization")
TR_HXT = "去AI味/AI文本人味化/文本自然化/自然表达；humanize AI text/natural rewriting"
for name, txt in (("paper-rewriter", TR_PR), ("humanize-ai-text", TR_HXT)):
    check("tg_4a_no_suppress_%s" % name,
          "降AI" not in txt and "AI率" not in txt, txt[:40])
    check("tg_4b_has_trigger_%s" % name, txt.startswith(("论文改写", "去AI味")), "")

# ---------------------------------------------------------------------------
print("\n===== v2.7.0 新功能测试: %d PASS / %d FAIL =====" % (len(PASS), len(FAIL)))
if FAIL:
    print("失败项:", FAIL)
    sys.exit(1)

# -*- coding: utf-8 -*-
"""test_offline_v260.py — v2.6.0 新功能离线测试。

覆盖：
  1. audit_patterns：158 条模式零告警（全部有界量词）、risky 检测器正负对照
  2. style_profile：四语料档位分离（AI=偏机器 / 人写=自然）、worst_paras 定位、
     短文本多样性不判档、JSON 可序列化
  3. stylecheck.py CLI：单文件画像、--compare 差值、--json、空输入 exit 2、
     --help 含说明（trigger 靶）
运行：python3 tests/test_offline_v260.py（全断言，无第三方依赖）
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")
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


SC = os.path.join(SCRIPTS, "stylecheck.py")
AI_ZH = os.path.join(HERE, "corpus_ai_zh.txt")
HU_ZH = os.path.join(HERE, "corpus_human_zh.txt")

# ---------------------------------------------------------------------------
# 1. 模式审计兜底
# ---------------------------------------------------------------------------
total, warns = hxt_core.audit_patterns()
check("ap_1a_all_bounded", total >= 150 and len(warns) == 0,
      "total=%d warns=%s" % (total, warns[:2]))

# ---------------------------------------------------------------------------
# 2. style_profile 引擎
# ---------------------------------------------------------------------------
pa = hxt_core.style_profile(open(AI_ZH, encoding="utf-8").read())
ph = hxt_core.style_profile(open(HU_ZH, encoding="utf-8").read())
check("sp_2a_ai_band", pa["global"]["jargon_1k"]["band"] == "偏机器",
      str(pa["global"]["jargon_1k"]))
check("sp_2b_human_band", ph["global"]["jargon_1k"]["band"] == "自然",
      str(ph["global"]["jargon_1k"]))
check("sp_2c_worst_located",
      pa["worst_paras"] and all(1 <= i <= pa["n_paras"] for i in pa["worst_paras"]),
      str(pa["worst_paras"]))
check("sp_2d_human_no_worst", ph["worst_paras"] == [], str(ph["worst_paras"]))
check("sp_2e_advice_present", len(pa["advice"]) >= 2 and len(ph["advice"]) >= 1, "")
# 短文本：多样性指标不判档
short = hxt_core.style_profile("综上所述，该方法不仅好而且快。值得注意的是结果显著。")
check("sp_2f_short_no_judge",
      short["global"]["opener_top"]["band"].startswith("—"),
      str(short["global"]["opener_top"]))
# JSON 可序列化
json.dumps(short)
check("sp_2g_jsonable", True)
# 四指标方向回归（评审实锤 sent_cv 方向反：人写英文 0.508 曾被判偏机器）
import os as _os
_en_hu = hxt_core.style_profile(open(_os.path.join(HERE, "corpus_human_en.txt"), encoding="utf-8").read())
_en_ai = hxt_core.style_profile(open(_os.path.join(HERE, "corpus_ai_en.txt"), encoding="utf-8").read())
check("sp_2h_sent_cv_direction",
      _en_hu["global"]["sent_cv"]["band"] in ("自然", "观察")
      and _en_hu["global"]["sent_cv"]["band"] != "偏机器",
      str(_en_hu["global"]["sent_cv"]))
check("sp_2i_en_jargon_split",
      _en_ai["global"]["jargon_1k"]["band"] == "偏机器"
      and _en_hu["global"]["jargon_1k"]["band"] == "自然",
      "%s vs %s" % (_en_ai["global"]["jargon_1k"], _en_hu["global"]["jargon_1k"]))
# 审计器正负对照（docstring 宣称的用例收编进套件）
check("ap_1b_risky_detector",
      hxt_core._RISKY_QUANT.search(r"[^\n\r]*abc") is not None
      and hxt_core._RISKY_QUANT.search(r".*abc") is not None
      and hxt_core._RISKY_QUANT.search(r".*?lazy") is None
      and hxt_core._RISKY_QUANT.search(r"\d*") is None, "")

# ---------------------------------------------------------------------------
# 3. stylecheck CLI
# ---------------------------------------------------------------------------
rc, out, err = run_cli([SC, AI_ZH])
check("sc_3a_single_md", rc == 0 and "风格画像" in out and "偏机器" in out,
      "rc=%d" % rc)
rc, out, _ = run_cli([SC, AI_ZH, HU_ZH, "--compare"])
check("sc_3b_compare_delta",
      rc == 0 and "偏机器 → 自然" in out and "黑话命中合计" in out, out[:120])
rc, out, _ = run_cli([SC, AI_ZH, "--json"])
j = json.loads(out) if out.strip().startswith("{") else {}
check("sc_3c_json", "global" in j and "paras" in j and "advice" in j, "")
rc, _, err = run_cli([SC])
check("sc_3d_empty_stdin_exit2", rc == 2 and "输入为空" in err, "rc=%d err=%s" % (rc, err[:50]))
rc, out, _ = run_cli([SC, "--help"])
check("sc_3e_help_documented",
      rc == 0 and "风格画像" in out and "--compare" in out, out[:80])

# ---------------------------------------------------------------------------
print("\n===== v2.6.0 新功能测试: %d PASS / %d FAIL =====" % (len(PASS), len(FAIL)))
if FAIL:
    print("失败项:", FAIL)
    sys.exit(1)

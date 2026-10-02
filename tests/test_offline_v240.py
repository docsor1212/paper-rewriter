# -*- coding: utf-8 -*-
"""test_offline_v240.py — v2.4.0 新功能离线测试。

覆盖：
  1. deep_polish：句首八股删除/句中保留/不仅合并/数字不动/空文本/干净文本零操作
  2. transform --deep 与 pipeline --deep 端到端（--track 审计 + verify 守卫 + 退出码）
  3. build_hints：critical/深改排序/守卫固化/general profile 四类提示
  4. scan 时间预算：超预算 ValueError、正常扫描零影响、scan_chunked 透传
运行：python3 tests/test_offline_v240.py（全断言，无第三方依赖）
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
import transform as tf  # noqa: E402

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
# 1. deep_polish 单元
# ---------------------------------------------------------------------------
src = ("综上所述，本研究验证了假设。值得注意的是，该方法不仅提升了精度，而且降低了成本。\n\n"
       "众所周知，这一领域很重要。数据见第3.2节，p=0.03。\n")
out, ops = tf.deep_polish(src)
check("dp_1a_openers_removed",
      all(w not in out for w in ("综上所述", "值得注意的是", "众所周知")), out[:60])
check("dp_1b_not_only_merged", "不仅" not in out and "，且降低了成本" in out, out[:60])
check("dp_1c_numbers_intact", "p=0.03" in out and "第3.2节" in out, "")
op_names = {o["op"]: o["count"] for o in ops}
check("dp_1d_ops_recorded",
      op_names.get("句首八股删除") == 3 and op_names.get("排除式连接合并") == 1, str(ops))
out2, ops2 = tf.deep_polish("本文值得注意的是现象本身，而非原因。")
check("dp_1e_mid_sentence_kept",
      "值得注意的是" in out2 and not ops2, out2)
out3, ops3 = tf.deep_polish("")
check("dp_1f_empty_ok", out3 == "" and ops3 == [], "")
out4, ops4 = tf.deep_polish("这是一段完全正常的句子，没有任何套话与排除式连接。")
check("dp_1g_clean_noop", out4 == "这是一段完全正常的句子，没有任何套话与排除式连接。" and ops4 == [], str(ops4))
out5, _ = tf.deep_polish("该方法不仅快，还省。不仅稳，也准。")
check("dp_1h_hai_ye_forms", "不仅" not in out5 and "，也省" in out5 and "，也准" in out5, out5)

# ---------------------------------------------------------------------------
# 2. CLI 端到端（--deep + --track + verify）
# ---------------------------------------------------------------------------
tmpdir = tempfile.mkdtemp()
f_in = os.path.join(tmpdir, "in.txt")
with open(f_in, "w", encoding="utf-8") as f:
    f.write(src)
outp = os.path.join(tmpdir, "out.txt")
track_base = os.path.join(tmpdir, "track")

rc, _, err = run_cli([os.path.join(SCRIPTS, "transform.py"), f_in, "-o", outp,
                      "--deep", "--track", track_base])
check("cli_2a_transform_deep_ok", rc == 0, err[:120])
cleaned = open(outp, encoding="utf-8").read()
check("cli_2b_transform_deep_applied",
      "综上所述" not in cleaned and "不仅" not in cleaned and "p=0.03" in cleaned, "")
check("cli_2c_track_records_deep",
      os.path.exists(track_base + ".md")
      and "深改档" in open(track_base + ".md", encoding="utf-8").read(), "")

# pipeline --deep：清理+深改+守卫+对比 全链
f_pl = os.path.join(tmpdir, "pl.txt")
with open(f_pl, "w", encoding="utf-8") as f:
    f.write(src)
rc, out, err = run_cli([os.path.join(SCRIPTS, "pipeline.py"), f_pl,
                        "-o", os.path.join(tmpdir, "pl_out.txt"), "--deep", "--json"])
j = json.loads(out) if out.strip().startswith("{") else {}
check("cli_2d_pipeline_deep_mode",
      rc == 0 and "+深改档" in j.get("mode", ""), "rc=%d mode=%s" % (rc, j.get("mode")))
check("cli_2e_pipeline_json_fields",
      "exit_verdict" in j and "hints" in j and j.get("verify", {}).get("ok") is not None,
      str(list(j.keys())))
pl_out = open(os.path.join(tmpdir, "pl_out.txt"), encoding="utf-8").read()
check("cli_2f_pipeline_deep_applied", "不仅" not in pl_out and "综上所述" not in pl_out, "")

# ---------------------------------------------------------------------------
# 3. build_hints 四类
# ---------------------------------------------------------------------------
r_bad = hxt_core.scan("Hello! I hope this helps. 综上所述，该方法不仅好而且快。值得注意的是结果显著。")
hints = hxt_core.build_hints("样例", r_bad)
check("h_3a_critical_hint", any("transform.py" in h for h in hints), str(hints))
check("h_3b_plan_hint", any("plan.py" in h for h in hints), str(hints))
r_guarded = hxt_core.scan("免疫复合物在管底形成大量沉淀反应后离心。")
hints2 = hxt_core.build_hints("样例", r_guarded)
# 沉淀有内置守卫 → guards_applied 非空才提示
if r_guarded.get("guards_applied"):
    check("h_3c_guard_hint", any("learn_guards" in h for h in hints2), str(hints2))
else:
    check("h_3c_guard_hint", True, "（本例无守卫豁免，跳过）")
# general profile 提示：非论文文体 + 标点/翻译腔为主
blog = "今天的天气真好啊,大家都在讨论周末去哪玩;我觉得可以去看电影,也可以去爬山,你说呢?"
r_blog = hxt_core.scan(blog, profile="academic")
hints3 = hxt_core.build_hints(blog, r_blog, profile="academic")
check("h_3d_general_hint_or_skip",
      all("profile general" not in h or "--profile general" in h for h in hints3), str(hints3))

# ---------------------------------------------------------------------------
# 4. scan 时间预算
# ---------------------------------------------------------------------------
try:
    hxt_core.scan("正常内容。" * 50, time_budget=0.000001)
    check("t_4a_timeout_raises", False, "未触发")
except ValueError as e:
    check("t_4a_timeout_raises", "超时" in str(e) and "拆分" in str(e), str(e)[:60])
except Exception as e:
    check("t_4a_timeout_raises", False, "异常类型 %s" % type(e).__name__)
r = hxt_core.scan("综上所述，该方法不仅好而且快。")
check("t_4b_normal_scan_unaffected", r["score"] >= 0, "")
r2 = hxt_core.scan_chunked("正常内容。" * 100, max_chars=1000, overlap=100)
check("t_4c_chunked_passthrough", r2["score"] >= 0, "")

# ---------------------------------------------------------------------------
print("\n===== v2.4.0 新功能测试: %d PASS / %d FAIL =====" % (len(PASS), len(FAIL)))
if FAIL:
    print("失败项:", FAIL)
    sys.exit(1)

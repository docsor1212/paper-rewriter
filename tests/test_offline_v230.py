# -*- coding: utf-8 -*-
"""test_offline_v230.py — v2.3.0 新功能离线测试。

覆盖：
  1. --exit-verdict 机器退出码矩阵（detect 单文件/batch、compare、pipeline 双模式）
  2. 缺省契约不回归：不带 --exit-verdict 恒 0；verify.py 契约不变
  3. en_opening 套路开场信号（正负对照）
  4. #摘要 无空格 markdown 标题；英文 #1 不误收
运行：python3 tests/test_offline_v230.py（全断言，无第三方依赖）
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


def w(tmpdir, name, content):
    fp = os.path.join(tmpdir, name)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)
    return fp


T_OK = ("这是一段完全正常的学术句子，讨论实验设计与数据分析。\n\n"
        "第二段也是正常内容，报告了统计结果与图表说明。\n\n"
        "第三段保持客观陈述，没有模板腔特征。\n")
T_BAD = ("综上所述，本研究具有重要意义。一方面该方法很高效，另一方面成本也低。"
         "值得注意的是结果显著，为应用提供了新思路。众所周知这个领域很重要。\n")
T_CHAT = ("这是一段正常句子。\n\nI hope this helps! Let me know if you have "
          "other questions.\n\n还有一段正常内容用于稀释占比，报告统计与设计。\n")
T_EN_OPEN = ("In the ever-evolving landscape of modern medicine, "
             "unlocking the full potential of CAR-T remains vital.\n")
T_EN_CLEAN = ("We analyzed 48 patients with IRAK4 deficiency using "
              "standard neutrophil enumeration protocols.\n")

tmpdir = tempfile.mkdtemp()
f_ok = w(tmpdir, "ok.txt", T_OK)
f_bad = w(tmpdir, "bad.txt", T_BAD)
f_chat = w(tmpdir, "chat.txt", T_CHAT)
f_en_open = w(tmpdir, "en_open.txt", T_EN_OPEN)
f_en_clean = w(tmpdir, "en_clean.txt", T_EN_CLEAN)

DET = os.path.join(SCRIPTS, "detect.py")
CMP = os.path.join(SCRIPTS, "compare.py")
PL = os.path.join(SCRIPTS, "pipeline.py")

# ---------------------------------------------------------------------------
# 1. detect --exit-verdict 矩阵
# ---------------------------------------------------------------------------
rc, out, _ = run_cli([DET, f_ok, "-s", "--exit-verdict"])
check("ev_1a_detect_clean", rc == 0 and out.strip().endswith("低"), "rc=%d out=%s" % (rc, out[:40]))
rc, out, _ = run_cli([DET, f_bad, "-s", "--exit-verdict"])
check("ev_1b_detect_work", rc == 3, "rc=%d" % rc)
rc, out, _ = run_cli([DET, f_chat, "-s", "--exit-verdict"])
check("ev_1c_detect_critical", rc == 4, "rc=%d" % rc)

# 2. 缺省契约不回归
rc, _, _ = run_cli([DET, f_bad, "-s"])
check("ev_2a_detect_default_zero", rc == 0, "rc=%d" % rc)
rc, _, _ = run_cli([DET, f_chat, "-j"])
check("ev_2b_detect_json_default_zero", rc == 0, "rc=%d" % rc)
rc, _, _ = run_cli([DET, "--batch", tmpdir])
check("ev_2c_batch_default_zero", rc == 0, "rc=%d" % rc)

# batch --exit-verdict：取最坏行
rc, _, _ = run_cli([DET, "--batch", tmpdir, "--exit-verdict"])
check("ev_1d_batch_worst", rc == 4, "rc=%d（目录含 critical 文件）" % rc)

# 3. compare --exit-verdict（改稿=原稿 → bad 仍 3）
rc, _, _ = run_cli([CMP, f_bad, f_bad, "--exit-verdict"])
check("ev_1e_compare_work", rc == 3, "rc=%d" % rc)
rc, _, _ = run_cli([CMP, f_bad, f_ok, "--exit-verdict"])
check("ev_1f_compare_clean", rc == 0, "rc=%d" % rc)

# 4. pipeline 全档
rc, _, _ = run_cli([PL, f_ok, "-o", os.path.join(tmpdir, "o1.txt"), "--exit-verdict"])
check("ev_1g_pipeline_clean", rc == 0, "rc=%d" % rc)
rc, _, _ = run_cli([PL, f_bad, "-o", os.path.join(tmpdir, "o2.txt"), "--exit-verdict"])
check("ev_1h_pipeline_work", rc in (1, 3), "rc=%d" % rc)
# --rewrite 破坏性改稿 → 1
f_rw_broken = w(tmpdir, "rw_broken.txt", "这句话被截断，数字全没了\n")
rc, _, _ = run_cli([PL, f_bad, "--rewrite", f_rw_broken, "--exit-verdict"])
check("ev_1i_pipeline_rewrite_fail", rc == 1, "rc=%d" % rc)
# --rewrite 合格改稿 → 0（长度对等、无新增数字，仅清模板腔）
f_rw_good = w(tmpdir, "rw_good.txt",
              "本研究针对上述假设给出了两项独立的验证证据，实验采用双盲随机分组"
              "设计，在成本控制与操作可行性两个维度均有改善，结论与原报告方向一致。\n")
rc, _, _ = run_cli([PL, f_bad, "--rewrite", f_rw_good, "--exit-verdict"])
check("ev_1j_pipeline_rewrite_pass", rc == 0, "rc=%d" % rc)

# JSON exit_verdict 字段与退出码一致（--json 与 --exit-verdict 同用时）
rc, out, _ = run_cli([PL, f_bad, "--rewrite", f_rw_good, "--json", "--exit-verdict"])
j = json.loads(out)
check("ev_1k_json_field_consistent",
      j["exit_verdict"] == rc, "field=%s rc=%d" % (j["exit_verdict"], rc))

# verdict_exit_code 单元
check("ev_1l_unit_threshold",
      hxt_core.verdict_exit_code(27) == 0 and hxt_core.verdict_exit_code(28) == 3
      and hxt_core.verdict_exit_code(10, True) == 4
      and hxt_core.verdict_exit_code(90, verify_ok=False) == 1, "")

# ---------------------------------------------------------------------------
# 5. en_opening 正负对照
# ---------------------------------------------------------------------------
r = hxt_core.scan(T_EN_OPEN)
n = r["categories"].get("en_opening", {}).get("count", 0)
check("en_5a_opening_hits", n >= 1, "count=%d（ever-evolving）" % n)
r = hxt_core.scan(T_EN_CLEAN)
n = r["categories"].get("en_opening", {}).get("count", 0)
check("en_5b_clean_no_hit", n == 0, "count=%d" % n)
r = hxt_core.scan("This paper aims to summarize current evidence on the topic.")
n = r["categories"].get("en_opening", {}).get("count", 0)
check("en_5c_academic_frame_not_hit", n == 0, "count=%d（this paper aims 属正当学术）" % n)

# ---------------------------------------------------------------------------
# 6. #摘要 无空格 markdown 标题
# ---------------------------------------------------------------------------
keys = [k for k, _, _ in hxt_core.detect_sections("# 论文\n\n#摘要\n\n内容。\n\n##方法\n\n内容2。")]
check("md_6a_no_space_heading",
      "abstract" in keys and "methods" in keys, str(keys))
keys2 = [k for k, _, _ in hxt_core.detect_sections("#1 cause of mortality\n\nbody.\n\n#Introduction\n\nx")]
check("md_6b_en_hash_not_eaten",
      keys2 == ["body"], str(keys2))


# ---------------------------------------------------------------------------
# 7. 评审回归：--structure critical 传播（NLP 实证缺陷）
# ---------------------------------------------------------------------------
f_struct_crit = w(tmpdir, "struct_crit.md",
                  "# 论文\n\n## 方法\n\nAs an AI language model, I cannot "
                  "provide that information.\n\n实验采用标准流程。\n")
rc, out, _ = run_cli([DET, f_struct_crit, "--structure", "--exit-verdict"])
check("ev_7a_structure_critical", rc == 4,
      "rc=%d（_methods 段含模型残留，--structure 门禁必须 4）" % rc)
rc, out, _ = run_cli([DET, f_struct_crit, "--structure", "--json", "--exit-verdict"])
j = json.loads(out) if out.strip().startswith("{") else {}
check("ev_7b_structure_json_exit", rc == 4 and j.get("critical_hit") is True,
      "rc=%d critical_hit=%s" % (rc, j.get("critical_hit")))

# 8. en_opening 正当句零误报（评审 90% 误报组）
legit_cases = [
    "How firms navigate the challenges of digital transformation.",
    "Unlocking the potential of cation-disordered oxides for lithium batteries.",
    "In the world of Dutch art markets, provenance matters.",
    "From these results it is evident that the inhibitor blocks phosphorylation.",
    "Within the world of condensed-matter physics, this remains debated.",
]
allclean = True
for tc in legit_cases:
    r = hxt_core.scan(tc)
    if r["categories"].get("en_opening", {}).get("count", 0):
        allclean = False
check("en_8_legit_zero_fp", allclean, str(legit_cases))

# 9. pipeline --batch --exit-verdict 聚合（目录含 critical 文件 → 4）
rc, _, _ = run_cli([PL, "--batch", tmpdir, "--exit-verdict"])
check("ev_9_pipeline_batch_worst", rc >= 3, "rc=%d（目录含残留/高分行）" % rc)

# 10. --html 写失败 → 2（不可目录作路径）
rc, _, _ = run_cli([DET, f_ok, "--html", tmpdir])
check("ev_10_html_fail_exit2", rc == 2, "rc=%d" % rc)

# ---------------------------------------------------------------------------
print("\n===== v2.3.0 新功能测试: %d PASS / %d FAIL =====" % (len(PASS), len(FAIL)))
if FAIL:
    print("失败项:", FAIL)
    sys.exit(1)

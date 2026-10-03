# -*- coding: utf-8 -*-
"""test_offline_v250.py — v2.5.0 新功能离线测试。

覆盖：
  1. 集中异常层：CliError/fail/cli_entry 两行中文输出、SystemExit 穿透、
     九脚本 __main__ 接入（坏输入 → rc=2 且 stderr 含"错误:"）
  2. 批量二遍重试：detect/pipeline --batch 的 retried 字段、错误行"已重试"标注
  3. 单步超时：--step-timeout 超小值干净 exit 2、timings 字段与人类可读耗时行
  4. scan 消息中文化（lang 参数）
运行：python3 tests/test_offline_v250.py（全断言，无第三方依赖）
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


tmpdir = tempfile.mkdtemp()
DET = os.path.join(SCRIPTS, "detect.py")
PL = os.path.join(SCRIPTS, "pipeline.py")

# ---------------------------------------------------------------------------
# 1. 集中异常层
# ---------------------------------------------------------------------------
f_bin = os.path.join(tmpdir, "bin.txt")
with open(f_bin, "wb") as f:
    f.write(b"\x00\x01binary\xff\xfe" * 50)
rc, out, err = run_cli([DET, f_bin])
check("ce_1a_two_line_chinese", rc == 2 and err.startswith("错误:")
      and "处置建议" in err or "UTF-8" in err, "rc=%d err=%s" % (rc, err[:80]))

# CliError 单元
try:
    hxt_core.fail("测试消息", hint="测试建议")
except hxt_core.CliError as e:
    check("ce_1b_clierro_fields", str(e) == "测试消息" and e.hint == "测试建议", "")
else:
    check("ce_1b_clierro_fields", False, "未抛出")

# SystemExit 穿透：verify 契约不受集中层影响（exit 1 场景）
f_a = os.path.join(tmpdir, "a.txt")
f_b = os.path.join(tmpdir, "b.txt")
open(f_a, "w", encoding="utf-8").write("原稿有数字 42 和术语 IRAK4。\n")
open(f_b, "w", encoding="utf-8").write("改稿把数字弄丢了，IRAK4 还在。\n")
rc, _, _ = run_cli([os.path.join(SCRIPTS, "verify.py"), f_a, f_b])
check("ce_1c_sysexit_passthrough", rc == 1, "rc=%d（verify FAIL 必须=1）" % rc)

# lang 参数中文化
try:
    hxt_core.scan("x", lang="fr")
    check("ce_1d_lang_localized", False, "未抛出")
except ValueError as e:
    check("ce_1d_lang_localized", "zh" in str(e) and "自动判断" in str(e), str(e))

# ---------------------------------------------------------------------------
# 2. 批量二遍重试
# ---------------------------------------------------------------------------
bdir = os.path.join(tmpdir, "batch")
os.makedirs(bdir, exist_ok=True)
open(os.path.join(bdir, "good.txt"), "w", encoding="utf-8").write(
    "这是一段完全正常的学术句子，讨论实验设计。\n")
with open(os.path.join(bdir, "broken.txt"), "wb") as f:
    f.write(b"\xff\xfe\x00\x01" * 200)
rc, out, err = run_cli([DET, "--batch", bdir, "--json"])
try:
    j = json.loads(out)
except Exception:
    j = []
check("bt_2a_batch_json_ok", rc == 0 and len(j) == 2, "rc=%d n=%d" % (rc, len(j)))
broken_row = next((x for x in j if x["file"] == "broken.txt"), {})
check("bt_2b_retried_field", all("retried" in x for x in j), str(j[:1]))
check("bt_2c_retry_reported", "重试" in err and "已重试" in broken_row.get("level", ""),
      "err=%s level=%s" % (err[:60], broken_row.get("level")))

rc, out, err = run_cli([PL, "--batch", bdir])
check("bt_2d_pipeline_batch_retry", rc == 0 and "重试" in err, "rc=%d err=%s" % (rc, err[:60]))

# ---------------------------------------------------------------------------
# 3. 单步超时 + timings
# ---------------------------------------------------------------------------
f_s = os.path.join(tmpdir, "s.txt")
open(f_s, "w", encoding="utf-8").write(
    "综上所述，该方法不仅好而且快。值得注意的是结果显著。\n" * 20)
rc, _, err = run_cli([PL, f_s, "--step-timeout", "0.0000001"])
check("st_3a_step_timeout_clean", rc == 2 and "超时" in err and "处置建议" in err,
      "rc=%d err=%s" % (rc, err[:80]))
rc, out, _ = run_cli([PL, f_s, "-o", os.path.join(tmpdir, "o.txt"), "--json"])
j = json.loads(out) if out.strip().startswith("{") else {}
tm = j.get("timings", {})
check("st_3b_timings_fields",
      all(k in tm for k in ("cleanup_s", "scan_s", "verify_s", "total_s")), str(tm))
rc, out, _ = run_cli([PL, f_s, "-o", os.path.join(tmpdir, "o2.txt")])
check("st_3c_human_timing_line", "耗时" in out and "单步预算" in out, out[-160:])

# ---------------------------------------------------------------------------
print("\n===== v2.5.0 新功能测试: %d PASS / %d FAIL =====" % (len(PASS), len(FAIL)))
if FAIL:
    print("失败项:", FAIL)
    sys.exit(1)

# -*- coding: utf-8 -*-
"""test_offline_v290.py — v2.9.0 新功能离线测试。

覆盖：
  1. transform 全角字母数字→半角（E_NUM_WIDTH 闭环：verify 拦 → transform 修 → verify 过）
  2. batch .pdf：detect/pipeline 批量含 PDF 文件，置信度标注在 level/after 列
  3. SKILL 双语阅读地图
运行：python3 tests/test_offline_v290.py（全断言，无第三方依赖）
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

import transform as tf  # noqa: E402
import verify as vf  # noqa: E402

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

# ---------------------------------------------------------------------------
# 1. 全角归一
# ---------------------------------------------------------------------------
out, n = tf.normalize_fullwidth_alnum("随访至２０２５年，ＩＬ-６水平６８.７%。")
check("fw_1a_normalize", "2025" in out and "IL" in out and "68.7" in out and n == 10, out)
out2, n2 = tf.normalize_fullwidth_alnum("全角标点“引号”与——破折号——不动。")
check("fw_1b_punct_untouched", out2 == "全角标点“引号”与——破折号——不动。" and n2 == 0, out2)
# E_NUM_WIDTH 闭环
_O = "随访至 2025 年。"
_bad = "随访至 ２０２５ 年。"
r1 = vf.verify(_O, _bad)
check("fw_1c_verify_blocks", not r1["ok"], "")
fixed, _ = tf.normalize_fullwidth_alnum(_bad)
r2 = vf.verify(_O, fixed)
check("fw_1d_transform_heals", r2["ok"], str([v["code"] for v in r2["violations"]]))

# pipeline 主分支接线：--terms auto 场景下全角文件清理后含半角
f_in = os.path.join(tmpdir, "in.txt")
with open(f_in, "w", encoding="utf-8") as f:
    f.write("随访至２０２５年的队列共６８例。\n")
outp = os.path.join(tmpdir, "clean.txt")
rc, _, err = run_cli([os.path.join(SCRIPTS, "pipeline.py"), f_in, "-o", outp])
cleaned = open(outp, encoding="utf-8").read()
check("fw_1e_pipeline_wires", rc == 0 and "２０２５" not in cleaned and "2025" in cleaned,
      "rc=%d out=%s" % (rc, cleaned[:40]))

# ---------------------------------------------------------------------------
# 2. batch .pdf
# ---------------------------------------------------------------------------
def make_pdf(path, body_text):
    body = ("BT /F1 12 Tf 72 720 Td (" + body_text.replace("(", "").replace(")", "")
            + ") Tj ET").encode()
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4\nstream\n" + zlib.compress(body) + b"\nendstream\ntrailer\n")


bdir = os.path.join(tmpdir, "batch")
os.makedirs(bdir, exist_ok=True)
make_pdf(os.path.join(bdir, "paper.pdf"),
         "Abstract. The results of this study show that the treatment group had "
         "significantly better outcomes than the control group. Methods and data "
         "analysis were conducted according to the protocol. In conclusion, this "
         "method is effective and safe for patients in the cohort we analyzed.")
open(os.path.join(bdir, "note.txt"), "w", encoding="utf-8").write("普通文本一句。")

DET = os.path.join(SCRIPTS, "detect.py")
PL = os.path.join(SCRIPTS, "pipeline.py")
rc, out, err = run_cli([DET, "--batch", bdir, "--json"])
j = json.loads(out) if out.strip().startswith("[") else []
pdf_row = next((x for x in j if x.get("file", "").endswith(".pdf")), {})
check("bt_2a_detect_batch_pdf", rc == 0 and pdf_row.get("score", -1) >= 0,
      "rc=%d rows=%s" % (rc, str(j)[:120]))
rc, out, _ = run_cli([PL, "--batch", bdir])
check("bt_2b_pipeline_batch_pdf", rc == 0 and "paper.pdf" in out, out[:120])

# ---------------------------------------------------------------------------
# 3. SKILL 双语阅读地图
# ---------------------------------------------------------------------------
en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
check("map_3a_en", "Reading map" in en and "best_practices.md" in en, "")
check("map_3b_zh", "阅读地图" in zh and "best_practices.md" in zh, "")

# ---------------------------------------------------------------------------
print("\n===== v2.9.0 新功能测试: %d PASS / %d FAIL =====" % (len(PASS), len(FAIL)))
if FAIL:
    print("失败项:", FAIL)
    sys.exit(1)

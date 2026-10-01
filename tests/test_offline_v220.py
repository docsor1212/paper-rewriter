# -*- coding: utf-8 -*-
"""test_offline_v220.py — v2.2.0 新功能离线测试。

覆盖：
  1. markdown 标题识别（## 摘要 / **方法**）与纯文本标题回归、内容句防误判
  2. 分块重叠缝合：跨块骑缝信号在 overlap>0 时被捕获、overlap=0 时漏检（增益对照）
  3. 分块总量守恒：小分块 + 重叠缝合的类别计数与整文扫描一致
  4. learn_guards：用户守卫合并进词库、命中被豁免、文件损坏降级
  5. plan.py：P0 队列排序、预算投影单调性、JSON 结构
  6. PDF 加固：无空格操作符、UTF-16BE 字符串、累计解压上限（合成 PDF）
运行：python3 tests/test_offline_v220.py（全断言，无第三方依赖）
"""

import json
import os
import subprocess
import sys
import tempfile
import zlib

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


# ---------------------------------------------------------------------------
# 1. markdown 标题
# ---------------------------------------------------------------------------
md = "# 论文\n\n## 摘要\n\n本文研究了 X。\n\n## 方法\n\n采用实验方法。\n\n**结论**\n\n结论如下。"
keys = [k for k, _, _ in hxt_core.detect_sections(md)]
check("md_heading_1", "abstract" in keys and "methods" in keys and "conclusion" in keys,
      str(keys))

plain = "标题\n\n摘要\n\n内容。\n\n2. 方法\n\n内容。\n\n3 结论\n\n完了。"
keys2 = [k for k, _, _ in hxt_core.detect_sections(plain)]
check("md_heading_2_plain_regression",
      "abstract" in keys2 and "methods" in keys2 and "conclusion" in keys2, str(keys2))

trap = ("# 笔记\n\n## 摘要：本文提出了一种全新的深度学习方法框架\n\n正文。\n\n"
        "**方法**学上存在争议。\n\nOK。")
keys3 = [k for k, _, _ in hxt_core.detect_sections(trap)]
check("md_heading_3_no_false_positive",
      "abstract" not in keys3 and "methods" not in keys3, str(keys3))

# ---------------------------------------------------------------------------
# 2/3. 分块重叠缝合（无换行语料 → 硬切点 = max_chars，骑缝探针精确定位）
# ---------------------------------------------------------------------------
filler = "这是一段正常的叙述文字，用于填充篇幅，不含任何模板腔特征。"
base = filler * 300                      # 全文无 \n → 切点硬切在 8000
MC, OV = 8000, 600
spans = hxt_core._chunk_spans(base, max_chars=MC, overlap=OV)
check("chunk_4a_hard_cut", spans[0][1] == MC and len(spans) >= 2, str(spans[:2]))
# 探针骑缝：「不仅」结束于切点，「好用，而且」在切点后（等长外插入，硬切点不动）
probe = "不仅好用，而且效果显著降低了计算成本，后续实验进一步验证了稳定性。"
text2 = base[:MC - 2] + probe + base[MC:]
r_ov = hxt_core.scan_chunked(text2, max_chars=MC, overlap=OV)
r_no = hxt_core.scan_chunked(text2, max_chars=MC, overlap=0)
n_ov = r_ov["categories"].get("zh_jargon_struct", {}).get("count", 0)
n_no = r_no["categories"].get("zh_jargon_struct", {}).get("count", 0)
check("chunk_4b_spanning_signal_stitched", n_ov >= 1,
      "骑缝探针（不仅…而且…）overlap=%d 未捕获" % OV)
check("chunk_4c_stitch_gain", n_ov > n_no,
      "缝合无增益：overlap=%d vs overlap0=%d" % (n_ov, n_no))

probe = "综上所述，本研究验证了假设，值得注意的是该方法具有良好的鲁棒性。\n\n"
text3 = filler * 100 + probe + filler * 50
r3 = hxt_core.scan_chunked(text3, max_chars=MC, overlap=OV)
r3w = hxt_core.scan(text3)
c1 = {k: c["count"] for k, c in r3["categories"].items() if c["count"]}
c2 = {k: c["count"] for k, c in r3w["categories"].items() if c["count"]}
check("chunk_5_conservation", c1 == c2, "分块 %s vs 整文 %s" % (c1, c2))
check("chunk_5b_burstiness_recovered",
      r3["stats"].get("burstiness_cv") is not None,
      "分块口径节奏统计未恢复")

# ---------------------------------------------------------------------------
# 4. learn_guards 守卫合并与豁免
# ---------------------------------------------------------------------------
tmpdir = tempfile.mkdtemp()
ug_path = os.path.join(SCRIPTS, "user_guards.json")
ug_backup = None
if os.path.exists(ug_path):
    with open(ug_path, encoding="utf-8") as f:
        ug_backup = f.read()
try:
    with open(ug_path, "w", encoding="utf-8") as f:
        json.dump({"_meta": {}, "term_guards": [
            {"term": "赋能", "allow_before": [],
             "allow_after": ["推进"], "lang": "zh"}]}, f, ensure_ascii=False)
    hxt_core.clear_pattern_cache()
    pats = hxt_core.load_patterns("zh")
    terms = [g.get("term") for g in pats["term_guards"]]
    check("guards_4a_merged", "赋能" in terms, str(terms[-3:]))

    # 赋能无内置守卫（纯机器腔），上下文「赋能推进」被用户守卫豁免
    r = hxt_core.scan("我们要以这个项目为赋能推进各项工作。")
    n_jargon = r["categories"].get("zh_jargon", {}).get("count", 0)
    check("guards_4b_exempt", n_jargon == 0,
          "用户守卫未豁免: zh_jargon=%d" % n_jargon)

    # 损坏文件降级：扫描不中断
    with open(ug_path, "w", encoding="utf-8") as f:
        f.write("{broken json!!")
    hxt_core.clear_pattern_cache()
    r = hxt_core.scan("本文提出了一个鲁棒的方法，值得注意的是结果显著。")
    check("guards_4c_corrupt_degrades", r["score"] >= 0)
finally:
    if ug_backup is not None:
        with open(ug_path, "w", encoding="utf-8") as f:
            f.write(ug_backup)
    else:
        if os.path.exists(ug_path):
            os.remove(ug_path)
    hxt_core.clear_pattern_cache()

# ---------------------------------------------------------------------------
# 5. plan.py CLI
# ---------------------------------------------------------------------------
sample = """# 医学综述

## 摘要

综上所述，本研究系统阐述了IRAK4信号通路的重要意义，值得注意的是，
该通路在先天免疫中发挥着至关重要的作用，为相关疾病的治疗提供了新的思路和方向。

## 引言

值得一提的是，随着测序技术的不断发展，越来越多的证据表明IRAK4与免疫缺陷密切相关。
此外，本文将从分子机制的角度进行深入的分析和探讨。

## 方法

检索PubMed与Web of Science数据库，筛选2020年至2026年间的英文文献。

## 结论

总之，IRAK4抑制剂的开发为患者带来了新的希望，不仅疗效显著，而且安全性良好。
"""
sfile = os.path.join(tmpdir, "sample.md")
with open(sfile, "w", encoding="utf-8") as f:
    f.write(sample)

env = dict(os.environ, PYTHONIOENCODING="utf-8")
p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "plan.py"), sfile,
                    "--json", "--top", "5"],
                   capture_output=True, text=True, encoding="utf-8", env=env)
check("plan_5a_json_ok", p.returncode == 0, p.stderr[:200])
try:
    pj = json.loads(p.stdout)
except Exception as e:
    pj = {}
    check("plan_5a_json_ok", False, str(e))
check("plan_5b_top_ranked",
      pj.get("top") and pj["top"][0]["pts"] >= pj["top"][-1]["pts"],
      str(pj.get("top", [])[:1]))
projs = pj.get("projections", [])
check("plan_5c_projection_monotonic",
      len(projs) >= 2 and all(projs[i]["projected_score"] >= projs[i + 1]["projected_score"]
                              for i in range(len(projs) - 1)),
      str([x["projected_score"] for x in projs]))
check("plan_5d_projection_not_above_cap",
      all(x["projected_score"] <= 100 for x in projs), "")
secs = [s["key"] for s in pj.get("meta", {}).get("sections", [])]
check("plan_5e_sections_md", "abstract" in secs and "methods" in secs, str(secs))

mdfile = os.path.join(tmpdir, "plan_out.md")
p2 = subprocess.run([sys.executable, os.path.join(SCRIPTS, "plan.py"), sfile,
                     "-o", mdfile], capture_output=True, text=True,
                    encoding="utf-8", env=env)
check("plan_5f_md_output", p2.returncode == 0 and os.path.exists(mdfile)
      and "P0 改写队列" in open(mdfile, encoding="utf-8").read(), p2.stderr[:200])

# ---------------------------------------------------------------------------
# 6. PDF 加固（合成 PDF）
# ---------------------------------------------------------------------------
def make_pdf(streams, literal=b"(Hello heavy AI vocabulary delve tapestry) Tj"):
    """streams: [(bytes, compress_bool)]；literal 为内容流模板"""
    body = b""
    for data, comp in streams:
        payload = zlib.compress(data) if comp else data
        body += b"stream\n" + payload + b"\nendstream\n"
    return b"%PDF-1.4\n" + body + b"trailer\n"


pdfdir = tempfile.mkdtemp()

# 6a. 无空格操作符 + UTF-16BE 字面串（BOM 在 ( ) 内）
content = (b"BT /F1 12 Tf 72 720 " + b"Td (No-space operators work)Tj T* ET\n"
           b"BT /F1 12 Tf 72 700 Td (\xfe\xff\x00H\x00i\x00 \x00U\x00T\x00F) Tj ET")
pdf1 = os.path.join(pdfdir, "a.pdf")
with open(pdf1, "wb") as f:
    f.write(b"%PDF-1.4\nstream\n" + zlib.compress(content) + b"\nendstream\ntrailer\n")
try:
    txt = hxt_core.read_text(pdf1)
    ok = "No-space operators work" in txt and "Hi UTF" in txt
    check("pdf_6a_nospace_utf16be", ok, repr(txt[:120]))
except ValueError as e:
    check("pdf_6a_nospace_utf16be", False, str(e))

# 6b. 累计解压上限：3 × ~18MB 解压流（单流 ≤20MB，合计 >50MB）→ 累计红线
big = b"(x) Tj\n" * (18 * 1024 * 1024 // 7)
pdf2 = os.path.join(pdfdir, "b.pdf")
with open(pdf2, "wb") as f:
    f.write(make_pdf([(big, True), (big, True), (big, True)]))
try:
    hxt_core._extract_pdf(pdf2)
    check("pdf_6b_cumulative_cap", False, "50MB 累计上限未触发")
except ValueError as e:
    check("pdf_6b_cumulative_cap", "50MB" in str(e), str(e))

# 6c. 回归：正常小 PDF 仍可读
pdf3 = os.path.join(pdfdir, "c.pdf")
with open(pdf3, "wb") as f:
    f.write(make_pdf([(b"BT /F1 12 Tf 72 720 Td (This paper presents a robust "
                       b"method that delves into the landscape of data.) Tj ET", True)]))
try:
    txt = hxt_core.read_text(pdf3)
    check("pdf_6c_regression", "delves" in txt, repr(txt[:100]))
except ValueError as e:
    check("pdf_6c_regression", False, str(e))

# ---------------------------------------------------------------------------
print("\n===== v2.2.0 新功能测试: %d PASS / %d FAIL ====="
      % (len(PASS), len(FAIL)))
if FAIL:
    print("失败项:", FAIL)
    sys.exit(1)

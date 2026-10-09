# -*- coding: utf-8 -*-
"""test_offline_v300.py — v3.0.0 新功能离线测试。

覆盖：
  1. 术语守卫域包：--list-packs / --pack 选域 / 域标签透出 / 嵌套安全校验
     （肝功⊂肝功能 存量嵌套对已移除）
  2. plan --handoff 深改交接块：markdown 与 JSON 双模式
  3. PDF 置信度：指标透出 / ToUnicode 封顶「中」/ 中文 CID 形态仍被探针拒收
  4. SKILL 双语 v3.0.0 状态锚 / 新 references / 功能状态 ⚠️ 醒目化 / displayName
运行：python3 tests/test_offline_v300.py（全断言，无第三方依赖）
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


def run_cli(args, cwd=ROOT):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable] + args, capture_output=True,
                       text=True, encoding="utf-8", cwd=cwd, env=env, timeout=60)
    return r


# ── 1. 术语守卫域包 ──────────────────────────────────────────
def test_term_packs():
    check("packs.嵌套安全: validate_packs 零违规", ct.validate_packs() == [],
          str(ct.validate_packs()))
    check("packs.肝功嵌套对已移除",
          ("肝功", "肝功能") not in ct._BUILTIN_PAIRS)
    # v3.1.0 起变体组制：兼容投影=每组前两变体，HF 三变体组投影后 28→27
    check("packs.兼容对数 27（v3.1.0 组制投影）", len(ct._BUILTIN_PAIRS) == 27,
          "got %d" % len(ct._BUILTIN_PAIRS))
    check("packs.八域齐全",
          set(ct._TERM_PACKS) == {"通用", "风湿免疫", "内分泌", "心血管",
                                  "肿瘤", "呼吸", "消化", "神经"})

    r = run_cli([os.path.join(SCRIPTS, "check_terms.py"), "--list-packs"])
    check("packs.--list-packs 退出 0 且列八域",
          r.returncode == 0 and "心血管" in r.stdout and "风湿免疫" in r.stdout,
          r.stdout[:80] + r.stderr[:80])

    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "t.md")
        open(f, "w", encoding="utf-8").write(
            "该患者（病人）确诊SLE（系统性红斑狼疮）。既往脑卒中（中风）病史。"
            "术后发生急性心肌梗死（AMI）。肿瘤组织 NSCLC（非小细胞肺癌）类型明确。")
        r = run_cli([os.path.join(SCRIPTS, "check_terms.py"), f, "--json"])
        d = json.loads(r.stdout)
        check("packs.默认全量含跨域命中",
              d["total"] >= 1 and all("pack" in x for x in d["inconsistencies"]),
              json.dumps(d, ensure_ascii=False)[:120])
        packs_seen = {x["pack"] for x in d["inconsistencies"]}
        check("packs.域标签正确（神经/风湿免疫/心血管/肿瘤）",
              {"神经", "风湿免疫", "心血管", "肿瘤"} <= packs_seen, str(packs_seen))

        r2 = run_cli([os.path.join(SCRIPTS, "check_terms.py"), f,
                      "--pack", "神经", "--json"])
        d2 = json.loads(r2.stdout)
        check("packs.--pack 选域非空", d2["total"] >= 1,
              json.dumps(d2, ensure_ascii=False)[:120])
        check("packs.--pack 选域只跑该域",
              all(x["pack"] == "神经" for x in d2["inconsistencies"]),
              json.dumps(d2, ensure_ascii=False)[:120])

        # --pack + --pairs：用户对与内置对重复时去重（不重复计行、不被误标内置域）
        pf = os.path.join(td, "u.txt")
        open(pf, "w", encoding="utf-8").write("脑卒中|中风\n Foo Bar | Baz Qux \n")
        r5 = run_cli([os.path.join(SCRIPTS, "check_terms.py"), f,
                      "--pack", "神经", "--pairs", pf, "--json"])
        d5 = json.loads(r5.stdout)
        rows_nm = [x for x in d5["inconsistencies"]
                   if {x["a"], x["b"]} == {"脑卒中", "中风"}]
        check("packs.用户对与内置对去重（不重复计行）", len(rows_nm) == 1,
              json.dumps(d5, ensure_ascii=False)[:160])
        check("packs.重复内置对不被标用户自定义",
              all(x["pack"] == "神经" for x in rows_nm))

        # 存量 bug 回归：只出现「肝功能」不报不一致（旧版肝功对会误计）
        f2 = os.path.join(td, "t2.md")
        open(f2, "w", encoding="utf-8").write("复查肝功能轻度异常。")
        r3 = run_cli([os.path.join(SCRIPTS, "check_terms.py"), f2, "--json"])
        d3 = json.loads(r3.stdout)
        check("packs.肝功能单出现不误报", d3["total"] == 0)

        r4 = run_cli([os.path.join(SCRIPTS, "check_terms.py"), f,
                      "--pack", "不存在的域"])
        check("packs.未知域报用法错误", r4.returncode == 2)


# ── 2. plan --handoff ────────────────────────────────────────
HANDOFF_TXT = ("众所周知，本研究采用回顾性设计。我们收集了2023年1月至2024年12月的"
               "患者数据。综上所述，该方法具有重要意义。In order to investigate "
               "the effect, we analyzed the data with care.\n")


def test_plan_handoff():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "d.md")
        open(f, "w", encoding="utf-8").write(HANDOFF_TXT)
        r = run_cli([os.path.join(SCRIPTS, "plan.py"), f, "--top", "5",
                     "--handoff"])
        check("handoff.markdown 含交接块标题", "深改交接块" in r.stdout)
        check("handoff.含守卫铁律行",
              "守卫铁律" in r.stdout and "DOI" in r.stdout)
        check("handoff.含逐句操作行", r.stdout.count("操作：") >= 2)
        check("handoff.含验收命令",
              "verify.py" in r.stdout and "stylecheck.py" in r.stdout)
        check("handoff.位于自检节之后",
              r.stdout.find("深改交接块") > r.stdout.find("改写后自检"))

        r2 = run_cli([os.path.join(SCRIPTS, "plan.py"), f, "--top", "5",
                      "--json", "--handoff"])
        d = json.loads(r2.stdout)
        h = d.get("handoff", "")
        check("handoff.JSON 键存在且含操作", "操作：" in h and "守卫铁律" in h)

        r3 = run_cli([os.path.join(SCRIPTS, "plan.py"), f, "--top", "5"])
        check("handoff.缺省旗标不产出交接块", "深改交接块" not in r3.stdout)


# ── 3. PDF 置信度 ────────────────────────────────────────────
def make_pdf(path, with_tounicode, sentence=None):
    sent = sentence or ("The treatment significantly reduced mortality in "
                        "patients with heart failure and improved quality of "
                        "life across all study groups over twelve months. ")
    txt = (sent * 3).encode("ascii")
    content = b"BT /F1 12 Tf (" + txt + b") Tj ET"
    stream = b"stream\r\n" + content + b"\nendstream"
    tu = b"/ToUnicode 5 0 R\n" if with_tounicode else b""
    head = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    head += b"4 0 obj<</Length %d>>\n" % len(stream) + stream + b"\nendobj\n"
    open(path, "wb").write(head + tu + b"trailer<</Root 1 0 R>>")


def test_pdf_confidence():
    check("pdf.__version__ >= 3.0.0",
          tuple(int(x) for x in hxt_core.__version__.split(".")) >= (3, 0, 0),
          hxt_core.__version__)
    with tempfile.TemporaryDirectory() as td:
        p1 = os.path.join(td, "en_plain.pdf")
        make_pdf(p1, with_tounicode=False)
        t, meta = hxt_core.read_text_ex(p1)
        check("pdf.纯净英文=高", meta["confidence"] == "高", str(meta))
        ind = meta.get("indicators") or {}
        check("pdf.指标四件套透出",
              set(ind) >= {"words", "probe_hit_rate", "ctrl_rate", "avg_word_len"},
              str(ind))

        p2 = os.path.join(td, "en_tu.pdf")
        make_pdf(p2, with_tounicode=True)
        t2, meta2 = hxt_core.read_text_ex(p2)
        check("pdf.ToUnicode 高封顶中", meta2["confidence"] == "中", str(meta2))
        check("pdf.封顶注记提示抽查",
              any("ToUnicode" in n or "抽查" in n for n in meta2.get("notes", [])),
              str(meta2.get("notes")))

        p3 = os.path.join(td, "cjk_soup.pdf")
        blob = bytes(range(1, 32)) * 40
        stream = b"stream\r\n" + zlib.compress(
            b"BT /F1 12 Tf (" + blob + b") Tj ET") + b"\nendstream"
        head = (b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\n"
                b"4 0 obj<</Length " + str(len(stream)).encode() + b">>\n"
                + stream + b"\nendobj\n")
        open(p3, "wb").write(head + b"trailer<</Root 1 0 R>>")
        try:
            hxt_core.read_text_ex(p3)
            check("pdf.控制字符汤仍被拒收", False, "竟然放行")
        except ValueError as e:
            check("pdf.控制字符汤仍被拒收", "控制字符" in str(e), str(e)[:60])

        p4 = os.path.join(td, "few.pdf")
        make_pdf(p4, with_tounicode=False, sentence="Short abstract only. ")
        t4, meta4 = hxt_core.read_text_ex(p4)
        check("pdf.词过少=低且 indicators 含 words",
              meta4["confidence"] == "低"
              and (meta4.get("indicators") or {}).get("words") is not None,
              str(meta4))

        # last_tounicode 复位方向：同进程先读 TU-PDF 再读普通 PDF，第二个必须回「高」
        t2b, meta2b = hxt_core.read_text_ex(p1)
        check("pdf.TU→普通 复位回高",
              meta2b["confidence"] == "高"
              and not any("ToUnicode" in n for n in meta2b.get("notes", [])),
              str(meta2b))

        # detect CLI 对 pdf 透出 pdf_meta.indicators
        r = run_cli([os.path.join(SCRIPTS, "detect.py"), p1, "--json"])
        d = json.loads(r.stdout)
        pm = d.get("pdf_meta") or {}
        check("pdf.detect --json 带 pdf_meta.indicators",
              "confidence" in pm and "indicators" in pm, str(pm)[:100])


# ── 4. SKILL 双语 / references / 合规 ─────────────────────────
def test_docs():
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    import re as _re
    check("docs.EN 版本锚 v3.x 在位",
          bool(_re.search(r"## Feature status \(v3\.\d+\.\d+\)", en)))
    check("docs.ZH 版本锚 v3.x 在位",
          bool(_re.search(r"功能状态（v3\.\d+\.\d+）", zh)))
    check("docs.新 references 存在且非空",
          os.path.getsize(os.path.join(ROOT, "references/pdf_confidence.md")) > 1000
          and os.path.getsize(os.path.join(ROOT, "references/deep_rewrite_guide.md")) > 1000)
    check("docs.校准文档含 200 篇实测口径",
          "200" in open(os.path.join(ROOT, "references/pdf_confidence.md"),
                        encoding="utf-8").read())
    check("docs.ZH 状态表 ⚠️ 醒目实验性行",
          "⚠️ **PDF 文本直读**" in zh and "⚠️ 实验性" in zh)
    check("docs.ZH 阅读地图挂两份新指南",
          "deep_rewrite_guide.md" in zh and "pdf_confidence.md" in zh)
    check("docs.EN 阅读地图挂两份新指南",
          "deep_rewrite_guide.md" in en and "pdf_confidence.md" in en)
    check("docs.ZH displayName 需求词改版",
          "displayName: 论文改写·降AI率去AI味｜学术表达优化" in zh)
    check("docs.ZH frontmatter desc 原样（语言铁律物料）",
          "论文降AI率、去AI味的风格自查与自然化改写工具" in zh)
    check("docs.ZH 工作流含 --handoff 与 --pack",
          "--handoff" in zh and "--pack" in zh)
    check("docs.EN 工作流含 handoff 与 pack",
          "--handoff" in en and "--pack" in en)
    # 合规红线：全文禁检测器品牌与规避表述
    blob = (en + zh).lower()
    for w in ("朱雀", "gptzero", "turnitin", "过ai检测", "降检测率", "去ai痕迹",
              "undetectable"):
        check("合规.禁词「%s」零命中" % w, w not in blob)


def main():
    test_term_packs()
    test_plan_handoff()
    test_pdf_confidence()
    test_docs()
    print("\n%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()

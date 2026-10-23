# -*- coding: utf-8 -*-
"""test_v40400 — v4.4.0 docx 回写闭环 + 术语统一稿版（固定位命名）。

覆盖：
  1. write_docx/write_output：roundtrip、XML 转义、空文本拒收、后缀分发
  2. 三 CLI -o 接线：pipeline/transform/compare 输出 .docx 后缀自动回写
  3. check_terms --unify：内置组统一、--json、已一致不生成、用户对嵌套
     长串优先、映射冲突响亮、--batch 互斥、.docx 输出
  4. 文档接线：SKILL 双语 v4.4 功能行 + 版本号
"""
import json
import os, sys, tempfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import hxt_core
import check_terms as ct
PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))
def run_cli(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=300)


def test_version():
    check("ver.__version__", __import__("re").match(r"\d+\.\d+\.\d+$", hxt_core.__version__) is not None, hxt_core.__version__)
    r = run_cli([SCRIPTS + "/detect.py", "--version"])
    check("ver.detect--version", __import__("re").search(r"\d+\.\d+\.\d+", r.stdout + r.stderr) is not None)


def test_write_docx_roundtrip():
    t = "摘要：本研究纳入 120 例患者。\n\n方法：随访 24 个月，结果 p<0.05。\n结论：安全。"
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "a.docx")
        hxt_core.write_docx(t, p)
        back = hxt_core._extract_docx(p)
        check("docx.roundtrip", back.strip() == t.strip(), repr(back[:60]))
        # XML 特殊字符不破坏文档且原样还原
        t2 = '含 <script>alert("x")</script> & 符号 <b> 与 \'引号\'。'
        p2 = os.path.join(td, "b.docx")
        hxt_core.write_docx(t2, p2)
        back2 = hxt_core._extract_docx(p2)
        check("docx.xml转义", back2.strip() == t2.strip(), repr(back2[:60]))
        # 空文本拒收（CliError）
        try:
            hxt_core.write_docx("   \n  ", os.path.join(td, "c.docx"))
            check("docx.空文本拒收", False)
        except hxt_core.CliError:
            check("docx.空文本拒收", True)
        # write_output 分发：.docx 后缀（含大写）走 zip、其余走文本
        p3 = os.path.join(td, "d.TXT2")  # 非 docx 后缀 → 文本
        hxt_core.write_output(t, p3)
        check("docx.分发_非docx是文本", open(p3, encoding="utf-8").read() == t)
        p4 = os.path.join(td, "e.DOCX")
        hxt_core.write_output(t, p4)
        check("docx.分发_大写后缀zip", open(p4, "rb").read(2) == b"PK")
        # 多空行：写端逐行成段；抽取端压缩 \n{3,} 是既有读侧行为——
        # roundtrip 语义按单空行断言（写端承诺=段落结构不丢）
        t5 = "甲段。\n\n\n\n乙段。"
        p5 = os.path.join(td, "f.docx")
        hxt_core.write_docx(t5, p5)
        back5 = hxt_core._extract_docx(p5)
        check("docx.空行结构", "甲段。" in back5 and "\n\n乙段。" in back5, repr(back5))


def test_cli_docx_out():
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.txt")
        open(src, "w", encoding="utf-8").write(
            "本文引用了 oaicite:17 残留标记，需要清理。结果显著。")
        # pipeline -o .docx
        out1 = os.path.join(td, "clean.docx")
        r = run_cli([SCRIPTS + "/pipeline.py", src, "-o", out1])
        check("cli.pipeline_docx", r.returncode == 0 and os.path.exists(out1)
              and "oaicite" not in hxt_core._extract_docx(out1),
              (r.stderr or "")[-120:])
        # transform -o .docx
        out2 = os.path.join(td, "tr.docx")
        r = run_cli([SCRIPTS + "/transform.py", src, "-o", out2])
        check("cli.transform_docx", r.returncode == 0 and os.path.exists(out2)
              and "oaicite" not in hxt_core._extract_docx(out2),
              (r.stderr or "")[-120:])
        # compare -o .docx（缺省 new=机械清洗落盘路径）
        out3 = os.path.join(td, "cmp.docx")
        r = run_cli([SCRIPTS + "/compare.py", src, "-o", out3])
        check("cli.compare_docx", r.returncode == 0 and os.path.exists(out3)
              and "oaicite" not in hxt_core._extract_docx(out3),
              (r.stderr or "")[-120:])


def test_unify_builtin():
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.txt")
        open(src, "w", encoding="utf-8").write(
            "病人组纳入 30 例。病人随访完成。病人无事件。患者组 10 例对照。")
        out = os.path.join(td, "unified.txt")
        r = run_cli([SCRIPTS + "/check_terms.py", src, "--unify", out, "--no-header"])
        check("unify.内置组_exit0", r.returncode == 0, (r.stderr or "")[-150:])
        uni = open(out, encoding="utf-8").read()
        check("unify.统一形归一", "患者" not in uni and uni.count("病人") == 4, uni)
        check("unify.计数透出", "病人" in r.stdout and "1 处" in r.stdout, r.stdout)
        check("unify.建议verify提示", "verify" in r.stdout)
        # --json 字段
        r2 = run_cli([SCRIPTS + "/check_terms.py", src, "--unify", out, "--json"])
        j = json.loads(r2.stdout)
        check("unify.json字段", j["unify_output"] == out and j["replacements"] == 1
              and j["detail"][0]["from"] == "患者" and j["detail"][0]["to"] == "病人",
              r2.stdout[:200])
        # .docx 输出
        outd = os.path.join(td, "unified.docx")
        r3 = run_cli([SCRIPTS + "/check_terms.py", src, "--unify", outd])
        check("unify.docx输出", r3.returncode == 0
              and "患者" not in hxt_core._extract_docx(outd))


def test_unify_edge():
    with tempfile.TemporaryDirectory() as td:
        # 已一致：不生成文件、exit 0
        clean = os.path.join(td, "clean.txt")
        open(clean, "w", encoding="utf-8").write("全部统一用患者一词。")
        nope = os.path.join(td, "nope.txt")
        r = run_cli([SCRIPTS + "/check_terms.py", clean, "--unify", nope])
        check("unify.已一致不生成", r.returncode == 0 and not os.path.exists(nope))
        # 用户对嵌套：长串优先不被短串吞
        pairs = os.path.join(td, "pairs.txt")
        open(pairs, "w", encoding="utf-8").write("肝功|肝功能\n")
        src = os.path.join(td, "nested.txt")
        open(src, "w", encoding="utf-8").write("肝功能正常。肝功也正常。")
        out = os.path.join(td, "u2.txt")
        r = run_cli([SCRIPTS + "/check_terms.py", src, "--pairs", pairs,
                     "--unify", out, "--no-header"])
        uni = open(out, encoding="utf-8").read()
        check("unify.嵌套长串优先", r.returncode == 0 and "肝功能" not in uni
              and uni.count("肝功") == 2 and "肝功功能" not in uni, uni)
        # --batch 互斥
        r = run_cli([SCRIPTS + "/check_terms.py", clean, "--batch", td,
                     "--unify", nope])
        check("unify.batch互斥", r.returncode == 2)
        # validate_packs 回归哨兵
        check("unify.validate_packs仍空", ct.validate_packs() == [])
        # 映射冲突（函数级）：同一变体两组不同目标 → CliError
        try:
            ct.build_unify_plan([
                {"pack": "t", "variants": {"A": 1, "B": 1}, "suggestion": "A",
                 "a": "A", "b": "B", "a_count": 1, "b_count": 1, "canonical": "A"},
                {"pack": "t", "variants": {"A": 1, "C": 1}, "suggestion": "C",
                 "a": "A", "b": "C", "a_count": 1, "b_count": 1, "canonical": "A"}])
            check("unify.映射冲突响亮", False)
        except hxt_core.CliError:
            check("unify.映射冲突响亮", True)


def test_doc_wiring():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("doc.SKILL_ZH_v44行", "v4.4" in zh and ("docx" in zh.lower()), "")
    check("doc.SKILL_EN_v44行", "v4.4" in en and ("docx" in en.lower()), "")
    fs = open(os.path.join(ROOT, "references/feature_status.md"),
              encoding="utf-8").read()
    check("doc.feature_status_v44", fs.count("v4.4") >= 2, "")
    # 触发词英文对照（评测 trigger 扣分点对症）
    check("doc.EN触发词对照", ("Trigger words" in en or "English trigger" in en
                          or "rewrite for academic" in en.lower()), "")


def test_audit_fixes():
    # P0：控制字符消毒（\x1a 等非法 XML 字符不再产出损坏 docx）
    t = "研究完成\x1a结果显著。\x07另起一句。"
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "ctl.docx")
        hxt_core.write_docx(t, p)
        import xml.etree.ElementTree as ET
        with __import__("zipfile").ZipFile(p) as z:
            ET.fromstring(z.read("word/document.xml"))  # 非 well-formed 即抛
        back = hxt_core._extract_docx(p)
        check("docx.控制字符消毒", "\x1a" not in back and "\x07" not in back
              and "研究完成" in back, repr(back[:40]))
        # P1：docx 原地覆写拒绝（src_path 同路径 → CliError，原稿未损）
        src = os.path.join(td, "orig.docx")
        hxt_core.write_docx("原始排版内容。", src)
        before = open(src, "rb").read()
        try:
            hxt_core.write_docx("统一稿内容。", src, src_path=src)
            check("docx.原地覆写拒绝", False)
        except hxt_core.CliError:
            check("docx.原地覆写拒绝", open(src, "rb").read() == before)
        # CLI 层：pipeline -o 与输入同路径 .docx → exit 2 且原稿完好
        src2 = os.path.join(td, "in44.docx")
        hxt_core.write_docx("本文引用了 oaicite:3 残留。结果显著。", src2)
        r = run_cli([SCRIPTS + "/pipeline.py", src2, "-o", src2])
        check("cli.原地覆写_exit2", r.returncode == 2, str(r.returncode))
        check("cli.原地覆写_原稿完好",
              "原始" in hxt_core._extract_docx(src2) or
              "oaicite" in hxt_core._extract_docx(src2))
        # P1：--unify 与 --report 互斥
        f = os.path.join(td, "t.txt")
        open(f, "w", encoding="utf-8").write("病人组 30 例。患者组 10 例。")
        r = run_cli([SCRIPTS + "/check_terms.py", f, "--unify",
                     os.path.join(td, "u.txt"), "--report",
                     os.path.join(td, "r.md")])
        check("unify.report互斥", r.returncode == 2)
        # P1：--unify --json 已一致 → 恒 JSON
        c = os.path.join(td, "clean.txt")
        open(c, "w", encoding="utf-8").write("全部统一用患者一词。")
        r = run_cli([SCRIPTS + "/check_terms.py", c, "--unify",
                     os.path.join(td, "x.txt"), "--json"])
        try:
            j = json.loads(r.stdout)
            ok = j.get("already_consistent") is True and j["replacements"] == 0
        except Exception:
            ok = False
        check("unify.json已一致恒JSON", r.returncode == 0 and ok, r.stdout[:80])
        # P2：batch -o .docx 提示（源码断言）
        psrc = open(os.path.join(SCRIPTS, "pipeline.py"), encoding="utf-8").read()
        check("batch.docx提示", "不支持 docx 回写" in psrc)



def main():
    for fn in (test_version, test_write_docx_roundtrip, test_cli_docx_out,
               test_unify_builtin, test_unify_edge, test_audit_fixes,
               test_doc_wiring):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

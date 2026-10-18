# -*- coding: utf-8 -*-
"""test_v30700 — v3.7.0 批量断点续传版（固定位命名）。

覆盖：
  1. 批量断点续传：pipeline/detect 状态落盘、--resume 跳过、变更重跑、
     空状态回退、跨 CLI kind 隔离（schema 污染防线）
  2. check_terms --batch：跨文件变体漂移检出/JSON 口径/互斥/报告落盘
  3. 报错人话化：NUL/GBK/PDF 门闸新文案（保留「低于门闸」测试锚）
  4. 文档接线：SKILL 功能状态行/permissions 写点/faq/errors/pitfalls/examples/INDEX
"""
import json
import os, sys, tempfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import hxt_core
PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))
def run_cli(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=180)

TXT = ("首先，本研究旨在探讨问题。此外，数据显示结果显著。"
       "综上所述，本文提出了方法。结果表明该方案有效。\n")


def make_batch_dir(td, n=3, body=TXT):
    for i in range(1, n + 1):
        open(os.path.join(td, "doc%d.txt" % i), "w", encoding="utf-8").write(body)
    return td


def test_pipeline_resume():
    with tempfile.TemporaryDirectory() as td:
        make_batch_dir(td)
        r = run_cli([os.path.join(SCRIPTS, "pipeline.py"), "--batch", td])
        check("pipeline.batch 首跑成功", r.returncode == 0, r.stderr[-120:])
        st = os.path.join(td, ".pr_batch_state.json")
        check("pipeline.batch 状态文件落盘", os.path.isfile(st))
        rec = json.load(open(st, encoding="utf-8"))["kinds"]["pipeline"]["files"]
        check("pipeline.batch 记录带 kind=pipeline",
              rec and all("tool" in v and v.get("status") == "done"
                          for v in rec.values()))
        # resume：全部命中 → 有续传提示且结果一致
        r2 = run_cli([os.path.join(SCRIPTS, "pipeline.py"), "--batch", td, "--resume"])
        check("pipeline.resume 跳过提示", "跳过 3 个已完成文件" in r2.stderr, r2.stderr[-120:])
        check("pipeline.resume 结果行完整", r2.stdout.count(",PASS,") == 3)
        # 变更一个文件 → 该文件重跑（分数变化），其余跳过
        open(os.path.join(td, "doc2.txt"), "w", encoding="utf-8").write("正常句子，没有八股开场。语言平实自然。\n")
        r3 = run_cli([os.path.join(SCRIPTS, "pipeline.py"), "--batch", td, "--resume"])
        check("pipeline.resume 变更重跑提示", "跳过 2 个已完成文件" in r3.stderr, r3.stderr[-120:])
        check("pipeline.resume 变更行反映新内容", "doc2.txt,0[低]" in r3.stdout, r3.stdout[:200])


def test_detect_resume_and_kind_isolation():
    with tempfile.TemporaryDirectory() as td:
        make_batch_dir(td)
        r = run_cli([os.path.join(SCRIPTS, "detect.py"), "--batch", td, "--json"])
        check("detect.batch 首跑成功", r.returncode == 0, r.stderr[-120:])
        d0 = json.loads(r.stdout)
        check("detect.batch score 为 int", all(isinstance(x["score"], int) for x in d0))
        # 跨 CLI 隔离：detect 的进度对 pipeline 不可见（kind 隔离）——
        # pipeline --resume 不得出现「跳过」提示（否则=消费了 detect 的行，schema 污染）
        r2 = run_cli([os.path.join(SCRIPTS, "pipeline.py"), "--batch", td, "--resume"])
        check("kind 隔离：pipeline 不消费 detect 进度", "跳过" not in r2.stderr, r2.stderr[-160:])
        # detect 自己 resume：跳 3 且 int schema 保持
        r3 = run_cli([os.path.join(SCRIPTS, "detect.py"), "--batch", td, "--resume", "--json"])
        check("detect.resume 跳过提示", "跳过 3 个已完成文件" in r3.stderr, r3.stderr[-160:])
        d3 = json.loads(r3.stdout)
        check("detect.resume int schema 保持",
              all(isinstance(x["score"], int) for x in d3), str(d3)[:120])
        # 状态文件损坏 → 回退空状态不炸
        open(os.path.join(td, ".pr_batch_state.json"), "w", encoding="utf-8").write("{broken")
        r4 = run_cli([os.path.join(SCRIPTS, "detect.py"), "--batch", td, "--resume"])
        check("detect.resume 损坏状态回退", r4.returncode == 0 and "跳过" not in r4.stderr,
              r4.stderr[-120:])
        # 非法状态（别的 kind 分区的记录）→ 不复用，且不破坏他分区
        json.dump({"kinds": {"别的": {"files": {"doc1.txt": {
            "status": "done", "fp": [1, 1],
            "row": ["doc1.txt", 0, "低", False, "-"]}}}}},
            open(os.path.join(td, ".pr_batch_state.json"), "w", encoding="utf-8"))
        r5 = run_cli([os.path.join(SCRIPTS, "detect.py"), "--batch", td, "--resume"])
        check("detect.resume kind 不符不复用", "跳过" not in r5.stderr, r5.stderr[-120:])


def test_check_terms_batch():
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "摘要.txt"), "w", encoding="utf-8").write("患者入院。患者接受评估，患者好转。\n")
        open(os.path.join(td, "讨论.txt"), "w", encoding="utf-8").write("病人入院。病人接受随访。\n")
        ct = os.path.join(SCRIPTS, "check_terms.py")
        r = run_cli([ct, "--batch", td])
        check("ct.batch 漂移检出", r.returncode == 1 and "跨文件变体漂移" in r.stdout,
              (r.stdout + r.stderr)[:160])
        check("ct.batch 建议=全局多数变体", "建议「患者」" in r.stdout)
        r2 = run_cli([ct, "--batch", td, "--json"])
        check("ct.batch JSON 恒 0 口径", r2.returncode == 0)
        d = json.loads(r2.stdout)
        check("ct.batch JSON 结构", d["files"] == 2 and d["total"] >= 1
              and d["cross_file_drift"][0]["files"]["讨论.txt"] == "病人")
        rep = os.path.join(tempfile.gettempdir(), "ct_rep_test.md")
        r3 = run_cli([ct, "--batch", td, "--report", rep])
        check("ct.batch 报告落盘含漂移节",
              os.path.isfile(rep) and "跨文件变体漂移" in open(rep, encoding="utf-8").read())
        # 一致 → exit 0
        open(os.path.join(td, "讨论.txt"), "w", encoding="utf-8").write("患者随访。患者满意。\n")
        r4 = run_cli([ct, "--batch", td])
        check("ct.batch 一致 exit 0", r4.returncode == 0, r4.stdout[:120])
        # 互斥
        r5 = run_cli([ct, os.path.join(td, "摘要.txt"), "--batch", td])
        check("ct.batch 与单文件互斥", r5.returncode == 2 and "互斥" in (r5.stdout + r5.stderr))
        # 全部文件读取失败 → exit 2（fail-closed，不得伪装「一致」）
        with tempfile.TemporaryDirectory() as td2:
            open(os.path.join(td2, "x.txt"), "wb").write(b"bad\x00file")
            r6 = run_cli([ct, "--batch", td2])
            check("ct.batch 全失败 fail-closed", r6.returncode == 2
                  and "全部读取失败" in (r6.stdout + r6.stderr),
                  (r6.stdout + r6.stderr)[:120])


def test_error_humanize():
    with tempfile.TemporaryDirectory() as td:
        # NUL 文件 → 新文案（含处置；不再裸奔 NUL 术语）
        f = os.path.join(td, "bin.txt")
        open(f, "wb").write(b"abc\x00def")
        r = run_cli([os.path.join(SCRIPTS, "detect.py"), f])
        blob = r.stdout + r.stderr
        check("humanize.二进制文案", "疑似二进制或损坏文件" in blob and ".docx" in blob, blob[:160])
        check("humanize.二进制不带 NUL 术语", "NUL" not in blob)
        # GBK → v4.0.0 编码自适应：透明转码成功（旧行为=拒收文案）
        g = os.path.join(td, "gbk.txt")
        open(g, "wb").write("患者，男，六十五岁。".encode("gbk") * 40)
        r2 = run_cli([os.path.join(SCRIPTS, "detect.py"), g])
        blob2 = r2.stdout + r2.stderr
        check("humanize.GBK 转码", r2.returncode == 0
              and "已自动转码" in blob2, blob2[:160])
        # 彻底不可识别编码 → 拒收+可识别清单文案
        g2 = os.path.join(td, "junk.txt")
        open(g2, "wb").write("正常文本。".encode("utf-8") + b"\xff" * 40)
        r2b = run_cli([os.path.join(SCRIPTS, "detect.py"), g2])
        blob2b = r2b.stdout + r2b.stderr
        check("humanize.不可识别文案", r2b.returncode == 2
              and "可识别文本编码" in blob2b and "另存为" in blob2b, blob2b[:160])
        # PDF 门闸：单元断言（含 v330 测试锚「低于门闸」+ 新增人话成分）
        e = hxt_core.pdf_gate_error("低", "中", notes=["控制字符率高"])
        s = str(e)
        check("humanize.pdf 门闸文案", "低于门闸" in s and "已拒收" in s
              and "--pdf-min-confidence" in s and "检测注记" in s, s[:160])
        # 源码不再有内联旧短文案（收拢单点）
        for cli in ("detect.py", "pipeline.py"):
            src = open(os.path.join(SCRIPTS, cli), encoding="utf-8").read()
            check("humanize.%s 门闸收拢" % cli,
                  "pdf_gate_error" in src and "低于门闸 --pdf-min-confidence" not in src)


def test_evaluator_auditor_fixes():
    # 评测员 P0：pipeline --deep 的操作必须进 --track（原记账错置 else 分支）
    with tempfile.TemporaryDirectory() as td:
        d = os.path.join(td, "d.txt")
        open(d, "w", encoding="utf-8").write(
            "众所周知，该方法具有重要意义。此外，实验数据支持这一结论。\n"
            "综上所述，本研究提出了有效方案。结果表明方案可行。\n")
        base = os.path.join(td, "base")
        r = run_cli([os.path.join(SCRIPTS, "pipeline.py"), d, "-o",
                     os.path.join(td, "out.txt"), "--deep", "--track", base])
        md = open(base + ".md", encoding="utf-8").read()
        check("fix.deep 记账进 --track（P0 回归）",
              r.returncode == 0 and "深改档" in md and "无修改记录" not in md,
              (r.stderr[-100:] + md[:100]))
    # 审计员 P1：指纹 mtime_ns（同秒窗口关闭）
    fp = hxt_core.batch_state_fingerprint
    check("fix.指纹纳秒粒度", len(fp(__file__)) == 2 and isinstance(fp(__file__)[1], int)
          and fp(__file__)[1] > 10**15, str(fp(__file__)))
    # 审计员 P1：check_terms --batch 部分失败且幸存零发现 → exit 1（防假 clean）
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "good.txt"), "w", encoding="utf-8").write("患者入院。患者出院。\n")
        open(os.path.join(td, "bad.txt"), "wb").write(b"bad\x00file")
        r = run_cli([os.path.join(SCRIPTS, "check_terms.py"), "--batch", td])
        check("fix.ct 部分失败不判一致", r.returncode == 1
              and "暂不判定" in (r.stdout + r.stderr), (r.stdout + r.stderr)[:150])
    # 评测员 P2-11：--resume 单用提示
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "x.txt")
        open(f, "w", encoding="utf-8").write("正常句子。")
        r = run_cli([os.path.join(SCRIPTS, "detect.py"), f, "--resume"])
        check("fix.resume 单用提示", r.returncode == 0
              and "仅在 --batch 下生效" in r.stderr, r.stderr[-100:])
    # 评测员 P2-4：pdf_gate_error docstring 4 处口径
    src = open(os.path.join(SCRIPTS, "hxt_core.py"), encoding="utf-8").read()
    check("fix.门闸收拢口径=4 处", "4 处调用点" in src and "6 处调用点" not in src)
    # 评测员 P2-6：批量错误行不再 60 字截断（人话化处置段保留）
    d2 = open(os.path.join(SCRIPTS, "detect.py"), encoding="utf-8").read()
    p2 = open(os.path.join(SCRIPTS, "pipeline.py"), encoding="utf-8").read()
    check("fix.批量错误行 200 字", "str(e)[:200]" in d2 and "str(e)[:200]" in p2)


def test_docs_wiring():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    perm = open(os.path.join(ROOT, "references", "permissions.md"), encoding="utf-8").read()
    faq = open(os.path.join(ROOT, "references", "faq.md"), encoding="utf-8").read()
    errs = open(os.path.join(ROOT, "references", "errors.md"), encoding="utf-8").read()
    pits = open(os.path.join(ROOT, "references", "pitfalls.md"), encoding="utf-8").read()
    ex = open(os.path.join(ROOT, "references", "examples.md"), encoding="utf-8").read()
    idx = open(os.path.join(ROOT, "references", "INDEX.md"), encoding="utf-8").read()
    # 版本锚用正则（v3.8.0 机制化：版本前缀随 bump 漂移，行内容才是稳定契约）
    import re as _re
    check("docs.SKILL_ZH 功能状态行", bool(_re.search(r"功能状态（v\d+\.\d+\.\d+）", zh))
          and "批量断点续传" in zh and "跨文件术语漂移" in zh)
    check("docs.SKILL_EN 功能状态行", bool(_re.search(r"Feature status \(v\d+\.\d+\.\d+\)", en))
          and "Batch resume" in en and "cross-file term drift" in en)
    check("docs.permissions 写点核对", ".pr_batch_state.json" in perm
          and "--resume" in perm and "原子替换" in perm)
    check("docs.faq 新 Q 覆盖", "Q11：术语前后不统一" in faq and "Q12：批量跑了一半中断" in faq
          and "Q15：PDF 直读的「置信度」" in faq)
    check("docs.errors 续传段", "批量断点续传（v3.7.0）" in errs and "kind 分区制" in errs)
    check("docs.pitfalls 26 条", "| 26 |" in pits and "交叉 `--resume`" in pits)
    check("docs.examples 新样例", "--resume" in ex and "跨文件术语漂移" in ex)
    check("docs.INDEX 路由行", "--batch 目录 --resume" in idx and "跨文件漂移" in idx)


def main():
    test_pipeline_resume()
    test_detect_resume_and_kind_isolation()
    test_check_terms_batch()
    test_error_humanize()
    test_evaluator_auditor_fixes()
    test_docs_wiring()
    print("\n%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        sys.exit(1)
    print("OK")

if __name__ == "__main__":
    main()

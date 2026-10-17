# -*- coding: utf-8 -*-
"""test_v30800 — v3.8.0 PDF 缺省安全门+批量熔断+深改交接块版（固定位命名）。

覆盖：
  1. PDF 缺省门=中（乱码形态默认拒收；--pdf-min-confidence 低 恢复旧标注）
  2. 批量熔断（同批 ≥3 PDF 被拒→批级警告；拒收=确定性失败不进重试队列）
  3. pipeline --handoff（人读/JSON 双口径；JSON stdout 不被污染）
  4. build_queue 复用核心（plan.build_queue 与 plan --json top 一致）
  5. 文档接线（SKILL 双语功能状态/faq Q15 默认/errors 熔断行/examples/api）
"""
import importlib.util
import json
import os, sys, tempfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import hxt_core
import plan as _plan
PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))
def run_cli(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=180)

_ns = {"__file__": os.path.abspath(os.path.join(HERE, "test_offline_v330.py"))}
_src = open(os.path.join(HERE, "test_offline_v330.py"), encoding="utf-8").read()
exec(compile(_src.split("def test_pdf_gate")[0], "t330head", "exec"), _ns)
make_pdf = _ns["make_pdf"]

TXT = ("众所周知，本研究具有重要意义。此外，数据表明结果显著。"
       "综上所述，本文提出了方法。研究结果证明了方案的有效性。\n")


def test_default_gate():
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "low.pdf")
        make_pdf(p, "Short abstract only. ")
        r = run_cli([os.path.join(SCRIPTS, "detect.py"), p])
        check("gate.缺省=中 拒收", r.returncode == 2
              and "低于门闸" in (r.stdout + r.stderr), (r.stdout + r.stderr)[:120])
        r2 = run_cli([os.path.join(SCRIPTS, "pipeline.py"), p,
                      "-o", os.path.join(td, "o.txt")])
        check("gate.pipeline 缺省=中 拒收", r2.returncode == 2
              and "低于门闸" in (r2.stdout + r2.stderr), (r2.stdout + r2.stderr)[:120])
        r3 = run_cli([os.path.join(SCRIPTS, "detect.py"), p, "--pdf-min-confidence", "低"])
        check("gate.低门恢复只标注", r3.returncode == 0
              and "置信度" in r3.stdout, r3.stdout[:100])
    # PdfGateRejected 是 ValueError 子类（存量 except 兼容）
    e = hxt_core.pdf_gate_error("低", "中")
    check("gate.PdfGateRejected 兼容 ValueError",
          isinstance(e, hxt_core.PdfGateRejected) and isinstance(e, ValueError))


def test_batch_breaker():
    with tempfile.TemporaryDirectory() as td:
        for i in range(3):
            make_pdf(os.path.join(td, "bad%d.pdf" % i), "Short abstract only. ")
        open(os.path.join(td, "ok.txt"), "w", encoding="utf-8").write(TXT)
        r = run_cli([os.path.join(SCRIPTS, "detect.py"), "--batch", td])
        blob = r.stdout + r.stderr
        check("breaker.detect 批级警告", "熔断" in blob and "源头质量" in blob, blob[-200:])
        check("breaker.拒收 3 行终态", blob.count("低于门闸") == 3)
        check("breaker.拒收不进重试队列", "错误（待重试）" not in blob
              and "二遍" not in r.stderr)
        r2 = run_cli([os.path.join(SCRIPTS, "pipeline.py"), "--batch", td])
        check("breaker.pipeline 批级警告",
              "熔断" in (r2.stdout + r2.stderr), (r2.stdout + r2.stderr)[-200:])
        # 低门不熔断（全部标注通过）
        r3 = run_cli([os.path.join(SCRIPTS, "detect.py"), "--batch", td,
                      "--pdf-min-confidence", "低"])
        check("breaker.低门不熔断", "熔断" not in (r3.stdout + r3.stderr)
              and r3.returncode == 0, (r3.stdout + r3.stderr)[-150:])


def test_handoff():
    with tempfile.TemporaryDirectory() as td:
        d = os.path.join(td, "d.txt")
        open(d, "w", encoding="utf-8").write(TXT)
        hp = os.path.join(td, "handoff.md")
        r = run_cli([os.path.join(SCRIPTS, "pipeline.py"), d, "-o",
                     os.path.join(td, "out.txt"), "--handoff", hp])
        md = open(hp, encoding="utf-8").read()
        check("handoff.人读口径生成", r.returncode == 0 and os.path.isfile(hp)
              and "深改交接块" in md and "操作：" in md, r.stderr[-120:])
        # JSON 模式：stdout 仍可解析（提示走 stderr）
        hp2 = os.path.join(td, "handoff2.md")
        r2 = run_cli([os.path.join(SCRIPTS, "pipeline.py"), d, "-o",
                      os.path.join(td, "out2.txt"), "--handoff", hp2, "--json"])
        try:
            json.loads(r2.stdout)
            ok = True
        except ValueError:
            ok = False
        check("handoff.JSON stdout 不污染", ok and "交接块" in r2.stderr, r2.stdout[:80])
        # build_queue 与 plan --json top 一致
        text = open(d, encoding="utf-8").read()
        top, secs, full = _plan.build_queue(text)
        r3 = run_cli([os.path.join(SCRIPTS, "plan.py"), d, "--json", "--handoff"])
        d3 = json.loads(r3.stdout)
        check("handoff.build_queue 与 plan 一致",
              len(top) == len(d3["top"]) and [x["sent"] for x in top] ==
              [x["excerpt"].rstrip("…") for x in d3["top"]],
              str([x["sent"] for x in top])[:100])
        # 超长守卫
        try:
            _plan.build_queue("字" * (_plan.MAX_PLAN_CHARS + 1))
            ok = False
        except ValueError:
            ok = True
        check("handoff.超长守卫", ok)


def test_docs():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    faq = open(os.path.join(ROOT, "references", "faq.md"), encoding="utf-8").read()
    errs = open(os.path.join(ROOT, "references", "errors.md"), encoding="utf-8").read()
    ex = open(os.path.join(ROOT, "references", "examples.md"), encoding="utf-8").read()
    api = open(os.path.join(ROOT, "references", "api.md"), encoding="utf-8").read()
    import re as _re
    check("docs.ZH 功能状态行", bool(_re.search(r"功能状态（v3\.\d+\.\d+）", zh))
          and "缺省门=中" in zh and "批量熔断" in zh and "pipeline --handoff" in zh)
    check("docs.EN 功能状态行", bool(_re.search(r"Feature status \(v3\.\d+\.\d+\)", en))
          and "default gate = 中" in en and "batch circuit-breaker" in en)
    check("docs.触发收拢", "场景直达" in zh and "翻译腔清理（=欧化句式" in zh
          and "translationese cleanup" in en)
    check("docs.faq Q15 缺省门", "v3.8.0 起缺省安全门=中" in faq and "熔断" in faq)
    check("docs.errors 门闸行", "v3.8.0 起缺省门=中" in errs and "批级熔断警告" in errs)
    check("docs.examples handoff", "--handoff 交接块.md" in ex)
    check("docs.api build_queue", "plan.build_queue" in api)


def main():
    test_default_gate()
    test_batch_breaker()
    test_handoff()
    test_docs()
    print("\n%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        sys.exit(1)
    print("OK")

if __name__ == "__main__":
    main()

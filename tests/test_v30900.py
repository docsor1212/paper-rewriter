# -*- coding: utf-8 -*-
"""test_v30900 — v3.9.0 分块降级+verify 处方版（固定位命名）。

覆盖：
  1. 分块降级：部分降级（mock 不可恢复块）带 degraded_chunks+覆盖率注记；
     全块失败 degrade 两种模式均响亮失败；degrade=False 兼容旧契约
  2. 双 CLI 降级接线：pipeline exit_verdict fail-closed（exit 2）+stderr 提示；
     detect 单文件 JSON degraded 字段
  3. verify 处方化：违规→怎么修+原句锚点（去重）；JSON remedies 字段；
     修复三步输出
  4. 文档接线：SKILL 双语 v3.9.0 行/errors 降级节/faq Q16b/examples/api/pitfalls 27
"""
import json
import os, sys, tempfile, subprocess
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import hxt_core
import verify as vf
PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))
def run_cli(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=300)

BODY = "这是一段正常文本，用来撑体量。" * 60000  # 90 万字符 > 80 万分块阈值


def test_engine_degrade():
    # 全块失败：degrade=True 响亮失败（部分覆盖语义不成立）
    try:
        hxt_core.scan_chunked(BODY, time_budget=0.001, degrade=True)
        ok = False
    except ValueError as e:
        ok = "全部分块" in str(e)
    check("engine.全块失败响亮", ok)
    # degrade=False 兼容旧契约
    try:
        hxt_core.scan_chunked(BODY, time_budget=0.001, degrade=False)
        ok = False
    except ValueError as e:
        ok = "扫描超时" in str(e)
    check("engine.degrade=False 旧契约", ok)
    # 部分降级：首块（含重试）不可恢复 → 标记继续，出报告+覆盖率注记
    real_scan = hxt_core.scan
    calls = {"n": 0}
    def flaky(segment, **kw):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise ValueError("扫描超时（模拟）")
        return real_scan(segment, **kw)
    with mock.patch.object(hxt_core, "scan", flaky):
        r = hxt_core.scan_chunked(BODY, time_budget=5, degrade=True)
    check("engine.部分降级标记", len(r["degraded_chunks"]) == 1
          and r["degraded_chunks"][0]["retried"] is True
          and r["degraded_chunks"][0]["chars"] == 800000, str(r["degraded_chunks"]))
    blob = "".join(r["stats"]["notes"])
    check("engine.覆盖率注记", "降级" in blob and "覆盖" in blob)
    check("engine.降级仍出报告", r["score"] >= 0 and r["chunked"] >= 2)


def test_cli_wiring():
    with tempfile.TemporaryDirectory() as td:
        big = os.path.join(td, "big.txt")
        open(big, "w", encoding="utf-8").write(BODY)
        p = run_cli([os.path.join(SCRIPTS, "pipeline.py"), big, "-o",
                     os.path.join(td, "o.txt"), "--step-timeout", "0.001",
                     "--json", "--exit-verdict"])
        check("cli.pipeline 全块失败 exit 2+拆分建议",
              p.returncode == 2 and "拆分" in p.stderr, p.stderr[:150])
        # verify 处方化（小文本即可）
        d = os.path.join(td, "d.txt")
        open(d, "w", encoding="utf-8").write("研究纳入 120 例患者，随访 24 个月。结果显著。\n")
        d2 = os.path.join(td, "d2.txt")
        open(d2, "w", encoding="utf-8").write("研究纳入约百余名患者，长期随访。结果显著。\n")
        r = run_cli([os.path.join(SCRIPTS, "verify.py"), d, d2])
        blob = r.stdout + r.stderr
        check("cli.verify 处方行", "怎么修" in blob and "原句锚点" in blob
              and "修复三步" in blob, blob[:200])
        check("cli.verify 锚点去重", blob.count("研究纳入 120 例患者") == 1, blob[:300])
        r2 = run_cli([os.path.join(SCRIPTS, "verify.py"), d, d2, "--json"])
        try:
            j = json.loads(r2.stdout)
            ok = any(x.get("check") == "numbers" and x.get("context") for x in j["remedies"])
        except Exception:
            ok = False
        check("cli.verify JSON remedies", ok, r2.stdout[:150])


def test_docs():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    errs = open(os.path.join(ROOT, "references", "errors.md"), encoding="utf-8").read()
    faq = open(os.path.join(ROOT, "references", "faq.md"), encoding="utf-8").read()
    ex = open(os.path.join(ROOT, "references", "examples.md"), encoding="utf-8").read()
    api = open(os.path.join(ROOT, "references", "api.md"), encoding="utf-8").read()
    pits = open(os.path.join(ROOT, "references", "pitfalls.md"), encoding="utf-8").read()
    check("docs.ZH v3.9.0 行", "功能状态（v3.9.0）" in zh
          and "分块扫描降级" in zh and "verify 处方化输出" in zh)
    check("docs.EN v3.9.0 行", "Feature status (v3.9.0)" in en
          and "Chunk-scan degradation" in en and "verify prescription" in en)
    check("docs.errors 降级节", "分块扫描降级（v3.9.0）" in errs and "remedies" in errs)
    check("docs.faq Q16b", "Q16b：超大规模文件扫描超时" in faq and "degraded_chunks" in faq)
    check("docs.examples", "怎么修" in ex and "degraded_chunks" in ex)
    check("docs.api", "scan_chunked(..., degrade=True)" in api
          and "build_remedies" in api)
    check("docs.pitfalls 27 条", "| 27 |" in pits and "27 条" not in "" )
    check("docs.计数 27", "（27 条）" in zh and "(27 items)" in en and "27 条集中式" in faq)


def main():
    test_engine_degrade()
    test_cli_wiring()
    test_docs()
    print("\n%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        sys.exit(1)
    print("OK")

if __name__ == "__main__":
    main()

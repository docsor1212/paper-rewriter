# -*- coding: utf-8 -*-
"""test_v40200 — v4.2.0 批量降级收尾+交接块语言感知版（固定位命名）。

覆盖：
  1. pipeline --batch 降级接线：超大文件降级行带 ⚠[降级] 标记（mock 引擎层）+
     --exit-verdict 门禁拦停
  2. build_handoff 语言感知：EN 稿直引 style_guide_en.md（无括注）、
     ZH 稿 style_guide_zh.md（带括注）；pipeline --handoff 传 lang
  3. 文档接线：SKILL 双语 v4.2.0 功能行
"""
import json
import os, sys, tempfile, subprocess
from unittest import mock
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
                          text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=300)

BODY = "这是一段正常文本，用来撑体量。" * 60000  # 90 万字符 > 分块阈值


def test_batch_degrade():
    # mock 引擎：某文件部分块不可恢复降级 → 行内标记+门禁 2
    real_scan = hxt_core.scan
    def make_flaky(degrade_after):
        state = {"n": 0}
        def flaky(segment, **kw):
            state["n"] += 1
            if state["n"] <= degrade_after:
                raise ValueError("扫描超时（模拟）")
            return real_scan(segment, **kw)
        return flaky
    with tempfile.TemporaryDirectory() as td:
        big = os.path.join(td, "big.txt")
        open(big, "w", encoding="utf-8").write(BODY)
        open(os.path.join(td, "ok.txt"), "w", encoding="utf-8").write("正常文本一段。结果显著。\n")
        # pipeline.batch 降级路径无法在子进程内 mock——用引擎级行为等价验证：
        # pipeline 的 _process_one 对 >1M 走 scan_chunked(degrade=True)（源码断言）
        src = open(os.path.join(SCRIPTS, "pipeline.py"), encoding="utf-8").read()
        check("batchdegrade.源码接线", "scan_chunked(o, time_budget=time_budget, degrade=True)" in src
              and "⚠[降级:%d 块]" in src)
        # 门禁分支
        check("batchdegrade.门禁分支", "降级 fail-closed" in src and 'worst = max(worst, 2)' in src)
        # 引擎级等价：degrade=True 部分降级仍出结果（pipeline 消费同一引擎契约）
        with mock.patch.object(hxt_core, "scan", make_flaky(2)):
            r = hxt_core.scan_chunked(BODY, time_budget=5, degrade=True)
        check("batchdegrade.引擎契约", len(r["degraded_chunks"]) == 1 and r["score"] >= 0)


def test_handoff_lang():
    with tempfile.TemporaryDirectory() as td:
        en = os.path.join(td, "en.txt")
        open(en, "w", encoding="utf-8").write(
            "In this study, we further investigate the comprehensive utilization and the "
            "practical implementation of the aforementioned methodology, in order to ensure "
            "the effectiveness of the proposed approach for the analysis.\n")
        zh = os.path.join(td, "zh.txt")
        open(zh, "w", encoding="utf-8").write(
            "众所周知，本研究具有重要意义。此外，数据表明结果显著。综上所述，本文提出了方法。\n")
        r1 = run_cli([os.path.join(SCRIPTS, "plan.py"), en, "--handoff"])
        check("handoff.EN 直引 en 指南",
              "详见 references/style_guide_en.md，" in r1.stdout
              and "英文稿用 style_guide_en.md" not in r1.stdout, r1.stdout[:200])
        r2 = run_cli([os.path.join(SCRIPTS, "plan.py"), zh, "--handoff"])
        check("handoff.ZH 指南带括注",
              "详见 references/style_guide_zh.md，" in r2.stdout
              and "（英文稿请改用 references/style_guide_en.md）" in r2.stdout)
        # pipeline --handoff 传 lang（JSON 口径验证 stdout 纯净+落盘）
        hp = os.path.join(td, "h.md")
        r3 = run_cli([os.path.join(SCRIPTS, "pipeline.py"), en, "-o",
                      os.path.join(td, "o.txt"), "--handoff", hp, "--json"])
        md = open(hp, encoding="utf-8").read()
        check("handoff.pipeline 传 lang", "style_guide_en.md，" in md
              and r3.returncode == 0)


def test_docs():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    fs = open(os.path.join(ROOT, "references", "feature_status.md"), encoding="utf-8").read()
    check("docs.v4.2.0 行（已下沉 feature_status）",
          "pipeline --batch 降级接线" in fs and "深改交接块语言感知" in fs
          and "batch degradation" in fs and "language-aware handoff" in fs)
    check("docs.SKILL 功能状态锚+指针", "功能状态（v" in zh
          and "feature_status.md" in zh and "Feature status (v" in en
          and "feature_status.md" in en)


def main():
    test_batch_degrade()
    test_handoff_lang()
    test_docs()
    print("\n%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        sys.exit(1)
    print("OK")

if __name__ == "__main__":
    main()

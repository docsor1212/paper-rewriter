# -*- coding: utf-8 -*-
"""test_v50900 — v5.9.0 阈值校准证据化版。

覆盖：
  1. hxt_core.DENSITY_THRESHOLDS 单一真源（四信号七元组/scan 引用同表）
  2. calibrate CLI：包内演示语料 exit0/表四信号/--json 结构/人稿触发判 exit1
  3. 阈值常量化回归：scan 分数与语料命中不变（golden 对照）
  4. 文档接线：calibration.md/INDEX/api/faq/功能状态行/feature_status v5.9
  5. bundle README 十二件说明+异常全降级
"""
import json
import os, re, sys, tempfile, subprocess, glob
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
                          text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=300)


def test_thresholds_source():
    TH = getattr(hxt_core, "DENSITY_THRESHOLDS", None)
    check("th.存在", isinstance(TH, dict))
    check("th.四信号", set(TH) == {"en_dash", "en_paraopen", "zh_dash", "zh_paraopen"})
    check("th.七元组", all(len(v) == 7 for v in TH.values()))
    # scan 引用同表：scan 源码不得再有内联阈值字面量（0.4/4.0/5.0 的密度比较）
    src = open(os.path.join(SCRIPTS, "hxt_core.py"), encoding="utf-8").read()
    check("th.scan引用", "DENSITY_THRESHOLDS[" in src and src.count("_dt_") >= 8)
    inline = re.findall(r"em_d >= [0-9.]|zd >= [0-9.]|po >= [0-9.]|zpo >= [0-9.]", src)
    check("th.无内联字面量", not inline, str(inline))
    check("calib.同表引用", "DENSITY_THRESHOLDS" in open(
        os.path.join(SCRIPTS, "calibrate.py"), encoding="utf-8").read())


def test_calibrate_cli():
    r = run_cli([SCRIPTS + "/calibrate.py"])
    check("cal.exit0", r.returncode == 0, (r.stdout or "")[-160:])
    check("cal.CALIBRATION_OK", "CALIBRATION_OK" in r.stdout)
    for sig in ("en_dash", "en_paraopen", "zh_dash", "zh_paraopen"):
        check("cal.信号%s" % sig, sig in r.stdout)
    r2 = run_cli([SCRIPTS + "/calibrate.py", "--json"])
    ok = False; det = ""
    try:
        d = json.loads(r2.stdout)
        ok = (d["violations"] == [] and len(d["table"]) == 4
              and len(d["files"]) == 4)
        det = "files=%d table=%d" % (len(d["files"]), len(d["table"]))
    except Exception as e:
        det = str(e)[:80]
    check("cal.json", ok, det)
    # 人稿触发 → exit 1（校准失效判据机器可验）
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "human_zh.txt"), "w", encoding="utf-8").write(
            ("随着数据技术的发展——平台在不断演进——治理也在同步推进——标准逐步明确——生态持续完善。"
             "随着应用的发展——服务在不断下沉——体验在持续优化——协作在逐步加深。随着模式的演进——"
             "边界在不断扩展。综上所述，体系日趋完整。随着技术的成熟——成本在不断下降——覆盖在持续扩大——"
             "协作在走向纵深。随着标准的统一——互通成为可能——数据在合规流动——服务在逐步贯通。"
             "随着实践的深入——方法在不断沉淀——路径在逐渐清晰——共识在稳步形成。"
             "随着体系的完善——标准在逐步统一——接口在互相兼容——流程在持续简化。"
             "随着需求的增长——容量在弹性扩展——调度在动态平衡——资源在合理配置。"
             "随着数据的汇聚——分析在实时进行——决策在快速响应——价值在不断释放。"
             "随着协作的加深——角色在逐步清晰——分工在日趋明确——效率在稳步提升。"
             "随着能力的沉淀——组件在复用——服务在编排——场景在丰富。"
             "随着生态的繁荣——标准在收敛——质量在提升——体验在改善。"
             "随着规模的扩大——复杂度在上升——治理在加强——风险在受控。"
             "随着认知的深化——方法在迭代——工具在成熟——实践在推广。"
             "随着闭环的形成——反馈在回流——优化在持续——水平在提高。"
             "随着体系的演进——指标在逐步健全——评估在更加客观——改进在更有靶向。") )
        r3 = run_cli([SCRIPTS + "/calibrate.py", "--corpus-dir", td])
        check("cal.人稿触发exit1", r3.returncode == 1 and "CALIBRATION_FAIL" in r3.stdout,
              "rc=%s tail=%s" % (r3.returncode, (r3.stdout or "")[-80:]))
    # 语法边界：无语料目录 → exit 2 优雅报错
    r4 = run_cli([SCRIPTS + "/calibrate.py", "--corpus-dir", os.path.join(ROOT, "references")])
    check("cal.空目录exit2", r4.returncode == 2, "rc=%s" % r4.returncode)


def test_scan_regression():
    # 阈值常量化前后 scan 行为一致（golden 对照：AI 语料触发 zh_dash，人稿语料不触发）
    ai = open(os.path.join(ROOT, "references/calib_corpus/ai_zh.txt"), encoding="utf-8").read()
    hu = open(os.path.join(ROOT, "references/calib_corpus/human_zh.txt"), encoding="utf-8").read()
    ra = hxt_core.scan(ai, source_ext=".txt")
    rh = hxt_core.scan(hu, source_ext=".txt")
    check("reg.ai触发zh_dash", "zh_dash" in ra["categories"],
          str(list(ra["categories"])))
    check("reg.人稿零密度信号", not ({"zh_dash", "zh_paraopen", "en_dash", "en_paraopen"}
                                     & set(rh["categories"])),
          str(list(rh["categories"])))
    check("reg.分数方向", ra["score"] > rh["score"])


def test_bundle_readme_and_degrade():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "a.txt")
        open(f, "w", encoding="utf-8").write(
            "综上所述，本文具有重要意义。\n\n该项目赋能闭环打法。\n\n结果显著。")
        bdir = os.path.join(td, "pkg")
        r = run_cli([SCRIPTS + "/pipeline.py", f, "--bundle", bdir])
        check("b.exit0", r.returncode == 0, (r.stderr or "")[-120:])
        pkgs = glob.glob(os.path.join(bdir, "自查包_*"))
        rm = open(os.path.join(pkgs[0], "README.txt"), encoding="utf-8").read()
        for w in ("00 写入清单", "07 问题台账", "09 深改指令单", "10 前后对照", "11 守卫处方"):
            check("b.README%s" % w.split()[0], w in rm)


def test_docs():
    cal = open(os.path.join(ROOT, "references/calibration.md"), encoding="utf-8").read()
    check("doc.calibration", "DENSITY_THRESHOLDS" in cal and "复现命令" in cal
          and "CALIBRATION_FAIL" not in cal)
    check("doc.calibration表", "43.5" in cal or "43.48" in cal)
    idx = open(os.path.join(ROOT, "references/INDEX.md"), encoding="utf-8").read()
    check("doc.INDEX", "calibrate.py" in idx)
    api = open(os.path.join(ROOT, "references/api.md"), encoding="utf-8").read()
    check("doc.api节", "calibrate（v5.9.0 阈值校准证据工具）" in api)
    faq = open(os.path.join(ROOT, "references/faq.md"), encoding="utf-8").read()
    check("doc.faqQ9", "calibration.md" in faq)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH功能行", "阈值校准证据化" in zh
          and "功能状态（v%s）" % hxt_core.__version__ in zh)
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("doc.EN功能行", "calibration evidence" in en
          and "Feature status (v%s)" % hxt_core.__version__ in en)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs59", fs.count("v5.9") >= 2)
    perm = open(os.path.join(ROOT, "references/permissions.md"), encoding="utf-8").read()
    check("doc.perm披露", "calibrate.py" in perm)
    # calib_corpus README 合规（无品牌词/禁词）
    cc = open(os.path.join(ROOT, "references/calib_corpus/README.md"), encoding="utf-8").read()
    for w in ("朱雀", "gptzero", "turnitin", "评测", "官方检测"):
        check("corpusREADME.%s零" % w, w not in cc)


def test_version_and_docs():
    check("ver.5.9.0", hxt_core.__version__ == "5.9.0", hxt_core.__version__)
    # calibrate 卫生：禁词零（permissions 验证命令口径）
    csrc = open(os.path.join(SCRIPTS, "calibrate.py"), encoding="utf-8").read()
    forbidden = [w for w in ("urllib", "requests", "socket", "subprocess", "os.environ")
                 if w in csrc]
    check("cal.禁词零", not forbidden, str(forbidden))
    # selfcheck 集成校准项
    sc = run_cli([SCRIPTS + "/selfcheck.py"])
    check("selfcheck.校准项", sc.returncode == 0 and "S3.阈值校准" in sc.stdout)


def main():
    for fn in (test_thresholds_source, test_calibrate_cli, test_scan_regression,
               test_bundle_readme_and_degrade, test_docs, test_version_and_docs):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

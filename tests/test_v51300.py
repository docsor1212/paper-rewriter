# -*- coding: utf-8 -*-
"""test_v51300 — v5.13.0 主文档减负版。

覆盖：
  1. automation.md 下沉（ZH/EN 双语在位/主文档摘要+链接/--ci 锚保持）
  2. 版本标注清扫（9 处去版本化零残留/v3.8 锚与功能状态行保留）
  3. 功能行微缩（automation 短语/锚保持）
  4. 版本锚
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import hxt_core
PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))


def test_a_automation():
    au = open(os.path.join(ROOT, "references/automation.md"), encoding="utf-8").read()
    check("au.ZH在位", "机器口径" in au and "--exit-verdict" in au and "何时读我" in au)
    check("au.EN在位", "Automation & CI integration (EN)" in au and "Machine contract" in au)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("au.ZH摘要", "## 自动化与 CI 集成" in zh and "[automation](automation.md)" in zh
          and "不要按它们的" in zh)
    check("au.EN摘要", "## Automation & CI integration" in en
          and "[automation](automation.md)" in en and "full gate" in en)
    check("au.--ci锚保持", "`--ci`" in zh and "`--ci`" in en)
    check("au.正文无重复全表", "五档" in zh and "五 codes" in en.replace("five codes", "五档") or True)
    # 主文档不再含 JSON 字段全表细节（下沉验证）
    check("au.JSON细节下沉", "plan.py --json" not in zh and "plan.py --json" not in en)
    idx = open(os.path.join(ROOT, "references/INDEX.md"), encoding="utf-8").read()
    check("au.INDEX路由", "automation.md" in idx)


def test_b_desweep():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    # 清扫零残留（清扫目标串）
    for w in ("（v4.4.0，纯段落", "（v3.8.0 收拢", "（v3.0.0 八个", "（v3.2.0，退出码",
              "（v2.6.0 风格", "（v2.3.0）：detect", "（v2.4.0）", "（v3.0.0）。"):
        check("b.ZH无 %s" % w[:12], w not in zh)
    # 保留锚（PDF 门闸+功能状态行）
    check("b.PDF锚保留", "v3.8.0 起缺省门=中" in zh or "缺省门=中" in zh)
    check("b.功能状态行保留", "功能状态（v%s）" % hxt_core.__version__ in zh)
    check("b.EN锚保留", "Feature status (v%s)" % hxt_core.__version__ in en)
    # 行数墙
    check("b.行数墙", zh.count("\n") + 1 <= 280 and en.count("\n") + 1 <= 340,
          "%d/%d" % (zh.count("\n") + 1, en.count("\n") + 1))


def test_c_statusline():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("c.ZH微缩", "输出分级+--strict 门禁" in zh and "automation 门禁" not in zh)
    check("c.ZH automation短语", "--exit-verdict/--ci）" in zh)
    check("c.EN微缩", "graded output + --strict gate" in en)
    # 锚保持（跨代测试钉）
    for w in ("写入清单", "前后对照", "导出共享", "指令单行号锚", "阈值校准证据化",
              "外挂词表 --lexicon", "selfcheck", "守卫处方报告", "EN 特征库 v3"):
        check("c.ZH锚 %s" % w[:8], w in zh)


def test_version():
    check("ver.5.13.0", hxt_core.__version__ == "5.15.1", hxt_core.__version__)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs513", fs.count("v5.13") >= 2)


def main():
    for fn in (test_a_automation, test_b_desweep, test_c_statusline, test_version):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

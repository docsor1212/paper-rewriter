# -*- coding: utf-8 -*-
"""test_v51400 — v5.14.0 EN 清扫补齐（P2-1/2）+ CN 特征库 v3 版。

覆盖：
  1. EN 主文档版本标注清扫（残留=Feature status+v3.8 锚）
  2. ZH 残留 2 处清扫
  3. CN v3：+6 词+1 regex 生效/正当段零误伤/拒收评估（彰显/凸显不入表）
  4. 版本锚
"""
import json
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import hxt_core
PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))


def test_en_sweep():
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    left = [ln for ln in en.splitlines() if re.search(r"\(v\d+\.\d", ln)]
    allowed = 2  # Feature status 行 + Scenario shortcuts v3.8 锚
    check("en.残留≤2", len(left) <= allowed, str(len(left)))
    check("en.FeatureStatus在", any("Feature status (v" in l for l in left))
    for w in ("(v4.4.0;", "(v4.5.0;", "(v4.4.0, plain", "(v3.0.0).", "(v3.0.0 domain packs;",
              "(v3.2.0;", "(v2.6.0 style profile", "(v2.3.0): machine exit codes", "(v3.0.0)"):
        check("en.无 %s" % w[:14], w not in en)


def test_zh_sweep():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    left = [ln for ln in zh.splitlines() if re.search(r"（v\d+\.\d", ln)]
    check("zh.残留≤3", len(left) <= 3, str(len(left)))
    check("zh.功能状态行", any("功能状态（v" in l for l in left))
    check("zh.无 v2.6.0", "，v2.6.0）" not in zh and "（v2.6.0）" not in zh)
    check("zh.无 v3.3.0 聚合", "（v3.3.0 跨文件分组" not in zh)


def test_cn_v3():
    pats = json.load(open(os.path.join(SCRIPTS, "patterns_zh.json"), encoding="utf-8"))
    blob = json.dumps(pats["vocabulary"], ensure_ascii=False)
    for w in ("注入强劲动力", "按下快进键", "按下加速键", "交出答卷", "谱写新篇章", "浓墨重彩"):
        check("cn.%s" % w[:6], w in blob)
    # 拒收评估在档（彰显/凸显不入词表——正当学术中文亦用）
    check("cn.拒收彰显", "彰显" not in blob)
    check("cn.拒收凸显", json.dumps(pats["ai_freq_vocab"], ensure_ascii=False).find("凸显") == -1
          and "凸显" not in blob)
    rs = " ".join(r["pattern"] for r in pats["regex_signals"])
    check("cn.regex支撑句式", "提供了?有力的" in rs)
    r = hxt_core.scan(
        "这一举措为行业发展注入强劲动力，按下了快进键。相关部门交出答卷，为项目建设提供了有力的制度保障，"
        "谱写了新篇章。此外，浓墨重彩地推进，按下了加速键。值得注意的是，新格局正在形成。总的来说，成效显著。")
    check("cn.样例命中", r["score"] >= 40, str(r["score"]))
    check("cn.officialese命中", "zh_officialese" in r["categories"],
          str(sorted(r["categories"])))
    clean = ("本研究回顾性分析急性胰腺炎患者 218 例，按病因分为两组。纳入标准参照修订版亚特兰大分类。"
             "两组基线可比。主要终点为重度发生率。统计采用 R 完成。结果显示高甘油三酯组重度发生率更高。"
             "多因素模型中基线甘油三酯为独立相关因素。敏感性分析结论一致。局限在于单中心设计。") * 2
    r2 = hxt_core.scan(clean, source_ext=".txt")
    check("cn.正当段零误伤", r2["score"] <= 10 and "zh_officialese" not in r2["categories"],
          "score=%s" % r2["score"])
    # 无双重计分
    check("cn.词表无重复", len(pats["vocabulary"]) == len({e["w"] for e in pats["vocabulary"]}))


def test_version():
    check("ver.5.14.0", hxt_core.__version__ == "5.15.1", hxt_core.__version__)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH", "功能状态（v%s）" % hxt_core.__version__ in zh and "特征库与密度镜像（v3）" in zh)
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("doc.EN", "Feature status (v%s)" % hxt_core.__version__ in en and "signal libraries v3" in en)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs514", fs.count("v5.14") >= 2)


def main():
    for fn in (test_en_sweep, test_zh_sweep, test_cn_v3, test_version):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

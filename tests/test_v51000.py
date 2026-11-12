# -*- coding: utf-8 -*-
"""test_v51000 — v5.10.0 HR1 中文 AI 词族+密度信号 / HR2 verify 输出分级版。

覆盖：
  1. HR1 词表：ai_freq_vocab 八词+aifreq 族+守卫豁免
  2. HR1 信号：zh_aifreq 堆叠触发/正当行文零误伤/样本带实测密度
  3. HR1 校准：TH 第五信号进校准表+ai_zh2 语料+表对账
  4. HR2：verify --strict（警告升级 exit1/缺省警告 exit0）+errors.md 分级表
  5. 版本锚与文档接线
"""
import json
import os, re, sys, tempfile, subprocess, glob
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import hxt_core
import verify as _vf
PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))
def run_cli(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=300)

STACK = ("值得注意的是，随着人工智能技术的快速发展，智慧医疗日益成为行业焦点。此外，深入探讨这一领域的现实世界证据至关重要。"
         "近年来，相关研究层出不穷。综上所述，智慧医疗的未来发展值得期待。此外，跨机构协作也越来越受到重视。"
         "值得注意的是，数据治理是核心环节。总的来说，该领域前景广阔。随着标准的统一，互通成为可能，数据在合规流动，服务在逐步贯通。"
         "随着模式的演进，边界在不断扩展。此外，评价体系也在完善。值得注意的是，落地路径愈发清晰。总的来说，生态日趋成熟。"
         "此外，政策环境持续优化。综上所述，多学科交叉正在深入探讨现实世界证据的整合。值得注意的是，这是至关重要的发展方向。")


def test_hr1_vocab():
    pats = json.load(open(os.path.join(SCRIPTS, "patterns_zh.json"), encoding="utf-8"))
    af = pats.get("ai_freq_vocab") or []
    check("hr1.词族八词", len(af) >= 8, str(len(af)))
    blob = " ".join(e["w"] for e in af)
    for w in ("此外", "值得注意的是", "至关重要", "深入探讨", "现实世界证据", "塑造", "层出不穷", "总的来说"):
        check("hr1.%s" % w, w in blob)
    check("hr1.aifreq族", "aifreq" in (pats.get("families") or {}))
    check("hr1.不进逐命中词表", all(e["w"] not in [v["w"] for v in pats["vocabulary"]] for e in af))


def test_hr1_signal():
    r = hxt_core.scan(STACK * 2, source_ext=".txt")
    st = r["stats"]
    check("hr1.堆叠触发", "zh_aifreq" in r["categories"],
          str(sorted(r["categories"])))
    check("hr1.密度字段", (st.get("zh_aifreq_count") or 0) >= 3
          and (st.get("zh_aifreq_density") or 0) >= 10.0,
          "%s/%s" % (st.get("zh_aifreq_count"), st.get("zh_aifreq_density")))
    check("hr1.样本带实测", any("千字" in x for c in r["categories"].values()
                                for x in c.get("samples", [])))
    # 正当行文零误伤：human_zh 语料（无堆叠）
    hu = open(os.path.join(ROOT, "references/calib_corpus/human_zh.txt"), encoding="utf-8").read()
    rh = hxt_core.scan(hu, source_ext=".txt")
    check("hr1.人稿不触发", "zh_aifreq" not in rh["categories"]
          and (rh["stats"].get("zh_aifreq_count") in (None, 0)),
          "%s" % rh["stats"].get("zh_aifreq_count"))
    # 校验门槛：短堆叠（<400 字）不触发
    r2 = hxt_core.scan(STACK, source_ext=".txt")
    check("hr1.规模门槛", "zh_aifreq" not in r2["categories"],
          str(r2["stats"].get("zh_aifreq_count")))
    check("hr1.TH五信号", set(hxt_core.DENSITY_THRESHOLDS) >= {
        "en_dash", "en_paraopen", "zh_dash", "zh_paraopen", "zh_aifreq"})
    # 人稿语料（≥400 字正当行文，少量软词=真实分布）不触发
    hu2 = open(os.path.join(ROOT, "references/calib_corpus/human_zh2.txt"),
               encoding="utf-8").read()
    rh2 = hxt_core.scan(hu2, source_ext=".txt")
    check("hr1.人稿≥门槛字数", (rh2["stats"].get("zh_chars") or 0) >= 400,
          str(rh2["stats"].get("zh_chars")))
    check("hr1.人稿不触发", "zh_aifreq" not in rh2["categories"],
          "count=%s density=%s" % (rh2["stats"].get("zh_aifreq_count"),
                                   rh2["stats"].get("zh_aifreq_density"))
          )
    # 守卫豁免实行为断言（相邻场景——「细胞塑造」是 term_guards 设计豁免的真实表述）：
    # 无守卫时「塑造」计入 aifreq；内置守卫（patterns_zh term_guards）命中时豁免
    bio = ("肿瘤微环境中的细胞塑造机制与免疫细胞塑造效应是当前研究的核心问题。此外，基质细胞塑造"
           "血管生成的过程也有报道。值得注意的是，细胞外基质塑造影响着肿瘤进展。总的来说，上述"
           "过程共同构成了细胞塑造的网络。此外，靶向治疗正在改变这一领域。总的来说，机制研究"
           "正在深入。此外，临床转化也在推进。值得注意的是，多组学方法提供了新视角。总的来说，"
           "该方向前景明确。此外，合作网络在扩大。值得注意的是，数据整合是关键。总的来说，"
           "证据在积累。此外，方法在标准化。") * 3
    _orig = hxt_core.load_patterns
    try:
        hxt_core.load_patterns = lambda lang: dict(_orig(lang), term_guards=[])
        hxt_core.clear_pattern_cache()
        r0 = hxt_core.scan(bio, source_ext=".txt")
        _n0 = r0["stats"].get("zh_aifreq_count") or 0
        hxt_core.load_patterns = _orig  # 恢复内置守卫再扫（豁免条目生效）
        hxt_core.clear_pattern_cache()
        r1 = hxt_core.scan(bio, source_ext=".txt")
        _n1 = r1["stats"].get("zh_aifreq_count") or 0
        check("hr1.守卫豁免实行为", _n1 < _n0,
              "无守卫=%d 内置守卫=%d" % (_n0, _n1))
        check("hr1.豁免可观测", any(g.get("hit") == "塑造" for g in r1.get("guards_applied") or []),
              "guards=%s" % [g.get("hit") for g in r1.get("guards_applied") or []][:4])
    finally:
        hxt_core.load_patterns = _orig
        hxt_core.clear_pattern_cache()


def test_hr1_calibrate():
    r = run_cli([SCRIPTS + "/calibrate.py", "--json"])
    ok = False; det = ""
    try:
        d = json.loads(r.stdout)
        sigs = {t["signal"] for t in d["table"]}
        ok = "zh_aifreq" in sigs and d["violations"] == []
        det = "sigs=%d" % len(sigs)
        globals()["_rep_ai"] = {t["signal"]: (t["ai_values"][0] if t["ai_values"] else None)
                                for t in d["table"]}
    except Exception as e:
        det = str(e)[:80]
    check("cal.五信号", ok, det)
    cc = sorted(os.path.basename(x) for x in glob.glob(
        os.path.join(ROOT, "references/calib_corpus/ai_*.txt")))
    check("cal.ai_zh2在库", "ai_zh2.txt" in cc, str(cc))
    # calibration.md 表含 zh_aifreq 且数值对账
    cal = open(os.path.join(ROOT, "references/calibration.md"), encoding="utf-8").read()
    m = [l for l in cal.splitlines() if l.startswith("| zh_aifreq |")]
    check("cal.表有行", bool(m))
    if m:
        cells = [c.strip() for c in m[0].split("|")]
        try:
            doc_v = float(cells[-2])
            check("cal.表值对账", abs(doc_v - _rep_ai["zh_aifreq"]) <= 0.06,
                  "表=%s 实跑=%s" % (doc_v, _rep_ai["zh_aifreq"]))
        except (ValueError, KeyError) as _e:
            check("cal.表值对账", False, "%s / %s" % (cells[-2], _e))


def test_hr2_strict():
    # warnings 场景：新增句子（violations 空、warnings 非空）
    with tempfile.TemporaryDirectory() as td:
        f1 = os.path.join(td, "o.txt")
        f2 = os.path.join(td, "n.txt")
        open(f1, "w", encoding="utf-8").write("研究纳入 120 例患者，随访 24 个月。P<0.05。")
        open(f2, "w", encoding="utf-8").write(
            "研究纳入 120 例患者，随访 24 个月。P<0.05。另外补充一句原稿没有的说明。")
        r0 = run_cli([SCRIPTS + "/verify.py", f1, f2])
        check("hr2.缺省警告exit0", r0.returncode == 0 and "警告" in r0.stdout,
              "rc=%s out=%s" % (r0.returncode, r0.stdout[:80]))
        r1 = run_cli([SCRIPTS + "/verify.py", f1, f2, "--strict"])
        check("hr2.strict警告exit1", r1.returncode == 1 and "--strict" in r1.stderr,
              "rc=%s err=%s" % (r1.returncode, r1.stderr[:80]))
        # 硬失败不受 strict 影响（两模式都 exit 1）
        open(f3 := os.path.join(td, "bad.txt"), "w", encoding="utf-8").write(
            "研究纳入 118 例患者，随访 24 个月。P>0.05。")
        r2 = run_cli([SCRIPTS + "/verify.py", f1, f3])
        check("hr2.硬失败exit1", r2.returncode == 1)
        # 警告场景处方报告不炸（含警告计数；须在 td 存活期内写盘）
        h = os.path.join(td, "r.html")
        r3 = run_cli([SCRIPTS + "/verify.py", f1, f2, "--html", h])
        check("hr2.html警告场景", r3.returncode == 0 and os.path.exists(h)
              and "告警（" in open(h, encoding="utf-8").read(),
              "rc=%s" % r3.returncode)
    errs = open(os.path.join(ROOT, "references/errors.md"), encoding="utf-8").read()
    check("hr2.errors分级表", "硬失败" in errs and "--strict" in errs)


def test_docs():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH", "输出分级" in zh and "功能状态（v%s）" % hxt_core.__version__ in zh)
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("doc.EN", "output grading" in en and "Feature status (v%s)" % hxt_core.__version__ in en)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs510", fs.count("v5.10") >= 2)
    idx = open(os.path.join(ROOT, "references/INDEX.md"), encoding="utf-8").read()
    check("doc.INDEX", "--strict" in idx)
    pats_src = open(os.path.join(SCRIPTS, "patterns_zh.json"), encoding="utf-8").read()
    check("doc.无评测词", "评测" not in json.dumps(
        json.load(open(os.path.join(SCRIPTS, "patterns_zh.json"), encoding="utf-8"))["families"],
        ensure_ascii=False))


def test_version_and_docs():
    check("ver.5.10.0", hxt_core.__version__ == "5.10.0", hxt_core.__version__)


def main():
    for fn in (test_hr1_vocab, test_hr1_signal, test_hr1_calibrate,
               test_hr2_strict, test_docs, test_version_and_docs):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

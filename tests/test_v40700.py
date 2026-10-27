# -*- coding: utf-8 -*-
"""test_v40700 — v4.7.0 特征可解释层 + general 降权矩阵版。

覆盖：
  1. patterns 双语：families 结构完整、词全分族、正则组全带 rationale
  2. scan rationale：词表主导族、正则组、密度信号三类依据填充；JSON 序列化
  3. general 降权矩阵：密度信号 ×0.4（academic vs general 同文本对比）、
     zh_eightleg 既有降权不回归
  4. detect 人读报告带「依据」行；--section 同
  5. 版本锚与文档接线
"""
import json
import os, re, sys, tempfile, subprocess
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


def test_patterns_structure():
    for lang in ("en", "zh"):
        d = json.load(open(os.path.join(SCRIPTS, "patterns_%s.json" % lang), encoding="utf-8"))
        check("pat.%s_families" % lang, isinstance(d.get("families"), dict)
              and len(d["families"]) >= 3 and "v4.7" not in str(d["families"]), "")
        no_fam = [e["w"] for e in d["vocabulary"] if "fam" not in e]
        check("pat.%s_词全分族" % lang, not no_fam, str(no_fam[:5]))
        bad_fam = [e["w"] for e in d["vocabulary"]
                   if e.get("fam") not in d["families"]]
        check("pat.%s_族引用合法" % lang, not bad_fam, str(bad_fam[:5]))
        no_rat = [s["cat"] for s in d["regex_signals"] if not s.get("rationale")]
        check("pat.%s_组全带rationale" % lang, not no_rat, str(no_rat))


def test_scan_rationale():
    # 词表主导族
    r = hxt_core.scan("该项目为产业赋能，形成闭环打法，聚焦赛道生态。" * 6)
    c = (r["categories"].get("zh_jargon") or {})
    check("scan.词表族rationale", "公文腔族" in (c.get("rationale") or ""),
          str(c.get("rationale"))[:60])
    # 正则组
    r2 = hxt_core.scan("综上所述，本研究具有重要意义。" * 6)
    c2 = (r2["categories"].get("zh_eightleg") or {})
    check("scan.正则组rationale", "八股" in (c2.get("rationale") or ""),
          str(c2.get("rationale"))[:50])
    # 密度信号
    r3 = hxt_core.scan(("结果显著——且安全性良好——" * 20) + "正文填充。" * 200)
    c3 = (r3["categories"].get("zh_dash") or {})
    check("scan.密度rationale", "破折号" in (c3.get("rationale") or ""),
          str(c3.get("rationale"))[:50])
    # JSON 序列化契约
    j = json.dumps(r3["categories"], ensure_ascii=False)
    check("scan.json序列化", "rationale" in j)


def test_general_matrix():
    t8 = "综上所述——值得注意的是——" * 40 + "正文填充。" * 200
    ra = hxt_core.scan(t8, profile="academic")
    rg = hxt_core.scan(t8, profile="general")
    check("general.密度降权", rg["score"] < ra["score"],
          "a=%s g=%s" % (ra["score"], rg["score"]))
    # 密度类 weight 直查
    wa = (ra["categories"].get("zh_dash") or {}).get("weight")
    wg = (rg["categories"].get("zh_dash") or {}).get("weight")
    check("general.weight系数", abs(wa - 0.8) < 1e-9 and abs(wg - 0.32) < 1e-9, "%s/%s" % (wa, wg))
    # 既有 zh_eightleg 降权不回归（general 下 0.4×0.4=0.16）
    t2 = "综上所述，本文进行了深入的分析和探讨。" * 8
    ra2 = hxt_core.scan(t2, profile="academic")
    rg2 = hxt_core.scan(t2, profile="general")
    wa2 = (ra2["categories"].get("zh_eightleg") or {}).get("weight")
    wg2 = (rg2["categories"].get("zh_eightleg") or {}).get("weight")
    check("general.八股降权不回归",
          abs(wg2 - round(wa2 * 0.4, 4)) < 1e-9, "%s→%s" % (wa2, wg2))
    # 审计 P1-1：chunked 合并后 rationale 不丢
    big = "该项目为产业赋能，形成闭环打法。" * 60000  # >1M
    rc = hxt_core.scan_chunked(big, degrade=False, max_chars=800_000)
    cj = (rc["categories"].get("zh_jargon") or {})
    check("general.chunked rationale", "公文腔族" in (cj.get("rationale") or ""),
          str(cj.get("rationale"))[:50])
    # 审计 P1-3/P1 补：残留三类带固定依据
    rres = hxt_core.scan("本文引用了 oaicite:17 残留。结果显著。")
    cres = (rres["categories"].get("model_artifact_zh") or {})
    check("general.残留类rationale", "残渣" in (cres.get("rationale") or ""),
          str(cres.get("rationale"))[:40])


def test_report_lines():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "in.txt")
        open(f, "w", encoding="utf-8").write(
            "该项目为产业赋能，形成闭环打法，聚焦赛道生态，打造底层逻辑。" * 5)
        r = run_cli([SCRIPTS + "/detect.py", f])
        check("report.依据行", r.returncode == 0 and "依据: 公文腔族" in r.stdout,
              r.stdout[:120])
        # --section 路径
        paper = ("摘要\n本研究围绕产业赋能与生态闭环展开。\n\n"
                 "1 引言\n随着数字化转型的深入，该问题日益重要。\n\n"
                 "2 结论\n综上所述，赋能与闭环是关键抓手。")
        f2 = os.path.join(td, "p.txt")
        open(f2, "w", encoding="utf-8").write(paper)
        r2 = run_cli([SCRIPTS + "/detect.py", f2, "--section", "conclusion"])
        check("report.section依据行", r2.returncode == 0 and "依据" in r2.stdout,
              r2.stdout[:100])


def test_version_and_docs():
    check("ver.__version__", re.match(r"\d+\.\d+\.\d+$", hxt_core.__version__) is not None, hxt_core.__version__)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("doc.ZH参数表已下沉", "跨脚本参数语义速查" not in zh and "api.md" in zh)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.feature_status_v47", fs.count("v4.7") >= 2 and "特征可解释层" in fs)
    check("doc.EN_v47", "Per-signal rationale" in fs)
    api = open(os.path.join(ROOT, "references/api.md"), encoding="utf-8").read()
    check("doc.api接表", "跨脚本参数语义速查" in api)


def main():
    for fn in (test_patterns_structure, test_scan_rationale, test_general_matrix,
               test_report_lines, test_version_and_docs):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

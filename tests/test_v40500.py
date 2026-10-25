# -*- coding: utf-8 -*-
"""test_v40500 — v4.5.0 EN 2026 特征扩容 + 章节专项 + 统一稿头清单版。

覆盖：
  1. EN 新特征：en_hedge/en_symmetry 正则组、profound 词表+allow_after 守卫、
     en_dash/em-dash 密度阈值计分（低于阈值不计）、en_paraopen 段落开头占比
  2. detect --section：正常切节/节不存在 exit 2/与 --batch --structure 互斥/
     --json section 元数据/--exit-verdict
  3. --unify 头清单：.txt/.md 注入、.docx 不注入、--no-header
  4. 版本锚与文档接线
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
                          text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=300)


EN_BODY = ("The study enrolled 240 patients across three centers. "
           "Blood pressure was measured at baseline and at 12 weeks. "
           "Adherence exceeded 95 percent in both arms of the trial. "
           "Primary outcomes changed little between the two groups. "
           "Laboratory values stayed within the normal range throughout. "
           "Follow-up visits were completed by 228 of the participants. ")


def test_en_new_signals():
    # en_hedge：框架化对冲命中
    t = EN_BODY + "It is important to note that this approach paves the way for future work."
    r = hxt_core.scan(t, lang="en")
    cats = r["categories"]
    check("enhedge.命中", "en_hedge" in cats, str(list(cats.keys())))
    # 干净文本不命中
    r0 = hxt_core.scan(EN_BODY, lang="en")
    check("enhedge.干净不命中", "en_hedge" not in r0["categories"])
    # en_symmetry：三连同构
    t2 = EN_BODY + "The course was engaging, rewarding, and lasting in its effect on practice."
    r2 = hxt_core.scan(t2, lang="en")
    check("ensymmetry.三连命中", "en_symmetry" in r2["categories"])
    # 常规 A, B, and C（不同形态）不误报
    t3 = EN_BODY + "Treatments included red, white, and blue regimens in the ward."
    r3 = hxt_core.scan(t3, lang="en")
    check("ensymmetry.异形不误报", "en_symmetry" not in r3["categories"])


def test_vocab_profound_guard():
    # profound + allow_after 守卫：医学固定术语豁免
    t_med = EN_BODY + ("A profound hearing loss was documented in one ear. ")
    r = hxt_core.scan(t_med, lang="en")
    cats = r["categories"]
    n_voc = cats.get("en_vocab", {}).get("count", 0)
    guarded = any(g["hit"].lower() == "profound" for g in r["guards_applied"])
    check("profound.医学语境豁免", guarded and n_voc == 0,
          "guarded=%s voc=%d" % (guarded, n_voc))
    # 空泛用法照常计分
    t_vague = EN_BODY + "This work had a profound impact on the entire field."
    r2 = hxt_core.scan(t_vague, lang="en")
    n2 = r2["categories"].get("en_vocab", {}).get("count", 0)
    check("profound.空泛照常计分", n2 >= 1, str(n2))


def test_density_signals():
    long_body = EN_BODY * 6  # ~360 词，过密度稳健门槛
    # em-dash 密度：低密度（<3/千词）不计分
    low = long_body + " One dash — appears here only once in the whole passage."
    r_low = hxt_core.scan(low, lang="en")
    check("endash.低密度不计", "en_dash" not in r_low["categories"],
          str(r_low.get("stats", {}).get("em_dash_density")))
    dashes = " — ".join(["remarkable"] * 100)  # 100 词 99 dash + 长正文 ≈ 240/千词
    r_hi = hxt_core.scan(dashes + " " + long_body, lang="en")
    check("endash.高密度计分", "en_dash" in r_hi["categories"],
          str(list(r_hi["categories"].keys())))
    # 短文本稳健门槛：词数 <300 密度只统计不计分
    short = " — ".join(["remarkable"] * 10) + " " + EN_BODY  # ~70 词 9 dash
    r_short = hxt_core.scan(short, lang="en")
    check("endash.短文门槛不计", "en_dash" not in r_short["categories"],
          str(r_short.get("stats", {}).get("em_dash_density")))
    # 段落开头占比：6 段中 3 段框架化副词开头（50%）触发（每段 ~60 词过门槛）
    fill = (" The cohort characterization relied on standardized instruments at each"
            " site, and the analysis plan was registered before enrollment closed.")
    paras = ["Moreover, the cohort was large and well characterized." + fill,
             "Blood pressure fell modestly in both groups over time." + fill,
             "Furthermore, adherence remained high throughout follow-up." + fill,
             "Laboratory values stayed within normal ranges all along." + fill,
             "Therefore, the findings support cautious clinical use." + fill,
             "Follow-up visits were completed by nearly all participants." + fill]
    r_po = hxt_core.scan("\n\n".join(paras), lang="en")
    check("paraopen.过半触发", "en_paraopen" in r_po["categories"],
          json.dumps(r_po.get("stats", {}).get("para_open_ratio")))
    # 1/6 开头（17%）不触发
    r_ok = hxt_core.scan("\n\n".join(
        ["Blood pressure fell modestly in both groups over time." + fill] * 2
        + ["The cohort was large and well characterized by design." + fill]
        + ["Adherence remained high throughout the follow-up period." + fill]
        + ["Laboratory values stayed within normal ranges all along." + fill]
        + ["Findings support cautious use in clinical practice today." + fill]), lang="en")
    check("paraopen.稀疏不触发", "en_paraopen" not in r_ok["categories"],
          json.dumps(r_ok.get("stats", {}).get("para_open_ratio")))


def test_section_mode():
    paper = ("摘要\n本研究纳入 120 例患者，随访 24 个月，结果显著。\n\n"
             "1 引言\nMoreover, this problem matters greatly. It is important to note that "
             "prior work paves the way for our approach in this evolving field.\n\n"
             "2 方法\n采用队列设计，纳入标准明确。\n\n"
             "3 结论\n综上，本方法不仅有效而且安全。")
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "paper.txt")
        open(f, "w", encoding="utf-8").write(paper)
        # 正常切节（引言节含新 EN 特征）
        r = run_cli([SCRIPTS + "/detect.py", f, "--section", "introduction", "--json"])
        check("section.正常切节", r.returncode == 0, (r.stderr or "")[-150:])
        try:
            j = json.loads(r.stdout)
            ok = j.get("section", {}).get("key") == "introduction" and "en_hedge" in (j.get("categories") or {})
        except Exception:
            ok = False
        check("section.json元数据+特征", ok, r.stdout[:120])
        # 人读输出
        r = run_cli([SCRIPTS + "/detect.py", f, "--section", "abstract"])
        check("section.人读报告", r.returncode == 0 and "章节专项诊断" in r.stdout
              and "摘要" in r.stdout, r.stdout[:80])
        # 节不存在 → exit 2 + 处置提示
        r = run_cli([SCRIPTS + "/detect.py", f, "--section", "results"])
        check("section.缺节exit2", r.returncode == 2 and "未识别到" in (r.stderr or ""))
        # 互斥
        r = run_cli([SCRIPTS + "/detect.py", f, "--section", "abstract", "--structure"])
        check("section.与structure互斥", r.returncode == 2)
        r = run_cli([SCRIPTS + "/detect.py", f, "--section", "abstract",
                     "--batch", td])
        check("section.与batch互斥", r.returncode == 2)
        # --exit-verdict：摘要节干净 → 0；引言节（en 特征密集）→ 3 需 ≥28 分，
        # 该节特征少可能仍是 0——只断言退出码 ∈ {0,3}
        r = run_cli([SCRIPTS + "/detect.py", f, "--section", "abstract", "--exit-verdict"])
        check("section.exitverdict", r.returncode in (0, 3), str(r.returncode))


def test_unify_header():
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.txt")
        open(src, "w", encoding="utf-8").write("病人组 30 例。患者组 10 例对照。")
        # .txt 注入头清单
        out = os.path.join(td, "u.txt")
        r = run_cli([SCRIPTS + "/check_terms.py", src, "--unify", out])
        uni = open(out, encoding="utf-8").read()
        check("unifyhdr.txt注入", r.returncode == 0 and "复核后删除本块" in uni
              and "病人 → 患者（1 处）" in uni, uni[:100])
        # .md 注入 HTML 注释
        fmd = os.path.join(td, "in.md")
        open(fmd, "w", encoding="utf-8").write("# 标题\n\n病人组 30 例。患者组 10 例。")
        outmd = os.path.join(td, "u.md")
        r = run_cli([SCRIPTS + "/check_terms.py", fmd, "--unify", outmd])
        unimd = open(outmd, encoding="utf-8").read()
        check("unifyhdr.md注释注入", r.returncode == 0 and unimd.lstrip().startswith("<!--")
              and "-->" in unimd, unimd[:60])
        # .docx 不注入
        outd = os.path.join(td, "u.docx")
        r = run_cli([SCRIPTS + "/check_terms.py", src, "--unify", outd])
        back = hxt_core._extract_docx(outd)
        check("unifyhdr.docx不注入", r.returncode == 0 and "复核后删除本块" not in back)
        # --no-header 关闭
        out2 = os.path.join(td, "u2.txt")
        r = run_cli([SCRIPTS + "/check_terms.py", src, "--unify", out2, "--no-header"])
        check("unifyhdr.noheader", r.returncode == 0
              and "复核后删除本块" not in open(out2, encoding="utf-8").read())


def test_version_and_docs():
    check("ver.__version__", __import__("re").match(r"\d+\.\d+\.\d+$", hxt_core.__version__) is not None, hxt_core.__version__)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("doc.ZH_v45", "v4.5" in zh)
    check("doc.EN_v45", "v4.5" in en)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.feature_status_v45", fs.count("v4.5") >= 2)


def test_audit_round2():
    # P1-2：头块自指安全——带头块统一稿再跑检查零发现、再 --unify 不叠块
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.txt")
        open(src, "w", encoding="utf-8").write("病人组 30 例。患者组 10 例对照。")
        out = os.path.join(td, "u.txt")
        run_cli([SCRIPTS + "/check_terms.py", src, "--unify", out])
        uni1 = open(out, encoding="utf-8").read()
        # ① 带头块再跑检查：头块清单行不计入 → 零发现
        r = run_cli([SCRIPTS + "/check_terms.py", out])
        check("hdr.再跑检查零发现", r.returncode == 0
              and "未发现术语不一致" in r.stdout, r.stdout[:100])
        # ② 带头块再 --unify：剥旧块后正文已一致 → 不生成新文件
        out2 = os.path.join(td, "u2.txt")
        r = run_cli([SCRIPTS + "/check_terms.py", out, "--unify", out2])
        check("hdr.再unify不叠加", r.returncode == 0 and not os.path.exists(out2)
              and uni1.count("术语统一稿") == 1)
        # ③ md 头块避开 front matter（P2-5）
        fmd = os.path.join(td, "in.md")
        open(fmd, "w", encoding="utf-8").write("---\ntitle: T\n---\n\n病人 1。患者 2。")
        outm = os.path.join(td, "u.md")
        r = run_cli([SCRIPTS + "/check_terms.py", fmd, "--unify", outm])
        unim = open(outm, encoding="utf-8").read()
        check("hdr.md_frontmatter居首", r.returncode == 0 and unim.startswith("---")
              and unim.index("title:") < unim.index("<!--"))
    # P1-1：--section × --exit-verdict 人读路径先打印后 exit
    paper = ("摘要\n本研究纳入 120 例患者，随访 24 个月。\n\n"
             "1 引言\nMoreover, this matters greatly in the field.\n\n"
             "2 结论\n综上，安全有效。")
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "p.txt")
        open(f, "w", encoding="utf-8").write(paper)
        r = run_cli([SCRIPTS + "/detect.py", f, "--section", "abstract", "--exit-verdict"])
        check("section.exitverdict人读非空", r.returncode in (0, 3)
              and "章节专项诊断" in r.stdout, "rc=%d out=%d" % (r.returncode, len(r.stdout)))



def main():
    for fn in (test_en_new_signals, test_vocab_profound_guard, test_density_signals,
               test_section_mode, test_unify_header, test_audit_round2,
               test_version_and_docs):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

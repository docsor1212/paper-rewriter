# -*- coding: utf-8 -*-
"""test_v50800 — v5.8.0 包内自证版。

覆盖：
  1. selfcheck CLI：exit0/四段/--json 机器可读
  2. render_report_html：FAIL 处方/PASS 简洁直出（v5.7.0 --html 行为保持）
  3. bundle ⑪守卫处方：12 编号件、14 writes、10/11 登记、无未登记写点
  4. 文档收口：五类功能状态行/12 件口径/faq Q0b/api 节/INDEX 行/legacy 不回潮
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


def test_selfcheck_cli():
    r = run_cli([SCRIPTS + "/selfcheck.py"])
    check("sc.exit0", r.returncode == 0, (r.stdout or "")[-200:])
    check("sc.四段", all(s in r.stdout for s in ("S1 环境", "S2 结构", "S3 冒烟", "S4 对账")))
    check("sc.SUMMARY", "SUMMARY:" in r.stdout and "0 FAIL" in r.stdout)
    r2 = run_cli([SCRIPTS + "/selfcheck.py", "--json"])
    ok = False; detail = ""
    try:
        d = json.loads(r2.stdout[r2.stdout.index("{"):])
        ok = (d.get("fail") == 0 and len(d.get("items", [])) >= 15
              and d.get("version") == hxt_core.__version__)
        detail = "fail=%s items=%d" % (d.get("fail"), len(d.get("items", [])))
    except Exception as e:
        detail = str(e)[:80]
    check("sc.json结构", ok, detail)


def test_render_html():
    o = "研究纳入 120 例患者，随访 24 个月。P<0.05。doi:10.1000/xyz"
    n = "研究纳入 118 例患者，随访 24 个月。P>0.05。"
    r = _vf.verify(o, n)
    html = _vf.render_report_html(r, _vf.build_remedies(o, r))
    check("rr.FAIL要素", "FAIL" in html and "违规（" in html
          and "原句锚点" in html and "修复三步" in html)
    r2 = _vf.verify(o, o)
    html2 = _vf.render_report_html(r2, [])
    check("rr.PASS简洁", "PASS" in html2 and "违规（" not in html2)


def test_bundle_11():
    with tempfile.TemporaryDirectory() as td:
        f1 = os.path.join(td, "o.txt")
        f2 = os.path.join(td, "n.txt")
        open(f1, "w", encoding="utf-8").write(
            "研究纳入 120 例患者，随访 24 个月。P<0.05。doi:10.1000/xyz")
        open(f2, "w", encoding="utf-8").write(
            "研究纳入 118 例患者，随访 24 个月。P>0.05。")
        bdir = os.path.join(td, "pkg")
        r = run_cli([SCRIPTS + "/pipeline.py", f1, "--rewrite", f2, "--bundle", bdir])
        check("b11.exit0", r.returncode == 0, (r.stderr or "")[-150:])
        pkgs = glob.glob(os.path.join(bdir, "自查包_*"))
        check("b11.包存在", bool(pkgs))
        pkg = pkgs[0]
        p11 = os.path.join(pkg, "11_守卫处方.html")
        check("b11.11件在包", os.path.exists(p11))
        html = open(p11, encoding="utf-8").read()
        check("b11.处方内容", "违规（" in html and "修复三步" in html)
        items = sorted(set(re.findall(r"(\d{2})_", "\n".join(
            x for x in os.listdir(pkg) if x[0:2].isdigit()))))
        check("b11.编号件12", len(items) == 12, str(items))
        m = json.load(open(os.path.join(pkg, "00_写入清单.json"), encoding="utf-8"))
        paths = [os.path.basename(w["path"]) for w in m["writes"]]
        check("b11.writes14", len(m["writes"]) == 14, str(len(m["writes"])))
        check("b11.10登记", any(p.startswith("10_") for p in paths))
        check("b11.11登记", any(p.startswith("11_") for p in paths))
        unreg = [f for f in os.listdir(pkg)
                 if re.match(r"\d{2}_", f) and not any(p.startswith(f[:3]) for p in paths)]
        check("b11.无未登记", not unreg, str(unreg))
        rm = open(os.path.join(pkg, "README.txt"), encoding="utf-8").read()
        check("b11.README两件", "10 前后对照" in rm and "11 守卫处方" in rm)


def test_docs():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH五类", all(k in zh for k in ("诊断", "深改", "守卫", "批量", "交付"))
          and "功能状态（v%s）" % hxt_core.__version__ in zh)
    check("doc.ZH12件", "00-11 共 12 个编号件" in zh)
    check("doc.ZH自检入口", "selfcheck.py" in zh)
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("doc.EN同步", "Feature status (v%s)" % hxt_core.__version__ in en
          and "selfcheck" in en and "12-item submission bundle" in en)
    faq = open(os.path.join(ROOT, "references/faq.md"), encoding="utf-8").read()
    check("doc.faqQ0b", "Q0b" in faq and "自查包 12 件" in faq)
    api = open(os.path.join(ROOT, "references/api.md"), encoding="utf-8").read()
    check("doc.api节", "selfcheck（v5.8.0 包内自检）" in api)
    idx = open(os.path.join(ROOT, "references/INDEX.md"), encoding="utf-8").read()
    check("doc.INDEX行", "selfcheck.py" in idx)
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs58", fs.count("v5.8") >= 2)
    src = open(os.path.join(SCRIPTS, "pipeline.py"), encoding="utf-8").read()
    check("doc.口径串", "00-11 共 12 件" in src)
    perm = open(os.path.join(ROOT, "references/permissions.md"), encoding="utf-8").read()
    check("doc.perm12", "写 00-11 共 12 个编号件" in perm and "selfcheck.py" in perm)
    # legacy 不回潮（与闸⑨ LEGACY 同源：全 .md glob，不留闸外盲区）
    import glob as _glob
    bad = []
    for w in ("00-10 共 11", "六件套", "写 8 个文件", "11 numbered items", "九件",
              "00-09 共 10", "10 numbered items", "9 numbered items", "六件数据"):
        for _md in _glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True):
            _rel = os.path.relpath(_md, ROOT)
            if _rel.startswith(("tests" + os.sep, ".git" + os.sep)):
                continue
            if w in open(_md, encoding="utf-8").read():
                bad.append("%s:%s" % (_rel, w))
    check("doc.legacy不回潮", not bad, str(bad[:6]))


def test_version_and_docs():
    check("ver.5.8.0", hxt_core.__version__ == "5.10.0", hxt_core.__version__)
    # selfcheck 模块级卫生：禁词不得出现（permissions 验证命令口径）
    scsrc = open(os.path.join(SCRIPTS, "selfcheck.py"), encoding="utf-8").read()
    forbidden = [w for w in ("urllib", "requests", "socket", "subprocess", "os.environ")
                 if w in scsrc]
    check("sc.禁词零", not forbidden, str(forbidden))


def main():
    for fn in (test_selfcheck_cli, test_render_html, test_bundle_11,
               test_docs, test_version_and_docs):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

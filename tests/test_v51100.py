# -*- coding: utf-8 -*-
"""test_v51100 — v5.11.0 阅读地图列表化 + 外挂词表版。

覆盖：
  1. 阅读地图四组列表（ZH/EN 同构、单行压扁消除、reference 全覆盖）
  2. load_patterns extra：合并三类/权重缺省/响亮报错/缓存隔离
  3. CLI 三入口 --lexicon（detect 命中/transform 建议/pipeline 透传）
  4. 文档接线：feature_status v5.11/api 行/customization schema
  5. 版本锚
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


def test_reading_map():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    # 四组列表存在
    check("rm.ZH四组", all(k in zh for k in ("**上手 / 排错**", "**流程 / 场景**",
                                             "**边界 / 合规**", "**参考 / 工具**")))
    check("rm.EN四组", all(k in en for k in ("**Start / troubleshoot**", "**Flow / scenarios**",
                                             "**Limits / compliance**", "**Reference / tools**")))
    # 单行压扁消除（原格式特征：同一行含「排错→」与「程序化→」）
    for ln in zh.splitlines():
        if "阅读地图" in ln:
            check("rm.ZH非单行压扁", not ("排错→" in ln and "程序化→" in ln))
            break
    # reference 全覆盖（闸 m3 语义：主文件指到每个 reference）
    refs = [f for f in os.listdir(os.path.join(ROOT, "references")) if f.endswith(".md")]
    missing = [f for f in refs if f.split(".")[0] not in zh and f not in zh]
    check("rm.ZH引用全覆盖", not missing, str(missing))
    missing_en = [f for f in refs if f.split(".")[0] not in en and f not in en]
    check("rm.EN引用全覆盖", not missing_en, str(missing_en))
    check("rm.行数墙", zh.count("\n") + 1 <= 280, str(zh.count("\n") + 1))


def test_load_patterns_extra():
    with tempfile.TemporaryDirectory() as td:
        lx = os.path.join(td, "lex.json")
        json.dump({"vocabulary": [{"w": "单元测试黑话", "alt": "规范说法"}],
                   "ai_freq_vocab": [{"w": "此外", "alt": "x"}],
                   "term_guards": [{"term": "示例术语", "allow_before": ["正当"], "allow_after": []}],
                   "auto_fixes": []}, open(lx, "w", encoding="utf-8"), ensure_ascii=False)
        base = hxt_core.load_patterns("zh")
        hxt_core.clear_pattern_cache()
        merged = hxt_core.load_patterns("zh", extra=lx)
        check("lex.合并vocabulary", any(e["w"] == "单元测试黑话" for e in merged["vocabulary"]))
        check("lex.合并aifreq", any(e["w"] == "此外" for e in merged["ai_freq_vocab"]))
        check("lex.合并guards", any(g["term"] == "示例术语" for g in merged["term_guards"]))
        _cust = [e for e in merged["ai_freq_vocab"] if e.get("fam") == "custom"]
        check("lex.权重缺省", _cust and all(e.get("weight") is not None
                                            for e in _cust),
              str(_cust[:2]))
        check("lex.内置不受污染", not any(e["w"] == "单元测试黑话" for e in base["vocabulary"]))
        hxt_core.clear_pattern_cache()
        # 缓存隔离：同 extra 二次加载命中缓存且内容一致
        m2 = hxt_core.load_patterns("zh", extra=lx)
        check("lex.缓存命中", any(e["w"] == "单元测试黑话" for e in m2["vocabulary"]))
        hxt_core.clear_pattern_cache()
        # 响亮报错
        bad = os.path.join(td, "bad.json")
        open(bad, "w", encoding="utf-8").write("not json")
        try:
            hxt_core.load_patterns("zh", extra=bad)
            check("lex.响亮报错", False)
        except ValueError:
            check("lex.响亮报错", True)
        hxt_core.clear_pattern_cache()


def test_cli_lexicon():
    with tempfile.TemporaryDirectory() as td:
        lx = os.path.join(td, "lex.json")
        json.dump({"vocabulary": [{"w": "单元测试黑话", "alt": "规范说法"}],
                   "auto_fixes": [{"pattern": "单元测试黑话", "replacement": "规范说法",
                                   "note": "外挂替换"}]},
                  open(lx, "w", encoding="utf-8"), ensure_ascii=False)
        f = os.path.join(td, "body.txt")
        open(f, "w", encoding="utf-8").write(
            "这里全是单元测试黑话的堆叠，单元测试黑话到处都是。综上所述，本文具有重要意义。"
            "该项目赋能闭环。结果显著。此外，单元测试黑话还在扩散。值得注意的是，"
            "单元测试黑话泛滥。总的来说，单元测试黑话需要清理。随着研究的深入，"
            "单元测试黑话仍在增加。") * 1
        r_on = run_cli([SCRIPTS + "/detect.py", f, "--lexicon", lx])
        check("cli.detect命中", "单元测试黑话" in r_on.stdout)
        r_off = run_cli([SCRIPTS + "/detect.py", f])
        check("cli.detect无外挂零命中", "单元测试黑话" not in r_off.stdout)
        # transform：外挂 auto_fixes 真实生效（机械替换被应用）
        r_t = run_cli([SCRIPTS + "/transform.py", f, "--lexicon", lx])
        _tj = {}
        try:
            _tj = json.loads(r_t.stdout[r_t.stdout.index("{"):])
        except Exception:
            pass
        check("cli.transform外挂替换", "外挂替换" in (_tj.get("applied_fixes") or {}),
              str(_tj.get("applied_fixes")))
        # 管线透传（外挂 vocabulary 命中归入 zh_jargon 族=「中文 AI 黑话」类别）
        r_p = run_cli([SCRIPTS + "/pipeline.py", f, "--lexicon", lx])
        check("cli.pipeline透传", r_p.returncode == 0 and "中文 AI 黑话" in r_p.stdout,
              "rc=%s out=%s" % (r_p.returncode, r_p.stdout[:80]))
        r_p2 = run_cli([SCRIPTS + "/pipeline.py", f])
        check("cli.pipeline无外挂对照", "单元测试黑话" not in r_p2.stdout
              or r_p2.stdout.count("中文 AI 黑话") < r_p.stdout.count("中文 AI 黑话"))
        # 响亮报错
        r_e = run_cli([SCRIPTS + "/detect.py", f, "--lexicon", os.path.join(td, "nope.json")])
        check("cli.响亮报错", r_e.returncode != 0 and "外挂词表不可读" in (r_e.stderr or ""))


def test_docs():
    fs = open(os.path.join(ROOT, "references/feature_status.md"), encoding="utf-8").read()
    check("doc.fs511", fs.count("v5.11") >= 2)
    api = open(os.path.join(ROOT, "references/api.md"), encoding="utf-8").read()
    check("doc.api行", "--lexicon" in api)
    cus = open(os.path.join(ROOT, "references/customization.md"), encoding="utf-8").read()
    check("doc.schema", "--lexicon" in cus and "ai_freq_vocab" in cus
          and "单一来源" in cus)
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("doc.ZH", "--lexicon" in zh and "功能状态（v%s）" % hxt_core.__version__ in zh)
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("doc.EN", "external lexicon" in en and "Feature status (v%s)" % hxt_core.__version__ in en)


def test_version():
    check("ver.5.11.0", hxt_core.__version__ == "5.21.0", hxt_core.__version__)
    # scan 旧调用兼容（不带 lexicon 关键字）
    r = hxt_core.scan("综上所述，本文具有重要意义。该项目赋能闭环。", source_ext=".txt")
    check("scan.旧签名兼容", "score" in r)


def main():
    for fn in (test_reading_map, test_load_patterns_extra, test_cli_lexicon,
               test_docs, test_version):
        print("── %s" % fn.__name__)
        fn()
    print("\n通过 %d / 失败 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        print("FAILED:", *FAIL, sep="\n  - ")
        sys.exit(1)


if __name__ == "__main__":
    main()

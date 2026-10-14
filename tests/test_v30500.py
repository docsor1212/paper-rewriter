# -*- coding: utf-8 -*-
"""test_v30500 — v3.5.0 检查清单与文档架构版（固定位命名：M1+m2+p2）。

覆盖（六模块移植验收）：
  1. M2 卡片断言：desc 首行前缀/需求词头 120 字符/品牌词不在首 60 字符/Skip when
  2. M3 文档架构：能力×边界表/INDEX 路由/三行块全覆盖/pitfalls 新条目/台账/下沉
  3. check_stats 动词前导词（纳入/入选）
  4. 版本规则：test_v30500 命名本身=模块 0.4 的首个执行样例
运行：python3 tests/test_v30500.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import hxt_core  # noqa: E402
import check_stats as cs  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))


def run_cli(args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT, env=env, timeout=120)


def test_m2_card():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    m = re.search(r"description: >\n((?:  .*\n)+?)(?=allowed-tools:)", zh)
    desc = " ".join(l.strip() for l in m.group(1).splitlines())
    check("m2.desc 首行前缀", desc.startswith("论文改写与降AI率工具"))
    check("m2.需求词头 120 字符",
          all(w in desc[:120] for w in ("论文改写", "降AI率", "去AI味")),
          desc[:120])
    check("m2.品牌词不在首 60 字符", "学术写作风格工具箱" not in desc[:60])
    check("m2.Skip when 负触发器", "Skip when" in desc)
    check("m2.desc ≤1024", len(desc) <= 1024, str(len(desc)))


def test_m3_docs():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    check("m3.能力×边界表（ZH/EN）",
          "能力×边界" in zh and "Capability × boundary" in en)
    check("m3.三节下沉（诚实边界/权限/自定义摘要化）",
          all(s in zh for s in ("诚实边界（摘要）", "权限与环境声明（摘要）", "自定义（摘要）"))
          and os.path.exists(os.path.join(ROOT, "references/honest_boundaries.md"))
          and os.path.exists(os.path.join(ROOT, "references/permissions.md"))
          and os.path.exists(os.path.join(ROOT, "references/customization.md")))
    check("m3.INDEX 路由表存在", os.path.exists(os.path.join(ROOT, "references/INDEX.md")))
    # 三行块全覆盖（除 INDEX 自身）
    missing = []
    for fn in sorted(os.listdir(os.path.join(ROOT, "references"))):
        if not fn.endswith(".md") or fn == "INDEX.md":
            continue
        head = open(os.path.join(ROOT, "references", fn), encoding="utf-8").read()[:200]
        if "何时读我" not in head or "回 [INDEX](INDEX.md)" not in head:
            missing.append(fn)
    check("m3.references 三行块全覆盖", not missing, str(missing))
    check("m3.pitfalls 防重复烧钱条目", "反复跑同一分析" in
          open(os.path.join(ROOT, "references/pitfalls.md"), encoding="utf-8").read())
    check("m3.主文件指针可发现性（主文件指到每个 reference）",
          all(fn.split('.')[0] in zh or fn in zh
              for fn in os.listdir(os.path.join(ROOT, "references")) if fn.endswith(".md")))
    check("m3.ZH 行数瘦身达标（≤280）", zh.count("\n") + 1 <= 280,
          str(zh.count("\n") + 1))


def test_stats_verbs():
    hits = cs.check_group_ns("本研究最终纳入干预组（n=118）。", source="a.md") + \
           cs.check_group_ns("纳入干预组（n=120）。", source="b.md")
    merged = cs._LABEL_PREFIX_WIDE_RX
    check("m4stats.动词前导词在宽前缀表", merged.search("纳入干预组") is not None
          and merged.search("本研究最终纳入干预组") is not None)


def test_ledger():
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "d.md")
        open(f, "w", encoding="utf-8").write(
            "众所周知，本研究具有重要意义。干预组（n=45）。\n")
        broot = os.path.join(td, "b")
        r = run_cli([os.path.join(SCRIPTS, "pipeline.py"), f,
                     "-o", os.path.join(td, "o.txt"), "--bundle", broot])
        subs = [d for d in os.listdir(broot) if d.startswith("自查包_")]
        led = os.path.join(broot, subs[0], "07_问题台账.md")
        check("m3.5.台账生成", os.path.exists(led))
        txt = open(led, encoding="utf-8").read()
        check("m3.5.台账三值+预算行",
              "unresolved" in txt and "预算台账" in txt and "zh_eightleg" in txt,
              txt[:200])


def test_rules():
    check("rules.版本 3.5.0", hxt_core.__version__ == "3.5.0")
    M, mi, pa = (int(x) for x in hxt_core.__version__.split("."))
    check("rules.本套件文件名=固定位命名", os.path.basename(__file__) ==
          f"test_v{M:01d}{mi:02d}{pa:02d}.py", os.path.basename(__file__))


def main():
    test_m2_card()
    test_m3_docs()
    test_stats_verbs()
    test_ledger()
    test_rules()
    print("\n%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()

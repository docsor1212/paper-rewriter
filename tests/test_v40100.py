# -*- coding: utf-8 -*-
"""test_v40100 — v4.1.0 dn 对齐版（固定位命名）。

覆盖：
  1. dn 六落点一致：frontmatter/预检常量/三套件断言同为新 dn「论文降AI率·…」
  2. 阅读地图前移：双语 TL;DR 区域 30 秒路由可见（前 40 行内）
  3. 两层分工消歧：双语一句话在头部
  4. plan 交接块尾部一句命令提示
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail and not cond else ""))

NEW_DN = "论文降AI率·去AI味改写｜论文改写·学术表达优化"
OLD_DN = "降AI率·去AI味改写｜论文改写·学术表达优化"


def test_dn():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    check("dn.frontmatter 新值", "displayName: " + NEW_DN in zh)
    check("dn.frontmatter 行精确", any(
        l.strip() == "displayName: " + NEW_DN for l in zh.splitlines()))
    pre = open(os.path.expanduser("~/release_tools/pr_preflight.py"), encoding="utf-8").read()
    check("dn.preflight 常量", 'DN = "%s"' % NEW_DN in pre)
    pub = open(os.path.expanduser("~/release_v100_humanize/sh_publish_pr_41.py"),
               encoding="utf-8").read() if os.path.exists(
        os.path.expanduser("~/release_v100_humanize/sh_publish_pr_41.py")) else ""
    if pub:
        check("dn.publish 脚本", 'DISPLAY_NAME = "%s"' % NEW_DN in pub)
    for f in ("test_offline_v300.py", "test_offline_v330.py", "test_offline_v340.py"):
        t = open(os.path.join(ROOT, "tests", f), encoding="utf-8").read()
        # 旧 dn 是新 dn 的子串——按整行/整串精确形态断言
        check("dn.%s 断言对齐" % f,
              ('displayName: %s" in zh)' % NEW_DN) in t
              and ('displayName: %s" in zh)' % OLD_DN) not in t)


def test_doc_moves():
    zh = open(os.path.join(ROOT, "SKILL_ZH.md"), encoding="utf-8").read()
    en = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    zh_head = zh.split("\n", 40)[0:40]
    check("map.ZH 阅读地图前 40 行", any("阅读地图（30 秒路由" in l for l in zh_head))
    check("map.ZH 两层分工头部", "两层分工一句话" in zh_head[-10:] or any("两层分工" in l for l in zh_head))
    check("map.ZH 无双份", zh.count("阅读地图（30 秒路由") == 1)
    en_head = en.split("\n", 40)[0:40]
    check("map.EN 前 40 行", any("Reading map (30-second" in l for l in en_head))
    check("map.EN 两层消歧", "Two layers in one line" in en)
    check("map.EN 无双份", en.count("Reading map (30-second") == 1)
    # plan 交接块一句命令提示
    t = open(os.path.join(SCRIPTS, "plan.py"), encoding="utf-8").read()
    check("plan.handoff 一句命令提示", "--handoff <本文件>" in t)


def main():
    test_dn()
    test_doc_moves()
    print("\n%d PASS / %d FAIL" % (len(PASS), len(FAIL)))
    if FAIL:
        sys.exit(1)
    print("OK")

if __name__ == "__main__":
    main()

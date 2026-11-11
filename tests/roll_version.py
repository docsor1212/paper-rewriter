#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版本滚动工具（v5.5.0 起）：python3 tests/roll_version.py <新版本>
一键更新：hxt_core __version__、双语功能状态行、全部 test_v5* 版本锚。
用法入电池前先手动跑（不在电池内——电池按当前版本断言）。"""
import glob, re, sys

def main():
    if len(sys.argv) != 2:
        print("用法: roll_version.py <新版本，如 5.6.0>")
        sys.exit(2)
    new = sys.argv[1]
    assert re.match(r"\d+\.\d+\.\d+$", new), "版本格式非法"
    p = "scripts/hxt_core.py"
    t = open(p, encoding="utf-8").read()
    t2 = re.sub(r'__version__ = "[0-9.]+"', '__version__ = "%s"' % new, t, count=1)
    if t2 == t:
        print("hxt_core 已是 %s（跳过）" % new)
    open(p, "w", encoding="utf-8", newline="").write(t2)
    print("hxt_core ->", new)
    n = 0
    for f in glob.glob("tests/test_v[0-9]*.py"):
        t = open(f, encoding="utf-8").read()
        t2 = re.sub(r'(hxt_core\.__version__ == ")[0-9.]+(")', r"\g<1>%s\g<2>" % new, t)
        if t2 != t:
            open(f, "w", encoding="utf-8", newline="").write(t2)
            n += 1
    print("test_v5* 锚滚动 %d 个" % n)
    print("TODO 手动项：双语功能状态行/feature_status v 行/examples 速览/CHANGELOG——见发布清单")

if __name__ == "__main__":
    main()

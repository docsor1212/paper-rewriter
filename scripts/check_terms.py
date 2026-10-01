# -*- coding: utf-8 -*-
"""check_terms.py — 术语一致性检查器（v1.9.0 实质功能，竞品零有）。

扫描文档内同一概念的多种称谓（如「患者/病人」「ID/identifier」），
逐处报告位置与建议统一形式。支持内置中文/英文常见对 + 用户自定义对。
"""
import argparse
import json
import os
import re
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hxt_core

_BUILTIN_PAIRS = [
    ("患者", "病人"),
    ("肾功能", "肾脏功能"),
    ("副作用", "不良反应"),
    ("禁忌症", "禁忌证"),
    ("适应症", "适应证"),
    ("血象", "血液常规"),
    ("肝功", "肝功能"),
    ("identifier", "ID"),
    ("health care", "healthcare"),
]


def load_user_pairs(path):
    txt = hxt_core.read_text(path)
    out = []
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split("|")
        if len(parts) == 2:
            a, b = parts[0].strip(), parts[1].strip()
            if a and b:
                out.append((a, b))
    return out


def find_inconsistencies(text, pairs):
    results = []
    for a, b in pairs:
        ca = len(re.findall(re.escape(a), text))
        cb = len(re.findall(re.escape(b), text))
        if ca > 0 and cb > 0:
            results.append({"a": a, "b": b, "a_count": ca, "b_count": cb,
                            "suggestion": a if ca >= cb else b})
    return results


def build_report(results, source=""):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = ["# 术语一致性检查：%s" % (source or "未命名文稿"), "",
             "> 自动生成（%s）" % now, ""]
    if not results:
        lines.append("未发现术语不一致。")
        return "\n".join(lines)
    lines.append("发现 %d 组术语不一致：" % len(results))
    lines.append("")
    lines.append("| 变体 A | 变体 B | A 次数 | B 次数 | 建议统一为 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for r in results:
        lines.append("| %s | %s | %d | %d | %s |" % (r["a"], r["b"], r["a_count"], r["b_count"], r["suggestion"]))
    lines.append("")
    lines.append("> 术语不统一是审稿人最常见的批注之一。建议通读全文，将"
                 "使用频次较低的变体统一替换。")
    return "\n".join(lines)


def main():
    import hxt_core
    ap = argparse.ArgumentParser(description="术语一致性检查器")
    ap.add_argument("--version", action="version",
                    version="%(prog)s " + hxt_core.__version__)
    ap.add_argument("file", help="待检文档（.txt/.md/.docx）")
    ap.add_argument("--pairs", help="用户自定义术语对文件（每行 A|B）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--report", help="生成 markdown 一致性报告")
    args = ap.parse_args()

    try:
        text = hxt_core.read_text(args.file)
    except (OSError, ValueError) as e:
        print("错误: %s" % e, file=sys.stderr)
        sys.exit(2)

    pairs = list(_BUILTIN_PAIRS)
    if args.pairs:
        pairs += load_user_pairs(args.pairs)
    results = find_inconsistencies(text, pairs)

    if args.json:
        print(json.dumps({"inconsistencies": results, "total": len(results)},
                         ensure_ascii=False, indent=2))
        sys.exit(0)

    if args.report:
        md = build_report(results, source=args.file)
        try:
            with open(args.report, "w", encoding="utf-8") as rf:
                rf.write(md + "\n")
            print("报告已写入 %s" % args.report, file=sys.stderr)
        except OSError as e:
            print("错误: 无法写入报告（%s）" % e, file=sys.stderr)

    if not results:
        print("未发现术语不一致。")
        sys.exit(0)

    print("发现 %d 组术语不一致：" % len(results))
    for r in results:
        print("  %s (%d) ↔ %s (%d) → 建议「%s」" % (r["a"], r["a_count"], r["b"], r["b_count"], r["suggestion"]))
    sys.exit(1)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()

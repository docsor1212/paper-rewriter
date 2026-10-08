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

# v3.0.0 域包制：内置对按学科域分组（--pack 选域 / 默认全量=向后兼容）。
# 嵌套铁律（v2.8.0 狼疮教训制度化）：任何变体不得是另一变体的子串——
# findall(子串) 会把包含它的长变体也计进去，次数虚高。validate_packs() 在测试里断言。
_TERM_PACKS = {
    "通用": [
        ("患者", "病人"),
        ("肾功能", "肾脏功能"),
        ("副作用", "不良反应"),
        ("禁忌症", "禁忌证"),
        ("适应症", "适应证"),
        ("血象", "血液常规"),
        # ("肝功","肝功能") v3.0.0 移除：肝功 ⊂ 肝功能 天然嵌套（狼疮同类），
        # findall(肝功) 会把「肝功能」也计入——validate_packs() 拦截证实
        ("identifier", "ID"),
        ("health care", "healthcare"),
    ],
    "风湿免疫": [
        ("SLE", "系统性红斑狼疮"),
    ],
    "内分泌": [
        ("T2DM", "2型糖尿病"),
        ("HbA1c", "糖化血红蛋白"),
        ("甲减", "甲状腺功能减退"),
        ("DKA", "糖尿病酮症酸中毒"),
    ],
    "心血管": [
        ("HF", "心力衰竭"),
        ("HF", "心衰"),
        ("AMI", "急性心肌梗死"),
        ("AF", "心房颤动"),
        ("PCI", "经皮冠状动脉介入治疗"),
        ("CHD", "冠心病"),
    ],
    "肿瘤": [
        ("NSCLC", "非小细胞肺癌"),
        ("化疗", "化学治疗"),
        ("实体瘤", "实体肿瘤"),
    ],
    "呼吸": [
        ("COPD", "慢性阻塞性肺疾病"),
        ("ARDS", "急性呼吸窘迫综合征"),
    ],
    "消化": [
        ("GERD", "胃食管反流病"),
        ("IBS", "肠易激综合征"),
    ],
    "神经": [
        ("脑卒中", "中风"),
        ("TIA", "短暂性脑缺血发作"),
    ],
}

_BUILTIN_PAIRS = [(a, b) for _pk, ps in sorted(_TERM_PACKS.items()) for a, b in ps]

_PAIR_PACK = {}
for _pk, _ps in _TERM_PACKS.items():
    for _a, _b in _ps:
        _PAIR_PACK[(_a, _b)] = _pk


def validate_packs():
    """嵌套安全校验：返回违规清单 [(变体A, 变体B, 所属域)]（A 是 B 的子串）。
    空列表=全部安全。测试套件对此断言为空。"""
    bad = []
    allvars = [(v, pk) for pk, ps in _TERM_PACKS.items() for pr in ps for v in pr]
    for i, (v1, p1) in enumerate(allvars):
        for v2, p2 in allvars:
            if v1 != v2 and v1 in v2:
                bad.append((v1, v2, p1))
    return bad


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
    lines.append("| 域 | 变体 A | 变体 B | A 次数 | B 次数 | 建议统一为 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for r in results:
        lines.append("| %s | %s | %s | %d | %d | %s |" % (r.get("pack", ""), r["a"], r["b"], r["a_count"], r["b_count"], r["suggestion"]))
    lines.append("")
    lines.append("> 术语不统一是审稿人最常见的批注之一。建议通读全文，将"
                 "使用频次较低的变体统一替换。")
    return "\n".join(lines)


def main():
    import hxt_core
    ap = argparse.ArgumentParser(description="术语一致性检查器")
    ap.add_argument("--version", action="version",
                    version="%(prog)s " + hxt_core.__version__)
    ap.add_argument("file", nargs="?", help="待检文档（.txt/.md/.docx）")
    ap.add_argument("--pairs", help="用户自定义术语对文件（每行 A|B）")
    ap.add_argument("--pack", help="只跑指定域包（如 心血管）；默认全量")
    ap.add_argument("--list-packs", action="store_true",
                    help="列出全部域包及对数后退出")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--report", help="生成 markdown 一致性报告")
    args = ap.parse_args()

    if args.list_packs:
        for pk in sorted(_TERM_PACKS):
            print("%s（%d 对）" % (pk, len(_TERM_PACKS[pk])))
        sys.exit(0)
    if not args.file:
        ap.error("缺少待检文档")
    if args.pack and args.pack not in _TERM_PACKS:
        ap.error("未知域包 %r；--list-packs 查看（%s）"
                 % (args.pack, "/".join(sorted(_TERM_PACKS))))

    try:
        text = hxt_core.read_text(args.file)
    except (OSError, ValueError) as e:
        print("错误: %s" % e, file=sys.stderr)
        sys.exit(2)

    pairs = ([(a, b) for a, b in _TERM_PACKS[args.pack]] if args.pack
             else list(_BUILTIN_PAIRS))
    if args.pairs:
        # 用户对去重合并：与内置对字面相同的不再追加（避免重复行且被误标内置域名）
        seen = set(pairs)
        for pr in load_user_pairs(args.pairs):
            if pr not in seen:
                pairs.append(pr)
                seen.add(pr)
    results = find_inconsistencies(text, pairs)
    for r in results:
        r["pack"] = _PAIR_PACK.get((r["a"], r["b"]), "用户自定义")

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
        print("  [%s] %s (%d) ↔ %s (%d) → 建议「%s」" % (r.get("pack", ""), r["a"], r["a_count"], r["b"], r["b_count"], r["suggestion"]))
    sys.exit(1)


if __name__ == "__main__":
    hxt_core.cli_entry(main)

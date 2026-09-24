# -*- coding: utf-8 -*-
"""detect.py — 风格特征自查（本地启发式，非任何官方检测分数）。

用法:
    python scripts/detect.py 文件.txt
    python scripts/detect.py 文件.txt -j          # JSON 输出
    python scripts/detect.py 文件.txt -s          # 只看分数
    python scripts/detect.py 文件.txt --lang zh   # 强制语言
    echo "文本" | python scripts/detect.py        # stdin

退出码: 0 正常 | 2 用法/文件错误
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hxt_core

LEVELS = {"低": "基本无模板腔特征", "中": "有一定模板腔特征", "高": "模板腔特征明显", "极高": "模板腔特征极重/含模型残留"}


def main():
    ap = argparse.ArgumentParser(description="写作风格特征自查（本地启发式）")
    ap.add_argument("file", nargs="?", help="文本文件；缺省读 stdin")
    ap.add_argument("-j", "--json", action="store_true", help="JSON 输出")
    ap.add_argument("-s", "--score", action="store_true", help="只输出分数与档位")
    ap.add_argument("--lang", choices=["zh", "en", "mix", "auto"], default="auto")
    ap.add_argument("--profile", choices=["academic", "general"], default="academic",
                    help="academic=论文口径（默认）；general=非学术文本，八股/公文信号降权")
    ap.add_argument("--suggestions", help="输出修订建议工作单（markdown 侧车）到此路径")
    ap.add_argument("--version", action="version", version="%(prog)s " + hxt_core.__version__)
    args = ap.parse_args()

    if args.file:
        try:
            text = hxt_core.read_text(args.file)
        except OSError as e:
            print("错误: 无法读取文件 %s（%s）" % (args.file, e), file=sys.stderr)
            sys.exit(2)
        except ValueError as e:
            print("错误: %s" % e, file=sys.stderr)
            sys.exit(2)
    else:
        text = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")

    if not text.strip():
        print("错误: 输入为空", file=sys.stderr)
        sys.exit(2)

    r = hxt_core.scan(text, lang=None if args.lang == "auto" else args.lang,
                      profile=args.profile)

    if args.suggestions:
        guide = {"zh": "references/style_guide_zh.md",
                 "en": "references/style_guide_en.md"}.get(r["lang"],
                                                           "references/style_guide_zh.md")
        try:
            with open(args.suggestions, "w", encoding="utf-8") as f:
                f.write(hxt_core.build_suggestions(text, r, guide))
            print("修订建议工作单已写入 %s" % args.suggestions, file=sys.stderr)
        except OSError as e:
            print("错误: 无法写入 %s（%s）" % (args.suggestions, e), file=sys.stderr)
            sys.exit(2)

    if args.score:
        print("%d/%s" % (r["score"], r["level"]))
        sys.exit(0)

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0)

    # ---- 人类可读报告 ----
    lang_disp = {"zh": "中文", "en": "英文", "mix": "中英混合"}[r["lang"]]
    print("=" * 62)
    print("写作风格特征自查（本地启发式 · 非任何官方检测分数）")
    print("=" * 62)
    if args.file:
        print("文件: %s" % args.file)
    print("语言: %s | 规模: %s 单元 / %d 句 | 模式: %s" % (
        lang_disp, r["units"], r["sentences"],
        "学术论文(academic)" if r.get("profile") == "academic" else "非学术(general)"))
    print()
    print("综合评分: %d/100  [%s]" % (r["score"], r["level"]))
    if r["critical_hit"]:
        print("级别依据: 含模型残留/聊天客套/知识截止声明等硬特征 → 直接判「极高」")
    print()
    if r["categories"]:
        print("分类明细:")
        for cid in sorted(r["categories"], key=lambda k: -r["categories"][k]["count"] * r["categories"][k]["weight"]):
            c = r["categories"][cid]
            mark = " [可自动修]" if cid in hxt_core.AUTO_FIXABLE else ""
            print("  · %-28s %3d 处%s" % (c["label"], c["count"], mark))
            for s in c["samples"][:4]:
                print("      - %s" % s)
    else:
        print("未发现明显的模板腔/模型残留特征。")
    print()
    st = r["stats"]
    extra = []
    if st.get("burstiness_cv") is not None:
        extra.append("句长变异系数 %.2f" % st["burstiness_cv"])
    if st.get("connector_density") is not None:
        extra.append("连接词 %.2f/句" % st["connector_density"])
    if st.get("em_dash_density") is not None:
        extra.append("破折号 %.1f/千词" % st["em_dash_density"])
    if extra:
        print("节奏统计: %s" % " | ".join(extra))
    for note in st.get("notes", []):
        print("  ⚠ %s" % note)
    if r["guards_applied"]:
        print("术语保护: 豁免正当用法 %d 处（%s）" % (
            len(r["guards_applied"]),
            ", ".join("%s←%s" % (g["hit"], g["guard"]) for g in r["guards_applied"][:5])))
    if r["suggestions"]:
        print("改写建议(前%d条): " % len(r["suggestions"]))
        for s in r["suggestions"][:6]:
            print("  · 「%s」→ 「%s」" % (s["from"], s["to"]))
    print()
    print("下一步: python scripts/transform.py <文件> -o out.txt   # 机械清洗")
    print("       深度改写按 SKILL.md 工作流（agent 依指南执行）")
    print("       python scripts/compare.py 原稿.txt 改稿.txt      # 前后对比+完整性")
    sys.exit(0)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()

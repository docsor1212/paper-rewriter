# -*- coding: utf-8 -*-
"""pipeline.py — 一键管线：自查 → 机械清理 → 深改任务简报 → 完整性守卫。

把 SKILL.md 的五步工作流合成一条命令（面向不想串多个脚本的用户/agent）：

    python scripts/pipeline.py draft.txt -o final.txt [--terms terms.txt] [--json]

产物:
    final.txt        机械清理后的文本（深度改写由 agent 按指南执行）
    (stdout)         管线报告：前后特征分、完整性判定、给 agent 的深改任务简报

--rewrite rewritten.txt: 已有人工/agent 改稿时，直接对改稿跑守卫+对比（跳过清理）。

退出码: 0 完成（完整性 FAIL 也算完成，看报告）| 2 用法/文件错误
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hxt_core
import transform as tf
import verify as vf

GUIDE = {"zh": "references/style_guide_zh.md", "en": "references/style_guide_en.md",
         "mix": "references/style_guide_zh.md + _en.md"}


def _read(path):
    try:
        return hxt_core.read_text(path)
    except OSError as e:
        print("错误: 无法读取 %s（%s）" % (path, e), file=sys.stderr)
        sys.exit(2)
    except ValueError as e:
        print("错误: %s" % e, file=sys.stderr)
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description="一键管线：自查→清理→深改简报→守卫")
    ap.add_argument("file", help="原稿")
    ap.add_argument("-o", "--output", help="清理结果落盘文件（建议必填）")
    ap.add_argument("--rewrite", help="已有改稿（提供则跳过机械清理，直接守卫+对比）")
    ap.add_argument("--terms", help="术语表文件（每行一个）")
    ap.add_argument("--lang", choices=["zh", "en", "mix", "auto"], default="auto")
    ap.add_argument("--profile", choices=["academic", "general"], default="academic",
                    help="academic=论文口径（默认）；general=非学术文本")
    ap.add_argument("--max-length-change", type=float, default=25.0)
    ap.add_argument("--suggestions", help="输出修订建议工作单（markdown 侧车）到此路径")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--version", action="version", version="%(prog)s " + hxt_core.__version__)
    args = ap.parse_args()

    orig = _read(args.file)
    profile = args.profile
    terms = vf.load_terms(args.terms) if args.terms else None

    if args.rewrite:
        new = _read(args.rewrite)
        mode = "对已有改稿守卫"
        applied, removed = {}, []
    else:
        fixes = tf.load_fixes(None, False)
        new, applied = tf.apply_auto_fixes(orig, fixes)
        new, removed = tf.drop_flagged_sentences(new)
        new, _ = tf.normalize_quotes(new)
        mode = "机械清理"
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(new)
            except OSError as e:
                print("错误: 无法写入 %s（%s）" % (args.output, e), file=sys.stderr)
                sys.exit(2)

    ro = hxt_core.scan(orig, profile=profile)
    rn = hxt_core.scan(new, profile=profile)
    vr = vf.verify(orig, new, terms, args.max_length_change)

    lang = rn["lang"]
    top = sorted(rn["categories"].items(),
                 key=lambda kv: -kv[1]["count"] * kv[1]["weight"])[:5]
    brief = {
        "guide": GUIDE.get(lang, GUIDE["mix"]),
        "remaining_patterns": ["%s ×%d" % (v["label"], v["count"]) for _, v in top],
        "auto_fixes_applied": applied,
        "sentences_removed": len(removed),
        "next_action": ("agent 按 %s 对 %s 做深度改写（保护数字/引用/术语），"
                        "然后重跑本命令 --rewrite 改稿文件复核" % (GUIDE.get(lang, ""), args.output or "改稿"))
                      if rn["score"] >= 28 else
                      ("特征已低；按 %s 复核语义自然度即可" % GUIDE.get(lang, "指南")),
    }

    if args.suggestions:
        guide = {"zh": "references/style_guide_zh.md",
                 "en": "references/style_guide_en.md"}.get(lang,
                                                           "references/style_guide_zh.md")
        try:
            with open(args.suggestions, "w", encoding="utf-8") as f:
                f.write(hxt_core.build_suggestions(orig, rn, guide))
        except OSError as e:
            print("错误: 无法写入 %s（%s）" % (args.suggestions, e), file=sys.stderr)
            sys.exit(2)

    report = {
        "mode": mode,
        "before": {"score": ro["score"], "level": ro["level"], "critical": ro["critical_hit"]},
        "after": {"score": rn["score"], "level": rn["level"], "critical": rn["critical_hit"]},
        "verify": vr,
        "agent_brief": brief,
        "honest_note": "本地启发式风格特征评分，非任何官方检测分数",
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=" * 62)
        print("一键管线报告（%s）" % mode)
        print("=" * 62)
        print("风格特征分: %d [%s] → %d [%s]%s" % (
            ro["score"], ro["level"], rn["score"], rn["level"],
            "  ⚠ 仍含模型残留" if rn["critical_hit"] else ""))
        print("完整性守卫: %s" % ("PASS ✓" if vr["ok"] else "FAIL ✗"))
        for v in vr["violations"]:
            print("  ✗ [%s] %s" % (v["check"], v["detail"]))
        for w in vr["warnings"]:
            print("  ⚠ [%s] %s" % (w["check"], w["detail"]))
        print("深改任务简报:")
        print("  指南: " + brief["guide"])
        for p in brief["remaining_patterns"]:
            print("  · 剩余特征: " + p)
        print("  下一步: " + brief["next_action"])
        if getattr(args, "suggestions", None):
            print("修订建议工作单: " + args.suggestions)
        print("口径: " + report["honest_note"])
    sys.exit(0)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()

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
    ap.add_argument("file", nargs="?", help="文本文件；缺省读 stdin（--batch 模式下传目录）")
    ap.add_argument("-j", "--json", action="store_true", help="JSON 输出")
    ap.add_argument("-s", "--score", action="store_true", help="只输出分数与档位")
    ap.add_argument("--lang", choices=["zh", "en", "mix", "auto"], default="auto")
    ap.add_argument("--profile", choices=["academic", "general"], default="academic",
                    help="academic=论文口径（默认）；general=非学术文本，八股/公文信号降权")
    ap.add_argument("--suggestions", help="输出修订建议工作单（markdown 侧车）到此路径")
    ap.add_argument("--html", help="生成单文件 HTML 报告到此路径")
    ap.add_argument("--batch", help="批量模式：扫描目录内全部 .txt/.md/.docx/.pdf，输出逐文件评分汇总（stdout；--json/--html 可同用）")
    ap.add_argument("--review", help="生成结构化审稿报告（markdown）到此路径")
    ap.add_argument("--structure", action="store_true",
                    help="章节感知：识别论文结构（摘要/引言/方法/结果/讨论），分章节评分（方法/结果自动降权）")
    ap.add_argument("--exit-verdict", action="store_true",
                    help="自动化集成（CI/agent 管线）：按判定设退出码——0=低/无残留，"
                         "3=风格特征中及以上（需深改），4=命中模型残留（critical）。"
                         "缺省恒 0（判定写在报告里，人读口径不变）")
    ap.add_argument("--ci", action="store_true", dest="exit_verdict",
                 help="CI 门禁模式：--exit-verdict 的短别名（机器退出码 0/3/4；1 仅 pipeline）")
    ap.add_argument("--version", action="version", version="%(prog)s " + hxt_core.__version__)
    args = ap.parse_args()

    if args.batch:
        root = args.batch
        if not os.path.isdir(root):
            print("错误: --batch 需要目录（%s）" % root, file=sys.stderr)
            sys.exit(2)
        rows_out = []
        pending = []  # (fp, 行索引)——二遍重试队列（v2.5.0 stability 处方）
        for fn in sorted(os.listdir(root)):
            if not fn.lower().endswith((".txt", ".md", ".docx", ".pdf")):
                continue
            fp = os.path.join(root, fn)
            try:
                if fp.lower().endswith(".pdf"):
                    t, _pm = hxt_core.read_text_ex(fp)
                    pdf_conf = _pm.get("confidence", "")
                else:
                    t = hxt_core.read_text(fp)
                    pdf_conf = ""
                if not t.strip():
                    rows_out.append((fn, -1, "空文件", False, "-"))
                    continue
                _ext = os.path.splitext(fn)[1].lower()
                rr = (hxt_core.scan_chunked(t, lang=None if args.lang == "auto" else args.lang,
                                            profile=args.profile, source_ext=_ext)
                      if len(t) > 1_000_000 else
                      hxt_core.scan(t, lang=None if args.lang == "auto" else args.lang,
                                    profile=args.profile, source_ext=_ext))
                if pdf_conf:
                    mark_pdf = " [置信度:%s]" % pdf_conf
                    rows_out.append((fn, rr["score"], rr["level"] + mark_pdf,
                                     rr["critical_hit"], rr["lang"]))
                else:
                    rows_out.append((fn, rr["score"], rr["level"], rr["critical_hit"], rr["lang"]))
            except (OSError, ValueError):
                # 首遍失败不放弃：进二遍重试队列（超时/IO 抖动多为瞬时态）
                pending.append((fp, len(rows_out)))
                rows_out.append((fn, -1, "错误（待重试）", False, "-"))
        retried = {}  # fn -> True(重试成功) / False(重试仍败)
        for fp, idx in pending:
            fn = rows_out[idx][0]
            try:
                pdf_conf = ""
                if fp.lower().endswith(".pdf"):
                    t, _pm = hxt_core.read_text_ex(fp)
                    pdf_conf = _pm.get("confidence", "")
                else:
                    t = hxt_core.read_text(fp)
                _ext = os.path.splitext(fn)[1].lower()
                rr = (hxt_core.scan_chunked(t, lang=None if args.lang == "auto" else args.lang,
                                            profile=args.profile, source_ext=_ext,
                                            time_budget=hxt_core.SCAN_TIME_BUDGET * 2)
                      if len(t) > 1_000_000 else
                      hxt_core.scan(t, lang=None if args.lang == "auto" else args.lang,
                                    profile=args.profile, source_ext=_ext,
                                    time_budget=hxt_core.SCAN_TIME_BUDGET * 2))
                lvl = rr["level"] + (" [置信度:%s]" % pdf_conf if pdf_conf else "")
                rows_out[idx] = (fn, rr["score"], lvl, rr["critical_hit"], rr["lang"])
                retried[fn] = True
            except (OSError, ValueError) as e:
                rows_out[idx] = (fn, -1, "错误: %s（已重试 1 次）" % str(e)[:60], False, "-")
                retried[fn] = False
        if retried:
            n_ok = sum(1 for v in retried.values() if v)
            print("[重试] 二遍扫描：%d 个失败文件重试，%d 个恢复" % (len(retried), n_ok),
                  file=sys.stderr)
        if args.json:
            print(json.dumps([{"file": f, "score": s, "level": l, "critical": c, "lang": g,
                               "retried": retried.get(f, False)}
                              for f, s, l, c, g in rows_out], ensure_ascii=False, indent=2))
        else:
            print("批量扫描 %d 个文件：" % len(rows_out))
            for f, s, l, c, g in rows_out:
                mark = (" %s/%s%s" % (s, l, " ⚠残留" if c else "")) if s >= 0 else (" %s" % l)
                if retried.get(f):
                    mark += "（重试成功）"
                print("  %-36s%s" % (f, mark))
        if args.html:
            import reporter
            trs = "".join("<tr><td>%s</td><td>%s</td></tr>" % (
                reporter.esc(f),
                ("%d [%s]%s" % (s, reporter.esc(l), " ⚠残留" if c else "")) if s >= 0
                else "<span class='bad'>%s</span>" % reporter.esc(l))
                for f, s, l, c, g in rows_out)
            body = ("<div class='card'><h1>批量扫描汇总</h1><p class='meta'>%d 个文件 · %s · "
                    "%s 模式</p></div>" % (len(rows_out), reporter.esc(root),
                                           "academic" if args.profile == "academic" else "general"))
            body += ("<div class='card'><table><tr><th>文件</th><th>结果</th></tr>%s</table></div>"
                     % trs) + reporter._FOOT.format(ts=reporter._now())
            try:
                with open(args.html, "w", encoding="utf-8") as hf:
                    hf.write(reporter._page("批量扫描汇总", body))
            except OSError as e:
                print("错误: 无法写入 %s（%s）" % (args.html, e), file=sys.stderr)
                sys.exit(2)
            print("HTML 汇总已写入 %s" % args.html, file=sys.stderr)
        if args.exit_verdict:
            # fail-closed：有文件两遍重试仍扫不出 → 门禁不给放行（exit 2）
            if any(x[1] < 0 for x in rows_out):
                print("错误: 批量中存在扫描失败的文件，--exit-verdict 门禁不予放行",
                      file=sys.stderr)
                sys.exit(2)
            worst_score = max((x[1] for x in rows_out), default=0)
            worst_crit = any(x[3] for x in rows_out)
            sys.exit(hxt_core.verdict_exit_code(worst_score, worst_crit))
        sys.exit(0)

    pdf_meta = None
    if args.file:
        try:
            if args.file.lower().endswith(".pdf"):
                text, pdf_meta = hxt_core.read_text_ex(args.file)
            else:
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

    if args.structure:
        _ext = os.path.splitext(args.file or "")[1].lower()
        _stext = text
        if _ext == ".md":
            # markdown 输入：剥掉 # / ## / ** 语法标记后再做章节识别
            # （v2.3.0 与 _sections_block._normalize_heading 同口径：# 后无空格
            #   紧邻汉字也收，如 #摘要）
            import re as _re
            _stext = _re.sub(r"^#{1,6}(?:\s+|(?=[\u4e00-\u9fff]))", "", text, flags=_re.M)
            _stext = _re.sub(r"\*\*([^*\n]+)\*\*", r"\1", _stext)
        try:
            rs = hxt_core.scan_sections(_stext, lang=None if args.lang == "auto" else args.lang,
                                        profile=args.profile, source_ext=_ext)
        except ValueError as e:
            print("错误: %s" % e, file=sys.stderr)
            sys.exit(2)
        if pdf_meta:
            rs["pdf_meta"] = pdf_meta
        if args.html:
            import reporter
            try:
                with open(args.html, "w", encoding="utf-8") as hf:
                    hf.write(reporter.render_sections(rs, source=args.file or "(stdin)"))
            except OSError as e:
                print("错误: 无法写入 %s（%s）" % (args.html, e), file=sys.stderr)
                sys.exit(2)
            print("章节报告已写入 %s" % args.html, file=sys.stderr)
        if args.suggestions:
            print("[提示] --structure 模式暂不生成 --suggestions 工作单（工作单面向整文诊断）",
                  file=sys.stderr)
        if args.json:
            print(json.dumps(rs, ensure_ascii=False, indent=2))
            if args.exit_verdict:
                sys.exit(hxt_core.verdict_exit_code(
                    rs["overall_score"], rs.get("critical_hit", False)))
            sys.exit(0)
        print("=" * 62)
        print("章节感知扫描（论文结构模式）")
        print("=" * 62)
        if rs.get("pdf_meta"):
            print("PDF 抽取置信度: %s" % rs["pdf_meta"]["confidence"])
            for note in rs["pdf_meta"]["notes"]:
                print("  ⚠ %s" % note)
        print("综合: %d [%s]" % (rs["overall_score"], rs["overall_level"]))
        for x in rs["sections"]:
            sc = ("%d [%s]" % (x["score"], x["level"])) if x["score"] is not None else "不扫描（引用列表）"
            crit = " ⚠残留" if x.get("critical") else ""
            print("  %-10s %s%s（%d 字符）" % (x["label"], sc, crit, x["chars"]))
        if rs["missing_sections"]:
            print("  ⚠ 未识别到章节: %s（非 IMRaD 结构可忽略）" % "/".join(rs["missing_sections"]))
        print("口径: 方法/结果段已自动降权（文体常态）；本地启发式，非官方分数")
        if args.exit_verdict:
            sys.exit(hxt_core.verdict_exit_code(
                rs["overall_score"], rs.get("critical_hit", False)))
        sys.exit(0)

    try:
        if len(text) > 1_000_000:
            r = hxt_core.scan_chunked(text, lang=None if args.lang == "auto" else args.lang,
                                      profile=args.profile,
                                      source_ext=os.path.splitext(args.file or "")[1].lower())
        else:
            r = hxt_core.scan(text, source_ext=os.path.splitext(args.file or "")[1].lower(), lang=None if args.lang == "auto" else args.lang,
                              profile=args.profile)
    except ValueError as e:
        print("错误: %s" % e, file=sys.stderr)
        sys.exit(2)

    if pdf_meta:
        r["pdf_meta"] = pdf_meta
    r["hints"] = hxt_core.build_hints(text, r, profile=args.profile)

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

    if args.html:
        import reporter
        try:
            with open(args.html, "w", encoding="utf-8") as hf:
                hf.write(reporter.render_detect(text, r, source=args.file or "(stdin)"))
        except OSError as e:
            print("错误: 无法写入 %s（%s）" % (args.html, e), file=sys.stderr)
            sys.exit(2)
        print("HTML 报告已写入 %s" % args.html, file=sys.stderr)

    if getattr(args, "review", None):
        import reporter
        md = reporter.build_review_md(text, r, source=args.file or "(stdin)")
        try:
            with open(args.review, "w", encoding="utf-8") as rf:
                rf.write(md + "\n")
            print("审稿报告已写入 %s" % args.review, file=sys.stderr)
        except OSError as e:
            print("错误: 无法写入审稿报告（%s）" % e, file=sys.stderr)
            sys.exit(2)

    if args.score:
        print("%d/%s" % (r["score"], r["level"]))
        if args.exit_verdict:
            sys.exit(hxt_core.verdict_exit_code(r["score"], r["critical_hit"]))
        sys.exit(0)

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        if args.exit_verdict:
            sys.exit(hxt_core.verdict_exit_code(r["score"], r["critical_hit"]))
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
    if pdf_meta:
        print("PDF 抽取置信度: %s" % pdf_meta["confidence"])
        for note in pdf_meta["notes"]:
            print("  ⚠ %s" % note)
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
    if r["hints"]:
        print("处置提示:")
        for h in r["hints"]:
            print("  → %s" % h)
        print()
    print()
    print("下一步: python scripts/transform.py <文件> -o out.txt   # 机械清洗")
    print("       深度改写按 SKILL.md 工作流（agent 依指南执行）")
    print("       python scripts/compare.py 原稿.txt 改稿.txt      # 前后对比+完整性")
    if args.exit_verdict:
        sys.exit(hxt_core.verdict_exit_code(r["score"], r["critical_hit"]))
    sys.exit(0)


if __name__ == "__main__":
    hxt_core.cli_entry(main)

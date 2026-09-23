# -*- coding: utf-8 -*-
"""hxt_core.py — 学术风格工具箱共享核心：模式加载、语言识别、扫描与评分。

设计原则：
- 纯 Python 标准库，零第三方依赖，100% 本地运行，零上传。
- 诚实口径：本引擎输出的是「风格特征启发式评分」，不是任何外部服务的官方分数，
  也不说明文字由谁写成。
- 术语保护：正当学术用法（如 mutational landscape、pivotal trial、序列对齐、
  沉淀反应）不误报。朴素词表会把它们当机器腔特征，这是本引擎的核心差异化。
"""

__version__ = "1.2.0"

import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# 模式加载
# ---------------------------------------------------------------------------

def read_text(path, max_mb=5.0):
    """共享文本读取（v1.2.0 输入健壮性三重守卫）：大小上限 / 二进制识别 /
    UTF-8 BOM 剥离。错误信息均带处置建议。只读调用方显式指定的路径；
    本工具不访问网络、不读其他位置、不需要任何环境变量。"""
    size = os.path.getsize(path)
    if size > max_mb * 1024 * 1024:
        raise ValueError(
            "文件 %.1fMB 超过 %.0fMB 上限——请按章节切分后分批处理，报告也会更可读"
            % (size / 1048576.0, max_mb))
    with open(path, "rb") as f:
        data = f.read()
    if 0 in data:
        raise ValueError(
            "输入疑似二进制文件（含 NUL 字节）——请转存为 UTF-8 纯文本（.txt/.md）再处理")
    text = data.decode("utf-8-sig", errors="replace")
    # 乱码守卫：非 UTF-8 文本（GBK/UTF-16 等）解码后大量 U+FFFD，
    # 「垃圾进→干净出」是对信任判断工具最坏的失败态，必须拒绝
    if text.count(chr(0xFFFD)) / max(1, len(text)) > 0.02:
        raise ValueError(
            "输入文件解码后乱码占比过高（疑似 GBK/UTF-16 等非 UTF-8 编码）——"
            "请转存为 UTF-8 纯文本后重试")
    return text


_PATTERN_CACHE = {}

def load_patterns(lang):
    """lang: 'en' | 'zh' -> dict。带缓存。"""
    if lang in _PATTERN_CACHE:
        return _PATTERN_CACHE[lang]
    path = os.path.join(HERE, "patterns_%s.json" % lang)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # 预编译
    for key in ("model_artifacts", "chatbot_artifacts", "knowledge_cutoff"):
        for item in data.get(key, []):
            item["_re"] = re.compile(item["pattern"], re.IGNORECASE if lang == "en" else 0)
    for item in data.get("regex_signals", []):
        item["_re"] = re.compile(item["pattern"], re.IGNORECASE if lang == "en" else 0)
    _PATTERN_CACHE[lang] = data
    return data


# ---------------------------------------------------------------------------
# 语言识别与基础切分
# ---------------------------------------------------------------------------

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

def cjk_ratio(text):
    if not text:
        return 0.0
    return len(_CJK_RE.findall(text)) / max(1, len(text))


def detect_language(text):
    """返回 'zh' | 'en' | 'mix'（两类字符都显著的混合文本，两种词库都扫）。"""
    r = cjk_ratio(text)
    if r < 0.05:
        return "en"
    if r > 0.45:
        return "zh"
    return "mix"


def split_sentences(text):
    """中英混合分句。按 。！？；!?; 与英文句号+空白切分（小数点后无空白不切），保留非空句。"""
    parts = re.split(r"(?<=[。！？；!?;])\s*|(?<=\.)\s+|\n+", text)
    return [p.strip() for p in parts if p and p.strip()]


def count_units(text, lang):
    """评分单元：英文=单词数；中文=汉字数/2（量纲对齐，500字≈250词）。"""
    if lang == "zh":
        return max(1, len(_CJK_RE.findall(text)) / 2.0)
    words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)
    en_share = 1.0 - cjk_ratio(text)
    return max(1.0, len(words) * max(0.35, en_share) + len(_CJK_RE.findall(text)) / 2.0 * 0.5)


# ---------------------------------------------------------------------------
# 术语保护（学术正当用法白名单）
# ---------------------------------------------------------------------------

def guard_hit(hit_text, before="", after="", guards=None):
    """判断一次词库命中是否属于正当用法（应豁免）。

    guards: patterns_xx.json 里的 term_guards 列表，每项：
      {"term": "landscape", "allow_before": ["mutational", ...], "allow_after": [...]}
    before/after 是命中词左右各 ~30 字符的上下文。
    """
    if not guards:
        return None
    low = hit_text.lower()
    before_low = before.lower()
    after_low = after.lower()
    for g in guards:
        if g.get("term", "").lower() != low:
            continue
        for w in g.get("allow_before", []):
            if re.search(re.escape(w.lower()) + r"[\u4e00-\u9fff\-]?\s*$", before_low):
                return w
        for w in g.get("allow_after", []):
            if re.search(r"^\s*[\u4e00-\u9fff\-]?\s*" + re.escape(w.lower()), after_low):
                return w
    return None


# ---------------------------------------------------------------------------
# 扫描引擎
# ---------------------------------------------------------------------------

# 人工核对过的中文连接词（用于连接词密度统计；不进替换词库）
_ZH_CONNECTORS = ["因此", "然而", "此外", "与此同时", "总之", "综上", "首先", "其次",
                  "最后", "另外", "同时", "并且", "而且", "不仅", "而且", "从而",
                  "进而", "由此可见", "换言之", "总的来说", "总而言之", "一方面", "另一方面"]
_EN_CONNECTORS = ["however", "moreover", "furthermore", "additionally", "in addition",
                  "therefore", "thus", "consequently", "nevertheless", "overall",
                  "in conclusion", "firstly", "secondly", "finally", "meanwhile"]


def scan(text, lang=None, profile="academic"):
    """全量扫描。返回结构化 dict：
    {
      lang, score, level, critical_hit, units, sentences,
      categories: {cat_id: {label, count, weight, samples: [...]}},
      guards_applied: [...], stats: {...}, suggestions: [...]
    }
    """
    if lang not in ("zh", "en", "mix", None):
        raise ValueError("lang must be zh/en/mix/None")
    if profile not in ("academic", "general"):
        raise ValueError("profile 必须是 academic（默认，论文口径）或 general（非学术文本）")
    detected = detect_language(text)
    lang = lang if lang in ("zh", "en") else detected

    cats = {}
    guards_applied = []
    pts_acc = [0.0]  # 逐命中累计分：每类的存储 weight 仅作展示，评分必须逐条计权
    vocab_stats = {}  # word -> [hits, guarded]：改写建议必须排除被守卫豁免的词

    def add_cat(cat_id, label, weight, n, samples, count_points=True):
        c = cats.setdefault(cat_id, {"label": label, "count": 0, "weight": weight,
                                     "samples": [], "auto_fixable": cat_id in AUTO_FIXABLE})
        c["count"] += n
        if count_points:
            pts_acc[0] += weight * n
        else:
            c["weight"] = weight
        c["samples"] = (c["samples"] + samples)[:6]

    def scan_simple_list(key, cat_id, label, weight, pats):
        # chatbot/knowledge cutoff/model artifacts 不做术语保护（不存在正当用法）
        for item in pats:
            for m in item["_re"].finditer(text):
                add_cat(cat_id, label, weight, 1, [m.group(0).strip()])

    zh_pats = load_patterns("zh") if lang in ("zh", "mix") else None
    en_pats = load_patterns("en") if lang in ("en", "mix") else None

    # --- critical：模型残留 / 聊天客套 / 知识截止 ---
    for pats, tag in ((zh_pats, "zh"), (en_pats, "en")):
        if not pats:
            continue
        scan_simple_list("model_artifacts", "model_artifact_%s" % tag,
                         "模型残留 bug" if tag == "zh" else "model artifacts", 3.0,
                         pats["model_artifacts"])
        scan_simple_list("chatbot_artifacts", "chatbot_%s" % tag,
                         "聊天客套/免责声明" if tag == "zh" else "chatbot artifacts", 3.0,
                         pats["chatbot_artifacts"])
        scan_simple_list("knowledge_cutoff", "cutoff_%s" % tag,
                         "知识截止声明" if tag == "zh" else "knowledge cutoff", 3.0,
                         pats["knowledge_cutoff"])

    # --- 词表类（带术语保护） ---
    guards_zh = zh_pats.get("term_guards", []) if zh_pats else []
    guards_en = en_pats.get("term_guards", []) if en_pats else []

    def scan_vocab(pats, guards, cat_id, label, zh_mode):
        if not pats:
            return
        for entry in pats.get("vocabulary", []):
            w = entry["w"]
            flags = re.IGNORECASE if not zh_mode else 0
            # 中文无词边界：裸子串匹配，正当用法交给 term_guards 豁免；
            # 英文用 \b 防止 delve 误命中 diligently 这类长词内部
            pat = re.escape(w) if zh_mode else r"\b" + re.escape(w) + r"\b"
            for m in re.finditer(pat, text, flags):
                s, e = m.span()
                hit = m.group(0)
                g = guard_hit(hit, text[max(0, s - 30):s], text[e:e + 30], guards)
                st = vocab_stats.setdefault(w, [0, 0])
                if g:
                    st[1] += 1
                    guards_applied.append({"hit": hit, "guard": g, "position": s})
                    continue
                st[0] += 1
                alt = entry.get("alt", "")
                add_cat(cat_id, label, float(entry.get("weight", 1.0)), 1,
                        ["%s → %s" % (hit, alt)] if alt else [hit])

    scan_vocab(zh_pats, guards_zh, "zh_jargon", "中文 AI 黑话", True)
    scan_vocab(en_pats, guards_en, "en_vocab", "AI vocabulary", False)

    # --- 正则结构信号 ---
    for pats in (zh_pats, en_pats):
        if not pats:
            continue
        for item in pats.get("regex_signals", []):
            n = len(item["_re"].findall(text))
            if n:
                w0 = float(item.get("weight", 0.6))
                # general 模式：学术八股/公文过渡在人写博客、公文里是常态，降权 60%
                if profile == "general" and item.get("cat") in ("zh_eightleg", "zh_trans"):
                    w0 *= 0.4
                add_cat(item["cat"], item["label"], w0,
                        n, [item["label"]] if not item.get("show_hits") else
                        [m.group(0)[:40] for m in item["_re"].finditer(text)][:4])

    # --- 统计特征 ---
    sentences = split_sentences(text)
    units = count_units(text, lang)
    stats = _structural_stats(text, sentences, lang)
    pts = pts_acc[0]

    score, level, critical = _score(pts, stats, units, cats, lang)

    suggestions = []
    if zh_pats:
        for entry in zh_pats.get("vocabulary", []):
            st = vocab_stats.get(entry["w"], [0, 0])
            if entry.get("alt") and st[0] > st[1]:
                suggestions.append({"from": entry["w"], "to": entry["alt"]})

    return {
        "lang_detected": detected,
        "lang": lang,
        "profile": profile,
        "score": score,
        "level": level,
        "critical_hit": critical,
        "units": round(units, 1),
        "sentences": len(sentences),
        "categories": cats,
        "guards_applied": guards_applied,
        "stats": stats,
        "suggestions": suggestions[:12],
        "honest_note": "本地启发式风格特征评分，非任何官方检测分数",
    }


AUTO_FIXABLE = {"model_artifact_zh", "model_artifact_en", "chatbot_zh", "chatbot_en",
                "cutoff_zh", "cutoff_en", "zh_punct", "en_filler", "markdown"}


def _structural_stats(text, sentences, lang):
    stats = {"burstiness_cv": None, "para_variance": None, "connector_density": None,
             "em_dash_density": None, "notes": []}
    lens = [len(s) for s in sentences]
    if len(lens) >= 8:
        mean = sum(lens) / len(lens)
        var = sum((x - mean) ** 2 for x in lens) / len(lens)
        cv = (var ** 0.5) / mean if mean else 0
        stats["burstiness_cv"] = round(cv, 3)
        stats["sentence_mean_len"] = round(mean, 1)
    paras = [p for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    plens = [len(p.strip()) for p in paras]
    if len(plens) >= 4:
        mean = sum(plens) / len(plens)
        stats["para_variance"] = round(sum((x - mean) ** 2 for x in plens) / max(1, len(plens)), 1)
    n_conn = 0
    if lang in ("zh", "mix"):
        for w in _ZH_CONNECTORS:
            n_conn += len(re.findall(re.escape(w), text))
    if lang in ("en", "mix"):
        for w in _EN_CONNECTORS:
            n_conn += len(re.findall(r"\b" + re.escape(w) + r"\b", text, re.IGNORECASE))
    if sentences:
        stats["connector_density"] = round(n_conn / len(sentences), 2)
    # em-dash 是英文 AI 特征（Wikipedia）；仅统计英文语境且排除数字相邻
    # （6–8 / 50–100 这类数值范围不是修辞破折号；中文「——」是正当标点）
    if lang == "en":
        words = max(1, len(re.findall(r"[A-Za-z]+", text)))
        n_em = len(re.findall(r"(?<!\d)—(?!\d)", text))
        stats["em_dash_density"] = round(n_em / words * 1000, 2)
    return stats


# 各语言归一化系数：同等「密度」的中英文，词表稀疏度不同（中文黑话稀疏但更致命），
# 校准基准：四条语料机器腔 ≥55（高），自然文 ≤10（低）。见 tests/test_offline.py
_LANG_K = {"zh": 7.0, "en": 3.2, "mix": 5.0}


def _score(pts, stats, units, cats, lang):
    """加权命中 → 0-100 分。critical 直接拉到「极高」档并给出依据。"""
    critical = any(k.startswith(("model_artifact", "chatbot", "cutoff")) and c["count"]
                   for k, c in cats.items())
    per100 = pts / units * 100.0
    # 短文本置信折减：8 个字命中一个黑话就判「极高」是评分退福——词表密度
    # 只有在足量文本上才有统计意义。20 单元以下线性折减。
    confidence = min(1.0, units / 20.0)
    score = min(100.0, per100 * _LANG_K.get(lang, 5.0)) * confidence

    bonus = 0.0
    cv = stats.get("burstiness_cv")
    if cv is not None:
        if cv < 0.30:
            bonus += 6
            stats["notes"].append("句长高度均匀（burstiness 低，AI 典型节奏）")
        elif cv < 0.42:
            bonus += 3
    cd = stats.get("connector_density")
    if cd is not None and cd > 0.8:
        bonus += 5
        stats["notes"].append("连接词密度 %.2f/句，明显高于自然写作（正式学术散文 0.6-0.8 属正常）" % cd)
    em = stats.get("em_dash_density")
    if em is not None and em > 6.0:
        bonus += 6
        stats["notes"].append("破折号密度 %.1f/千词，Em-dash 爱好者特征" % em)
    score = min(100.0, score + bonus)

    if critical:
        score = max(score, 88.0)
    score = int(round(score))
    if score >= 75 or critical:
        level = "极高"
    elif score >= 50:
        level = "高"
    elif score >= 28:
        level = "中"
    else:
        level = "低"
    if units < 15 and not critical:
        stats["notes"].append("文本过短（<15 单元），评分仅供参考")
    return score, level, critical

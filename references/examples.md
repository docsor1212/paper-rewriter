# 完整输入输出样例（End-to-End Examples）

> 每个样例 = 真实命令 + 真实输出（来自回归语料，可复现）。样例中的数字/事实仅用于演示格式。

## 样例 1：中文改写全流程

**输入** `draft.txt`（节选，模板腔密集）：

```
综上所述，智慧医疗作为一项新兴范式，正在为整个行业赋能。一方面，它能够整合海量医疗数据，为临床决策提供新的思路；另一方面，它还可以优化资源配置，为分级诊疗制度的落地保驾护航。
```

**Step 1 自查**：

```console
$ python scripts/detect.py draft.txt
==============================================================
写作风格特征自查（本地启发式 · 非任何官方检测分数）
==============================================================
文件: draft.txt
语言: 中文 | 规模: 216.5 单元 / 13 句

综合评分: 58/100  [高]
...
改写建议(前10条):
  · 「赋能」→ 「支持 / 帮助 / 为…提供能力」
  · 「抓手」→ 「工具 / 途径 / 切入点」
```

**Step 2 机械清理**（本例无模型残留/客套句，清理近零改动——正常）：

```console
$ python scripts/transform.py draft.txt -o step1.txt
{
  "applied_fixes": {"半角逗号→全角": 2},
  "removed_sentences": [],
  "note": "机械清洗只覆盖语法安全层；黑话/八股/节奏需 agent 按指南深改，..."
}
```

**Step 3 深改**（agent 按 `references/style_guide_zh.md` 七步法执行，改后节选）：

```
智慧医疗的价值集中在两处：把分散的病历、影像和检验数据汇到一起供临床调用，以及让上级医院的诊断能力透过远程会话下沉到基层。前者的瓶颈是数据标准，后者是责任认定——这两点不解决，分级诊疗借不上智慧医疗的力。
```

**Step 4+5 守卫与对比**：

```console
$ python scripts/verify.py draft.txt step2.txt --terms terms.txt
完整性守卫 verify：PASS ✓
  数字/DOI/PMID/缩写/术语 全部保全。

$ python scripts/compare.py draft.txt step2.txt
风格特征分: 58 [高] → 12 [低]  （-46）
完整性守卫: PASS ✓
```

## 样例 2：英文模型残留清理 + 守卫拦截

**输入** `ai_paste.txt`（从聊天窗口粘贴的稿子，带残留与客套句）：

```
综上所述，本研究纳入 128 例患者，其中 68 例进入试验组（p = 0.031）。
值得注意的是，两组基线具有可比性 [cite: 1][cite: 3]，随访 24 个月。
希望以上内容对您有所帮助！如需进一步修改请告诉我。
```

**一键管线**：

```console
$ python scripts/pipeline.py ai_paste.txt -o clean.txt
==============================================================
一键管线报告（机械清理）
==============================================================
风格特征分: 47 [中] → 18 [低]
完整性守卫: PASS ✓
  数字/DOI/PMID/缩写/术语 全部保全。
深改任务简报:
  指南: references/style_guide_zh.md
  · 剩余特征: 学术八股（人写也有，看密度） ×3
  下一步: agent 按 references/style_guide_zh.md 对 clean.txt 做深度改写（保护数字/引用/术语），然后重跑本命令 --rewrite 改稿文件复核
口径: 本地启发式风格特征评分，非任何官方检测分数
```

清理效果：`[cite: 1][cite: 3]` 行内摘除（句子保留）、客套句整句移除、数字 128/68/0.031/24 全部原样。

## 样例 3：完整性守卫拦截演示（守卫不讲价）

```console
$ python scripts/verify.py 原稿.txt 改稿.txt
完整性守卫 verify：FAIL ✗（学术安全红线）
  ✗ [numbers] 数字丢失/被改: 62
  ✗ [comparison] 比较方向/比较数字被改: <0.05
判定: 未通过——请修复改稿后重跑
$ echo $?
1
```

改稿把「血沉 62mm/h」改成 58、把「P<0.05」改成「P>0.05」——无论措辞多流畅，exit 1。修的是改稿，不是守卫。

## 样例 4：术语保护（正当学术用法不误报）

```console
$ python scripts/detect.py -s
The mutational landscape was profiled in this pivotal trial; robust regression confirmed the effect. (×3)
6/低
```

mutational landscape / pivotal trial / robust regression 全部豁免；换成 "the startup landscape ... plays a pivotal role" 这类非学术语境则正常计分。

## 样例 5：markdown 稿件全链路（v2.2.0：章节感知 + 句级计划 + 守卫拦截）

**输入** `case_medical.md`（markdown 医学综述，模板腔密度中等）。v2.2.0 起
`## 摘要`/`## 方法` 等 markdown 标题直接进章节感知，.md 语法残留自动豁免。

**Step 1 自查 + 章节感知**：

```console
$ python scripts/detect.py case_medical.md --structure
章节: 题引 / 摘要 / 引言 / 方法 / 讨论 / 结论（markdown 标题逐一识别）
综合评分: 23/100  [低]
  · 学术八股（人写也有，看密度）      9 处   （综上所述 / 值得注意的是 / 众所周知…）
  · 排比/对仗结构（一方面…另一方面）   1 处
节奏统计: 句长变异系数 0.62 | 连接词 0.41/句
```

**Step 2 改写优先级计划**（v2.2.0 新增，先定位再动手）：

```console
$ python scripts/plan.py case_medical.md --json
P1 [结论] 2.2点  「…从而为临床决策的落地保驾护航。」
P2 [引言] 0.9点  「众所周知，IRAK4在Toll样受体…」
P3 [摘要] 0.8点  「取得了显著进展，为新型治疗策略的开发…」
预算投影: 改完前5句→11 | 前10句→4 | 全部→2   （线性近似，仅供排序）
```

**Step 3 agent 深改**（按 style_guide 改 P0 队列，事实全保留：1/250000、
48 篇、2005-2026、8 例/12 个月）。

**Step 4 守卫拦截过度删减**——第一版深改把 IRAK4 从 12 次引述压到 11 次：

```console
$ python scripts/verify.py case_medical.md case_medical_v2.md
  ✗ [numbers] 数字丢失/被改: 4        ← IRAK4 里的 4 连带丢失
  ✗ [latin_abbr] 大写缩写丢失: IRAK4
判定: 未通过——请修复改稿后重跑（exit 1）
```

补回自然引述（「IRAK4抑制剂的耐药机制」）后重跑：

```console
$ python scripts/verify.py case_medical.md case_medical_v2.md
判定: 通过（exit 0）| 规模 694 → 609 字符

$ python scripts/compare.py case_medical.md case_medical_v2.md
  学术八股          已清除 9 处
  翻译腔/空泛过渡    已清除 4 处
  中文 AI 黑话      已清除 2 处
  排比/对仗结构      已清除 1 处
完整性守卫: PASS ✓
```

**要点**：markdown 章节直接被识别；plan 把深改力气指向贡献最大的句子；
verify 连「缩写次数被压低」都能抓到——守卫拦的是内容损失，不是措辞。

## 样例 6：误报 → 守卫固化（v2.2.0 learn_guards）

「抓手」在词表里是营销黑话，但机械工程语境的「机械抓手」是正当术语——
守卫按上下文豁免，不是整词洗白：

```console
$ echo "装配平台的机械抓手采用气驱动设计，抓取力可调。" | python scripts/detect.py -s
46/中                                  ← 误报

$ python scripts/learn_guards.py add 抓手 --before "机械,装置" --after "采用,夹持"
已保存守卫：抓手（lang=zh，前文 2 项 / 后文 2 项）

$ echo "装配平台的机械抓手采用气驱动设计，抓取力可调。" | python scripts/detect.py -s
0/低                                   ← 机械语境豁免

$ echo "以创新为抓手，全面赋能业务增长。" | python scripts/detect.py -s
35/中                                  ← 营销语境照常计分（对照）
```

守卫存进 `scripts/user_guards.json`（升级词表不丢）；`list` 查看、
`remove 抓手` 撤销、`from-text 术语 样本.txt` 从真实语料自动提取上下文
（中英双语口径）。强制要求 `--before/--after` 上下文——纯词白名单会被拒绝。

## 样例 7：CI/agent 门禁——机器退出码（v2.3.0 --exit-verdict）

把改稿质量卡进自动化流程：改稿不达标就拦截，不需要人读报告。

```console
$ # 坏改稿：改稿=原稿（一句没改），门禁应拦截
$ python scripts/pipeline.py draft.txt --rewrite draft.txt --exit-verdict
$ echo $?
3                                    ← 风格特征中及以上（52/高），进深改队列

$ # 好改稿：事实保留、模板腔清除，门禁放行
$ python scripts/pipeline.py draft.txt --rewrite rewritten.txt --exit-verdict
完整性守卫: PASS ✓
$ echo $?
0

$ # JSON 里的同源字段（agent 管线直接读）
$ python scripts/pipeline.py draft.txt --rewrite draft.txt --json | jq .exit_verdict
3
```

退出码全表（0/1/3/4/2 两套口径）：`references/errors.md` 第一节。
`detect --exit-verdict` / `compare --exit-verdict` 只出 0/3/4——完整性 FAIL
的 exit 1 契约专属 verify.py 与 pipeline。

## 样例 8：确定性深改档（v2.4.0 --deep）+ 处置提示

**输入**（模板腔中文段落）：

```
综上所述，本研究验证了假设。值得注意的是，该方法不仅提升了精度，而且降低了成本。众所周知，数据见第3.2节，p=0.03。
```

**transform --deep（句式级确定性转换，--track 可审计）**：

```console
$ python scripts/transform.py in.txt -o out.txt --deep --track track
深改档: 句首八股删除 ×3
深改档: 排除式连接合并 ×1

$ cat out.txt
本研究验证了假设。该方法提升了精度，且降低了成本。数据见第3.2节，p=0.03。
```

**守卫确认零损失**：

```console
$ python scripts/verify.py in.txt out.txt
  数字/DOI/PMID/缩写/术语 全部保全。
判定: 通过
```

track.md 里每笔深改操作独立可查（`深改档:句首八股删除 ×3`）。
--deep 只做零信息损失操作（删纯套话标记/拆排除式连接）；黑话替换、
节奏重排、立场重写仍由 agent 按指南执行——两层互补，不互相替代。

**处置提示（v2.4.0，报告尾部 + JSON hints 字段）**——非论文文体自动建议切 profile：

```console
$ python scripts/detect.py blog_post.txt
…
处置提示:
  → 深改排序：python scripts/plan.py <文件> -o plan.md 生成句级优先级计划
  → 未识别到论文章节且特征以标点/翻译腔为主——非论文文体（博客/公文/通知）
    可加 --profile general 降权八股信号
```

## 样例 9：集中异常层 + 批量重试 + 单步超时（v2.5.0）

**两行中文错误（错误 + 处置建议）**——所有 CLI 统一格式，非技术用户也能照着做：

```console
$ python scripts/detect.py photo.png
错误: 输入疑似二进制文件（含 NUL 字节）——请转存为 UTF-8 纯文本（.txt/.md）再处理
```

**批量二遍重试**——首遍失败的文件自动以双倍时间预算重扫一次，瞬时故障
（负载抖动导致超时等）第二遍即恢复；真坏文件如实标注"已重试"：

```console
$ python scripts/detect.py --batch ./papers
[重试] 二遍扫描：1 个失败文件重试，0 个恢复
  a.txt                                0/低
  broken.txt                           错误: 输入疑似二进制文件…（已重试 1 次）
```

`--json` 输出逐文件携带 `retried` 字段（true=重试后成功）。

**单步超时与耗时透明**——`--step-timeout`（缺省 120 秒）管住清理与扫描
每一步，超时干净报错；JSON 报告新增 `timings`：

```console
$ python scripts/pipeline.py draft.txt -o out.txt
耗时: 清理 0.0s | 扫描 0.1s | 守卫 0.0s（合计 0.2s，单步预算 120 秒）

$ python scripts/pipeline.py draft.txt -o out.txt --json | jq .timings
{ "cleanup_s": 0.0, "scan_s": 0.11, "verify_s": 0.0, "total_s": 0.11 }
```

## 样例 10：风格画像——深改的量化验收（v2.6.0 stylecheck）

**单文件画像**（AI 语料演示，黑话命中定位到段）：

```console
$ python scripts/stylecheck.py draft.txt
| 指标 | 值 | 档位 |
|---|---|---|
| 黑话密度（每千字） | 36.81 | 偏机器 |
| 句长变异系数 | 0.388 | 自然 |
| 最高频句首占比 | 0.077 | 自然 |
| 最长连续同开场 | 1 | 自然 |

## 重点段落（黑话命中降序）
- 第 1 段（104 字/3 句，命中 4）：赋能 → 支持 / 帮助 / 为…提供能力
- 第 2 段（112 字/4 句，命中 5）：保驾护航 → 保障 / 支持
- 第 4 段（126 字/2 句，命中 5）：抓手 → 工具 / 途径 / 切入点
```

**--compare 验收差值**（AI 语料 → 人写语料的演示对比，深改实际效果介于其间）：

```console
$ python scripts/stylecheck.py 原稿.txt 改稿.txt --compare
| 黑话密度（每千字） | 36.81 | 0.0 | 偏机器 → 自然 |
黑话命中合计：18 → 0（-18）
```

档位阈值用本地语料校准（AI 语料黑话密度 17-37/千字 vs 人写 0），只做验收
提示、不改评分；改稿完整性仍以 verify.py 为准。深改验收闭环：
plan.py 排队列 → agent 按指南改 → --compare 看画像差值 → verify 过守卫。

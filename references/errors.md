# 错误码与处置速查（Error Codes Reference）

> 全部 CLI 脚本的退出码、违规/告警类别、触发条件与处置动作的统一映射表。
> 程序化集成请以 `verify.py` 的退出码为契约（见下表）；其余脚本把判定写在输出里。

## 一、退出码（CLI 契约）

**缺省口径**（不带 `--exit-verdict`，人读/人工流程）：

| 退出码 | 脚本 | 含义 | 处置 |
|---|---|---|---|
| 0 | 全部 | 完成（verify: 完整性 PASS） | 正常继续；其余脚本的判定读输出报告 |
| 1 | **仅 verify.py** | 完整性守卫 FAIL——改稿动了数字/引用/术语 | **修改改稿**，不是改守卫、不是换参数 |
| 2 | 全部 | 用法或文件错误 | 看 stderr 提示：路径错/文件空/二进制/编码/超限，每条提示自带处置建议 |

> pipeline.py / compare.py 的守卫判定在输出报告的「完整性守卫: PASS/FAIL」行；按退出码分支的脚本请调 verify.py。

**自动化口径**（v2.3.0：detect/compare/pipeline 加 `--exit-verdict` 后）：

| 退出码 | 含义 | 典型 CI 动作 |
|---|---|---|
| 0 | 干净（低档、无残留；pipeline 另含完整性 PASS） | 合并/继续 |
| 1 | 完整性守卫 FAIL（仅 pipeline 会产出；与 verify 契约同义） | 拒绝该改稿，回给 agent 重改 |
| 3 | 风格特征中及以上（≥28，需要深改） | 进深改队列（plan.py 排优先级） |
| 4 | 命中模型残留（critical） | 先跑 transform.py 清理 |
| 2 | 用法/文件错误（不受 --exit-verdict 影响） | 修调用 |

> detect/compare 的 `--exit-verdict` 只出 0/3/4（完整性仍只写报告——exit 1 契约专属 verify/pipeline）；
> **pipeline 是唯一 1/3/4 全档判定命令**，CI 门禁推荐 `pipeline.py 原稿 --rewrite 改稿 --exit-verdict`。

## 一B、集中异常层（v2.5.0）

全部 CLI 的 `__main__` 统一经 `hxt_core.cli_entry(main)` 进入：任何用户侧
异常输出**两行中文**——「错误: <发生了什么>」+「处置建议: <怎么办>」——并以
exit 2 结束。`CliError(msg, hint)` 是脚本内主动报错的规范方式；SystemExit
原样穿透，各脚本语义化退出码不受影响。程序内部 bug 仍带完整 traceback
冒出（宁可吵，不可吞）。

## 二、verify.py 违规类别（exit 1 = violations；WARN = 告警继续）

| 类别 | 级别 | 含义 | 常见原因与处置 |
|---|---|---|---|
| numbers | E_NUM_LOST | ✗ 红线 | 数字丢失/被改 | 深改时把数据句改写了——恢复原数字或重写该句 |
| comparison | E_CMP_FLIP | ✗ 红线 | 比较方向被改（P<0.05→P>0.05 级） | 结论方向反转，必须恢复原文方向 |
| doi / pmid | ✗ 红线 | DOI / PMID 丢失 | 引用被删或改写——恢复 |
| latin_abbr | E_ABBR_LOST | ✗ 红线 | 大写缩写丢失（DNA/PCR 类） | 缩写被中文化或删除——恢复原缩写 |
| terms | E_TERMS_LOST | ✗ 红线 | 术语表条目缺失/减少 | 术语被替换——恢复，或把该词从术语表移除（若确认非术语） |
| cjk_ratio | E_CJK_SHIFT | ✗ 红线 | 中英占比漂移超阈 | 整段被删或被译——检查是否误删段落 |
| length | E_LEN_DRIFT | ✗ 红线 | 长度变化超阈（长文 ±25%，短文放宽） | 内容被整段删除——核对删减是否有意 |
| numbers_added | W_NUM_ADDED | ⚠ 告警 | 出现原稿没有的数字 | **编造防线**：深改时凭空补的数字必须删除 |
| number_context | W_CTX_SWAP | ⚠ 告警 | 数字上下文/顺序变化 | 两臂互换/方位错位——人工核对方向 |
| years | W_YEARS | ⚠ 告警 | 年份数量变化 | 年份引用被删——核对 |

阈值均可 CLI 覆盖：`--max-length-change`、`--max-cjk-shift`。

## 三、退出码 2 的常见触发与处置

| 触发 | 提示关键词 | 处置 |
|---|---|---|
| 文件不存在 | 无法读取 | 核对路径（相对路径基于技能目录） |
| 输入为空 | 输入为空 | 文件无内容或只传了空白 |
| 二进制文件 | 疑似二进制（含 NUL 字节） | 转存 UTF-8 纯文本；Word 用 .docx 直读 |
| 编码错误 | 乱码占比过高 | 文件是 GBK/UTF-16 等——转存 UTF-8 |
| 文件超限 | 超过 50MB 上限 | 拆分文件分批处理 |
| docx 缺部件 | 缺少正文部件 | 可能只是改了扩展名——另存为真正 .docx |
| docx 加密 | 受密码保护 | 解除密码后另存 |
| 参数错误 | argparse 提示 | `--help` 查看合法取值（如 --profile academic/general） |

## 四、detect/pipeline 报告中的级别

| 级别 | 含义 | 建议 |
|---|---|---|
| 低（0-27） | 基本无模板腔特征 | 无需处理 |
| 中（28-49） | 有一定模板腔 | 可按 style_guide 选择性处理 |
| 高（50-74） | 模板腔特征明显 | 按 style_guide 深改 |
| 极高（75+ 或含硬残留） | 特征极重/含模型残留 | 先 transform.py 清硬残留，再按指南深改 |

分数口径：本地启发式风格诊断，非任何官方检测分数；短文本（<15 单元）自动降权并标注「仅供参考」。

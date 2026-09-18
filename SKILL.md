---
name: group-meeting-lit-report
description: 把学术文献（PDF 图书/论文章节）的指定页码范围，产出为「组会汇报版」或「课题组学习解析版」两种报告之一，经两轮审查闸门后默认交付 Markdown，用户确认后再导出为 LaTeX→PDF 或 Word。默认走组会汇报版：英中逐句翻译 + 内容解析 + 图表读法讲解。用户要「课题组学习」「学习解析版」「按段翻译」「便于看懂版」时改出学习版：按段翻译 + 图表精简讲解（元素逐类讲清）+ 公式的前后文联系。当用户说「组会汇报」「汇报这篇文献的某几页」「逐句翻译并讲解」「解析这两页的图表」「把文献做成汇报材料」「导出成 LaTeX / PDF / Word 汇报稿」时使用本技能。group meeting, literature report, sentence-by-sentence translation, paragraph-by-paragraph translation, study notes, figure explanation, LaTeX export。
version: 1.8.1
agent_created: true
---

# 组会文献汇报（两阶段）

## 这个技能做什么

把「一篇文献的指定页码范围」变成「可以直接拿去讲、并且经得起追问的材料」：

- **阶段一**：翻译（英中对照）+ 内容解析 + 图表讲解 → **两轮审查** → 默认产出 `.md`
- **阶段二**：经用户确认后，把阶段一成果转为 LaTeX 并编译成 **PDF（默认）** 或 Word

本技能的重点不在"翻译得漂亮"，而在**每一句断言都能回到原文证据**，以及**用闸门机制保证没弄清楚的地方不会溜进最终稿**。

## 两种输出模式（先定这个，再动手）

| | 组会汇报版（**默认**） | 课题组学习解析版 |
|---|---|---|
| 用户怎么说 | 「组会汇报」「汇报这几页」「逐句翻译并讲解」 | 「课题组学习」「学习解析版」「按段翻译」「便于看懂版」 |
| 翻译粒度 | 逐句，`#### 句 N` | **按段**，`#### 第 N 段`（每页内从 1 连续） |
| 图表 | 必讲清单 10 条（含判读清单、读图局限、易错点、接口） | **精简**：不写延伸项，但每类元素都要有一句解释 |
| 公式／重点 | 术语逐条解释 + 组会预设问答 | **前后文联系**：首次定义在哪、本页为何用、后文还用在哪、各符号量纲 |
| 服务目标 | 扛住组会上被追问 | 让读者尽可能容易看懂 |
| 骨架 | `assets/report-template.md` | `assets/study-template.md` |
| 细则 | `references/phase1-translate-review.md` | `references/study-mode.md` |
| 门禁 | `check_report.py --md … --pages …` | `check_report.py --md … --pages … --mode study` |
| 交付命名 | `<起>-<止>-汇报.md` | `<起>-<止>-学习.md` |

**判定顺序**：用户没明说 → 走组会汇报版。用户说了学习版那一组词 → 走学习版。**两版都要 → 产出两个文件**，各自独立过门禁，不要合成一份。

**交付命名是固定的，不许自由发挥**：

- 汇报版 `<起>-<止>-汇报.md`、学习版 `<起>-<止>-学习.md`，审查记录 `<起>-<止>-审查记录.md`。
- 页码一律用**书内页**，起止之间用**半角连字符** `-`；例：书 p.478–479 → `478-479-汇报.md`。
- **不加文献简称、不加下划线、不加 `p`**。以前的 `<文献简称>_p<起>-<止>_汇报.md` 写法已废弃。
- 同一次任务的两版落在**同一个用户指定目录**下，文件名只靠结尾的 `-汇报` / `-学习` 区分。
- **阶段二产物同规则**：主 `.tex` 文件叫 `<起>-<止>-汇报.tex`（学习版 `<起>-<止>-学习.tex`），导出的 PDF / Word 因此同名——`compile_pdf.py` 的 PDF 名跟着 `.tex` 主文件名走，`.tex` 起对名 PDF 就自然对；Word 走 pandoc 时保持同一基名，即 `<起>-<止>-汇报.docx`。**不要把主文件叫 `main.tex`**。

**两条线共用同一套结构锚点**（`## 〇、阅读说明与页码对账`、`## 一、章节地图`、`## 二、第 X 页`、`### n.m`、`## 首轮自检与修订记录`、`## 待确认项`、`### 附 N`），差别只在 `2.2` 一节用 `#### 句 N` 还是 `#### 第 N 段`。五条铁律、三档标注、收尾清单、豁免开关对两种模式**完全一致**。

## 五条铁律（不可违反，优先级高于效率）

1. **证据回溯**。任何关于文献内容的陈述都必须落回证据：正文原句（标页码）、图表（标图号+坐标读数）、公式（标公式号）。**绝不允许凭学科常识或印象补写文献没说的内容。** 三档标注见下。**本页没交代的符号与公式，必须标注来源并补足推导**（见 `references/anti-hallucination.md` 规则 I）。
2. **阶段闸门**。第一轮审查未完成、或第二轮审查产出的"待确认项"未全部获得用户确认并修正之前，**禁止进入阶段二**。不允许用"用户应该会同意"自行闭合待确认项。
3. **不静默降级**。工具缺失、编译失败、某页文字层是空的（扫描页）、图表无法读刻度——必须明确告知用户并给出替代方案，不得略过或假装已完成。
4. **交付物落地**。阶段一默认产出**文件**（MD + 高清图目录），不是只在对话里输出；阶段二必须产出可打开的文件。**交付方式按宿主 Agent 来**：WorkBuddy 用 `present_files`；其它 Agent（Claude Code / Cursor / Codex / Copilot / Gemini 等）没有这个工具，改为**直接给出文件路径并说明已产出**即可。这条铁律约束的是"必须落盘成文件"，不是"必须用某个工具"。
5. **输出目录先行确认**。**写任何文件之前**，必须先向用户确认这次产出放在哪个文件夹；用户指定了目录，就**只能写进那个目录**——不许改写别处，也不许顺手多存一份。用户没指定、或说"随便／你定"时，**报出建议目录并停下来等一句确认**，不许默认写当前工作目录、不许拿上次的目录顶替。阶段二同理：`.tex`、`build/`、PDF 都落在确认过的目录里。这条覆盖**所有交付给用户的文件**，含 `figures/` 与 `evidence/`。

## 开场必做：原样输出这句声明

> **本轮使用 group-meeting-lit-report，因为涉及文献页码范围内的翻译与解析。**

（这是"本轮走了本技能流程"的凭据，不是寒暄。阶段二开局把"因为涉及…"改成对应的导出动作。）

声明之后第一件事是**确认输出目录**（铁律 5）：**文献路径、页码范围、输出模式、输出目录**四项齐了才开工；缺哪项就问哪项，问完再动手。

## 收尾必做：固定字段清单

每次收尾（无论阶段一还是阶段二）必须列齐下面字段；没有的写"无"，不能省略**整项**：

| 字段 | 内容 |
|---|---|
| 页码对账 | `PDF <a> = 书 <X>`，偏移多少 |
| 输出目录 | 用户指定的目录（**写入前已确认**，见铁律 5）；没有就写"未确认"并说明为何仍写了 |
| 产出路径 | 报告 / 图目录 / `.tex` / PDF 等绝对或相对路径 |
| 第一轮审查 | 抓到了什么（几处结构问题、几处内容问题），或"无"。**原始明细在 `_review/` 审查记录里，交付物不含这一节** |
| 第二轮待确认项 | 逐条列出（带 OQ-ID），或写 **待确认：无**。同样只在收尾说明里汇报 |
| 未检查项与原因 | 例如"图 19.5 的点标记是位图，无法逐点计数，改为按设计推断" |
| 使用的豁免开关 | 用了 `--allow-scan-pages` 等就写明，未用写"无" |
| 门禁结果 | `check_report.py` 的退出码与成功串 |

**交付物里不放过程凭据**：`## 首轮自检与修订记录` 与 `## 待确认项` 写进 `<用户指定目录>/_review/<起>-<止>-审查记录.md`（骨架见 `assets/review-template.md`），门禁带 `--review` 指向它。**这两项只在上表里汇报**，不塞进报告正文——读者要看的是文献，不是工作日志。

## 文档优先级仲裁表（冲突时谁赢）

| 优先级 | 来源 | 说明 |
|---|---|---|
| 1（最高） | **用户当次指令** | 当次会话明确要求的口径、格式、取舍 |
| 2 | **文献原文** | 正文、图注、公式、表注的原文措辞 |
| 3 | **本技能规范** | 本技能定义的流程、格式、审查要求 |
| 4（最低） | **通用学科常识** | 仅用于理解文献，**不得**用来覆盖上面任何一层 |

**明确禁止**：用通用常识覆盖文献原文；用"更合理"的写法替换文献原句；把"按学科惯例应该是"写成"书中指出"。凡属第 4 层参与形成的结论，必须标 `【推论】` 或 `<待确认:…>`。

## 三档标注（写正文时强制使用）

| 档位 | 含义 | 写法 |
|---|---|---|
| A 类 | 文献原话/原文数字 | `【原文 p.N】`，直接引用，翻译不加解释性扩充 |
| B 类 | 由本文献的模型设定、公式或数据**直接推出** | `【推论】`，并写明依据是哪条式子/哪条假设 |
| C 类 | 由图表坐标反算或目测得到 | `【按图读数】`，写明"由矢量坐标反算/目测，原文未印出" |

三档不混。被追问时，A 类翻书即答，B 类讲推理，C 类承认是读数。

**本页没交代的符号与公式，必须交代来源 + 补足推导**（细则见 `references/anti-hallucination.md` 规则 I）：

- 用到**目标页范围内没有给出定义**的字母参数、公式，或由它们推出的数值时，必须写清它**首次定义在哪一页／哪一公式**；属于前文接口的归入附录，并标 `p.N`。
- 由公式推出某个结果（例如"饱和值 = β₁ + β₂"）时，**必须写出推导的关键一步**——依据哪条式子 → 取极限／代入／整理 → 结果。**不许只给结论。**
- 自己算出来的数（如 `β₂ ≈ 99.7`）**不许写成原文印出的数**，要标 `【推论】` 或 `【按图读数】` 并写出反算依据。
- 本文献通篇未定义的符号：写 `<待确认:该符号在本文献中未给出定义>`，登记 `state/oq-ledger.md`，**不许从常识补**。

## 阶段总览

| 阶段 | 启动条件 | 交付物 | 必需工具（插件） |
|---|---|---|---|
| **阶段一** | 用户给出文献路径 + 页码范围 **+ 输出目录（铁律 5）** | 组会汇报版：`<起>-<止>-汇报.md`（按 `assets/report-template.md`）；学习版：`<起>-<止>-学习.md`（按 `assets/study-template.md`）；两者都带 `figures/` 高清图目录、`evidence/` 取证素材，以及 `_review/<起>-<止>-审查记录.md`（自检与待确认项，**不随交付物**） | **Python + pymupdf**（必需）；可选 pypdf |
| **阶段二** | 阶段一闸门通过 **且** 用户明确选择导出格式；**若阶段一 MD 来自 HTML 机械转换，先跑 `scripts/normalize_md_residue.py` 并重跑门禁**（否则 pandoc 会静默丢掉原始 HTML 表格） | `build/<起>-<止>-汇报.tex` + `build/<起>-<止>-汇报.pdf`（默认）；或 `<起>-<止>-汇报.docx`。学习版把 `-汇报` 换成 `-学习` | **TeX Live**（xelatex + latexmk，PDF 必需）；**pandoc**（仅 Word 需要） |

## 跨 Agent 使用（本技能是开放标准的 Skill，不只 WorkBuddy 能用）

本技能遵循 **Agent Skills** 开放标准：一个目录 + `SKILL.md`（YAML frontmatter 的 `name` / `description`）+ 可选的 `scripts/`、`references/`、`assets/`。因此**同一份文件在其它 Agent 上也能用**，只需要放到对应 Agent 的技能目录里：

| Agent | 项目级 | 用户级 |
|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Cursor | `.cursor/skills/` | 项目级为主（也读 `.agents/`、`.claude/`） |
| OpenAI Codex | `.agents/skills/` | `~/.agents/skills/` |
| VS Code / GitHub Copilot | `.github/skills/` | `~/.copilot/skills/` |
| Gemini CLI | `.gemini/skills/` | `~/.gemini/skills/` |
| Windsurf | `.windsurf/skills/` | `~/.codeium/windsurf/skills/` |
| OpenCode | `.opencode/skills/` | `~/.config/opencode/skills/` |

**最省事的跨 Agent 做法：放到 `.agents/skills/`**——这是厂商中立路径，Codex 用它是默认，Cursor、VS Code、Gemini CLI 也都认，一份文件多个 Agent 都能发现，不用到处复制。

**跨 Agent 时的三点差异**（不影响流程，只影响措辞）：

1. `present_files` 是 WorkBuddy 的工具，其它 Agent 没有 → 见上面铁律 4。
2. frontmatter 里的 `agent_created` 是 WorkBuddy 专有字段，**其它 Agent 会静默忽略**，不需要删。
3. 触发靠 `description`：本技能的描述写得比较长且具体，Claude Code / Cursor 匹配较准；Copilot 等较保守的实现可能需要把请求说得**更贴近描述原文**（例如直接说"组会汇报这篇文献的第 X–Y 页，逐句翻译并讲解图表"）。

## 开工前：环境与插件自检（每个阶段都必须做，阶段二尤其不能跳）

先探测，再动手。**缺失项按下表处理：先向用户说明缺什么、为什么需要、准备用什么命令装，请求授权后由 Agent 自动安装；不要静默跳过，也不要让用户自己去装。**

| 工具 | 探测命令 | 用途 | 缺失时的安装方式（需先获授权） |
|---|---|---|---|
| pymupdf | `python -c "import pymupdf"` | 阶段一取正文、渲染图表、反算坐标 | `pip install pymupdf`（装进隔离 venv） |
| TeX Live / xelatex | `where xelatex` | 阶段二编译 PDF（中文必须用 xelatex） | Windows：`winget install TeXLive.TeXLive` 或 `choco install texlive`（体积大，装完需重开终端） |
| latexmk | `where latexmk` | 自动多轮编译（目录/交叉引用） | 随 TeX Live 自带，通常无需单独装 |
| pandoc | `where pandoc` | 阶段二导出 Word | `winget install --id JohnMacFarlane.Pandoc` 或 `choco install pandoc` |

探测写法（本机 PowerShell 的 stdout 不会被工具捕获，**一律重定向到文件再 Read**）：

```powershell
$out = "env_probe.txt"
foreach($e in @("xelatex","latexmk","pandoc")){ "$e => " + ((& where.exe $e 2>&1) -join " | ") | Out-File $out -Append -Encoding utf8 }
& kpsewhich ctex.sty | Out-File $out -Append -Encoding utf8
```

## 读档纪律（控制上下文，避免漏读）

**同一轮内只读当前步骤需要的文件**，完成后再读下一步：

- 阶段一：先定模式（见「两种输出模式」），再按骨架读档——组会汇报版：`assets/report-template.md` → `references/pdf-evidence-extraction.md` → `references/anti-hallucination.md` → `references/phase1-translate-review.md`；学习版把最后一步换成 `assets/study-template.md` → `references/study-mode.md`（按此顺序，不要一次性全载入）。
- **不要**在没进入阶段二时通读 `references/latex-cookbook.md`。
- 大文件按小节读：`references/pdf-evidence-extraction.md` 用 `offset/limit` 只读需要的那一节，单轮新开小节 ≤ 3 个。
- `state/oq-ledger.md` 每轮必读（先读后写），但它只是表格，按行扫即可。

## 执行入口

| 要做的事 | 读哪个文件 |
|---|---|
| 阶段一（翻译 + 解析 + 两轮审查） | `references/phase1-translate-review.md` |
| 组会汇报版固定骨架 | `assets/report-template.md` |
| 学习版固定骨架 | `assets/study-template.md` |
| 审查记录骨架（自检与待确认项，不随交付物） | `assets/review-template.md` |
| 学习版执行细则（精简边界 / 元素讲清 / 前后文联系） | `references/study-mode.md` |
| 从 PDF 取证（矢量反算等） | `references/pdf-evidence-extraction.md` |
| 防幻觉硬规则 A–H | `references/anti-hallucination.md` |
| 已经确认过的口径 / 待确认项 | `state/oq-ledger.md` |
| 阶段二（LaTeX/PDF/Word） | `references/phase2-export.md` |
| LaTeX 排版与编译 | `references/latex-cookbook.md` |

## 捆绑脚本

| 脚本 | 作用 | 关键约束 |
|---|---|---|
| `scripts/extract_pages.py` | 一键建工作区：按页码范围抽取正文、渲染整页与图表高清图、导出矢量坐标、扫章节地图。阶段一开工第一步就跑它 | 输出写到文件再 Read |
| `scripts/check_report.py` | **静态门禁**：结构类 R1–R6／R13 阻断（`exit 1`），内容类 R7–R12／R14 只警告；`--mode study` 换成学习版骨架（S2 阻断，S7/S8 警告）；`--outdir` 核对交付物是否落在用户指定目录（R13）；`--review` 从独立审查记录读自检与待确认项；`--figures-full` 按完整图表清单查 R7；**R14 默认开启**，查「希腊字母参数 ≈/＝ 数值」有无就近出处。**不写 `--mode` 默认按汇报版查** | **`exit 1` 时不得宣称阶段一完成；`--gate phase2` 未过不得进入阶段二** |
| `scripts/normalize_md_residue.py` | **阶段二前置**：把阶段一 MD 里 HTML→MD 的残留（原始 table 块、sub/sup、br、`\[`）归一化为 Markdown 原生形式 | 只做等价改写，带「纯文本骨架全等」与「不得引入 `{{`/`}}`」两道安全网；**改完必须重跑 `check_report.py`** |
| `scripts/compile_pdf.py` | 用 latexmk/xelatex 编译 `.tex`，捕获并摘要 LaTeX 报错（含行号） | 编译不通过不算完成 |

```bash
python scripts/extract_pages.py --pdf "<文献.pdf>" --pages 491-492 --book-offset 15 --out work --dpi 430
python scripts/check_report.py --md <报告>.md --pages 476-477 \
    --outdir "<用户确认的输出目录>" --review "<用户指定目录>/_review/<起>-<止>-审查记录.md" --figures-full
python scripts/check_report.py --md <报告>.md --gate phase2      # 进入阶段二前的硬前置，参数同上
python scripts/check_report.py --md <学习版>.md --pages 476-477 --mode study   # 学习版骨架，参数同上
python scripts/compile_pdf.py --tex report/<起>-<止>-汇报.tex --outdir report/build
```

### 具名豁免开关（替代模糊例外）

需要例外时**只允许用这些开关**，且**必须在收尾清单的「使用的豁免开关」一行声明**：

| 开关 | 什么时候用 |
|---|---|
| `--allow-scan-pages` | 目标页无文字层（扫描页），只能人工转写 |
| `--allow-no-precise-reading` | 用户明示不需要精确读数，允许"目测约" |
| `--user-approved-open` | 用户已明确批准带未关闭的待确认项进入阶段二 |

**禁止**用"情况特殊"这类自由文本绕过——没有对应开关就说明不该绕。

## 本技能的自我维护（元规则，强制）

**凡改动本技能目录内的规则/流程/自检类文档**（`SKILL.md`、`references/`、`assets/`、`state/` 的协议、`scripts/` 的判定逻辑），**须在同一轮内**于 `optimization-record.md` 末尾**追加一条记录**（固定四段：日期说明 / 需求·触因 / 规则摘要 / 波及文件表）。日期必须是**落盘当天**并用命令核对：

```powershell
Get-Date -Format yyyy-MM-dd
```

**禁止**只改规则不写记录；**禁止**照抄上一条的日期。会话总结里要写明"已追加 optimization-record · 日期 · 标题关键词"。

**打包分发时先排除工作区数据**：技能目录里的 `.workbuddy-ai/`（工作区记忆与缓存）**不属于技能内容，不要打进 ZIP**。做法是先把技能目录复制到一个临时目录（跳过 `.workbuddy-ai/`），再对副本打包；直接对整个技能目录打包会把记忆文件一起发出去。

## 已知环境（本机实测，2026-09；换机器必须重新探测）

- TeX Live **2026**：`D:\TEXlive\texlive\2026\bin\windows\`，`pdflatex / xelatex / lualatex / latexmk / latex / tex` 均在 PATH
- pandoc **3.11**：`%LOCALAPPDATA%\Pandoc\pandoc.exe`（已在 PATH）
- winget、choco 均可用（用于自动安装）
- 中文宏包齐备：`ctex`、`xeCJK`、`ctexart`、`booktabs`、`longtable`、`tabularx`、`array`、`enumitem`、`caption`、`graphicx`、`amsmath`、`geometry`、`xcolor`、`hyperref`、`bookmark`、`listings`、`adjustbox`、`fontspec`、`unicode-math`
- **本机缺失、不要用**：`titlesec`、`tocloft`、`tcolorbox`、`needspace`（要用就先 `kpsewhich` 验证，缺则 `tlmgr install`）
- **已知编译坑**：`ctexart` + `enumitem`(v3.11) 的 `description` 配 `style=nextline` 必然失败；`\hypersetup` 不要传 `bookmarks=true`。详见 `references/latex-cookbook.md` §4
- 中文字体：系统有 `NSimSun/simsun.ttc`、`simhei`、`FangSong`、`STSong`、`Noto Sans SC`；TeX Live 自带 `Fandol` 系列
- **执行外部命令（python / pandoc / xelatex）走 Bash 通道**（2026-09-16 实测：coreutils 齐全，stdout 能被工具直接捕获，含中文输出）。**不要把命令交给 PowerShell 工具**——实测它返回退出码 0 却根本没有启动进程，命令没有任何产物，最容易被误判成"脚本已经跑过了"。PowerShell 只用于 `Get-Date`、`Compress-Archive` 这类 cmdlet。

（结论：本机**无需下载任何东西**即可直接出 PDF 和 Word。只有当探测失败时才走"请求授权→自动安装"流程。）

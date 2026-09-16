# 阶段二：导出为 LaTeX → PDF（默认）或 Word

**前置条件（缺一不可，先验证再动手）**：

```bash
python scripts/check_report.py --md <报告>.md --gate phase2 \
    --outdir "<用户确认的输出目录>" --review "<用户指定目录>/_review/<简称>_p<起>-<止>_审查记录.md" --figures-full
python scripts/check_report.py --md <学习版>.md --gate phase2 --mode study   # 学习版务必带 --mode study，其余参数同上
```

必须以 `[ok] report-gate passed` 与 `exit 0` 结束。**未通过则不得启动本阶段**——回去处理待确认项，或由用户明确批准后加 `--user-approved-open`（加了这个开关，收尾清单必须声明）。

其余前置：阶段一的两轮审查已完成、用户已看到并认可阶段一交付物、用户已明确选择导出格式。**再加上一条铁律 5 的前置：阶段二的输出目录已确认**——`.tex`、`figures/` 引用、`build/`（含 `main.pdf`、`compile.log`）都落在用户指定的目录里。可以在阶段一目录下开子目录（例如 `<阶段一目录>/pdf/`），但**必须让用户认可这个子目录**，不许自己决定。用户没指定时，报出建议目录并停下等确认。"报告已写完"不等于"闸门已过"。

---

## Step 0　阶段一 MD 的 HTML 残留归一化（前置于一切导出，PDF 与 Word 都要做）

**触发条件**：阶段一的 MD 是**由 HTML 报告机械转换**来的（HTML→MD），或肉眼能看到 `<table>`、`<sub>`、`<br />`、`\[` 这类残留。纯手写 MD 可跳过本节。

**为什么不能跳过——实测结论**（不是"不好看"，是**静态丢内容**）：

| 残留 | pandoc `-t latex` 时的行为 | 后果 |
|---|---|---|
| 原始 `<table>` 块 | 整块被当作 raw block **静默丢弃** | **表格整块消失**（实测：3 张表全部不出现，且不报任何错） |
| 行内 `<sub>X</sub>` / `<sup>Y</sup>` | 只丢弃标签、保留内容 | `y<sub>i</sub>` → 字面 `yi`，下标语义丢失 |
| `\[ … \]` | 被当作**行间公式** | 区间 `\[0.94, 0.99\]` 变成段落中间一个独立的 display 公式 |
| `<br />` | 在管道表单元格内无法表达 | 单元格内容被粘成一行 |

**处理方式（一条命令）**：

```bash
python <skill>/scripts/normalize_md_residue.py --md "<报告>.md"           # 先 dry-run，看核对报告
python <skill>/scripts/normalize_md_residue.py --md "<报告>.md" --apply   # 落盘（自动备份）
```

它做 token 级**等价**改写：表格 → 管道表；上下标 → 行内数学片段（`$_i$`、`$_{\theta}^{2}$`）；`<br />` → 空格；`\[ \]`、`\#` 去转义；`<strong>` → `**`。改名前后有两道安全网，任一不过就**拒绝落盘**：① 纯文本骨架全等（剥掉全部 HTML／Markdown／LaTeX 记号后逐字比较，必须一字不差）；② 不得引入 `{{` 或 `}}`（那是门禁 `check_report.py` 的 R4 判定点）。

**落盘后必须重跑门禁**（本步会改变报告的机器可读形态，可能报出新警告）：

```bash
python scripts/check_report.py --md "<报告>.md" --pages <起>-<止>
```

**已知副作用（可接受，但要心里有数）**：`$_i$` 这类片段的**基字符仍在文本模式**、只有上下标在数学模式，故 PDF 里基字符是正体、上下标是斜体；并且基字符（θ、β、σ、`−`、`∝` 等 Unicode）依靠字体覆盖。真正的解法是在手写 `.tex`（Step 3 路线 A）时把整个符号写成完整数学式，例如 `$y_i$`、`$\sigma_\theta^2$`。若编译后发现缺字/方框，见 Step 4 的"中文变成方框"一行。

---

## Step 1　询问导出格式（必问，不要默认替用户决定）

一次问清三件事：

1. **要 PDF 还是 Word？**（默认 PDF）
2. 要不要同时保留 **`.tex` 源文件**？
3. 表格与公式多，**要不要双栏**？（默认单栏——本类报告含大量英中对照块与宽表，单栏更安全）

**同时把这一步的工具需求讲清楚：**

| 目标格式 | 必需工具（插件） | 本机状态 |
|---|---|---|
| PDF（默认） | **TeX Live**（`xelatex` + `latexmk`）。中文必须用 xelatex，pdflatex 处理中文会直接失败 | 已装（TeX Live 2026，全部在 PATH） |
| Word（.docx） | **pandoc**（把 MD 转 docx） | 已装（pandoc 3.11） |
| 两者都要 | 上述两者 | 均已就绪 |

**若探测发现缺失**：向用户说明「缺什么、为什么必须有、准备执行哪条命令」，**请求授权后由 Agent 自动安装**，不要让用户自己装、也不要跳过。安装命令：

```
TeX Live : winget install --id TeXLive.TeXLive      （或 choco install texlive；体积大，装完需重开终端）
pandoc   : winget install --id JohnMacFarlane.Pandoc（或 choco install pandoc）
缺失宏包 : tlmgr install <包名>                      （本机缺 titlesec / tocloft / tcolorbox / needspace，见 SKILL.md）
```

装完**必须重新探测**（`where xelatex` / `where pandoc` / `kpsewhich ctex.sty`），确认可用再继续。

---

## Step 2　关于"用什么方法编译"——比 VSCode 里点按钮更好的做法

用户在 VSCode 里装了 LaTeX Workshop，旧流程是「AI 出 LaTeX 代码 → 在 VSCode 里编译出 PDF」。这个流程有三个问题：**要人工点、完整报错看不到、目录/交叉引用需要手动多编译几遍**。改用下面这条命令行闭环，全自动且可自愈：

```
latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build main.tex
```

- **`latexmk`** 自动决定要编译几遍（目录、页码、超链接引用一次搞定，不会出现 `??`）。
- **`-xelatex`** 强制用 xelatex，中文（ctex）与系统字体才能正常工作。
- **`-interaction=nonstopmode -halt-on-error -file-line-error`** 让报错不阻塞、且带**文件名+行号**，Agent 可以直接定位行去改，形成「编译 → 读日志 → 修 → 再编译」的自动循环。
- 用本技能的 `scripts/compile_pdf.py` 包一层，它会把日志里的 `!` 错误、`l.<行号>`、缺失宏包（`File ... not found`）摘要成一张清单，失败时返回非零退出码。

规则：**编译不通过就不算完成**。最多自动迭代 5 轮；仍失败则把错误清单原样交给用户，不要交付半成品 PDF。

---

## Step 3　生成 `.tex`

### 路线选择

| 路线 | 何时用 | 说明 |
|---|---|---|
| **A. 直接手写 `.tex`（推荐）** | 本类报告的默认 | 报告含英中对照句块、宽表、图注、公式——需要精细控制版式。以 MD 为内容底稿，直接产出结构化 `.tex`，排版可控 |
| B. `pandoc md → tex` 再修 | 内容以纯段落为主、表格少 | pandoc 对中文与自定义块支持有限，产出后通常仍需大改，不推荐作为首选 |

**Word 一律走路线 C**：`pandoc <报告>.md -o <报告>.docx --reference-doc=<模板.docx> --toc`。**不要**用 LaTeX 转 docx（公式与中文容易崩）。

### 已验证可用的导言区

**完整可编译骨架、英中对照句块宏、三档标注宏、数值表与宽表模式、CJK 专属坑、交付前自检清单，全部在 `references/latex-cookbook.md`，生成 `.tex` 前先读它并直接套用。**

要点速记（详细内容见 cookbook）：

```latex
\documentclass[11pt,a4paper]{ctexart}
\usepackage{fontspec}
\setCJKmainfont{FandolSong-Regular.otf}[BoldFont=FandolHei-Bold.otf]  % 或 fontset=windows 用系统字体
\usepackage{geometry}\geometry{margin=2.4cm}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{tabularx}
\usepackage{array}
\usepackage{enumitem}
\usepackage{caption}
\usepackage{graphicx}
\usepackage{adjustbox}     % 宽表缩放
\usepackage{xcolor}
\usepackage{listings}
\usepackage{fancyhdr}
\usepackage{hyperref}\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=blue,bookmarks=true}
\usepackage{bookmark}
```

- **中文方案**：`ctexart` + xelatex。字体用 `\setCJKmainfont{Fandol...}`（TeX Live 自带，最稳、可移植）；或 `\documentclass[fontset=windows]{ctexart}` 走系统字体（本机有 simsun/simhei/FangSong）。
- **不要用** `titlesec` / `tocloft` / `tcolorbox` / `needspace`——本机未安装。要用就先 `kpsewhich <包>.sty` 验证，缺了走 `tlmgr install`。用 `\section` 默认样式 + `fancyhdr` 足够做出干净版面。
- **图**：`\includegraphics[width=\linewidth]{figures/fig_x.png}`，放在 `figure` 环境里，`[htbp]`；图注用 `\caption{}`。图片路径指向阶段一产出的 `figures/`，不要重新抽图。
- **表**：跨页用 `longtable`；过宽用 `\begin{adjustbox}{width=\linewidth}` 或 `\small` + `tabularx`。
- **英中对照句块**：用 `\begin{quote}` 或自定义 `\paragraph` 实现，原文用 `\itshape`、译文用正体，编号用 `\textsuperscript{...}`。**不要**用未装的主题宏包。

### 与阶段一的三档标注保持一致

A/B/C 三档标注在 PDF 里也要保留：建议 A 类引文用小号斜体 + 页码、B 类用「【推论】」前缀、C 类用「【按图读数】」前缀，并在导言区用一个 `\newcommand` 定义统一格式，避免手写出错。

### 排版自检（编译前）

- [ ] 所有 `\includegraphics` 的文件都存在（用脚本核对路径，缺图是编译失败的最常见原因）
- [ ] 所有用到的宏包都已通过 `kpsewhich` 验证或已 `tlmgr install`
- [ ] 表格列数与 `tabularx` 的 `X` 列数一致
- [ ] 中文里没有半角标点误用；参考文献/页码中的连字符用 `--`
- [ ] `%`、`&`、`_`、`#` 等特殊字符在正文中已转义

---

## Step 4　编译与自愈循环

```bash
python <skill>/scripts/compile_pdf.py --tex report/main.tex --outdir report/build
```

- 成功 → 得到 `report/build/main.pdf`；检查页数、目录是否有点开、有无 `??` 未解析引用。
- 失败 → 读脚本摘要出的错误清单，改 `.tex`，重编译。常见错误与对策：

| 报错 | 原因 | 对策 |
|---|---|---|
| `File 'ctex.sty' not found` | 用了 pdflatex 而非 xelatex，或 TeX Live 不全 | 换 `-xelatex`；`tlmgr install ctex` |
| `File 'xxx.sty' not found` | 宏包未安装 | `tlmgr install xxx`，或换等价宏包 |
| `Missing number, treated as zero` | 表格/长度参数写错 | 检查 `tabularx` 列宽与 `\includegraphics[width=]` |
| `Runaway argument` | 特殊字符未转义 | 转义 `& % _ # $` |
| `! Package hyperref Error` | 与 `bookmark` 顺序冲突 | 保证 `hyperref` 在 `bookmark` 之前加载 |
| 中文变成方框 | 字体未生效 | 确认用 xelatex，并显式 `\setCJKmainfont` |

## Step 5　Word 路线（若用户选 Word）

```bash
pandoc "<报告>.md" -o "<报告>.docx" --toc --toc-depth=3 --reference-doc=<模板.docx>
```

- 没有模板就直接 `pandoc "<报告>.md" -o "<报告>.docx" --toc`；若用户想要统一格式，用一份已有 docx 作为 `--reference-doc`。
- **图片路径**：pandoc 会按 MD 里的相对路径解析，务必在 MD 所在目录下执行，或先 `cd` 到该目录。
- 转完**要打开检查**：公式会转成 OMML，中文与公式混排常需要手工微调。**先做 Step 0 的残留归一化**——否则 MD 里的 HTML 表格与上下标标签同样不会进 docx。
- **说明清楚**：Word 与 PDF 是两条独立产线（同一份 MD 分别转出），不要期待两者版式完全一致。

## Step 6　交付

1. 交付 **PDF（或 docx）**，同时把 **`.tex`** 与 `figures/` 一并挂上（用户以后复用/改排版要用）。WorkBuddy 用 `present_files`；其它 Agent 直接给出文件路径。
2. 按 `SKILL.md` 的**固定收尾字段清单**逐项汇报；阶段二的这一份额外要写清：格式、文件路径、页数、编译是否零报错、用到的工具版本。
3. 若中途装过任何插件，明确说明装了什么、装在哪、以后是否需要再装。
4. **技能自我维护**：若本阶段改动过技能目录内的规则/流程/自检文档（含 `latex-cookbook.md` 里的坑表），必须同轮在 `optimization-record.md` 追加一条记录，并在总结里写明"已追加 optimization-record · 日期 · 标题关键词"。

# LaTeX 排版手册：可直接套用的骨架与模式

配合 `phase2-export.md` 使用。本文件给出**完整可编译的骨架**和几种固定版式模式，避免每次重新设计导言区。

## 0. 前置检查（编译前必做）

```powershell
# 宏包存在性（不要用未安装的宏包）
foreach($p in @("ctex","xeCJK","booktabs","longtable","tabularx","array","enumitem","caption","graphicx","adjustbox","xcolor","listings","fancyhdr","hyperref","bookmark","amsmath")){
  "$p => " + ((& kpsewhich "$p.sty" 2>&1) -join "") | Out-File pkg.txt -Append -Encoding utf8
}
# 字体
& kpsewhich FandolSong-Regular.otf
```
**本机缺失（不要用）**：`titlesec`、`tocloft`、`tcolorbox`、`needspace`。需要就先 `tlmgr install <包名>`。

## 1. 完整骨架（实测可编译）

```latex
% !TEX program = xelatex
\documentclass[11pt,a4paper]{ctexart}

% ---- 中文与字体：用 TeX Live 自带的 Fandol，可移植性最好 ----
\usepackage{fontspec}
\setCJKmainfont{FandolSong-Regular.otf}[BoldFont=FandolHei-Bold.otf]
\setCJKsansfont{FandolHei-Regular.otf}
\setmainfont{TeX Gyre Termes}          % 西文衬线；若报错则删掉此行用默认

% ---- 版面 ----
\usepackage{geometry}\geometry{margin=2.3cm}
\usepackage{xcolor}
\usepackage{fancyhdr}
\pagestyle{fancy}\fancyhf{}
\lhead{\small 组会汇报}\rhead{\small \leftmark}
\cfoot{\small\thepage}
\renewcommand{\headrulewidth}{0.4pt}

% ---- 数学与图表 ----
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{tabularx}
\usepackage{array}
\usepackage{adjustbox}
\usepackage{enumitem}
\usepackage[font=small,labelfont=bf]{caption}

% ---- 代码/引用 ----
\usepackage{listings}
\lstset{basicstyle=\ttfamily\small,breaklines=true,frame=single,columns=fullflexible}

% ---- 超链接（必须放在 bookmark 之前）----
\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=teal,urlcolor=blue,citecolor=teal,bookmarksnumbered=true}
\usepackage{bookmark}

% ================= 版式宏（英中对照 / 三档标注）=================
\definecolor{enzhbg}{HTML}{F2F6F6}
\definecolor{tierA}{HTML}{0F5C6B}
\definecolor{tierB}{HTML}{A8551A}

\newcommand{\SentencePair}[3]{%
  % #1 编号  #2 原文  #3 译文
  \par\medskip\noindent
  \textsuperscript{\textcolor{tierA}{\textbf{#1}}}\hspace{0.4em}%
  {\itshape\small\color{black!70} #2}\par
  \nopagebreak\noindent\hspace{0pt}#3\par\smallskip
}

% 三档标注（与阶段一的三档严格对应，不可混用）
\newcommand{\Acite}[2]{\textcolor{tierA}{【原文 #1】}#2}          % A 类：文献原话+页码
\newcommand{\Binf}[1]{\textcolor{tierB}{【推论】}#1}              % B 类：由模型/公式直接推出
\newcommand{\Cread}[1]{\textcolor{tierB}{【按图读数】}#1}         % C 类：矢量反算或目测

% 读图卡片：坐标轴信息表
\newcommand{\AxisTable}[4]{%
  \begin{tabularx}{\linewidth}{@{}lX@{}}
  \toprule
  横坐标 & #1 \\ \midrule
  纵坐标 & #2 \\ \midrule
  图形元素 & #3 \\ \midrule
  读法 & #4 \\
  \bottomrule
  \end{tabularx}}

\begin{document}

% ---- 封面 ----
\begin{center}
{\LARGE\bfseries <文献标题>}\\[0.6em]
{\large 第 <X>--<Y> 页 逐句翻译与图表讲解}\\[0.5em]
{\small 组会汇报 \quad <日期> \quad 页码对账：PDF <a> = 书 <b>}
\end{center}
\vspace{1em}

\tableofcontents
\clearpage

% ---- 正文 ----
\section{页码对应与章节地图}
...

\section{第 <X> 页}
\subsection{本页版式与功能}
\subsection{逐句翻译}
\SentencePair{1}{原文英文 ……}{对应中文译文 ……}
\subsection{图 <编号> 详解}
\begin{figure}[htbp]\centering
  \includegraphics[width=\linewidth]{figures/fig_19_4.png}
  \caption{图 <编号>：<图注译文>。\Cread{本图由 PDF 矢量层重新渲染。}}
\end{figure}
\AxisTable{<横轴说明>}{<纵轴说明>}{<元素含义>}{<判读清单>}

\section{第 <Y> 页}
...

\appendix
\section{本页用到的前文接口}
\section{首轮自检与修订记录}

\end{document}
```

## 2. 常用版式模式

### 2.1 英中对照句块
用上面的 `\SentencePair{编号}{原文}{译文}`。**原文小号斜体、译文正体**，视觉上一眼能分。图注/表注单独成块并保留"注"的性质。

### 2.2 数值表（从图上反算的读数）
```latex
\begin{longtable}{@{}lrrr@{}}
\toprule
样品 & 中位数 & 50\% 区间 & 95\% 区间 \\ \midrule
\endfirsthead
\toprule 样品 & 中位数 & 50\% 区间 & 95\% 区间 \\ \midrule
\endhead
\bottomrule
\endlastfoot
Unknown 1 & 0.0230 & [0.0217, 0.0243] & [0.0194, 0.0268] \\
...
\end{longtable}
```
表下方必须写明：**`\Cread{由 PDF 矢量坐标反算，原文未印出此数。}`**

### 2.3 过宽的表
```latex
\begin{adjustbox}{width=\linewidth}
\begin{tabular}{...} ... \end{tabular}
\end{adjustbox}
```
或 `\small` + `tabularx` 的 `X` 列。**列数必须与列格式字符串里的列数一致**，否则报 `Extra alignment tab`。

### 2.4 三档标注的视觉规范（建议固定下来）
| 档 | 命令 | 效果 |
|---|---|---|
| A 原文 | `\Acite{p.483}{……}` | 【原文 p.483】…… |
| B 推论 | `\Binf{……}` | 【推论】…… |
| C 读数 | `\Cread{……}` | 【按图读数】…… |

### 2.5 会话式问答（组会预设问答）

**不要用 `style=nextline`**（见第 4 节，在本机 ctexart + enumitem v3.11 下会直接编译失败）。用已验证可用的写法：

```latex
\subsection{组会预设问答}
\begin{description}[font=\bfseries,leftmargin=1.5em,itemsep=0.4em]
  \item[Q1 这张图的纵轴为什么取对数？] A：……
  \item[Q2 这 10 条线是 10 个人吗？] A：……
\end{description}
```

若想让"问题"单独占一行（更接近讲义效果），用自定义宏，不要依赖 nextline：

```latex
\newcommand{\QA}[2]{\par\medskip\noindent\textbf{#1}\par\nopagebreak\noindent #2\par}
\QA{Q1 这张图的纵轴为什么取对数？}{A：因为代谢比例跨越约两个数量级。}
```

## 3. 编译

```powershell
latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build <起>-<止>-汇报.tex
```
或用本技能脚本（会把错误摘要成清单）：
```powershell
& "<venv>\Scripts\python.exe" "<skill>\scripts\compile_pdf.py" --tex <起>-<止>-汇报.tex --outdir build
```

- 中间文件（`.aux/.log/.out/.toc`）会落在 `build/`，源目录保持干净。
- 需要清理时：`latexmk -c -outdir=build`（保留 PDF）或 `latexmk -C -outdir=build`（连 PDF 一起删）。
- **目录出现 `??`** → 说明 `latexmk` 没跑够轮次；通常再跑一次即可（正常情况 latexmk 会自动处理）。

## 4. CJK 专属坑

| 现象 | 原因 | 对策 |
|---|---|---|
| 中文变方框/空白 | 用了 pdflatex | 必须 `-xelatex`，且 `\setCJKmainfont` 指定了存在的字体 |
| 报 `Font ... not found` | 字体名写错（要用文件名或字体的真实 family 名） | 用 Fandol：`FandolSong-Regular.otf`；用系统字体：`SimSun`、`SimHei`、`FangSong` |
| 中文标点间距怪 | 半角标点混入 | 中文用全角，英文/公式上下文用半角 |
| 页码/连字符出现 `?` | 用了 Unicode 特殊字符 | 破折号用 `--`，区间用 `--` 或 `\textendash` |
| 英中混排基线上跳 | 中西文字体基线不一致 | 在 `\setCJKmainfont` 后加 `\setlength{\parindent}{2em}` 一般即可；必要时给西文设 `Scale=.95` |
| **`Argument of \enit@postlabel@i has an extra }`** | **ctexart + enumitem(v3.11, 2025/02/06) 的 `description` 环境配 `style=nextline` 必然报错**（同样的代码在非 ctex 的 `article` 下正常，`itemize` 配 nextline 也正常） | **不要用 `style=nextline`**。改用 `\begin{description}[font=\bfseries,leftmargin=1.5em]`，或用自定义 `\QA` 宏实现"问题独占一行" |
| `Option 'bookmarks' has already been used` | 给 `\hypersetup` 传了 `bookmarks=true`，而 `bookmark` 宏包已设置过 | 从 `\hypersetup` 里删掉 `bookmarks=true`（保留 `bookmarksnumbered=true` 即可） |
| **表格比版心宽出一个缩进量**（`Overfull \hbox (21.9pt too wide)`，21.9pt 恰等于 `2em`） | 设了 `\setlength{\parindent}{2em}` 之后，`tabularx`／`tabular` 被当作段落首行，整表被缩进 2em 再按 `\linewidth` 排版 | 表格前加 **`\noindent`**（改列格式或调 `p{}` 宽度都无效——错的是缩进不是列宽） |

实测结论（本机 TeX Live 2026）：上表各条都在真实编译中复现过并已给出可用替代写法，其余组合均编译通过。

## 5. 交付前的自检清单

- [ ] 编译零报错（不是"忽略错误也能出 PDF"）
- [ ] **编译日志里没有 `Overfull \hbox`**（表格被 `\parindent` 顶宽是最常见的一种，见第 4 节）
- [ ] 目录页码正确、无 `??`
- [ ] 所有图片实际出现在 PDF 中（不是红框/缺图）
- [ ] 宽表未溢出页面（打印预览过一遍）
- [ ] 三档标注与阶段一 MD 完全一致，无遗漏
- [ ] 文末保留「首轮自检与修订记录」附录
- [ ] 同时交付 `.tex` 与 `figures/`，方便用户以后改排版

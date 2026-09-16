#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_report.py —— 阶段一报告静态校验（门禁脚本，退出码即判据）

设计对齐工程实践里的"静态门禁"：把"我记得我审过了"变成"脚本能验出来"。
两级判定：
  · 结构类（R1–R6 / 学习版的 S2）：不合格 -> exit 1，**不得宣称阶段一完成**
  · 内容类（R7–R12 / 学习版的 S7–S8）：只警告，不影响退出码（可用 --strict-content 升级为阻断）

两种模式（--mode，默认 report，既有用法与结果完全不变）：
  · report  组会汇报版骨架：逐句翻译（R2）+ 图表四讲（R7）
  · study   课题组学习版骨架：按段翻译（S2）+ 图表元素覆盖（S7）+ 公式前后文联系（S8）

两模式共用：R1 页码对账、R3 小节编号、R4 占位符、R5 修订记录、
R6/R12 待确认项闸门、R8 数值表出处、R9 英文直引出处、R10 推断标注、R11 页码越界。

用法：
  python check_report.py --md 报告.md
  python check_report.py --md 报告.md --outdir "<用户确认的输出目录>"   # 核对交付物落在指定目录（R13）
  python check_report.py --md 报告.md --review "<审查记录.md>"          # 自检/待确认放在独立文件里
  python check_report.py --md 报告.md --figures-full                   # 图表按完整清单查六项
  python check_report.py --md 报告.md --gate phase2                    # 进入阶段二前的硬前置
  python check_report.py --md 报告.md --gate phase2 --user-approved-open
  python check_report.py --md 学习版.md --mode study                    # 校验学习版骨架
  python check_report.py --md 报告.md --strict-content                 # 内容类也阻断
  python check_report.py --md 报告.md --json                           # 机器可读结果

具名豁免开关（用任一开关时，会话收尾必须声明用了哪个）：
  --allow-scan-pages          该页无文字层（扫描页），只做人工转写，不要求坐标反算
  --allow-no-precise-reading  用户明示不需要精确读数，允许"目测约"
  --user-approved-open        用户已明确批准带未关闭的待确认项进入阶段二

退出码：
  0  通过（可能含内容类警告）
  1  未通过（结构类不合格 / phase2 门禁未过 / 脚本自身异常）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import OrderedDict

# ----------------------------------------------------------------------------
# 规则说明（人机两用：既报"哪里错"，也给"怎么改"）
# ----------------------------------------------------------------------------
RULE_HELP = {
    "R1": "在『阅读说明』里补一条页码对账，形如 `PDF 491 = 书 476`；或放一张含『课本页 / PDF 页』两列的表。没有对账，全篇页码引用都不可信。",
    "R2": "每个句子对用固定格式：`#### 句 N` + `- **原文**：…` + `- **译文**：…`；N 从 1 起连续、不得跳号或重号。",
    "R3": "小节编号必须与所属章节序号一致且从 1 连续：`## 二、…` 下面只能用 2.1、2.2、2.3…；附录用 `### 附 1`、`附 2`…",
    "R4": "删除占位符，或把未完成的部分改成明确的待确认项（`<待确认:…>`），不要留在正文里。",
    "R5": "在文末补一节「首轮自检与修订记录」，用表格列『问题 / 性质 / 核查依据与处置』。这是审查确实发生过的凭据。",
    "R6": "存在未关闭的待确认项时不得进入阶段二：先逐条向用户确认并修正，或由用户明确批准（`--user-approved-open`）。",
    "R7": "每张图/表都要有独立的详解小节，且覆盖四要素：回答什么问题 / 横坐标 / 纵坐标 / 怎么读（判读清单）。加 `--figures-full` 时按完整清单查六项，多出『为什么要有这张图』与『这张图还能说明什么』。",
    "R8": "表格里出现的小数值若来自读图，必须在小节里标注出处：`按图读数`、`矢量反算`、`原文给出` 之一。",
    "R9": "引用英文原句的小节要标页码（`p.476`）或公式号（`式 (19.1)`），否则读者无法回查。",
    "R10": "正文使用了『推断/推论』类表述时，要打 `【推论】` 标注；反算读数打 `【按图读数】`。三档不混。",
    "R11": "正文页码引用越出目标页范围较多，确认是否为有意的跨页补充（如引用后文的正式解释）。",
    "R12": "缺「待确认项」小节。即使没有待确认，也要写一节并写明『待确认：无』，闸门才能判定。",
    "S2": "学习版按段翻译用固定格式：`#### 第 N 段` + `- **原文**：…` + `- **译文**：…`；N 每页从 1 起连续、不得跳号或重号。",
    "S7": "学习版的图表讲解要『精简但不漏元素』，共十条：回答什么问题 / 为什么要有这张图 / 怎么读 / 坐标轴 / 点 / 线段 / 符号 / 颜色 / 图例 / 这张图还能说明什么。图上出现过的每一类元素都要有一句解释它代表什么统计量。",
    "S8": "学习版的重点公式要写前后文联系：首次定义在哪一页／哪一公式（标位置）、本页为什么用它、后文还会在哪用。缺任一项都会让读者接不上。",
    "R13": "报告必须落在用户确认过的输出目录里：带 `--outdir <目录>` 跑门禁，脚本会核对报告的实际位置是否在该目录内。不一致说明写错了地方，先搬到指定目录再重跑。",
}

PLACEHOLDER_PAT = re.compile(r"TODO|FIXME|TBD|\{\{|\}\}|XX\s*页|待填|待补|此处省略|略去")
CN_NUM = "〇一二三四五六七八九十"
H2_SEC_PAT = re.compile(r"^##\s*([" + CN_NUM + r"]+)、\s*(.+?)\s*$")
H3_SUB_PAT = re.compile(r"^###\s*(\d+)\.(\d+)\s*(.*)$")
H3_APP_PAT = re.compile(r"^###\s*附\s*(\d+)")
SENT_PAT = re.compile(r"^####\s*句\s*(\d+)\s*$")
PARA_PAT = re.compile(r"^####\s*第\s*(\d+)\s*段\s*$")
ANNEX_FIG_PAT = re.compile(r"^###+\s*(?:图表详解|图\s*[\d.]+.*详解|表\s*[\d.]+.*详解)")
FIG_TITLE_PAT = re.compile(r"^(?:#{3,5})\s*.*(?:图|表)\s*\d+[.\-]\d+")
RECONCILE_PATS = [
    re.compile(r"[Pp][Dd][Ff]\s*(\d+)\s*(?:页)?\s*(?:=|＝|→|对应|即)\s*(?:书|课本|印刷)?\s*(?:页)?\s*(\d+)"),
    re.compile(r"(?:书|课本|印刷页)\s*(\d+)\s*(?:页)?\s*(?:=|＝|→|对应|即)\s*[Pp][Dd][Ff]\s*(\d+)"),
]
PAGE_REF_PAT = re.compile(r"(?:p{1,2}\.\s*\d+|第\s*\d+\s*页)")
EN_QUOTE_PAT = re.compile(r"[“\"][A-Z][^”\"]{40,}[”\"]")
ARITH_MARKERS = ("按图读数", "矢量反算", "原文给出", "原文印出", "书中给出", "书中未印出", "反算", "目测")
DECIMAL_PAT = re.compile(r"\d+\.\d+")
# "数值单元格"：整格只由数字/小数点/千分位/百分号/括号/范围连接符组成，且至少含一个小数点。
# 这样才能把 "图 19.4、图 19.5 及比较小节"（含中文）和 "§19.1 收尾" 这类编号排除掉。
_NUMERIC_CELL_PAT = re.compile(r"^[\d\.,\[\]\(\)%\s\u2212\-–—~/～+]+$")


def _numeric_cell_count(row):
    if not row.strip().startswith("|"):
        return 0
    n = 0
    for cell in row.strip().strip("|").split("|"):
        c = cell.strip()
        if not c or "." not in c:
            continue
        if _NUMERIC_CELL_PAT.match(c):
            n += 1
    return n
FIG_SECTION_KEYWORDS = OrderedDict([
    ("回答什么问题", ("回答什么问题", "想回答", "回答的是", "这张图", "本图", "此图")),
    ("横坐标", ("横坐标", "横轴")),
    ("纵坐标", ("纵坐标", "纵轴")),
    ("怎么读", ("怎么读", "读法", "判读", "读图", "怎么看")),
])
# --figures-full：完整清单，在四要素之外再查『为什么要有这张图』与『这张图还能说明什么』
FIG_SECTION_KEYWORDS_FULL = OrderedDict([
    ("回答什么问题", FIG_SECTION_KEYWORDS["回答什么问题"]),
    ("为什么要有这张图", ("为什么要有", "为什么要放", "这张图的作用", "本图的作用",
                          "为什么需要", "放这张图", "为什么给出")),
    ("横坐标", FIG_SECTION_KEYWORDS["横坐标"]),
    ("纵坐标", FIG_SECTION_KEYWORDS["纵坐标"]),
    ("怎么读", FIG_SECTION_KEYWORDS["怎么读"]),
    ("这张图还能说明什么", ("还能说明", "还能看出", "进一步说明", "进一步看出",
                            "还可以看出", "另外还能", "额外的信息", "没被作者点明")),
])
# R10 只针对"断言式"表述，不针对术语：像"后验推断""统计推断"这类是标准名词，不该判为缺标注。
# 因此这里不匹配裸词"推断/推论"，只匹配那些"我在原有文本之外补了一句"的典型措辞。
INFER_PAT = re.compile(
    r"(由此可得|由此推出|由此可以推出|可以推出|可以推断|据此推断|"
    r"由.{0,10}直接得到|由.{0,10}直接推出|由.{0,10}可得|"
    r"并非原文|原文未(说|提)|原文没有说|原文没写|书中未提)"
)
TIER_PAT = re.compile(r"【(推论|按图读数|原文[^】]*|证据[^】]*)】")

# ---------------------------------------------------------------------------
# 学习版（study）专用判定
# ---------------------------------------------------------------------------
# S7 的元素覆盖用"关键词弱校验"：只要图上出现过某一类元素，正文就该有一句解释它代表什么。
# 这是弱校验——正文没提某类关键词不代表图上真没有，所以只报警告、不阻断。
STUDY_ELEMENT_KEYWORDS = OrderedDict([
    ("坐标轴", ("横坐标", "纵坐标", "横轴", "纵轴", "坐标轴", "x 轴", "y 轴")),
    ("点", ("点", "散点", "圆点", "点标记", "每个点", "标记")),
    ("线段", ("线段", "实线", "虚线", "曲线", "误差条", "区间线", "竖线", "横线")),
    ("符号", ("符号", "圆圈", "叉号", "实心", "空心")),
    ("颜色", ("颜色", "配色", "灰色", "深灰", "浅灰", "蓝色", "红色", "绿色", "橙色", "色阶")),
    ("图例", ("图例", "legend")),
])
# 学习版的图表讲解可以精简，但这十条是下限，不能省。
STUDY_FIG_MUST = OrderedDict([
    ("回答什么问题", ("回答什么问题", "想回答", "回答的是", "这张图", "本图", "此图")),
    ("为什么要有这张图", ("为什么要有", "为什么要放", "这张图的作用", "本图的作用",
                          "为什么需要", "放这张图", "为什么给出")),
    ("怎么读", ("怎么读", "读法", "判读", "读图", "怎么看")),
    ("这张图还能说明什么", ("还能说明", "还能看出", "进一步说明", "进一步看出",
                            "还可以看出", "另外还能", "额外的信息", "没被作者点明")),
])
# S8：哪些小节算"公式小节"。只认承载"前后文联系"职责的标题——
# 附录里的「前文接口：式 (19.4)」是接口清单，不是前后文联系小节，另行排除。
FORMULA_SEC_PAT = re.compile(r"(公式|前后文|符号说明)")
# S8：前后文联系的两端线索
FIRST_DEF_PAT = re.compile(r"(首次(定义|出现|引入|给出)|首见于|最初(定义|出现)|定义(在|于)|出自\s*p\.)")
LATER_USE_PAT = re.compile(r"(后文|后续|下文|后面|之后|还会(在|被)|再次出现|被.{0,8}(引用|用到|使用))")


class Issue:
    __slots__ = ("rule", "level", "loc", "msg")

    def __init__(self, rule, level, loc, msg):
        self.rule, self.level, self.loc, self.msg = rule, level, loc, msg

    def fmt(self):
        tag = "x" if self.level == "block" else "!"
        return "[%s] %-4s %-18s %s  -> %s" % (tag, self.rule, self.loc, self.msg, RULE_HELP.get(self.rule, ""))


def _sections(lines):
    """把 md 拆成 [(标题行号, 标题文本, 正文行列表)]，标题为 h2 及以上"""
    out = []
    cur = (-1, "(前言)", [])
    for i, ln in enumerate(lines):
        if re.match(r"^#{1,2}\s+", ln):
            out.append(cur)
            cur = (i, ln.strip(), [])
        else:
            cur[2].append(ln)
    out.append(cur)
    return out


def _blocks(lines):
    """
    按 h3 切块，并为每块附上"上下文"（所属 h2 标题 + 自身标题 + 正文）。
    上下文很重要：页码常常只写在 h2（如 `## 二、第 476 页`），
    而引文的出处判定要看上下文，不能只看 h3 自身。
    返回 [dict(h2_idx, h2, h3_idx, h3, body, ctx)]
    """
    out = []
    h2_idx, h2_title = -1, "(前言)"
    cur = None
    for i, ln in enumerate(lines):
        if re.match(r"^#{1,2}\s+", ln):
            if cur:
                out.append(cur)
                cur = None
            h2_idx, h2_title = i, ln.strip()
        elif re.match(r"^#{3}\s+", ln):
            if cur:
                out.append(cur)
            cur = {"h2_idx": h2_idx, "h2": h2_title, "h3_idx": i,
                   "h3": ln.strip(), "body": []}
        else:
            if cur is None:
                cur = {"h2_idx": h2_idx, "h2": h2_title, "h3_idx": -1,
                       "h3": "(无小节)", "body": []}
            cur["body"].append(ln)
    if cur:
        out.append(cur)
    for b in out:
        b["ctx"] = "\n".join([b["h2"], b["h3"]] + b["body"])
    return out


def check_r1(lines, text, issues):
    """页码对账"""
    ok = False
    offset = None
    for m in RECONCILE_PATS[0].finditer(text):
        pdf, book = int(m.group(1)), int(m.group(2))
        offset = pdf - book
        ok = True
        break
    if not ok:
        for m in RECONCILE_PATS[1].finditer(text):
            book, pdf = int(m.group(1)), int(m.group(2))
            offset = pdf - book
            ok = True
            break
    if not ok and "课本页" in text and "PDF" in text:
        ok = True          # 让步：至少有对照表
    if not ok:
        issues.append(Issue("R1", "block", "全文", "未找到页码对账（形如 `PDF 491 = 书 476`）"))
    return offset


def check_r2(lines, issues):
    """句子对编号连续 + 原文/译文成对"""
    seq = []
    for i, ln in enumerate(lines):
        m = SENT_PAT.match(ln.strip())
        if m:
            seq.append((i, int(m.group(1))))
    if not seq:
        issues.append(Issue("R2", "block", "全文", "未找到任何 `#### 句 N` 句子对（逐句翻译是本技能的必备产出）"))
        return
    nums = [n for _i, n in seq]
    # 允许每个小节内重新从 1 开始，故按"段内连续"判定
    runs, cur = [], [nums[0]]
    for a, b in zip(nums, nums[1:]):
        if b == a + 1:
            cur.append(b)
        else:
            runs.append(cur)
            cur = [b]
    runs.append(cur)
    for run in runs:
        if run[0] != 1:
            issues.append(Issue("R2", "block", "句 %d" % run[0],
                                "句子编号不是从 1 开始（本段首个编号为 %d）" % run[0]))
        if run != list(range(run[0], run[0] + len(run))):
            issues.append(Issue("R2", "block", "句 %d–%d" % (run[0], run[-1]), "句子编号有跳号或重号"))
    # 原文/译文成对
    for idx, _n in seq:
        chunk = "\n".join(lines[idx: idx + 8])
        if "**原文**" not in chunk:
            issues.append(Issue("R2", "block", lines[idx].strip(), "该句缺 `- **原文**：…`"))
        if "**译文**" not in chunk:
            issues.append(Issue("R2", "block", lines[idx].strip(), "该句缺 `- **译文**：…`"))


def check_r3(lines, issues):
    """小节编号连续且与所属章节序号一致"""
    cur_sec = None
    counters = {}
    saw_sub = False
    for i, ln in enumerate(lines):
        m2 = H2_SEC_PAT.match(ln.strip())
        if m2:
            cn = m2.group(1)
            cur_sec = CN_NUM.index(cn[0]) if cn and cn[0] in CN_NUM else cur_sec
            if cn == "〇":
                cur_sec = 0
            counters = {}
            continue
        m3 = H3_SUB_PAT.match(ln.strip())
        if m3:
            saw_sub = True
            major, minor = int(m3.group(1)), int(m3.group(2))
            if cur_sec is not None and major != cur_sec:
                issues.append(Issue("R3", "block", "第 %d 行" % (i + 1),
                                    "小节编号 %d.%d 与所属章节序号 %s 不一致" % (major, minor, cur_sec)))
            exp = counters.get(major, 0) + 1
            if minor != exp:
                issues.append(Issue("R3", "block", "第 %d 行" % (i + 1),
                                    "小节编号跳到 %d.%d，期望 %d.%d" % (major, minor, major, exp)))
            counters[major] = minor
    # 附录编号
    app = [int(H3_APP_PAT.match(ln.strip()).group(1))
           for ln in lines if H3_APP_PAT.match(ln.strip())]
    for k, n in enumerate(app, start=1):
        if n != k:
            issues.append(Issue("R3", "block", "附 %d" % n, "附录编号不连续，期望 附 %d" % k))
    if not saw_sub and not app:
        issues.append(Issue("R3", "block", "全文", "未找到任何小节编号（`### 2.1 …`）"))


def check_r4(text, issues):
    for m in PLACEHOLDER_PAT.finditer(text):
        ln = text[:m.start()].count("\n") + 1
        issues.append(Issue("R4", "block", "第 %d 行" % ln, "残留占位符 %r" % m.group(0)))
        if len([1 for x in issues if x.rule == "R4"]) >= 12:
            break


def check_r5(lines, issues):
    if not any(re.search(r"(首轮自检|自检与修订|核查与修订|审查记录|修订记录)", ln) for ln in lines):
        issues.append(Issue("R5", "block", "文末", "缺「首轮自检与修订记录」章节"))


def check_r6(lines, text, issues, gate, approved, exempt):
    """待确认项闸门"""
    sec = None
    for i, ln in enumerate(lines):
        if re.search(r"待确认", ln) and re.match(r"^#{1,4}\s+", ln):
            sec = i
    if sec is None:
        issues.append(Issue("R12", "warn" if gate != "phase2" else "block", "全文", "缺「待确认项」小节"))
        open_items = 0
    else:
        body = lines[sec:]
        body_txt = "\n".join(body)
        if re.search(r"待确认[^\n]{0,6}[:：]\s*(无|没有|none)", body_txt, re.I):
            open_items = 0
        else:
            open_items = 0
            open_items += len(re.findall(r"^\s*[-*+]\s*\[ \]", body_txt, re.M))
            open_items += len(re.findall(r"<待确认[:：]", body_txt))
            open_items += len(re.findall(r"\|\s*open\s*\|", body_txt, re.I))
    if gate == "phase2" and open_items > 0 and not (approved or "user-approved-open" in exempt):
        issues.append(Issue("R6", "block", "待确认项",
                            "存在 %d 条未关闭待确认项，不得进入阶段二" % open_items))
    return open_items


def check_r7(lines, issues, full=False):
    """图表详解要素覆盖。full=True（--figures-full）时按完整清单查六项。"""
    blocks = _blocks(lines)
    fig_blocks = [b for b in blocks
                  if re.search(r"(图|表)\s*\d+[.\-]\d+", b["h3"]) and re.search(r"详解|解析|讲解", b["h3"])]
    checklist = FIG_SECTION_KEYWORDS_FULL if full else FIG_SECTION_KEYWORDS
    if not fig_blocks:
        issues.append(Issue("R7", "warn", "全文", "未找到『图/表 N.M 详解』小节，无法核对要素覆盖"))
        return
    for b in fig_blocks:
        ctx = b["ctx"].replace("**", "") if full else b["ctx"]
        miss = [name for name, keys in checklist.items()
                if not any(k in ctx for k in keys)]
        if miss:
            issues.append(Issue("R7", "warn", "第 %d 行 %s" % (b["h3_idx"] + 1, b["h3"][:40]),
                                "该图表详解缺要素：%s" % "、".join(miss)))


def check_r13(md_path, outdir, issues):
    """输出目录闸门：交付物必须落在用户确认过的目录里。
    没提供 --outdir 时不做任何判定（既有用法与结果不变）。"""
    if not outdir:
        return
    md_dir = os.path.dirname(os.path.abspath(md_path))
    want = os.path.abspath(outdir)
    if md_dir == want:
        return
    try:
        inside = os.path.commonpath([md_dir, want]) == want
    except ValueError:                     # 不同盘符
        inside = False
    if not inside:
        issues.append(Issue("R13", "block", "输出目录",
                            "报告不在用户指定的输出目录内：报告在 %s，指定目录是 %s" % (md_dir, want)))


def check_r8(lines, issues):
    """表格里出现"读数值单元格" -> 所属小节（含所属大节标题的页码）须有出处标注"""
    for b in _blocks(lines):
        n_cells = sum(_numeric_cell_count(ln) for ln in b["body"])
        if n_cells == 0:
            continue
        if any(k in b["ctx"] for k in ARITH_MARKERS):
            continue
        issues.append(Issue("R8", "warn", "第 %d 行 %s" % (b["h3_idx"] + 1, b["h3"][:40]),
                            "该小节表格含 %d 个数值单元格，但未标注出处（按图读数/矢量反算/原文给出）" % n_cells))


def check_r9(lines, issues):
    """
    逐条英文直引检查出处：引文所在行及其后 2 行内，必须出现页码或公式号。
    以"引文"为单位而不是"小节"为单位——因为小节标题本身常已带页码，
    按小节判会永远通过（等于没检查）。
    """
    hit = 0
    for i, ln in enumerate(lines):
        if not EN_QUOTE_PAT.search(ln):
            continue
        window = "\n".join(lines[i:i + 3])
        if PAGE_REF_PAT.search(window) or re.search(r"式\s*\(\d+\.\d+\)", window):
            continue
        issues.append(Issue("R9", "warn", "第 %d 行" % (i + 1),
                            "英文直引未标出处：%s" % ln.strip()[:44]))
        hit += 1
        if hit >= 8:
            break


def check_r10(text, issues):
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if INFER_PAT.search(ln) and len(ln.strip()) >= 12 and not TIER_PAT.search(ln):
            issues.append(Issue("R10", "warn", "第 %d 行" % (i + 1),
                                "出现推断类表述但无【推论】标注：%s" % ln.strip()[:40]))
            if len([1 for x in issues if x.rule == "R10"]) >= 8:
                break


def check_r11(text, issues, offset, pages_hint):
    if offset is None or not pages_hint:
        return
    lo, hi = min(pages_hint), max(pages_hint)
    bad = set()
    for m in re.finditer(r"p{1,2}\.\s*(\d+)", text):
        v = int(m.group(1))
        if v < lo - 30 or v > hi + 30:
            bad.add(v)
    for m in re.finditer(r"第\s*(\d+)\s*页", text):
        v = int(m.group(1))
        if v < lo - 30 or v > hi + 30:
            bad.add(v)
    if bad:
        issues.append(Issue("R11", "warn", "全文",
                            "页码引用越界较多：%s（目标范围 %d–%d，已放宽 ±30）"
                            % (", ".join("p.%d" % v for v in sorted(bad)), lo, hi)))


def _para_extent(lines, idx):
    """一个段落块的结束行：下一个任意级别的标题行（没有则到文末）。
    不能像 check_r2 那样只看后 8 行——按段翻译时一段的原文/译文可以很长，
    窗口太小会把"缺译文"误报成缺失。"""
    for j in range(idx + 1, len(lines)):
        if re.match(r"^#{1,6}\s+", lines[j]):
            return j
    return len(lines)


def check_s2(lines, issues):
    """学习版：段落编号连续 + 每段有原文与译文（替代 report 模式的 R2）"""
    seq = []
    for i, ln in enumerate(lines):
        m = PARA_PAT.match(ln.strip())
        if m:
            seq.append((i, int(m.group(1))))
    if not seq:
        issues.append(Issue("S2", "block", "全文",
                            "未找到任何 `#### 第 N 段` 段落对（按段翻译是学习版的必备产出）"))
        return
    nums = [n for _i, n in seq]
    runs, cur = [], [nums[0]]
    for a, b in zip(nums, nums[1:]):
        if b == a + 1:
            cur.append(b)
        else:
            runs.append(cur)
            cur = [b]
    runs.append(cur)
    for run in runs:
        if run[0] != 1:
            issues.append(Issue("S2", "block", "第 %d 段" % run[0],
                                "段落编号不是从 1 开始（本页首个编号为 %d）" % run[0]))
        if run != list(range(run[0], run[0] + len(run))):
            issues.append(Issue("S2", "block", "第 %d–%d 段" % (run[0], run[-1]),
                                "段落编号有跳号或重号"))
    for idx, _n in seq:
        chunk = "\n".join(lines[idx:_para_extent(lines, idx)])
        if "**原文**" not in chunk:
            issues.append(Issue("S2", "block", lines[idx].strip(), "该段缺 `- **原文**：…`"))
        if "**译文**" not in chunk:
            issues.append(Issue("S2", "block", lines[idx].strip(), "该段缺 `- **译文**：…`"))


def check_s7(lines, issues):
    """学习版：图表讲解的元素覆盖 + 两项必留内容（警告级弱校验）"""
    blocks = _blocks(lines)
    fig_blocks = [b for b in blocks
                  if re.search(r"(图|表)\s*\d+[.\-]\d+", b["h3"]) and re.search(r"详解|解析|讲解", b["h3"])]
    if not fig_blocks:
        issues.append(Issue("S7", "warn", "全文",
                            "未找到『图/表 N.M 讲解』小节，无法核对图表元素覆盖"
                            "（本页范围确实没有图表时可忽略）"))
        return
    for b in fig_blocks:
        # 去掉加粗记号再匹配：`- **点**：…` 这类写法不该因为两个星号被判成"没讲点"
        ctx = b["ctx"].replace("**", "")
        miss = [name for name, keys in STUDY_FIG_MUST.items()
                if not any(k in ctx for k in keys)]
        miss += [name for name, keys in STUDY_ELEMENT_KEYWORDS.items()
                 if not any(k in ctx for k in keys)]
        if miss:
            issues.append(Issue("S7", "warn", "第 %d 行 %s" % (b["h3_idx"] + 1, b["h3"][:40]),
                                "该图表讲解未覆盖：%s" % "、".join(miss)))


def check_s8(lines, issues):
    """学习版：重点公式/符号是否给出前后文联系（首次定义位置 + 后续使用位置）"""
    targets = [b for b in _blocks(lines)
               if FORMULA_SEC_PAT.search(b["h3"]) and not H3_APP_PAT.match(b["h3"].strip())]
    if not targets:
        return
    for b in targets:
        miss = []
        if not FIRST_DEF_PAT.search(b["ctx"]):
            miss.append("首次定义位置")
        if not LATER_USE_PAT.search(b["ctx"]):
            miss.append("后续使用位置")
        if not (PAGE_REF_PAT.search(b["ctx"]) or re.search(r"式\s*\(?\d+\.\d+\)?", b["ctx"])):
            miss.append("位置标注（页码或公式号）")
        if miss:
            issues.append(Issue("S8", "warn", "第 %d 行 %s" % (b["h3_idx"] + 1, b["h3"][:40]),
                                "公式的前后文联系缺：%s" % "、".join(miss)))


def main():
    ap = argparse.ArgumentParser(description="阶段一报告静态校验（退出码即判据）")
    ap.add_argument("--md", required=True, help="待校验的 Markdown 报告")
    ap.add_argument("--gate", default="report", choices=["report", "phase2"],
                    help="report=阶段一收尾检查；phase2=进入阶段二前的硬前置")
    ap.add_argument("--mode", default="report", choices=["report", "study"],
                    help="report=组会汇报版骨架（默认）；study=课题组学习版骨架")
    ap.add_argument("--strict-content", action="store_true", help="把内容类警告升级为阻断")
    ap.add_argument("--allow-scan-pages", action="store_true")
    ap.add_argument("--allow-no-precise-reading", action="store_true")
    ap.add_argument("--user-approved-open", action="store_true")
    ap.add_argument("--pages", default="", help="目标书内页范围，如 476-477（用于越界检查）")
    ap.add_argument("--outdir", default="",
                    help="用户确认过的输出目录；提供时校验报告是否落在其中（铁律 5）")
    ap.add_argument("--review", default="",
                    help="审查记录文件（含「首轮自检与修订记录」「待确认项」）——"
                         "交付物里不再包含这两节时，用本参数把门禁指向它")
    ap.add_argument("--figures-full", action="store_true",
                    help="按完整图表清单查 R7（多查『为什么要有这张图』与『这张图还能说明什么』）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    try:
        raw = open(args.md, "rb").read()
        text = raw.decode("utf-8", "replace")
    except Exception as exc:
        print("[!!] check-report 无法读取文件，不得静默通过：%s" % exc)
        return 1

    exempt = [k for k, v in (("allow-scan-pages", args.allow_scan_pages),
                             ("allow-no-precise-reading", args.allow_no_precise_reading),
                             ("user-approved-open", args.user_approved_open)) if v]
    review_text = ""
    if args.review:
        try:
            review_text = open(args.review, "rb").read().decode("utf-8", "replace")
        except Exception as exc:
            print("[!!] check-report 无法读取审查记录文件，不得静默通过：%s" % exc)
            return 1

    lines = text.split("\n")
    # 「首轮自检与修订记录」「待确认项」允许放在独立的审查记录文件里（交付物不再包含这两节）。
    # 没给 --review 时 lines_aux/text_aux 与 lines/text 完全相同，既有用法与结果不变。
    lines_aux = lines + (["", ""] + review_text.split("\n") if review_text else [])
    text_aux = text + ("\n" + review_text if review_text else "")
    issues = []

    try:
        pages_hint = []
        if args.pages:
            for part in args.pages.replace(" ", "").split(","):
                if "-" in part:
                    a, b = part.split("-", 1)
                    pages_hint.extend(range(int(a), int(b) + 1))
                elif part:
                    pages_hint.append(int(part))
        offset = check_r1(lines, text, issues)
        if args.mode == "study":
            check_s2(lines, issues)
        else:
            check_r2(lines, issues)
        check_r3(lines, issues)
        check_r4(text, issues)
        check_r5(lines_aux, issues)
        check_r9(lines, issues)
        if "allow-no-precise-reading" not in exempt:
            check_r8(lines, issues)
        if args.mode == "study":
            check_s7(lines, issues)
            check_s8(lines, issues)
        else:
            check_r7(lines, issues, args.figures_full)
        check_r10(text, issues)
        if not pages_hint:
            book_pages = [int(m.group(2)) for m in RECONCILE_PATS[0].finditer(text)]
            book_pages += [int(m.group(1)) for m in RECONCILE_PATS[1].finditer(text)]
            pages_hint = book_pages
        check_r11(text, issues, offset, pages_hint)
        open_items = check_r6(lines_aux, text_aux, issues, args.gate, args.user_approved_open, exempt)
        check_r13(args.md, args.outdir, issues)
    except Exception as exc:                                  # 异常不得静默通过
        print("[!!] check-report 异常，不得静默通过。请修复后重试：%s" % exc)
        return 1

    blocks = [i for i in issues if i.level == "block"]
    warns = [i for i in issues if i.level == "warn"]
    if args.strict_content:
        blocks, warns = blocks + warns, []

    uniq, seen = [], set()
    for it in blocks + warns:
        key = (it.rule, it.loc, it.msg)
        if key not in seen:
            seen.add(key)
            uniq.append(it)
    blocks = [i for i in uniq if i.level == "block" or args.strict_content]
    warns = [i for i in uniq if i.level == "warn" and not args.strict_content]

    result = {
        "md": args.md,
        "mode": args.mode,
        "gate": args.gate,
        "outdir": args.outdir,
        "review": args.review,
        "figures_full": args.figures_full,
        "blocking": len(blocks),
        "warnings": len(warns),
        "open_items": open_items,
        "exemptions": exempt,
        "issues": [{"rule": i.rule, "level": i.level, "loc": i.loc, "msg": i.msg} for i in uniq],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif not args.quiet:
        print("=" * 72)
        print("check-report  %s   gate=%s" % (args.md, args.gate))
        if args.mode == "study":
            print("模式          study（课题组学习版骨架）")
        if exempt:
            print("豁免开关      %s  （会话收尾必须声明）" % ", ".join("--" + e for e in exempt))
        print("待确认项      %d 条未关闭" % open_items)
        print("-" * 72)
        if blocks:
            print("结构类（阻断，%d 条）：" % len(blocks))
            for i in blocks:
                print("  " + i.fmt())
        else:
            print("结构类（阻断）：无")
        if warns:
            print("内容类（仅警告，%d 条）：" % len(warns))
            for i in warns:
                print("  " + i.fmt())
        print("-" * 72)
        gate_name = "study-gate" if args.mode == "study" else "report-gate"
        done_word = "学习版阶段一" if args.mode == "study" else "阶段一"
        if blocks:
            print("[!!] %s: %d blocking issue(s) -- 不得宣称%s完成" % (gate_name, len(blocks), done_word))
        else:
            print("[ok] %s passed (%d warnings)" % (gate_name, len(warns)))
            if warns:
                print("     内容类警告不影响放行，但请在收尾清单里说明处理情况。")

    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())

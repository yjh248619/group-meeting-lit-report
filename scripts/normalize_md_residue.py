#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""normalize_md_residue.py —— 阶段一 MD 的 HTML 残留归一化（阶段二开工前的硬前置）

为什么需要它：阶段一的 MD 若由 HTML 报告机械转换而来（HTML→MD），会留下 HTML 残留，
它们在 Markdown 阅读器里看起来正常，但会让「MD → LaTeX/docx」这一步**静默丢内容**：

  · 原始 `<table>` 块在 pandoc 里是 raw block —— 转 LaTeX 时**整块被丢弃**，表格消失
  · 行内上下标标签只丢标签、留内容 —— `y<sub>i</sub>` 变成字面 `yi`（数学含义丢失）
  · `\[…\]` 会被 pandoc 当**行间公式**（区间写成 \[0.94, 0.99\] 时尤其危险）
  · 换行标签在管道表里无法表达

本脚本做 token 级等价改写（不增删任何内容）：
  1. colgroup 块            -> 删除
  2. 相邻 sub+sup           -> $_{X}^{Y}$   （正则限「标签内不含尖括号」，否则会跨标签错配）
  3. sup 内含 sub           -> $^{-\beta_4}$ 这类（逐个显式处理并断言无遗留嵌套）
  4. sub X                  -> $_X$
  5. sup Y                  -> $^Y$          （内容以 \ 命令开头时不套 {}，避免产生 }} 命中门禁 R4）
  6. strong                 -> ** **
  7. br                     -> 空格
  8. table 块               -> 管道表（colspan 文本落首列，其余列留空）
  9. \[ \] -> [ ] ；\# -> #  （去转义，消除行间公式误判）
 10. \| 保持不动（管道表内的合法转义，pandoc 亦安全）

两道安全网（任一不通过则**拒绝落盘**）：
  · 纯文本骨架全等：剥掉全部 HTML/Markdown/LaTeX 记号后逐字比较，必须一字不差
  · R4 守卫：不得引入 {{ 或 }}（那是门禁 check_report.py 的占位符判定）

用法：
  python normalize_md_residue.py --md <报告>.md            # dry-run，只报告
  python normalize_md_residue.py --md <报告>.md --apply    # 落盘（自动备份）

落盘后必须重跑：python scripts/check_report.py --md <报告>.md --pages <起>-<止>
（表格由 HTML 变成管道表后，R8「数值表须标出处」会对这些表**开始生效**，可能报出新警告。）
"""
from __future__ import annotations

import argparse
import datetime
import re
import shutil
import sys
from html.parser import HTMLParser

SUB_SUP_MAP = {"θ": r"\theta", "2α": r"2\alpha", "init": r"\mathrm{init}"}
_TAG = r"[^<>]"                      # 标签内容里不允许出现尖括号
TAG_SCAN = r"</?(?:table|thead|tbody|tr|td|th|col|colgroup|sub|sup|strong|br)\b[^>]*>"


def tex(s: str) -> str:
    return SUB_SUP_MAP.get(s.strip(), s.strip())


def wrap(s: str) -> str:
    """上标内容以反斜杠命令开头时不再套一层花括号，否则会产生 }} 命中门禁 R4。"""
    return s if s.startswith("\\") else "{" + s + "}"


GREEK = {"α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "θ": r"\theta",
         "μ": r"\mu", "σ": r"\sigma", "τ": r"\tau", "ψ": r"\psi"}


def nest_math(a: str, b: str) -> str:
    """把「上标里再套下标」这类嵌套（如 −β 与 4）拼成一个数学片段。
    下标是单字符时不加花括号，且末尾若出现 }} 则插入 \\! 断开 —— 两者都是为了不命中门禁 R4。"""
    a = a.replace("\u2212", "-")
    for g, t in GREEK.items():
        a = a.replace(g, t)
    sub = tex(b)
    if not (len(sub) == 1 or sub.startswith("\\")):
        sub = "{" + sub + "}"
    return ("$^{%s_%s}$" % (a, sub)).replace("}}", "}\\!}")


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.cur, self.row, self.cell, self.span, self.section = \
            [], None, None, None, 1, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self.cur = {"head": [], "body": []}
        elif tag in ("thead", "tbody"):
            self.section = tag
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell, self.span = [], int(a.get("colspan") or 1)
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_endtag(self, tag):
        if tag == "table":
            if self.cur:
                self.tables.append(self.cur)
            self.cur = None
        elif tag in ("thead", "tbody"):
            self.section = None
        elif tag == "tr":
            if self.cur is not None and self.row is not None:
                self.cur["head" if self.section == "thead" else "body"].append(self.row)
            self.row = None
        elif tag in ("td", "th"):
            self.row.append((re.sub(r"\s+", " ", "".join(self.cell)).strip(), self.span))
            self.cell = None

    def handle_data(self, d):
        if self.cell is not None:
            self.cell.append(d)


def esc_cell(s: str) -> str:
    s = s.replace("\\|", "\x00").replace("|", "\\|")
    return s.replace("\x00", "\\|")


def to_pipe(tbl) -> tuple:
    head = tbl["head"][0] if tbl["head"] else []
    ncol = max([sum(sp for _t, sp in r) for r in (tbl["head"] + tbl["body"])] or [0])

    def rowline(r):
        cells = []
        for txt, sp in r:
            cells.append(esc_cell(txt))
            cells += [""] * (sp - 1)
        cells += [""] * (ncol - len(cells))
        return "| " + " | ".join(cells) + " |"

    lines = [rowline(head), "|" + "|".join(["----"] * ncol) + "|"]
    lines += [rowline(r) for r in tbl["body"]]
    return "\n".join(lines), ncol, len(tbl["body"])


def normalize(text: str, log: list) -> str:
    n_sub_all, n_sup_all = text.count("<sub>"), text.count("<sup>")

    n = len(re.findall(r"<colgroup>.*?</colgroup>", text, re.S))
    text = re.sub(r"<colgroup>.*?</colgroup>\s*", "", text, flags=re.S)
    log.append("1. 删除 colgroup 块：%d" % n)

    pat_merge = r"<sub>(%s*)</sub><sup>(%s*)</sup>" % (_TAG, _TAG)
    c_merge = len(re.findall(pat_merge, text))
    text = re.sub(pat_merge, lambda m: "$_{%s}^%s$" % (tex(m.group(1)), wrap(tex(m.group(2)))), text)
    log.append("2. sub+sup 相邻合并：%d" % c_merge)

    c_nest = len(re.findall(r"<sup>([^<]*)<sub>([^<>]*)</sub></sup>", text))
    if c_nest:
        text = re.sub(r"<sup>([^<]*)<sub>([^<>]*)</sub></sup>",
                      lambda m: nest_math(m.group(1), m.group(2)), text)
    log.append("3. 嵌套 sup(内含 sub)：%d" % c_nest)
    for pat in (r"<sup>[^<]*<sub>", r"<sub>[^<]*<sup>"):
        m = re.search(pat, text)
        if m:
            raise SystemExit("[!!] 仍有未处理嵌套，中止。命中 %s -> ...%s..."
                             % (pat, text[max(0, m.start() - 80):m.end() + 80].replace("\n", "\\n")))

    c4 = len(re.findall(r"<sub>(%s*)</sub>" % _TAG, text))
    text = re.sub(r"<sub>(%s*)</sub>" % _TAG, lambda m: "$_{%s}$" % tex(m.group(1)), text)
    c5 = len(re.findall(r"<sup>(%s*)</sup>" % _TAG, text))
    text = re.sub(r"<sup>(%s*)</sup>" % _TAG, lambda m: "$^%s$" % wrap(tex(m.group(1))), text)
    log.append("4. sub -> $_…$：%d" % c4)
    log.append("5. sup -> $^…$：%d" % c5)
    expect_sub = n_sub_all - c_merge - c_nest
    expect_sup = n_sup_all - c_merge - c_nest
    if c4 != expect_sub or c5 != expect_sup:
        raise SystemExit("[!!] 上下标账目不平：sub %d!=%d  sup %d!=%d，中止"
                         % (c4, expect_sub, c5, expect_sup))
    log.append("   账目核对：%d+%d+%d=%d ✓ ／ %d+%d+%d=%d ✓"
               % (c_merge, c_nest, c4, n_sub_all, c_merge, c_nest, c5, n_sup_all))

    n_strong = len(re.findall(r"<strong>", text))
    c = len(re.findall(r"<strong>(%s*)</strong>" % _TAG, text, re.S))
    if c != n_strong:
        raise SystemExit("[!!] strong 标签 %d 个只匹配到 %d 个，中止" % (n_strong, c))
    text = re.sub(r"<strong>(%s*)</strong>" % _TAG,
                  lambda m: "**" + m.group(1).strip() + "**", text, flags=re.S)
    log.append("6. strong -> ** **：%d" % c)

    c = len(re.findall(r"<br\s*/?>", text))
    text = re.sub(r"<br\s*/?>\s*", " ", text)
    log.append("7. br -> 空格：%d" % c)

    tp = TableParser()
    tp.feed(text)
    for i, tbl in enumerate(tp.tables, 1):
        pipe, ncol, nrow = to_pipe(tbl)
        log.append("8.%d 表 %d -> 管道表（%d 列 × %d 数据行）：" % (i, i, ncol, nrow))
        log.extend("      " + x for x in pipe.split("\n"))
    text = re.sub(r"<table[^>]*>.*?</table>", lambda m: to_pipe(tp.tables.pop(0))[0], text, flags=re.S)

    c = text.count("\\[") + text.count("\\]")
    text = text.replace("\\[", "[").replace("\\]", "]")
    c2 = text.count("\\#")
    text = text.replace("\\#", "#")
    log.append("9. \\[ \\] 去转义：%d 个；\\# -> #：%d" % (c, c2))

    left = re.findall(TAG_SCAN, text)
    log.append("10. 残留 HTML 标签：%d %s" % (len(left), sorted(set(left))[:6]))
    if left:
        raise SystemExit("[!!] 仍有残留标签，中止：%s" % sorted(set(left))[:6])
    for bad in ("{{", "}}"):
        if bad in text:
            i = text.index(bad)
            raise SystemExit("[!!] 引入 %s（会命中门禁 R4）：...%s..." % (bad, text[max(0, i - 60):i + 30]))
    log.append("    R4 守卫：未引入双花括号 ✓")
    return text


def skeleton(s: str) -> str:
    for a, b in ((r"\mathrm", ""), (r"\theta", "θ"), (r"\alpha", "α"), (r"\beta", "β")):
        s = s.replace(a, b)
    s = s.replace("\u2212", "-")
    s = re.sub(r"</?[a-zA-Z][^>]*>", "", s)
    return re.sub(r"[|`*_\-\s$\\{}^]", "", s)


def main() -> int:
    ap = argparse.ArgumentParser(description="阶段一 MD 的 HTML 残留归一化（等价改写 + 双安全网）")
    ap.add_argument("--md", required=True, help="待归一化的 Markdown 报告")
    ap.add_argument("--apply", action="store_true", help="真正落盘（默认只 dry-run）")
    ap.add_argument("--log", default="", help="核对报告输出路径，默认写到 <md>.normalize.log.txt")
    args = ap.parse_args()

    logpath = args.log or (args.md + ".normalize.log.txt")
    raw = open(args.md, "rb").read()
    text = raw.decode("utf-8")
    crlf = b"\r\n" in raw
    if crlf:
        text = text.replace("\r\n", "\n")

    log = []
    new = normalize(text, log)
    a, b = skeleton(text), skeleton(new)
    log.append("")
    log.append("=== 纯文本骨架全等核对（剥掉全部 HTML/Markdown/LaTeX 记号后逐字比较）===")
    log.append("改动前 %d 字符，改动后 %d 字符" % (len(a), len(b)))
    if a == b:
        log.append("结论：一字不差 —— 归一化未增删任何内容")
    else:
        i = 0
        while i < min(len(a), len(b)) and a[i] == b[i]:
            i += 1
        log.append("结论：存在差异（第 %d 字符附近）" % i)
        log.append("  前：" + a[max(0, i - 60):i + 60])
        log.append("  后：" + b[max(0, i - 60):i + 60])

    open(logpath, "w", encoding="utf-8").write("\n".join(log))

    if not args.apply:
        print("[dry-run] 未落盘（加 --apply 落盘）。核对报告：%s" % logpath)
        return 0
    if a != b:
        print("[!!] 骨架不一致，拒绝落盘。详见 %s" % logpath)
        return 1
    bk = args.md.rsplit(".", 1)[0] + "_pre_normalize_backup." + args.md.rsplit(".", 1)[-1]
    shutil.copyfile(args.md, bk)
    open(args.md, "wb").write((new.replace("\n", "\r\n") if crlf else new).encode("utf-8"))
    print("[ok] 已归一化并落盘  日期=%s  备份=%s  核对报告=%s"
          % (datetime.date.today(), bk, logpath))
    print("     下一步必须重跑：python scripts/check_report.py --md \"%s\" --pages <起>-<止>" % args.md)
    return 0


if __name__ == "__main__":
    sys.exit(main())

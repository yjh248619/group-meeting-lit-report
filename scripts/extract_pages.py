#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
extract_pages.py —— 组会文献汇报取证工具（阶段一开工第一步）

按页码范围抽取正文、导出版本地图、渲染整页与图表高清图、导出矢量坐标素材。

用法示例：
  python extract_pages.py --pdf "book.pdf" --pages 491-492 --book-offset 15 --out work --dpi 430
  python extract_pages.py --pdf "book.pdf" --pages 491,492 --book-offset 15 \
      --crop "491:98,56,380,190:fig_19_4" --crop "492:136,58,358,212:fig_19_6"

输出结构：
  <out>/text/page_<pdf页>.txt        逐页正文（已修正跨行连字符）
  <out>/pages/page_<pdf页>.png       整页渲染（dpi=200，供人工定位）
  <out>/figures/<name>.png           按 --crop 裁剪的高清图（dpi=--dpi）
  <out>/vectors/page_<pdf页>.txt     矢量元素坐标 + 词坐标 + 绘制类型统计
  <out>/summary.txt                  字符数、页码对账、章节地图、异常提示

注意：本机 PowerShell 的 stdout 不会被工具捕获，建议把本脚本输出同时写到文件：
  & "<venv>\Scripts\python.exe" extract_pages.py ... *> extract_log.txt
"""
from __future__ import annotations

import argparse
import os
import re
import sys

try:
    import pymupdf as fitz
except Exception:  # pragma: no cover
    try:
        import fitz  # older PyMuPDF
    except Exception as exc:  # pragma: no cover
        sys.exit("需要 pymupdf：pip install pymupdf  (%s)" % exc)


def parse_pages(spec: str):
    """'491-492' / '491,492' / '491-492,500' -> sorted list[int]"""
    out = []
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def dehyphenate(text: str) -> str:
    """修正跨行连字符断行：'metabo-\\nlized' -> 'metabolized'"""
    return re.sub(r"([A-Za-z])-\n([a-z])", r"\1\2", text)


def _lines_with_fonts(page):
    """按行取出文本及其 span 字体信息"""
    rows = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            spans = [s for s in l.get("spans", []) if s.get("text")]
            if not spans:
                continue
            rows.append(("".join(s["text"] for s in spans), spans))
    return rows


def _is_bold_font(name):
    """粗体/黑体判定：CMBX10 这类用 'bx'，中文黑体用 'hei'，其余用 'bold'/'black'/'heavy'"""
    n = (name or "").lower()
    return any(k in n for k in ("bx", "bold", "black", "heavy", "hei", "semibold"))


_PAT_NUM = re.compile(r"^[1-9]\d?\.\d{1,2}(\.\d{1,2})?$")
_PAT_NUM_TITLE = re.compile(r"^[1-9]\d?\.\d{1,2}(\.\d{1,2})?\s+[A-Z(（]")
_PAT_NAMED = re.compile(
    r"^(bibliographic note|further reading|exercises|references|bibliography|"
    r"acknowledg(e)?ments?|讨论|小结|本章小结|习题|参考文献)$", re.I)
# 形如表格数据行：只含数字/标点
_NUMERIC_ONLY = re.compile(r"^[\d.,%()\[\]+\-/–—\s]+$")


def _is_table_number(line, prev, nxt):
    """判断一行是否是表格里的纯数值行（首行/末行的邻居检查）"""
    if not _PAT_NUM.match(line):
        return False
    return bool(_NUMERIC_ONLY.match(prev or "")) or bool(_NUMERIC_ONLY.match(nxt or ""))


def section_map(doc, pages, offset):
    """
    用"字体特征"识别小节标题：章节号独立成行时字号常与正文相同（如 CMBX10），
    所以不能只靠字号，要靠"整行基本为粗体/黑体"这一特征。
    并保留一套收紧后的正则作为兜底（应对标题不带粗体的排版）。
    """
    hits = []
    for pno in pages:
        if pno < 1 or pno > doc.page_count:
            continue
        page = doc[pno - 1]
        try:
            lines = _lines_with_fonts(page)
        except Exception:
            lines = []
        if not lines:
            continue
        sizes = {}
        for _txt, spans in lines:
            for s in spans:
                sizes[round(s["size"], 1)] = sizes.get(round(s["size"], 1), 0) + len(s["text"])
        body = max(sizes.items(), key=lambda kv: kv[1])[0] if sizes else 10.0
        found = False
        for txt, spans in lines:
            t = txt.strip()
            if not t or len(t) > 90:
                continue
            total = max(1, len("".join(s["text"] for s in spans).strip()))
            bold_len = sum(len(s["text"]) for s in spans if _is_bold_font(s["font"]))
            big = max(s["size"] for s in spans) > body + 0.2
            mostly_bold = bold_len / total > 0.8
            if not (big or mostly_bold):
                continue
            if _PAT_NUM.match(t) or _PAT_NUM_TITLE.match(t) or _PAT_NAMED.match(t):
                hits.append((pno, pno - offset, t))
                found = True
        if not found:
            # 兜底：纯文本正则（收紧版），并排除表格里的纯数值行
            raw_lines = [s.strip() for s in page.get_text("text").split("\n") if s.strip()]
            for i, s in enumerate(raw_lines):
                if not s or len(s) > 90:
                    continue
                prev = raw_lines[i - 1] if i > 0 else ""
                nxt = raw_lines[i + 1] if i + 1 < len(raw_lines) else ""
                if _is_table_number(s, prev, nxt):
                    continue
                if _PAT_NUM.match(s) or _PAT_NUM_TITLE.match(s):
                    hits.append((pno, pno - offset, s))
                elif _PAT_NAMED.match(s) and len(s) <= 40 and ". " not in s:
                    hits.append((pno, pno - offset, s))
    return hits


def dump_vectors(page, path):
    lines = []
    lines.append("page.rect = %s" % page.rect)
    # 1) text words
    lines.append("\n=== WORDS ===")
    for w in page.get_text("words"):
        lines.append("%8.2f %8.2f %8.2f %8.2f  %r" % (w[0], w[1], w[2], w[3], w[4]))
    # 2) drawings
    lines.append("\n=== DRAWINGS (type, width, dashes, rect, item kinds) ===")
    try:
        dr = page.get_drawings()
    except Exception as exc:
        dr = []
        lines.append("get_drawings failed: %s" % exc)
    for d in dr:
        r = d.get("rect")
        kinds = "".join(sorted({i[0] for i in d.get("items", [])}))
        lines.append("type=%-3s w=%-7.3f dash=%-10s items=%-6s rect=[%.2f %.2f %.2f %.2f]" % (
            d.get("type"), d.get("width", -1), str(d.get("dashes")), kinds,
            r.x0, r.y0, r.x1, r.y1))
    lines.append("n_drawings=%d" % len(dr))
    # 3) bboxlog type histogram（判断点标记是否为位图）
    lines.append("\n=== BBOXLOG TYPE COUNTS ===")
    try:
        from collections import Counter
        c = Counter(it[0] for it in page.get_bboxlog())
        lines.append(str(dict(c)))
        lines.append("提示：若 fill-imgmask 数量很大，说明散点被渲染成小位图，"
                     "get_drawings() 拿不到，不能逐点计数，应改为按实验设计推断。")
    except Exception as exc:
        lines.append("bboxlog failed: %s" % exc)
    open(path, "w", encoding="utf-8").write("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description="组会文献汇报取证工具")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True, help="PDF 页码，如 491-492 或 491,492")
    ap.add_argument("--book-offset", type=int, default=0,
                    help="书内页 = PDF 页 - 该值（例：PDF491=书476 则填 15）")
    ap.add_argument("--out", default="work")
    ap.add_argument("--context", type=int, default=6, help="上下各多抽几页正文用于写章节地图")
    ap.add_argument("--dpi", type=int, default=430, help="裁剪图渲染 dpi")
    ap.add_argument("--crop", action="append", default=[],
                    help='裁剪图，格式 "PDF页:x0,y0,x1,y1:文件名"（pt 坐标），可重复')
    ap.add_argument("--no-vectors", action="store_true", help="跳过矢量坐标导出")
    args = ap.parse_args()

    if not os.path.exists(args.pdf):
        sys.exit("找不到 PDF：%s" % args.pdf)

    target = parse_pages(args.pages)
    allp = sorted(set(target + [p + d for p in target
                                for d in range(-args.context, args.context + 1)]))
    allp = [p for p in allp if 1 <= p <= 10 ** 9]

    doc = fitz.open(args.pdf)
    d_text = os.path.join(args.out, "text")
    d_page = os.path.join(args.out, "pages")
    d_fig = os.path.join(args.out, "figures")
    d_vec = os.path.join(args.out, "vectors")
    for d in (d_text, d_page, d_fig, d_vec):
        os.makedirs(d, exist_ok=True)

    rep = []
    rep.append("pdf            = %s" % args.pdf)
    rep.append("总页数          = %d" % doc.page_count)
    rep.append("目标 PDF 页     = %s" % target)
    rep.append("目标 书内页     = %s" % [p - args.book_offset for p in target])
    rep.append("")

    rep.append("=== 逐页正文抽取 ===")
    for pno in allp:
        if pno < 1 or pno > doc.page_count:
            continue
        page = doc[pno - 1]
        raw = page.get_text("text")
        txt = dehyphenate(raw)
        open(os.path.join(d_text, "page_%d.txt" % pno), "w", encoding="utf-8").write(txt)
        n_img = len(page.get_images(full=True))
        flag = ""
        if len(raw.strip()) == 0:
            flag = "  <<< 无文字层：可能是扫描页，需人工转写并在待确认项登记"
        rep.append("pdf %-4d (书 %-4d)  chars=%-6d images=%d%s" % (
            pno, pno - args.book_offset, len(txt), n_img, flag))

    rep.append("")
    rep.append("=== 整页渲染（dpi=200，供人工定位裁剪框）===")
    for pno in target:
        page = doc[pno - 1]
        pix = page.get_pixmap(dpi=200)
        fn = os.path.join(d_page, "page_%d.png" % pno)
        pix.save(fn)
        rep.append("%s  %dx%d  rect=%s" % (fn, pix.width, pix.height, page.rect))

    if args.crop:
        rep.append("")
        rep.append("=== 图表裁剪（dpi=%d）===" % args.dpi)
        for spec in args.crop:
            try:
                pg, rect, name = spec.split(":", 2)
                x0, y0, x1, y1 = [float(v) for v in rect.split(",")]
                if not name.lower().endswith(".png"):
                    name += ".png"
                pix = doc[int(pg) - 1].get_pixmap(dpi=args.dpi, clip=fitz.Rect(x0, y0, x1, y1))
                fn = os.path.join(d_fig, name)
                pix.save(fn)
                rep.append("%s  %dx%d" % (fn, pix.width, pix.height))
            except Exception as exc:
                rep.append("!! 裁剪失败 %r : %s" % (spec, exc))

    if not args.no_vectors:
        rep.append("")
        rep.append("=== 矢量坐标导出（用于反算坐标轴与读数）===")
        for pno in target:
            fn = os.path.join(d_vec, "page_%d.txt" % pno)
            dump_vectors(doc[pno - 1], fn)
            rep.append(fn)

    rep.append("")
    rep.append("=== 章节地图（本页 ± %d 页内的小节标题）===" % args.context)
    for pno, bno, s in section_map(doc, allp, args.book_offset):
        rep.append("pdf %-4d (书 %-4d)  %s" % (pno, bno, s))

    rep.append("")
    rep.append("=== 下一步提示 ===")
    rep.append("1) 用 Read 打开 pages/*.png 目测图表位置，再微调 --crop 参数重跑，得到紧凑高清图。")
    rep.append("2) 用 Read 打开每张 figures/*.png 人工读出坐标轴刻度值（刻度标签常在文本层之外）。")
    rep.append("3) 在 vectors/page_*.txt 里找刻度短线与数据元素，建立坐标映射并做交叉验证"
               "（详见 references/pdf-evidence-extraction.md）。")
    rep.append("4) 立刻检查上面的 chars=0 提示：有扫描页要写进第二轮审查的待确认项。")

    txt = "\n".join(rep)
    outp = os.path.join(args.out, "summary.txt")
    open(outp, "w", encoding="utf-8").write(txt)
    print(txt)
    print("\n[OK] 汇总已写入 %s" % outp)


if __name__ == "__main__":
    main()

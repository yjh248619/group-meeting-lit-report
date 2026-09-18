#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
compile_pdf.py —— LaTeX 编译与自愈工具（阶段二）

优先用 latexmk（自动多轮编译，目录/交叉引用一次到位）；没有 latexmk 时退回直接调用
xelatex 两遍。编译日志会被解析成一张精简的错误清单，便于 Agent 定位到行号后自动修错重编。

用法示例：
  python compile_pdf.py --tex report/478-479-汇报.tex --outdir report/build
  python compile_pdf.py --tex 478-479-学习.tex --engine xelatex --clean-first

退出码：0 = 编译成功且未发现致命错误；1 = 失败（错误清单见 <outdir>/errors.txt）

配合 references/latex-cookbook.md 使用。
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys

FATAL_PATTERNS = [
    (re.compile(r"^!\s*(.*)$"), "LaTeX 错误"),
    (re.compile(r"^l\.(\d+)\s*(.*)$"), "出错行"),
    (re.compile(r"File `([^']+)' not found"), "缺少文件/宏包"),
    (re.compile(r"! LaTeX Error: File `([^']+)' not found"), "缺少宏包"),
    (re.compile(r"Emergency stop"), "紧急停止"),
    (re.compile(r"Runaway argument"), "参数未闭合"),
    (re.compile(r"Undefined control sequence"), "未定义命令"),
    (re.compile(r"Missing \\$ inserted"), "数学模式未闭合"),
    (re.compile(r"Extra alignment tab"), "表格列数不匹配"),
    (re.compile(r"Missing number, treated as zero"), "长度/数字参数缺失"),
    (re.compile(r"Font .* not found"), "字体未找到"),
    (re.compile(r"Overfull \\hbox \((\d+\.\d+)pt too wide\)"), "内容超宽（警告）"),
]

WARN_HINTS = [
    (re.compile(r"Package hyperref Warning"), "hyperref 警告"),
    (re.compile(r"There were undefined references"), "存在未解析引用（目录/交叉引用）"),
    (re.compile(r"Citation .* undefined"), "引用未定义"),
]


def find_exe(name):
    p = shutil.which(name)
    if p:
        return p
    # 常见安装位置兜底
    for cand in (
        r"D:\TEXlive\texlive\2026\bin\windows\%s.exe" % name,
        r"C:\texlive\2026\bin\windows\%s.exe" % name,
        os.path.expanduser(r"~\AppData\Local\Programs\MiKTeX\miktex\bin\x64\%s.exe" % name),
    ):
        if os.path.exists(cand):
            return cand
    return None


def run(cmd, cwd, log_fh):
    log_fh.write("\n$ " + " ".join(cmd) + "\n")
    log_fh.flush()
    env = dict(os.environ)
    env["LC_ALL"] = "C"          # 抑制 perl 的 locale 警告
    env["LANG"] = "C"
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       env=env, text=True, encoding="utf-8", errors="replace")
    log_fh.write(p.stdout or "")
    log_fh.flush()
    return p.returncode, (p.stdout or "")


def parse_errors(text):
    found = []
    for raw in text.split("\n"):
        line = raw.rstrip()
        for pat, label in FATAL_PATTERNS:
            m = pat.search(line)
            if m:
                found.append("%-16s | %s" % (label, line.strip()[:180]))
                break
    seen, uniq = set(), []
    for f in found:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


def parse_warnings(text):
    out = []
    for raw in text.split("\n"):
        for pat, label in WARN_HINTS:
            if pat.search(raw):
                out.append("%-24s | %s" % (label, raw.strip()[:160]))
                break
    seen, uniq = set(), []
    for f in out:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


def main():
    ap = argparse.ArgumentParser(description="LaTeX 编译与错误摘要")
    ap.add_argument("--tex", required=True, help="主 .tex 文件路径")
    ap.add_argument("--outdir", default="build")
    ap.add_argument("--engine", default="xelatex",
                    choices=["xelatex", "pdflatex", "lualatex"],
                    help="中文必须用 xelatex（默认）")
    ap.add_argument("--clean-first", action="store_true", help="编译前清理中间文件")
    ap.add_argument("--max-rounds", type=int, default=2,
                    help="没有 latexmk 时直接调引擎的轮数（默认 2，处理目录/引用）")
    args = ap.parse_args()

    tex = os.path.abspath(args.tex)
    if not os.path.exists(tex):
        print("[FATAL] 找不到 .tex：%s" % tex)
        return 1
    texdir = os.path.dirname(tex)
    basename = os.path.splitext(os.path.basename(tex))[0]
    outdir = os.path.abspath(os.path.join(texdir, args.outdir)) \
        if not os.path.isabs(args.outdir) else args.outdir
    os.makedirs(outdir, exist_ok=True)

    logpath = os.path.join(outdir, "compile.log")
    errpath = os.path.join(outdir, "errors.txt")

    engine_exe = find_exe(args.engine)
    latexmk_exe = find_exe("latexmk")
    if engine_exe is None:
        msg = ("[FATAL] 找不到 %s。\n"
               "请先向用户说明并请求授权后安装 TeX Live：\n"
               "  winget install --id TeXLive.TeXLive   （或 choco install texlive）\n"
               "装完需重开终端，并重新验证 where xelatex / kpsewhich ctex.sty" % args.engine)
        print(msg)
        open(errpath, "w", encoding="utf-8").write(msg)
        return 1

    allout = []
    with open(logpath, "w", encoding="utf-8") as fh:
        if args.clean_first:
            if latexmk_exe:
                run([latexmk_exe, "-C", "-outdir=" + outdir, basename + ".tex"], texdir, fh)
            else:
                for ext in (".aux", ".log", ".toc", ".out", ".pdf"):
                    p = os.path.join(outdir, basename + ext)
                    if os.path.exists(p):
                        os.remove(p)

        if latexmk_exe:
            cmd = [latexmk_exe, "-" + args.engine, "-interaction=nonstopmode",
                   "-halt-on-error", "-file-line-error",
                   "-outdir=" + outdir, basename + ".tex"]
            rc, out = run(cmd, texdir, fh)
            allout.append(out)
            mode = "latexmk -" + args.engine
        else:
            mode = "%s ×%d（未找到 latexmk）" % (args.engine, args.max_rounds)
            for _ in range(max(1, args.max_rounds)):
                cmd = [engine_exe, "-interaction=nonstopmode", "-halt-on-error",
                       "-file-line-error", "-output-directory=" + outdir,
                       basename + ".tex"]
                rc, out = run(cmd, texdir, fh)
                allout.append(out)

    joined = "\n".join(allout)
    errs = parse_errors(joined)
    warns = parse_warnings(joined)

    pdf = os.path.join(outdir, basename + ".pdf")
    pdf_ok = os.path.exists(pdf) and os.path.getsize(pdf) > 1000

    rep = []
    rep.append("=" * 72)
    rep.append("编译方式 : %s" % mode)
    rep.append("引擎      : %s" % engine_exe)
    rep.append("latexmk   : %s" % (latexmk_exe or "未安装（已退回直接调用引擎）"))
    rep.append("日志      : %s" % logpath)
    rep.append("PDF       : %s  (%s)" % (pdf, ("%.1f KB" % (os.path.getsize(pdf) / 1024)) if pdf_ok else "未生成"))

    if pdf_ok:
        try:
            import pymupdf as fitz
            d = fitz.open(pdf)
            rep.append("页数      : %d" % d.page_count)
            d.close()
        except Exception:
            pass

    rep.append("-" * 72)
    if errs:
        rep.append("错误清单（%d 条，按出现顺序）：" % len(errs))
        rep.extend(errs)
    else:
        rep.append("错误清单 : 无致命错误")
    if warns:
        rep.append("-" * 72)
        rep.append("警告（%d 条，通常不阻断，但请检查）：" % len(warns))
        rep.extend(warns[:20])

    rep.append("-" * 72)
    if pdf_ok and not any("LaTeX 错误" in e or "紧急停止" in e for e in errs):
        rep.append("结果      : 成功")
        rep.append("下一步    : 交付 PDF 并同时附上 .tex 与 figures/ 目录"
                   "（WorkBuddy 用 present_files；其它 Agent 直接给出文件路径）")
        rc_out = 0
    else:
        rep.append("结果      : 失败")
        rep.append("下一步    : 按上面的行号修改 .tex 后重跑本脚本；常见对策见 references/phase2-export.md")
        rc_out = 1

    text = "\n".join(rep)
    open(errpath, "w", encoding="utf-8").write(text)
    print(text)
    print("\n[摘要已写入 %s]" % errpath)
    return rc_out


if __name__ == "__main__":
    sys.exit(main())

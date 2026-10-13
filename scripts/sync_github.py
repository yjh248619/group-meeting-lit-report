#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""sync_github.py —— 把技能目录同步到 GitHub（git commit + push）。

设计目标（对齐本技能的"规则要能校验、改动要留痕"）：
  · 一条命令完成 commit + push，提交信息自动带上版本号与变更摘要
  · token 只从**文件**读，绝不进命令行（带 token 的命令行会触发安全弹窗）
  · 推前先 `git fetch` 看远端有没有别人推的东西，避免非快进覆盖
  · 只同步技能内容；`.workbuddy-ai/`（记忆/备份）由 `.gitignore` 挡在库外
  · `--dry-run` 只显示"会提交什么"，不动任何东西

用法：
    python scripts/sync_github.py                  # 提交并推送
    python scripts/sync_github.py --dry-run        # 只看变更
    python scripts/sync_github.py -m "自定义信息"   # 覆盖自动提交信息
    python scripts/sync_github.py --check          # 检查远端是否落后于本地

依赖：git（本机 2.55）、token 文件（见 TOKEN_FILES）。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import pathlib
import re
import subprocess
import sys

# 技能目录 = 本脚本的上上级
ROOT = pathlib.Path(__file__).resolve().parents[1]
REMOTE = "origin"
BRANCH = "main"

# token 文件候选路径（按顺序找第一个存在的；都不存在则回落到 git 凭据助手）
TOKEN_FILES = [
    pathlib.Path(r"C:\Users\yan\WorkBuddy\2026-09-14-15-14-18\_work\gh_token.txt"),
    pathlib.Path.home() / ".workbuddy-ai" / "gh_token.txt",
]

SKILL_MD = ROOT / "SKILL.md"


def run(cmd, check=True, capture=True):
    return subprocess.run(cmd, cwd=str(ROOT), check=check,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.STDOUT if capture else None,
                          text=True, encoding="utf-8", errors="replace")


def git(*args, check=True):
    return run(["git", *args], check=check)


def die(msg, code=1):
    print("[X] " + msg)
    sys.exit(code)


def read_token() -> str:
    for p in TOKEN_FILES:
        try:
            if p.is_file():
                t = p.read_text(encoding="utf-8").strip()
                if t:
                    return t
        except OSError:
            continue
    return ""


def skill_version() -> str:
    try:
        m = re.search(r"^version:\s*(\S+)", SKILL_MD.read_text(encoding="utf-8"), re.M)
        return m.group(1) if m else "?"
    except OSError:
        return "?"


def changed_files() -> list[str]:
    """已跟踪文件的改动（含未暂存）+ 未跟踪文件。不含被 .gitignore 挡掉的。"""
    out = git("status", "--porcelain").stdout or ""
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:                    # 重命名：取新名
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files


def diff_summary(files: list[str]) -> str:
    """按目录归类，生成一行能看懂的摘要。"""
    buckets = {}
    for f in files:
        top = f.split("/")[0] if "/" in f else "(根目录)"
        buckets.setdefault(top, []).append(f)
    parts = []
    for top in sorted(buckets, key=lambda k: (k != "SKILL.md", k)):
        n = len(buckets[top])
        parts.append("%s×%d" % (top, n) if n > 1 else top)
    return "、".join(parts)


def auto_message(files: list[str]) -> str:
    ver = skill_version()
    today = _dt.date.today().isoformat()
    head = "v%s：同步 %s" % (ver, diff_summary(files)) if files else "v%s：同步" % ver
    body = "\n".join("- %s" % f for f in sorted(files)[:40])
    if len(files) > 40:
        body += "\n- …（共 %d 个文件）" % len(files)
    return "%s\n\n%s\n\n同步日期：%s" % (head, body, today)


def ensure_repo(remote_url: str):
    """首次使用时把技能目录初始化成 git 仓库并接上远端。"""
    if not (ROOT / ".git").is_dir():
        print("1) 首次初始化 git 仓库")
        git("init", "-b", BRANCH)
        print("   OK  git init -b %s" % BRANCH)
    else:
        print("1) git 仓库已存在")

    remotes = git("remote", check=False).stdout or ""
    if REMOTE not in remotes.split():
        git("remote", "add", REMOTE, remote_url)
        print("   OK  已接上远端 %s" % REMOTE)
    else:
        git("remote", "set-url", REMOTE, remote_url)
        print("   OK  远端地址已更新")


def remote_url_with_token(token: str, owner: str, repo: str) -> str:
    return "https://%s@github.com/%s/%s.git" % (token, owner, repo)


def main():
    ap = argparse.ArgumentParser(description="技能目录 -> GitHub 同步")
    ap.add_argument("--owner", default="yjh248619")
    ap.add_argument("--repo", default="group-meeting-lit-report")
    ap.add_argument("-m", "--message", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true", help="只报告本地与远端的差异")
    ap.add_argument("--no-push", action="store_true", help="只提交，不推送")
    args = ap.parse_args()

    token = read_token()
    if not args.dry_run and not token:
        die("读不到 token。请把 PAT 单独一行写进：\n    %s"
            % "\n    ".join(str(p) for p in TOKEN_FILES))

    files = changed_files()
    print("=" * 68)
    print("技能目录  %s" % ROOT)
    print("版本      v%s" % skill_version())
    print("待同步    %d 个文件" % len(files))
    if files:
        for f in files[:60]:
            print("   · %s" % f)
        if len(files) > 60:
            print("   · …（共 %d 个）" % len(files))
    print("-" * 68)

    if args.dry_run:
        print("[dry-run] 只显示变更，未写入任何东西。")
        if files:
            print("将使用的提交信息：")
            print(auto_message(files))
        return 0

    ensure_repo(remote_url_with_token(token, args.owner, args.repo))

    # 拉远端状态，避免非快进覆盖
    print("2) 读取远端状态")
    git("fetch", REMOTE, BRANCH, check=False)
    local = git("rev-parse", BRANCH, check=False).stdout.strip()
    remote = git("rev-parse", "%s/%s" % (REMOTE, BRANCH), check=False).stdout.strip()
    if not remote:
        print("   远端还没有 %s 分支 → 首次推送" % BRANCH)
    elif remote == local:
        print("   已与远端一致（%s）" % local[:12])
    else:
        ahead = git("rev-list", "--count", "%s..%s" % (remote, local), check=False).stdout.strip()
        behind = git("rev-list", "--count", "%s..%s" % (local, remote), check=False).stdout.strip()
        print("   本地领先 %s / 落后 %s" % (ahead or "?", behind or "?"))
        if behind and behind != "0":
            die("远端有本地没有的提交（落后 %s 个）。先 `git pull` 再同步，"
                "不要强推覆盖别人的东西。" % behind)

    if args.check:
        print("=" * 68)
        print("检查完毕：待同步 %d 个文件。" % len(files))
        return 0

    if not files:
        print("3) 没有需要提交的改动，已是最新。")
        if not args.no_push:
            git("push", REMOTE, BRANCH, check=False)
        return 0

    print("3) 暂存并提交")
    git("add", "-A")
    msg = args.message or auto_message(files)
    git("commit", "-m", msg)
    new = git("rev-parse", "HEAD").stdout.strip()
    print("   OK  commit = %s" % new[:12])

    if args.no_push:
        print("4) --no-push：已提交未推送。")
        return 0

    print("4) 推送")
    r = git("push", REMOTE, BRANCH, check=False)
    out = r.stdout or ""
    if r.returncode != 0:
        # 凭证可能被回显，打码后再报错
        print(out.replace(token, "***") if token else out)
        die("推送失败。若提示认证问题，检查 token 是否有 repo 写权限、是否过期。")
    print("   OK  %s" % out.strip().splitlines()[-1] if out.strip() else "   OK")
    print("=" * 68)
    print("仓库地址：https://github.com/%s/%s" % (args.owner, args.repo))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env bash
# 打印最新一章全文，给私人助手转发到手机
BOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
f="$(ls "$BOOK"/正文/第*章*.txt 2>/dev/null | sort | tail -1)"
[ -n "$f" ] || { echo "还没有章节" >&2; exit 1; }
echo "【$(basename "$f" .txt)】"; echo; cat "$f"

#!/usr/bin/env bash
# Batch mode: "continue" chapter after chapter; stop after N chapters or on a problem.
# Usage: bin/auto.sh 12                    write 12 chapters
#        bin/auto.sh 12 'one overall hint' add this hint to every chapter's instruction
# Each chapter goes through bin/novel-call.sh as usual (bookkeeping, write, screen, commit).
# A chapter that fails checks was already fixed once inside novel-call.sh; if it still
# fails, it is rewritten once; if that fails too, stop and wait for the reader.
# Every EVERY chapters (default 3): rebuild 全书.txt, push, and run NOTIFY "<message>" if set.
#   e.g. NOTIFY='your-send-message-command' bin/auto.sh 19
# Exit codes: 0 done; 1 model call failed; 2 still failing after rewrite; 3 environment or
# memory wrong; 64 usage.
#
# 連寫：一章一章地「繼續」，寫滿 N 章或出問題就停
# 用法：bin/auto.sh 12            連寫 12 章
#       bin/auto.sh 12 '一句總方向'  每章的指令都帶上這句（例如「這一卷是零的過去」）
# 每章照常走 bin/novel-call.sh：記賬、寫、粗篩、提交推送
# 某章沒過檢查：novel-call.sh 裡已經修過一次；還不過就整章重寫一次，再不過就停下等讀者
# 每寫完 EVERY 章（預設 3）合一次 全书.txt 並推上去；設了 NOTIFY 就再跑它，把一句通知當參數傳進去
#   例：NOTIFY='你的發消息命令' bin/auto.sh 19
# 退出碼：0 寫完；1 模型調用失敗；2 重寫後仍沒過檢查；3 環境或記憶不對；64 用法錯

set -uo pipefail
BOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BOOK" || exit 1
# The batch git-pulls between chapters to pick up fixed rules; run from a copy of this script so the pull can't change the file while bash is executing it.
# 連寫中途會 git pull 拿 Claude 修好的規則；先把自己複製一份再跑，免得 pull 改到正在執行的這個腳本
if [ -z "${AUTO_COPY:-}" ]; then
  mkdir -p logs && cp "$0" logs/.auto-run.sh && AUTO_COPY=1 exec bash logs/.auto-run.sh "$@"
fi
N="${1:-}"; HINT="${2:-}"; EVERY="${EVERY:-3}"
case "$N" in ''|*[!0-9]*) echo "usage: $0 章數 ['總方向']" >&2; exit 64 ;; esac

latest() { ls 正文/第*章*.txt 2>/dev/null | sed -nE 's/.*第0*([0-9]+)章.*/\1/p' | sort -n | tail -1; }
start="$(latest)"; start="${start:-0}"
done_n=0
# Every EVERY chapters: rebuild the book, push, notify (a failed notification doesn't stop the batch).
# 每 EVERY 章：重新合本、推上去、發通知（通知失敗不影響連寫）
batch() {
  done_n=$((done_n+1))
  [ $((done_n % EVERY)) -eq 0 ] || return 0
  python3 tools/build_book.py >/dev/null 2>&1
  if [ -z "${NOPUSH:-}" ] && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    who=(); git config user.email >/dev/null || who=(-c user.name=cc -c user.email=cc@local)
    git add 全书.txt && git ${who[@]+"${who[@]}"} commit -q -m "全书合本（到第 $(latest) 章）" && git push -q 2>&1 || true
  fi
  msg="子航線：又寫好 ${EVERY} 章，已到第 $(latest) 章（第 $((start+1))–$(latest) 章），全书.txt 已更新"
  echo "$msg"
  [ -n "${NOTIFY:-}" ] && { $NOTIFY "$msg" || echo "通知沒發出去" >&2; }
  return 0
}
echo "從第 $((start+1)) 章連寫 $N 章；中途想停就 Ctrl+C，已寫完的章都已提交"

for i in $(seq 1 "$N"); do
  ch=$(( $(latest) + 1 ))
  echo; echo "=== 第 $ch 章（$i/$N）$(date +%H:%M)"
  # Pull the latest rules and checks before each chapter; if the pull fails, carry on with the old ones.
  # 每章開寫前拿一次最新的規則和檢查（Claude 可能剛修過）；拉不下來就照舊寫
  [ -z "${NOPUSH:-}" ] && git pull -q --rebase 2>/dev/null || true
  bin/novel-call.sh "繼續${HINT:+ $HINT}"; rc=$?
  if [ "$rc" -eq 0 ]; then batch; continue; fi
  if [ "$rc" -eq 2 ]; then
    fails="$(grep -h '^FAIL' "章节/第$(printf %03d "$ch")章/检查.txt" 2>/dev/null | head -3 | tr '\n' ' ')"
    echo "第 $ch 章沒過檢查，自動重寫一次：$fails"
    if [ "$(latest)" -ge "$ch" ]; then
      bin/novel-call.sh "重寫第${ch}章 上一稿沒過檢查，這次避開：${fails}${HINT:+ $HINT}"; rc=$?
    else  # no prose was written: just try again. 正文沒寫出來：重來一次
      bin/novel-call.sh "繼續${HINT:+ $HINT}"; rc=$?
    fi
    if [ "$rc" -eq 0 ]; then batch; continue; fi
  fi
  echo "第 $ch 章停下（退出碼 $rc），已寫到第 $(latest) 章；看上面的提示再決定" >&2
  exit "$rc"
done
echo; echo "連寫完成：第 $((start+1))–$(latest) 章"
[ -n "${NOTIFY:-}" ] && { $NOTIFY "子航線：連寫完成，第 $((start+1))–$(latest) 章" || true; }

#!/usr/bin/env bash
# 寫一章（第一版的寫法）：記賬 → 寫手照走向直接寫 → 粗篩 → 提交
# 用法：bin/novel-call.sh '繼續'
#       bin/novel-call.sh '一段走向'
#       bin/novel-call.sh '重寫第N章 要求'
#       bin/novel-call.sh --續跑 [N]    上次斷在中間：只補跑後面的步驟（越界還原、粗篩、修稿、焦點、提交）
#       bin/novel-call.sh 全書 | 唠唠… | 改設定… | 停下
#       bin/novel-call.sh --doctor      只檢查環境，不調模型（也會報出沒跑完的章）
# 每章調一次模型（寫加記賬）；只有硬傷沒過才多調一次修稿
# 進行中標記：開寫一章時在 章节/第NNN章/进行中 記下階段，流程跑完（含提交）才刪；
#   進程被殺（重啟、斷線）時標記還在，下次調用會停下，不會把沒跑完的章當成已完成去寫下一章
# 退出碼：0 正常；1 模型調用失敗；2 沒過檢查；3 環境或記憶不對、上一章沒跑完；64 用法錯；75 另一次還在跑

set -uo pipefail

BOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL="${MODEL:-gemini-3.8-flash-low}"
AGY="${AGY:-agy}"
LIMIT_PLAN="${LIMIT_PLAN:-600}"
LIMIT_WRITE="${LIMIT:-2400}"
LIMIT_FIX="${LIMIT_FIX:-900}"
PY="$(command -v python3 || command -v python || true)"
# Mac 和遠端 VM 都要能跑：macOS 自帶 bash 3.2，沒有 timeout、flock，base64 參數也不一樣
if command -v timeout >/dev/null; then TIMEOUT=(timeout)
elif command -v gtimeout >/dev/null; then TIMEOUT=(gtimeout)
else TIMEOUT=("$PY" "$BOOK/tools/timeout.py"); fi
b64e() { "$PY" -c 'import base64,sys; print(base64.b64encode(sys.stdin.buffer.read()).decode())'; }
b64d() { "$PY" -c 'import base64,sys; sys.stdout.write(base64.b64decode(sys.stdin.read().strip() or b"").decode("utf-8","replace"))' 2>/dev/null; }

cd "$BOOK" || exit 1

doctor() {
  local ok=0
  for f in AGENTS.md 作者意图.md 路标.md 设定/规则.md 设定/设定.md 设定/子航.md 设定/封存.md \
           记忆/进度.md 记忆/伏笔.md 记忆/当前焦点.md 文风/卡片.md 文风/段落库.md \
           tools/compose.py tools/outline.py tools/check.py tools/merge_update.py tools/guard.py; do
    [ -f "$f" ] || { echo "缺文件：$f"; ok=3; }
  done
  [ -d 正文 ] || { echo "缺目錄：正文"; ok=3; }
  [ -n "$PY" ] && echo "python：$PY" || { echo "沒有 python3"; ok=3; }
  command -v "$AGY" >/dev/null && echo "agy：$(command -v "$AGY")" || { echo "找不到 $AGY（可用 AGY=路徑 指定）"; ok=3; }
  echo "限時：${TIMEOUT[*]}"
  echo "系統：$(uname -s)，bash $BASH_VERSION"
  echo "模型：$MODEL"
  [ -f 记忆/待更新.md ] && echo "注意：有 记忆/待更新.md，下次寫作會先把它併進記憶"
  [ $ok -eq 0 ] && echo "環境 OK"
  return $ok
}

# ── 進行中標記 ──────────────────────────────────────────
# 標記文件在 章节/第NNN章/进行中，一行一項「鍵=值」；不進 git（提交時排除）
pending_n() {  # 印出有標記的最大章號；沒有就什麼都不印
  local f n best=""
  for f in 章节/第*章/进行中; do
    [ -f "$f" ] || continue
    n="$(printf '%s' "$f" | sed -nE 's#.*第0*([0-9]+)章/进行中#\1#p')"
    [ -n "$n" ] || continue
    if [ -z "$best" ] || [ "$n" -gt "$best" ]; then best="$n"; fi
  done
  printf '%s' "$best"
}
mark_path() { printf '章节/第%03d章/进行中' "$1"; }
mval() { sed -n "s/^$2=//p" "$(mark_path "$1")" 2>/dev/null | head -1; }
latest() { "$PY" -c 'import sys; sys.path.insert(0,"tools"); import book; print(book.latest())'; }
chapter_file() { ls "$BOOK"/正文/第"$(printf %03d "$1")"章_*.txt 2>/dev/null | head -1; }  # 寫手自己定章名，按章號找

if [ "${1:-}" = "--doctor" ]; then
  doctor; rc=$?
  pn="$(pending_n)"
  if [ -n "$pn" ]; then
    echo "進行中：第 $pn 章上次沒跑完（停在「$(mval "$pn" 階段)」，開始於 $(mval "$pn" 開始)）"
    f="$(chapter_file "$pn")"
    if [ -f "$f" ]; then echo "  正文已經在，可以用：bin/novel-call.sh --續跑 $pn"
    else echo "  還沒有正文，用：bin/novel-call.sh '重寫第${pn}章'"; fi
    rc=3
  fi
  exit $rc
fi
[ $# -ge 1 ] || { echo "usage: $0 '指令' | --續跑 [N] | --doctor" >&2; exit 64; }
case "$1" in 全書|全书) exec "$PY" tools/build_book.py ;; esac
doctor >/dev/null || { doctor; exit 3; }

exec 9>"$BOOK/.novel.lock"
if command -v flock >/dev/null; then
  flock -n 9 || { echo "另一次調用還在寫，等它結束" >&2; exit 75; }
else
  # macOS 沒有 flock：用目錄當鎖，裡面記 pid；進程已經不在了就當舊鎖清掉
  LOCKDIR="$BOOK/.novel.lock.d"
  if ! mkdir "$LOCKDIR" 2>/dev/null; then
    old="$(cat "$LOCKDIR/pid" 2>/dev/null)"
    if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
      echo "另一次調用還在寫，等它結束" >&2; exit 75
    fi
    rm -rf "$LOCKDIR"; mkdir "$LOCKDIR" 2>/dev/null || { echo "拿不到鎖：$LOCKDIR" >&2; exit 75; }
  fi
  echo $$ >"$LOCKDIR/pid"
  trap 'rm -rf "$LOCKDIR"' EXIT
fi

mkdir -p logs
LOG="logs/$(date +%Y%m%d-%H%M%S).log"

# 調一次模型：限時、輸出同時進日誌
call() {
  local limit="$1" prompt="$2"
  echo "---- $(date +%H:%M:%S) 調模型（限 ${limit} 秒）" >>"$LOG"
  "${TIMEOUT[@]}" "$limit" "$AGY" --dangerously-skip-permissions --model "$MODEL" --add-dir "$BOOK" \
    -p "$prompt" 2>&1 | tee -a "$LOG"
  local rc=${PIPESTATUS[0]}
  [ "$rc" -eq 124 ] && echo "超時（${limit} 秒）被中斷" >&2
  return "$rc"
}

# 提交並推送。標記文件不提交；SAFE_ADD 有值時只提交這些路徑（續跑時守衛底稿不可信用）
commit() {
  [ -n "${NOPUSH:-}" ] && return 0
  git -C "$BOOK" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
  if [ -n "${SAFE_ADD:-}" ]; then
    # shellcheck disable=SC2086
    git -C "$BOOK" add -A -- $SAFE_ADD ':(exclude,glob)**/进行中' 2>/dev/null
  else
    git -C "$BOOK" add -A -- . ':(exclude,glob)**/进行中' 2>/dev/null
  fi
  git -C "$BOOK" diff --cached --quiet 2>/dev/null && return 0
  # VM 上沒設 git 身份時用預設的（cc），不然提交直接失敗、章節推不上去
  local who=(); git -C "$BOOK" config user.email >/dev/null || who=(-c user.name=cc -c user.email=cc@local)
  if git -C "$BOOK" ${who[@]+"${who[@]}"} commit -q -m "$1"; then
    git -C "$BOOK" push -q 2>&1 || echo "推送失敗，下次再推" >&2
  else
    echo "提交失敗，改動還在本地，沒推上去" >&2
  fi
}

# 寫標記：mark 階段。開始時間只在第一次寫
mark() {
  MARK_START="${MARK_START:-$(date '+%F %T')}"
  {
    echo "章號=$N"
    echo "階段=$1"
    echo "開始=$MARK_START"
    echo "更新=$(date '+%F %T')"
    echo "開關=${FLAGS[*]:-}"
    echo "檢查=${CHECK[*]:-}"
    echo "指令=$(printf '%s' "$INSTR" | b64e)"
  } >"$MARK"
}
# 流程在這裡正常結束（成功、沒過檢查、模型失敗都算，下次重跑就行）：刪標記再退出
end() { [ -n "${MARK:-}" ] && rm -f "$MARK"; exit "$1"; }

# 越界守衛：每次調模型前存底，調完還原。meta 記下這份底是哪一章、哪一步前存的，續跑時靠它確認底稿可信
guard_save() { "$PY" tools/guard.py save && printf '%s %s\n' "$N" "$1" >logs/.guard.meta; }
guard_restore() { "$PY" tools/guard.py restore "$N" "$@" | tee -a "$LOG"; }
guard_trusted() {
  case "$(cat logs/.guard.meta 2>/dev/null)" in
    "$N write"|"$N fix") [ -f logs/.guard/.tops ] ;;
    *) return 1 ;;
  esac
}

# 人設提醒放在寫手提示最前面：模型看到「子航」會自動套成楚子航，光靠文件壓不住
build_remind() {
  REMIND="【你在寫一部長篇小說，文筆參考江南的《龍族》（學他的寫法，不搬原作的人物和情節）。這是第 ${N} 章，不是記流水賬：這章圍繞一件事寫（多半是過日子的事，不是每章都要賭約和比賽），寫出它怎麼起、怎麼變、怎麼收；不要把一天從早到晚過一遍，不要從上課開場（路標點名要的除外）。】【先讀 AGENTS.md，照它列的順序讀材料，寫作規矩只有 设定/规则.md 一份。主角子航是原創人物，不是《龍族》的楚子航：沒有言靈、沒有村雨、不用君焰、不暴血、不開邁巴赫、沒有專屬名刀。他懶、嘴貧、常出糗，不是慫，只是嫌麻煩；口氣照 设定/子航.md，不學上一章末尾。全章 10000 字以上、4 到 5 場有事發生的戲，9000 是底線不是目標。】"
  case " ${FLAGS[*]:-} " in *" --wrap "*) REMIND="$REMIND【讀者要把這段劇情寫完：在戲裡收線，不寫「落下帷幕」式總結；待更新.md 的「最新扣子」寫「- 無（讀者要自己加新劇情）」。】" ;; esac
}

# 粗篩：check.py 加 待更新.md 格式；沒有 待更新.md 也算沒過（寫手沒記賬，下一章會被記憶守衛卡住）
screen() {
  "$PY" tools/check.py ${CHECK[@]+"${CHECK[@]}"} --fed 文风/旁白範本.md "$CH" >"$W/检查.txt"
  if [ -f 记忆/待更新.md ]; then
    "$PY" tools/merge_update.py --check >>"$W/检查.txt"
  else
    echo "FAIL 沒有 记忆/待更新.md，照大綱和正文寫這章的賬" >>"$W/检查.txt"
  fi
  cat "$W/检查.txt"
  ! grep -q '^FAIL' "$W/检查.txt"
}

# 第 4、5 步：粗篩 → 沒過修稿一次 → 過了才動焦點 → 提交。正常流程和 --續跑 共用
finish_chapter() {
  mark 粗篩
  echo "== 檢查 $CH_REL"
  local failed fails
  if ! screen; then
    fails="$(grep '^FAIL' "$W/检查.txt")"
    echo "沒過，修一次" | tee -a "$LOG"
    mark 修稿
    guard_save fix
    call "$LIMIT_FIX" "$REMIND
【修稿】讀 AGENTS.md「修稿」一節。第 ${N} 章 ${CH_REL} 沒過檢查：
${fails}
只改報錯的地方；字數不夠就補一場真正的戲，不拉長已寫的場，補的內容不能和已寫的重複或矛盾（同一件事換個說法再說一遍不算補）。待更新.md 沒有或報錯就對照正文寫、改 记忆/待更新.md。改完再跑一遍檢查。" >/dev/null
    guard_restore "$CH_REL" 记忆/待更新.md
    echo "== 修完再查"
    screen; failed=$?
  else
    failed=0
  fi
  mark 收尾
  commit "$(basename "$CH" .txt)（$SHORT）"
  if [ -n "${SAFE_ADD:-}" ]; then
    left="$(git -c core.quotepath=false status --short 2>/dev/null | grep -v '进行中' | grep -v '^??.*logs/' || true)"
    [ -n "$left" ] && { echo "這些改動沒有提交（可能是越界，請看一眼）：" >&2; echo "$left" >&2; }
  fi
  [ "$failed" -ne 0 ] && { echo "第 $N 章沒過檢查，結果在 ${W}/检查.txt；可發「重寫第${N}章 要求」" >&2; end 2; }
  end 0
}

# --續跑 [N]：對有「進行中」標記的那一章，補跑後面的步驟
resume() {
  local want="${1:-}" pn
  pn="$(pending_n)"
  if [ -z "$pn" ]; then
    if [ -n "$want" ] && [ "$want" = "$(latest)" ] && [ -f "章节/第$(printf %03d "$want")章/设定.md" ]; then
      # 標記功能加進來之前就斷掉的章：按工作區補一個標記，指令和開關已經不知道，檢查不帶 --long/--no-ling/--wrap
      N="$want"; NNN="$(printf %03d "$N")"; W="章节/第${NNN}章"; MARK="$W/进行中"
      FLAGS=(); CHECK=(); INSTR="（補跑，原指令不明）"
      mark 補跑
      echo "第 $N 章沒有進行中標記（可能是舊版腳本斷的），按工作區補了一個"
    else
      echo "沒有「進行中」標記的章，不需要續跑。"
      [ -n "$want" ] && echo "如果第 $want 章是舊版腳本斷的，確認它是最新一章、章节/第$(printf %03d "$want")章/设定.md 在，再跑一次。"
      exit 0
    fi
  else
    if [ -n "$want" ] && [ "$want" != "$pn" ]; then
      echo "進行中標記在第 $pn 章，不是第 $want 章。" >&2; exit 64
    fi
    N="$pn"; NNN="$(printf %03d "$N")"; W="章节/第${NNN}章"; MARK="$W/进行中"
    FLAGS=(); CHECK=()
    read -ra FLAGS <<<"$(mval "$N" 開關)"
    read -ra CHECK <<<"$(mval "$N" 檢查)"
    INSTR="$(mval "$N" 指令 | b64d)"
    MARK_START="$(mval "$N" 開始)"
  fi
  CH="$(chapter_file "$N")"; CH_REL="${CH#$BOOK/}"
  if [ ! -f "$CH" ]; then
    echo "第 $N 章沒有正文，續跑補不了。用「重寫第${N}章」從頭來。" >&2
    exit 3
  fi
  SHORT="續跑"
  build_remind
  echo "續跑第 $N 章（上次停在「$(mval "$N" 階段)」）：$CH_REL" | tee -a "$LOG"
  SAFE_ADD=""
  if guard_trusted; then
    echo "守衛底稿確認是第 $N 章寫手調用前存的，做越界還原" | tee -a "$LOG"
    guard_restore "$CH_REL" 记忆/待更新.md
  else
    echo "警告：守衛底稿不是第 $N 章調模型前存的（沒有 logs/.guard.meta 或章號對不上），不敢還原，跳過。" >&2
    echo "      這次只提交：本章正文、记忆/、本章工作區；其他改動留在工作區，結束時列出來。" >&2
    SAFE_ADD="$CH_REL 记忆 $W 旧版"
  fi
  finish_chapter
}

# 只聊天、只改設定、停手：不走寫章流程，直接交給模型（AGENTS.md 裡有這幾條的做法）
case "$1" in
  唠唠*|嘮嘮*|停下*)
    call "$LIMIT_PLAN" "$*"; exit $? ;;
  改設定*|改设定*)
    call "$LIMIT_PLAN" "$*"; rc=$?; commit "改設定（$("$PY" -c 'import sys; print(sys.argv[1][:20])' "$*")）"; exit $rc ;;
  --續跑|--续跑|--resume)
    resume "${2:-}" ;;
esac

INSTR="$*"
# 「重寫第N章 要求」：第 N 章以後收進 旧版/、記憶退回，再當成寫新的第 N 章
N="$(printf '%s' "$1" | sed -nE 's/^重(寫|写)第0*([0-9]+)章.*/\2/p')"
if [ -z "$N" ] && printf '%s' "$1" | grep -qE '^重(寫|写)'; then
  N="$(latest)"
  INSTR="重寫第${N}章${*#重[寫写]}"
fi
pn="$(pending_n)"
if [ -n "$N" ]; then
  rm -f 章节/第*章/进行中   # 重寫就是放棄沒跑完的那章；先刪標記，免得跟著工作區被收進 旧版/ 再被提交
  last="$(latest)"
  if [ "$N" -gt "$last" ]; then
    # 這章連正文都沒寫出來（斷在規劃師或寫手之前）：把未完成的工作區和殘留的 待更新.md 收起來，記憶本來就停在上一章
    if [ "$N" -eq $((last + 1)) ] && [ -d "章节/第$(printf %03d "$N")章" ]; then
      d="旧版/重寫前_$(date +%Y%m%d-%H%M%S)_未完成"; mkdir -p "$d"
      mv "章节/第$(printf %03d "$N")章" "$d/"
      [ -f 记忆/待更新.md ] && mv 记忆/待更新.md "$d/"
      echo "第 $N 章沒有正文，已把未完成的工作區收進 $d"
    else
      echo "沒有第 $N 章，最新是第 $last 章" >&2; exit 1
    fi
  else
    "$PY" tools/rewrite_from.py "$N" || exit 1
  fi
  INSTR="重寫這一章（舊稿在 旧版/，不要讀）。讀者的要求：${INSTR#*章}"
else
  # 上一章沒跑完就不能接著寫新章：它的正文已經算進章數，待更新.md 也還沒過檢查，這時去併記憶會把沒驗過的賬記進去
  if [ -n "$pn" ]; then
    echo "停：第 $pn 章上次沒跑完（停在「$(mval "$pn" 階段)」，開始於 $(mval "$pn" 開始)），不去寫第 $((pn + 1)) 章。" >&2
    f="$(chapter_file "$pn")"
    if [ -f "$f" ]; then
      echo "正文已經在：bin/novel-call.sh --續跑 $pn 補跑後面的步驟；或「重寫第${pn}章」整章重來。" >&2
    else
      echo "還沒有正文：用「重寫第${pn}章」清掉重來。" >&2
    fi
    exit 3
  fi
  # 讀者接著寫新章，代表接受了上一章：先把 待更新.md 併進記憶
  if [ -f 记忆/待更新.md ]; then
    "$PY" tools/merge_update.py || { echo "记忆/待更新.md 沒併成功，按上面的 FAIL 改好再跑" >&2; exit 3; }
  fi
fi

# 記憶守衛：进度.md 落後正文，中間的事模型不知道（第 26 章的收線就這樣丟過）
latest_n="$(latest)"
mem_n="$(sed -nE 's/.*對應章節：第0*([0-9]+)章.*/\1/p' 记忆/进度.md | head -1)"
if [ "$latest_n" -gt 0 ] && [ -n "$mem_n" ] && [ "$mem_n" -lt "$latest_n" ]; then
  echo "停：正文已到第 ${latest_n} 章，记忆/进度.md 還停在第 ${mem_n} 章，中間的記憶沒併進去。" >&2
  echo "補上第 $((mem_n+1))–${latest_n} 章的 待更新.md，或用「重寫第$((mem_n+1))章」從那裡重來。" >&2
  exit 3
fi

N=$((latest_n + 1)); NNN="$(printf %03d "$N")"; W="章节/第${NNN}章"
mkdir -p "$W"
rm -f "$W/检查.txt"   # 上一次嘗試留下的
echo "第 $N 章：$INSTR" | tee -a "$LOG"
# 提交信息裡的指令摘要；按字截（VM 的 locale 可能是 C，bash 會按字節截斷成亂碼）
SHORT="$("$PY" -c 'import sys; print(sys.argv[1][:20])' "$INSTR")"

# 指令裡的開關
FLAGS=(); CHECK=()
case "$INSTR" in *寫多點*|*写多点*|*想寫多長*|*想写多长*) FLAGS+=(--long); CHECK+=(--long) ;; esac
if printf '%s' "$INSTR" | grep -qE '零(不在|不出|沒在|没在|不跟|不去|不用出)|(沒有|没有|不要|不帶|不带)零'; then FLAGS+=(--no-ling); CHECK+=(--no-ling); fi
if printf '%s' "$INSTR" | grep -qE '寫完|写完|收尾|收線|收线|完結|完结|不(要|用)?留扣子|不留(懸念|悬念)'; then FLAGS+=(--wrap); CHECK+=(--wrap); fi
build_remind

# 從這裡開始是「進行中」：標記在，流程走到 end 才刪
MARK="$W/进行中"; MARK_START=""
mark 寫手

# ── 寫手（照走向直接寫正文，再記賬） ─────────────────
HINTS="$("$PY" tools/compose.py write "$N" "$INSTR")" || end 3
WRITE_PROMPT="$REMIND${HINTS}
【寫手】這是第 ${N} 章。設定讀 ${W}/设定.md（已按當前時期挑過）。正文寫進 正文/第${NNN}章_章名.txt（章名自己定）。檢查命令：python3 tools/check.py ${CHECK[*]:-} 正文/第${NNN}章_章名.txt
讀者的指令：${INSTR}"
guard_save write
call "$LIMIT_WRITE" "$WRITE_PROMPT"; rc=$?
CH="$(chapter_file "$N")"; CH_REL="${CH#$BOOK/}"
guard_restore ${CH_REL:+"$CH_REL"} 记忆/待更新.md
[ -n "$CH" ] && [ -f "$CH" ] || { echo "寫手沒寫出第 ${N} 章正文（退出碼 $rc），日誌 $LOG" >&2; end 1; }
echo "正文：${CH_REL}"

# ── 4、5. 粗篩 → 修稿 → 焦點 → 提交 ───────────────────
finish_chapter

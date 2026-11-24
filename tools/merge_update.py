"""Bookkeeping: merge the writer's 记忆/待更新.md ("pending update") into the
long-term memory files, snapshot memory, then delete the pending file.

The writer model never edits memory directly. After each chapter it writes a
small structured note (current state / who knows what / foreshadowing changes /
latest hook); this script merges it at the start of the next run. Keeping the
merge in code means memory can't be silently rewritten or lost by the model.

Usage: python3 tools/merge_update.py              merge
       python3 tools/merge_update.py --check      validate format only, change nothing
       python3 tools/merge_update.py --snapshot   only snapshot current memory
Rules: "current state" and "latest hook" replace the old sections; "who knows
what" is appended without duplicates; foreshadowing changes go to the change log
at the end of 伏笔.md, tagged with the chapter number; an optional "focus:
change to ..." replaces 当前焦点.md. Originals are backed up under 旧版/.

記賬：把 记忆/待更新.md 併進 进度.md 和 伏笔.md，存一份快照，然後刪掉它。

用法：python3 tools/merge_update.py           合併
      python3 tools/merge_update.py --check   只檢查格式，不改文件
      python3 tools/merge_update.py --snapshot 只存當前記憶的快照

規則：
- 进度.md 的「當前狀態」「最新扣子」整節換成 待更新.md 的。
- 「誰知道什麼」逐條追加，已有的同一句不重複加。
- 「伏筆變動」追加到 伏笔.md 末尾的「變動記錄」，標上章號。
- 「焦點」（可選）寫「改成：……」就換掉 当前焦点.md，寫「不變」或沒寫就不動。
- 原件備份到 旧版/待更新_第NNN章.md；記憶快照存到 旧版/记忆/第NNN章后/。
"""
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from book import (FOCUS, FORESHADOW, MEMORY, OLD, PROGRESS, ROOT, SNAPSHOT_FILES, SNAPSHOTS, UPDATE,
                  bullets, latest, read, sections, write)
from check import CHU_TRAITS, DEATH, SIMPLIFIED, sealed_keywords

# The four sections the note must have: current state, who knows what,
# foreshadowing changes, latest hook.  待更新.md 必須有的四節。
REQUIRED = ['當前狀態', '誰知道什麼', '伏筆變動', '最新扣子']
LOG_HEADING = '## 變動記錄'


def join_sections(head, parts):
    """Inverse of book.sections(): rebuild markdown from (heading, body) pairs.  把小節拼回 markdown。"""
    out = head.rstrip('\n') + '\n'
    for title, body in parts:
        out += f'\n## {title}\n\n{body.strip()}\n'
    return out


def save_snapshot(n):
    """Copy memory files to 旧版/记忆/第NNN章后/ so rewrite_from.py can roll back.  存記憶快照，重寫時退回用。"""
    target = os.path.join(SNAPSHOTS, f'第{n:03d}章后')
    os.makedirs(target, exist_ok=True)
    for name in SNAPSHOT_FILES:
        src = os.path.join(MEMORY, name)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(target, name))


def stated_chapter(found):
    """Chapter number the note claims to describe ('對應章節：第N章').  待更新寫的是第幾章。"""
    match = re.search(r'對應章節[：:]\s*第\s*(\d+)\s*章', found.get('當前狀態', ''))
    return int(match.group(1)) if match else None


def load_update():
    """Parse 待更新.md and list every format or content problem.
    Content checks reuse check.py's lists: no deaths, no traits of the canon
    character the protagonist must not turn into, nothing about sealed plot
    threads, no simplified characters (the novel is in traditional Chinese).
    解析待更新.md，列出所有問題。"""
    found = {title: body for title, body in sections(read(UPDATE))[1]}
    problems = []
    whole = ''.join(found.values())
    for word in DEATH:
        if word in whole:
            problems.append(f'寫到死亡「{word}」，改成失蹤、退居一類的寫法')
    for word in CHU_TRAITS:
        if word in whole:
            problems.append(f'寫成了楚子航：「{word}」，刪掉')
    for thread, word in sealed_keywords():
        if word in whole:
            problems.append(f'提到了封存的{thread}（「{word}」），刪掉')
            break
    # 里 is legitimate in traditional text in these words; drop them before the
    # simplified-character scan.  這些詞裡的「里」繁體也這麼寫，先拿掉再查簡體。
    scan = re.sub(r'(公|英|海|千|萬|鄰|故|鄉|德)里|里程|里數', '', whole)
    simp = sorted({c for c in scan if c in SIMPLIFIED})
    if simp:
        problems.append('疑似簡體字：' + ''.join(simp))
    # Chapter numbers in memory leak into the next chapter's prose ("as in chapter 5..."),
    # so only the one 對應章節 line may contain one.
    # 記憶裡的章號會被下一章照抄進正文，所以只准「對應章節」那一條有。
    if re.search(r'第\s*[0-9一二三四五六七八九十]+\s*章|上一章|前幾章', re.sub(r'.*對應章節.*', '', whole)):
        problems.append('除了「對應章節」那一條，別處不要寫章號（下一章會照抄進正文）')
    for name in REQUIRED:
        if name not in found:
            problems.append(f'缺少小節「## {name}」')
        elif not found[name].strip():
            problems.append(f'小節「{name}」是空的')
    n = stated_chapter(found)
    if n is None:
        problems.append('「當前狀態」第一條要寫「- 對應章節：第N章」')
    elif n != latest():
        problems.append(f'「對應章節」寫的是第 {n} 章，最新一章是第 {latest()} 章')
    return found, problems


def main():
    args = sys.argv[1:]
    if '--snapshot' in args:
        save_snapshot(latest())
        print(f'已存第 {latest()} 章的記憶快照')
        return 0
    if not os.path.exists(UPDATE):
        print('沒有 待更新.md，不用合併')
        return 0
    found, problems = load_update()
    n = stated_chapter(found)
    # A note for an older chapter is stale (e.g. left over after a crash): set it aside, don't merge.
    # 寫的是舊章就是過期文件（比如斷電留下的），移走不併。
    if n is not None and n < latest() and '--check' not in args:
        target = os.path.join(OLD, f'待更新_過期_第{n:03d}章.md')
        shutil.move(UPDATE, target)
        print(f'待更新.md 寫的是第 {n} 章，最新已是第 {latest()} 章，屬過期文件，不合併，已移到 {os.path.relpath(target, ROOT)}')
        return 0
    for problem in problems:
        print('FAIL', problem)
    if problems:
        print('待更新.md 格式不對，照 AGENTS.md「寫手」一節第 4 步改好')
        return 1
    if '--check' in args:
        print('PASS 待更新.md 格式正確')
        return 0

    head, parts = sections(read(PROGRESS))
    titles = [title for title, _ in parts]
    for name in ('當前狀態', '誰知道什麼', '最新扣子'):
        if name not in titles:
            parts.append((name, ''))
    merged = []
    for title, body in parts:
        if title in ('當前狀態', '最新扣子'):
            body = found[title]
        elif title == '誰知道什麼':
            old = bullets(body)
            body = '\n'.join(old + [b for b in bullets(found[title]) if b not in old])
        merged.append((title, body))

    fs = read(FORESHADOW).rstrip('\n')
    if LOG_HEADING not in fs:
        fs += f'\n\n{LOG_HEADING}\n\n編號條目是原始記錄，這裡是之後每章的推進和回收，以最後一條為準。\n'
    changes = bullets(found['伏筆變動']) or ['- ' + found['伏筆變動'].strip()]
    fs += f'\n第 {n} 章：\n' + '\n'.join(changes) + '\n'

    backup = os.path.join(OLD, f'待更新_第{n:03d}章.md')
    os.makedirs(OLD, exist_ok=True)
    shutil.copyfile(UPDATE, backup)
    write(PROGRESS, join_sections(head, merged))
    write(FORESHADOW, fs)
    focus = re.sub(r'^-\s*', '', found.get('焦點', '')).strip()
    if re.match(r'改成[：:]', focus):
        focus = re.sub(r'^改成[：:]\s*', '', focus)
        write(FOCUS, f'# 當前焦點\n\n接下來幾章往哪寫。寫手在一條線收完時改它，讀者也可以直接改。\n\n{focus}\n\n（第 {n} 章寫手更新）\n')
        print('焦點已更新：' + focus.splitlines()[0][:60])
    os.remove(UPDATE)
    save_snapshot(n)
    print(f'已合併第 {n} 章的 待更新.md，備份在 {os.path.relpath(backup, ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

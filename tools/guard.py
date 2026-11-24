"""Scope guard: snapshot the repo before every model call, and afterwards keep only
the files the model was allowed to touch; every other change is rolled back.

Why: at chapter 44 a script the model left behind overwrote chapter 31 down to
1,800 characters and littered tools/ with make_ch44.py files. Prompt rules alone
did not stop this, so the pipeline enforces scope in code instead.

Usage: python3 tools/guard.py save
       python3 tools/guard.py restore N ALLOWED_PATH...
       (chapter N's own workspace 章节/第NNN章/ is always allowed)
What restore does: deleted files are restored, edited files are reverted, and
new files are moved to 章节/第NNN章/草稿/越界/ (kept for inspection, not deleted).

越界守衛：模型每次動手前存一份底，動完只放行它該寫的文件，別的改動一律還原。

第 44 章時，模型留下的腳本把第 31 章覆蓋成 1800 字，還在 tools/ 裡留了一堆 make_ch44.py。這裡就是防這個。

用法：python3 tools/guard.py save
      python3 tools/guard.py restore N 允許的路徑...   （第 N 章工作區 章节/第NNN章/ 總是允許）
"""
import filecmp
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from book import ROOT, workdir

# Where the "before" snapshot lives.  存底的位置。
BASE = os.path.join(ROOT, 'logs', '.guard')
# Folders whose files the model must not change unless explicitly allowed.
# 這些資料夾裡的文件，沒被允許就不許動。
WATCH_DIRS = ('正文', '设定', '记忆', '文风', 'tools', 'bin', '章节', '往作')
SKIP = ('__pycache__', 'logs', '.git', '.novel.lock')


def files(top, base=ROOT):
    """Yield every file under `top` as a path relative to `base`.  列出 top 下所有文件（相對路徑）。"""
    for folder, dirs, names in os.walk(top):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for name in names:
            yield os.path.relpath(os.path.join(folder, name), base)


def watched():
    """Files at the repo root plus everything in WATCH_DIRS.  根目錄的文件＋WATCH_DIRS 裡的全部文件。"""
    out = [n for n in os.listdir(ROOT) if os.path.isfile(os.path.join(ROOT, n)) and n not in SKIP]
    for d in WATCH_DIRS:
        out += list(files(os.path.join(ROOT, d)))
    return set(out)


def save():
    shutil.rmtree(BASE, ignore_errors=True)
    for rel in watched():
        dst = os.path.join(BASE, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(ROOT, rel), dst)
    # Also remember the top-level names, so new top-level folders can be caught later.
    # 另記一份根目錄的名字，之後才抓得到新冒出來的頂層資料夾。
    with open(os.path.join(BASE, '.tops'), 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(sorted(os.listdir(ROOT))))
    return 0


def restore(n, allowed):
    own = os.path.relpath(workdir(n), ROOT) + os.sep
    allow = {os.path.normpath(a) for a in allowed}
    stray = os.path.join(workdir(n), '草稿', '越界')
    notes = []
    if not os.path.exists(os.path.join(BASE, '.tops')):
        print('越界 守衛沒有底稿，這次沒查')
        return 0
    before = set(files(BASE, BASE)) - {'.tops'}
    for rel in sorted(watched() | before):
        if rel in allow or rel.startswith(own):
            continue
        # Three cases: deleted -> restore; new -> move aside; edited -> revert.
        # 三種情況：被刪→還原；多出來→移走；被改→還原。
        here, base = os.path.join(ROOT, rel), os.path.join(BASE, rel)
        if rel in before and not os.path.exists(here):
            os.makedirs(os.path.dirname(here), exist_ok=True)
            shutil.copy2(base, here)
            notes.append(f'刪了 {rel}，已還原')
        elif rel not in before:
            dst = os.path.join(stray, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(here, dst)
            notes.append(f'多出 {rel}，已移到 {os.path.relpath(dst, ROOT)}')
        elif not filecmp.cmp(here, base, shallow=False):
            shutil.copy2(base, here)
            notes.append(f'改了 {rel}，已還原')
    tops = set(open(os.path.join(BASE, '.tops'), encoding='utf-8').read().split('\n'))
    for name in sorted(set(os.listdir(ROOT)) - tops - set(SKIP)):
        dst = os.path.join(stray, name)
        os.makedirs(stray, exist_ok=True)
        shutil.move(os.path.join(ROOT, name), dst)
        notes.append(f'根目錄多出 {name}，已移到 {os.path.relpath(dst, ROOT)}')
    for note in notes:
        print('越界', note)
    return 0


def main():
    args = sys.argv[1:]
    if args[:1] == ['save']:
        return save()
    if args[:1] == ['restore'] and len(args) >= 2 and args[1].isdigit():
        return restore(int(args[1]), args[2:])
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())

"""Check and use the planner's chapter outline (章节/第NNN章/大纲.md).

The planner model writes an outline before the writer model writes prose.
This script validates it so a bad outline is caught before the expensive step.

Usage: python3 tools/outline.py check N [--instr 'reader instruction'] [--no-ling]
       python3 tools/outline.py path  N    print the chapter file path from the outline's title
       python3 tools/outline.py focus N    if the outline changes the focus, write 记忆/当前焦点.md

大綱的檢查和取用。

用法：python3 tools/outline.py check N [--instr '讀者的指令'] [--no-ling]   檢查大綱格式
      python3 tools/outline.py path  N                                     按大綱章名給出正文路徑
      python3 tools/outline.py focus N                                     大綱裡改了焦點就寫進 记忆/当前焦点.md
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from book import FOCUS, TEXT, chapters, read, section, title_of, workdir, write

# Allowed scene types: set piece, daily life, the couple alone, wrap-up.
# 場次類型：大場面、日常、兩人、收尾。
KINDS = ('大場面', '日常', '兩人', '收尾')
# Required outline sections: title, focus, scenes, the couple's scene, must have,
# must not have, foreshadowing, ending.  大綱必須有的小節。
NEEDED = ('章名', '焦點', '場次', '兩人的戲', '必須有', '不能有', '伏筆', '結尾')


def load(n):
    """Outline text for chapter n ('' if missing).  第 n 章的大綱。"""
    return read(os.path.join(workdir(n), '大纲.md'))


def title(text):
    """Chapter title from the '## 章名' section, quotes stripped.  取章名。"""
    line = section(text, '章名').splitlines()
    return re.sub(r'^[-\s]+', '', line[0]).strip('「」 ') if line else ''


def check(n, instruction='', no_ling=False):
    """Return a list of problems; empty means the outline passes.
    `instruction` is what the reader asked for: if it was a concrete plot request
    (not just "continue"), every detail must be listed under "must have", because
    losing a reader's plot detail is the worst failure of this pipeline.
    `no_ling` = the heroine is absent this chapter, so no couple scene is required.
    回傳問題清單，空的就是通過。"""
    text = load(n)
    if not text.strip():
        return [f'沒有大綱文件 章节/第{n:03d}章/大纲.md']
    problems = []
    for name in NEEDED:
        if f'## {name}' not in text:
            problems.append(f'缺少小節「## {name}」')
    name = title(text)
    used = {title_of(p): k for k, p in chapters().items() if k != n}
    if not name:
        problems.append('章名是空的')
    elif len(name) > 6 or re.search(r'[\s/\\：:第章]', name):
        problems.append(f'章名「{name}」要四字以內，不帶章號和符號')
    elif name in used:
        problems.append(f'章名「{name}」第 {used[name]} 章用過了，換一個')
    scenes = [line for line in section(text, '場次').splitlines() if re.match(r'\s*\d+[.、]', line)]
    if not 4 <= len(scenes) <= 5:
        problems.append(f'場次要 4 到 5 場，現在 {len(scenes)} 場（每場一行，「1. 【類型】…」）')
    for line in scenes:
        kind = re.search(r'【(.+?)】', line)
        if not kind or kind.group(1) not in KINDS:
            problems.append(f'場次沒標類型或類型不對（只能是 {"、".join(KINDS)}）：{line.strip()[:30]}')
    if re.search(r'第\s*\d+\s*章|上一章|前幾章', section(text, '場次') + section(text, '結尾')):
        problems.append('場次和結尾裡不要寫章號、「上一章」，寫手會照抄進正文')
    pair = section(text, '兩人的戲').strip('- ')
    if not no_ling and (not pair or pair.startswith('無')):
        problems.append('「兩人的戲」是空的；零在場就要有一段兩人的戲')
    must = section(text, '必須有').strip('- ')
    if instruction and not re.match(r'^(繼續|继续)', instruction) and (not must or must.startswith('無')):
        problems.append('讀者給了走向，「必須有」要把走向裡的每一個細節列出來，不能寫無')
    return problems


def path(n):
    """正文/第NNN章_<title>.txt"""
    name = title(load(n))
    return os.path.join(TEXT, f'第{n:03d}章_{name}.txt')


def focus(n):
    """Write the outline's new focus to 当前焦点.md unless it says 'unchanged'.  大綱改了焦點就寫進去。"""
    body = section(load(n), '焦點')
    text = re.sub(r'^-\s*', '', body).strip()
    if not text or text.startswith('不變') or text.startswith('不变'):
        print('焦點不變')
        return 0
    text = re.sub(r'^改成[：:]\s*', '', text)
    write(FOCUS, f'# 當前焦點\n\n接下來幾章往哪寫。規劃師在一條線收完時改它，讀者也可以直接改。\n\n{text}\n\n（第 {n} 章規劃時更新）\n')
    print('焦點已更新：' + text.splitlines()[0][:60])
    return 0


def main():
    args = sys.argv[1:]
    if len(args) < 2 or not args[1].isdigit():
        print(__doc__)
        return 2
    cmd, n = args[0], int(args[1])
    if cmd == 'check':
        instruction = args[args.index('--instr') + 1] if '--instr' in args else ''
        problems = check(n, instruction, '--no-ling' in args)
        for problem in problems:
            print('FAIL', problem)
        if not problems:
            print('PASS 大綱格式正確')
        return 1 if problems else 0
    if cmd == 'path':
        print(path(n))
        return 0
    if cmd == 'focus':
        return focus(n)
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())

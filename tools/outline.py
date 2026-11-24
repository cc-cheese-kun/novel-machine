"""大綱的檢查和取用。

用法：python3 tools/outline.py check N [--instr '讀者的指令'] [--no-ling]   檢查大綱格式
      python3 tools/outline.py path  N                                     按大綱章名給出正文路徑
      python3 tools/outline.py focus N                                     大綱裡改了焦點就寫進 记忆/当前焦点.md
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from book import FOCUS, TEXT, chapters, read, section, title_of, workdir, write

KINDS = ('大場面', '日常', '兩人', '收尾')
NEEDED = ('章名', '焦點', '場次', '兩人的戲', '必須有', '不能有', '伏筆', '結尾')


def load(n):
    return read(os.path.join(workdir(n), '大纲.md'))


def title(text):
    line = section(text, '章名').splitlines()
    return re.sub(r'^[-\s]+', '', line[0]).strip('「」 ') if line else ''


def check(n, instruction='', no_ling=False):
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
    name = title(load(n))
    return os.path.join(TEXT, f'第{n:03d}章_{name}.txt')


def focus(n):
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

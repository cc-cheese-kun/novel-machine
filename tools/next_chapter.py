"""Print the file path for the next chapter.

Usage: python3 tools/next_chapter.py [title]
Looks at 正文/第NNN章_*.txt, takes the highest chapter number + 1, and prints
正文/第{N+1:03d}章_{title}.txt. Exits 1 if the title was already used, because
the writer model tends to reuse titles and duplicate titles are confusing to read.

打印下一章的文件路徑。
用法：python3 tools/next_chapter.py [章名]
在 正文/ 裡找最大的章號加一，拼出 正文/第NNN章_章名.txt。
章名用過了就退出 1：寫手愛重複起名，同名章讀起來分不清。
"""
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
# Repo root = parent of tools/.  倉庫根目錄＝tools/ 的上一層。
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
numbers = []
for path in glob.glob(os.path.join(root, '正文', '第*章*.txt')):
    match = re.search(r'第(\d+)章', os.path.basename(path))
    if match:
        numbers.append(int(match.group(1)))
title = sys.argv[1] if len(sys.argv) > 1 else ''
used = [re.sub(r'^第\d+章_?', '', os.path.basename(p)[:-4]) for p in glob.glob(os.path.join(root, '正文', '第*章*.txt'))]
if title and title in used:
    print(f'FAIL 章名「{title}」用過了，換一個', file=sys.stderr)
    sys.exit(1)
suffix = '_' + title if title else ''
print(os.path.join(root, '正文', f'第{max(numbers, default=0) + 1:03d}章{suffix}.txt'))

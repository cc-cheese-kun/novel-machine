import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
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

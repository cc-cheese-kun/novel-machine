"""Merge every chapter in 正文/ into one file, 全书.txt, in chapter order.

Usage: python3 tools/build_book.py
Pure text concatenation with a heading per chapter - no model involved, so nothing
can be dropped. Fails on duplicate chapter numbers, warns on gaps.

把 正文/ 的章節按章號合併成 全书.txt，每章前加章名。不經過模型，不會漏字。

用法：python3 tools/build_book.py
"""
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    chapters = []
    for path in glob.glob(os.path.join(ROOT, '正文', '第*章*.txt')):
        match = re.match(r'第(\d+)章_?(.*)\.txt$', os.path.basename(path))
        if match:
            chapters.append((int(match.group(1)), match.group(2), path))
    chapters.sort()
    if not chapters:
        print('正文/ 裡沒有章節')
        return 1
    numbers = [n for n, _, _ in chapters]
    if len(set(numbers)) != len(numbers):
        print('FAIL 有重複章號：', sorted({n for n in numbers if numbers.count(n) > 1}))
        return 1
    missing = sorted(set(range(1, numbers[-1] + 1)) - set(numbers))
    if missing:
        print('WARN 缺章：', missing)
    parts, total = [], 0
    for number, title, path in chapters:
        with open(path, encoding='utf-8') as handle:
            body = handle.read().strip()
        # Count CJK characters only (the usual way to count Chinese word length).
        # 只數漢字（中文字數的通常算法）。
        total += len(re.findall(r'[一-鿿]', body))
        heading = f'第{number}章' + (f'　{title}' if title else '')
        parts.append(f'{heading}\n\n{body}\n')
    with open(os.path.join(ROOT, '全书.txt'), 'w', encoding='utf-8') as handle:
        handle.write('\n\n'.join(parts))
    print(f'全书.txt：{len(chapters)} 章，{total} 字')
    return 0


if __name__ == '__main__':
    sys.exit(main())

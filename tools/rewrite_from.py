"""從第 N 章開始重寫：第 N 章到最新一章（正文和 章节/ 工作區）收進 旧版/，記憶退回第 N-1 章寫完時。

用法：python3 tools/rewrite_from.py N

之後照正常流程寫第 N 章，再用「繼續」一章章往後寫。不要倒著重寫。
"""
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from book import MEMORY, OLD, ROOT, SNAPSHOT_FILES, SNAPSHOTS, UPDATE, chapters, read, workdir


def focus_from_rewritten(start):
    """当前焦点.md 是不是第 start 章以後的規劃師改的（merge_update.py 會寫上「第 N 章寫手更新」，舊的是「規劃時更新」）。"""
    m = re.search(r'第 (\d+) 章(?:規劃時|寫手)更新', read(os.path.join(MEMORY, '当前焦点.md')))
    return bool(m) and int(m.group(1)) >= start


def main():
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print(__doc__)
        return 2
    start = int(sys.argv[1])
    found = chapters()
    last = max(found, default=0)
    if start < 1 or start > last:
        print(f'FAIL 沒有第 {start} 章，最新是第 {last} 章')
        return 1
    snapshot = os.path.join(SNAPSHOTS, f'第{start - 1:03d}章后')
    if not os.path.exists(os.path.join(snapshot, '进度.md')):
        print(f'FAIL 沒有第 {start - 1} 章寫完時的記憶快照（{os.path.relpath(snapshot, ROOT)}），不能自動退回')
        return 1

    archive = os.path.join(OLD, '重寫前_' + time.strftime('%Y%m%d-%H%M%S'))
    base, k = archive, 2
    while os.path.exists(archive):
        archive, k = f'{base}_{k}', k + 1
    os.makedirs(archive)
    moved = []
    for number in sorted(n for n in found if n >= start):
        shutil.move(found[number], os.path.join(archive, os.path.basename(found[number])))
        moved.append(os.path.basename(found[number]))
        if os.path.isdir(workdir(number)):
            shutil.move(workdir(number), os.path.join(archive, os.path.basename(workdir(number))))
    for name in SNAPSHOT_FILES + ('待更新.md',):
        path = os.path.join(MEMORY, name)
        if os.path.exists(path):
            shutil.copyfile(path, os.path.join(archive, name))
    if os.path.exists(UPDATE):
        os.remove(UPDATE)
    for name in SNAPSHOT_FILES:
        src = os.path.join(snapshot, name)
        if not os.path.exists(src):  # 舊快照沒有 当前焦点.md，就保留現在的
            continue
        if name == '当前焦点.md' and not focus_from_rewritten(start):
            continue  # 焦點是讀者或 Claude 手改的，不是被重寫的那幾章改的，留著
        shutil.copyfile(src, os.path.join(MEMORY, name))
    print(f'已收起：{"、".join(moved)} → {os.path.relpath(archive, ROOT)}')
    print(f'記憶已退回第 {start - 1} 章寫完時，現在寫的就是第 {start} 章')
    return 0


if __name__ == '__main__':
    sys.exit(main())

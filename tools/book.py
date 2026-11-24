"""Shared paths and small helpers for every script. Other scripts import paths
from here instead of building their own, so a folder rename happens in one place.

Folder map: 正文 = finished chapters, 章节 = per-chapter workspaces (outline,
drafts), 设定 = settings and rules, 记忆 = running memory (progress,
foreshadowing, current focus), 文风 = style samples, 旧版 = archives and memory
snapshots.

全書共用的路徑和小工具。別的腳本都從這裡拿路徑，不各自拼。
"""
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = os.path.join(ROOT, '正文')
WORK = os.path.join(ROOT, '章节')
SETTING = os.path.join(ROOT, '设定')
MEMORY = os.path.join(ROOT, '记忆')
STYLE = os.path.join(ROOT, '文风')
OLD = os.path.join(ROOT, '旧版')

PROGRESS = os.path.join(MEMORY, '进度.md')
FORESHADOW = os.path.join(MEMORY, '伏笔.md')
FOCUS = os.path.join(MEMORY, '当前焦点.md')
UPDATE = os.path.join(MEMORY, '待更新.md')
INTENT = os.path.join(ROOT, '作者意图.md')
MILESTONES = os.path.join(ROOT, '路标.md')
SNAPSHOTS = os.path.join(OLD, '记忆')
# Memory files snapshotted after every chapter, so a rewrite can roll back.
# 每章寫完存一份快照，重寫時退回用
SNAPSHOT_FILES = ('进度.md', '伏笔.md', '当前焦点.md')


def read(path, default=''):
    """Read a UTF-8 file; return `default` if it is missing.  讀文件，不存在就回 default。"""
    try:
        with open(path, encoding='utf-8') as handle:
            return handle.read()
    except OSError:
        return default


def write(path, text):
    """Write a UTF-8 file, creating parent folders.  寫文件，順手建上層資料夾。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def chapters():
    """{chapter number: path}, sorted by number.  {章號: 路徑}，按章號排。"""
    found = {}
    for path in glob.glob(os.path.join(TEXT, '第*章*.txt')):
        match = re.match(r'第(\d+)章', os.path.basename(path))
        if match:
            found[int(match.group(1))] = path
    return dict(sorted(found.items()))


def latest():
    """Highest chapter number, 0 if none.  最新章號，沒有就是 0。"""
    return max(chapters(), default=0)


def title_of(path):
    """'第007章_換車.txt' -> '換車'."""
    return re.sub(r'^第\d+章_?', '', os.path.basename(path)[:-4])


def workdir(n):
    """Workspace folder for chapter n: 章节/第NNN章.  第 n 章的工作區。"""
    return os.path.join(WORK, f'第{n:03d}章')


def sections(text):
    """Split markdown by '## ' headings: (preamble, [(heading, body), ...]).
    回傳 (開頭, [(標題, 內容), ...])，標題是「## 」後面的字。"""
    parts = re.split(r'^## +(.+?)\s*$', text, flags=re.M)
    return parts[0], [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts), 2)]


def section(text, name):
    """Body of the '## name' section, or ''.  取「## name」那一節的內容。"""
    for title, body in sections(text)[1]:
        if title == name:
            return body.strip()
    return ''


def bullets(body):
    """Lines starting with '- '.  取「- 」開頭的條目。"""
    return [line.strip() for line in body.splitlines() if line.strip().startswith('- ')]


def han(text):
    """Count CJK characters (Chinese length).  數漢字。"""
    return len(re.findall(r'[一-鿿]', text))


def bigrams(text):
    """Set of 2-character pieces; used to measure how similar two texts are.
    兩字一組的集合，用來量兩段文字有多像。"""
    chars = re.sub(r'[^一-鿿A-Za-z0-9]', '', text)
    return {chars[i:i + 2] for i in range(len(chars) - 1)}

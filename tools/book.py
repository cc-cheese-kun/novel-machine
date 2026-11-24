"""全書共用的路徑和小工具。別的腳本都從這裡拿路徑，不各自拼。"""
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
# 每章寫完存一份快照，重寫時退回用
SNAPSHOT_FILES = ('进度.md', '伏笔.md', '当前焦点.md')


def read(path, default=''):
    try:
        with open(path, encoding='utf-8') as handle:
            return handle.read()
    except OSError:
        return default


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def chapters():
    """{章號: 路徑}，按章號排。"""
    found = {}
    for path in glob.glob(os.path.join(TEXT, '第*章*.txt')):
        match = re.match(r'第(\d+)章', os.path.basename(path))
        if match:
            found[int(match.group(1))] = path
    return dict(sorted(found.items()))


def latest():
    return max(chapters(), default=0)


def title_of(path):
    return re.sub(r'^第\d+章_?', '', os.path.basename(path)[:-4])


def workdir(n):
    return os.path.join(WORK, f'第{n:03d}章')


def sections(text):
    """回傳 (開頭, [(標題, 內容), ...])，標題是「## 」後面的字。"""
    parts = re.split(r'^## +(.+?)\s*$', text, flags=re.M)
    return parts[0], [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts), 2)]


def section(text, name):
    for title, body in sections(text)[1]:
        if title == name:
            return body.strip()
    return ''


def bullets(body):
    return [line.strip() for line in body.splitlines() if line.strip().startswith('- ')]


def han(text):
    return len(re.findall(r'[一-鿿]', text))


def bigrams(text):
    chars = re.sub(r'[^一-鿿A-Za-z0-9]', '', text)
    return {chars[i:i + 2] for i in range(len(chars) - 1)}

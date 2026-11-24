#!/usr/bin/env python3
"""測「進行中」標記和 --續跑：用假 agy 跑到一半 kill -9 整個進程組（模擬 VM 重啟），再看後面能不能接上。

用法：python3 tests/test_resume.py        （在副本裡跑，不碰正式倉庫）
"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAKE = os.path.join(SRC, 'tests', 'fake_agy.py')
failures = []


def check(cond, msg):
    print(('  ok   ' if cond else '  FAIL ') + msg)
    if not cond:
        failures.append(msg)


def sh(cwd, *cmd, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env={**os.environ, **(env or {})})


def new_repo(tmp, name):
    """副本：正式倉庫的文件（不含 .git、logs），掛一個本地 bare 遠端，這樣提交和推送也測得到。"""
    book = os.path.join(tmp, name)
    shutil.copytree(SRC, book, ignore=shutil.ignore_patterns('.git', 'logs', '__pycache__', '.novel.lock'))
    for d in ('章节',):
        shutil.rmtree(os.path.join(book, d), ignore_errors=True)
    os.makedirs(os.path.join(book, '章节'))
    remote = os.path.join(tmp, name + '.git')
    sh(tmp, 'git', 'init', '-q', '--bare', '-b', 'main', remote)
    sh(book, 'git', 'init', '-q', '-b', 'main')
    sh(book, 'git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'add', '-A')
    sh(book, 'git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'init')
    sh(book, 'git', 'remote', 'add', 'origin', remote)
    sh(book, 'git', 'push', '-q', '-u', 'origin', 'main')
    return book


def kill_session(sid):
    """殺掉整個會話：timeout 會給子進程另開進程組，只殺進程組會漏掉假 agy（它還握著鎖）。"""
    out = subprocess.run(['ps', '-eo', 'pid=,sid='], capture_output=True, text=True).stdout
    for line in out.splitlines():
        pid, s = line.split()
        if int(s) == sid:
            try:
                os.kill(int(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass


def run_and_kill(book, hang, instr='繼續'):
    """跑 novel-call.sh，等假 agy 說「到點了」就 kill -9 整個進程組。"""
    flag = os.path.join(book, '.flag')
    if os.path.exists(flag):
        os.remove(flag)
    env = {**os.environ, 'AGY': FAKE, 'FAKE_HANG': hang, 'FAKE_FLAG': flag}
    proc = subprocess.Popen(['bash', 'bin/novel-call.sh', instr], cwd=book, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(600):
        if os.path.exists(flag):
            break
        time.sleep(0.1)
    else:
        kill_session(proc.pid)
        raise SystemExit('假 agy 沒到點，測試本身有問題')
    kill_session(proc.pid)
    proc.wait()


def novel(book, *args):
    return sh(book, 'bash', 'bin/novel-call.sh', *args, env={'AGY': FAKE})


def exists(book, *p):
    return os.path.exists(os.path.join(book, *p))


def text(book, *p):
    with open(os.path.join(book, *p), encoding='utf-8') as h:
        return h.read()


def at(book):
    """副本裡已經有的章不算，這次測的是下一章：回傳 (章號, 工作區名, 下一章工作區名)。"""
    n = len(chapters(book)) + 1
    return n, f'第{n:03d}章', f'第{n + 1:03d}章'


def chapters(book):
    return sorted(c for c in os.listdir(os.path.join(book, '正文')) if c.startswith('第'))


def tracked(book):
    return sh(book, 'git', '-c', 'core.quotepath=false', 'ls-files').stdout.split('\n')


tmp = tempfile.mkdtemp(prefix='resume_')
try:
    # 場景 A：寫手落盤後被殺 → 擋住 → doctor 報出 → 續跑走完
    print('A. 寫手落盤後進程被殺，再 --續跑')
    b = new_repo(tmp, 'a')
    N, W, W2 = at(b)
    intent = text(b, '作者意图.md')
    run_and_kill(b, 'write')
    check(exists(b, '章节', W, '进行中'), '被殺後標記還在')
    check(len([c for c in chapters(b) if c.startswith(W)]) == 1, '正文已落盤')
    check(exists(b, '记忆', '待更新.md'), '待更新.md 已落盤')
    check(text(b, '作者意图.md') != intent and exists(b, 'tools', 'make_ch.py'), '寫手的越界改動還在（還沒還原）')
    r = novel(b, '繼續')
    check(r.returncode == 3 and f'第 {N} 章上次沒跑完' in r.stderr, '再跑原指令被擋住，exit 3：' + r.stderr.strip().split('\n')[0])
    check(not any(c.startswith(W2) for c in chapters(b)), '沒有去寫第 2 章')
    check(exists(b, '章节', W, '进行中'), '被擋住時標記沒被動')
    r = novel(b, '--doctor')
    check(r.returncode == 3 and f'進行中：第 {N} 章' in r.stdout and f'--續跑 {N}' in r.stdout, '--doctor 報出沒跑完的章')
    r = novel(b, '--續跑', str(N + 2))
    check(r.returncode == 64, '章號對不上標記時報用法錯')
    r = novel(b, '--續跑')
    check(r.returncode == 0, f'--續跑 走完 exit 0（實際 {r.returncode}）\n{r.stdout[-600:]}{r.stderr[-300:]}')
    check(f'守衛底稿確認是第 {N} 章寫手調用前存的' in r.stdout, '續跑確認過守衛底稿')
    check(not exists(b, '章节', W, '进行中'), '走完後標記已刪')
    check(text(b, '作者意图.md') == intent, '越界改動已還原（作者意图.md）')
    check(not exists(b, 'tools', 'make_ch.py') and exists(b, '章节', W, '草稿', '越界', 'tools', 'make_ch.py'), '越界文件已挪走')
    log = sh(b, 'git', 'log', '--format=%s').stdout.split('\n')
    check(any(W in s for s in log), '章節已提交：' + log[0])
    check(not any('进行中' in f for f in tracked(b)), '標記沒進 git')
    check(sh(b, 'git', 'status', '--short').stdout.strip() == '', '工作區乾淨（全部已提交）')
    check(sh(b, 'git', 'rev-parse', 'HEAD').stdout == sh(b, 'git', '--git-dir', os.path.join(tmp, 'a.git'), 'rev-parse', 'main').stdout, '已推到遠端')
    r = novel(b, '繼續')
    check(r.returncode == 0 and any(c.startswith(W2) for c in chapters(b)), '之後正常寫第 2 章')

    # 場景 B：寫手還沒落盤就被殺（沒有正文）→ 續跑補不了 → 重寫第 1 章清掉重來
    print('B. 寫手還沒落盤就被殺（沒有正文）')
    b = new_repo(tmp, 'b')
    N, W, W2 = at(b)
    run_and_kill(b, 'plan')
    check(exists(b, '章节', W, '进行中') and not any(c.startswith(W) for c in chapters(b)), '標記在、沒有正文')
    r = novel(b, '繼續')
    check(r.returncode == 3 and f'重寫第{N}章' in r.stderr, '再跑原指令被擋住，提示用重寫：' + r.stderr.strip().split('\n')[-1])
    r = novel(b, '--續跑')
    check(r.returncode == 3 and f'重寫第{N}章' in r.stderr, '--續跑 補不了，提示用重寫')
    check(exists(b, '章节', W, '进行中'), '補不了時標記還在')
    r = novel(b, f'重寫第{N}章 從頭來')
    check(r.returncode == 0, f'重寫第 1 章走完（實際 {r.returncode}）\n{r.stdout[-400:]}{r.stderr[-300:]}')
    check(any(c.startswith(W) for c in chapters(b)) and not exists(b, '章节', W, '进行中'), '重寫後正文在、標記已清')
    check(any(d.endswith('_未完成') for d in os.listdir(os.path.join(b, '旧版'))), '未完成的工作區收進了 旧版/')

    # 場景 C：舊版腳本斷掉的章（沒有標記、沒有 .guard.meta）→ --續跑 1 補標記，守衛不可信就不亂提交
    print('C. 舊版腳本斷掉的章（沒有標記和守衛 meta）')
    b = new_repo(tmp, 'c')
    N, W, W2 = at(b)
    intent = text(b, '作者意图.md')
    run_and_kill(b, 'write')
    os.remove(os.path.join(b, '章节', W, '进行中'))
    os.remove(os.path.join(b, 'logs', '.guard.meta'))
    r = novel(b, '--續跑')
    check(r.returncode == 0 and '沒有「進行中」標記' in r.stdout and '--續跑' not in r.stderr, '不給章號時不動手')
    r = novel(b, '--續跑', str(N))
    check(r.returncode == 0, f'--續跑 1 走完（實際 {r.returncode}）\n{r.stdout[-500:]}{r.stderr[-400:]}')
    check('按工作區補了一個' in r.stdout and '不敢還原' in r.stderr, '補了標記，並說明守衛底稿不可信')
    files = tracked(b)
    check(any(f.startswith('正文/' + W) for f in files) and '记忆/进度.md' in files, '正文和記憶已提交')
    check('tools/make_ch.py' not in files and text(b, '作者意图.md') != intent, '越界改動沒被提交，也沒被亂還原')
    check(sh(b, 'git', 'show', 'HEAD:作者意图.md').stdout == intent, '遠端上的 作者意图.md 還是原樣')
    check(not exists(b, '章节', W, '进行中'), '走完後標記已刪')
    check('沒有提交' in r.stderr and 'make_ch.py' in r.stderr, '結束時列出了沒提交的改動')

    # 場景 D：正常跑完不留標記，也不把標記提交
    print('D. 正常跑完')
    b = new_repo(tmp, 'd')
    N, W, W2 = at(b)
    r = novel(b, '繼續')
    check(r.returncode == 0, f'正常跑完 exit 0（實際 {r.returncode}）')
    check(not exists(b, '章节', W, '进行中'), '沒留標記')
    check(sh(b, 'git', 'status', '--short').stdout.strip() == '', '工作區乾淨')
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if failures:
    print(f'{len(failures)} 項沒過')
    sys.exit(1)
print('全部通過')

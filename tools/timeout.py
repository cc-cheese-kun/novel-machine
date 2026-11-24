"""Run a command with a time limit, for machines without GNU timeout (stock macOS).

Usage: python3 tools/timeout.py SECONDS COMMAND ARGS...
On timeout, kills the command's whole process group and exits 124 (same as GNU
timeout); otherwise exits with the command's own code. Output goes straight to
the terminal.

限時跑一個命令，給沒有 GNU timeout 的機器用（macOS 默認沒有）。

用法：python3 tools/timeout.py 秒數 命令 參數...
超時就殺掉命令的整個進程組，退出碼 124（和 GNU timeout 一樣）；否則退出碼照命令的。
輸出直接接到終端，不經過這裡。
"""
import os
import signal
import subprocess
import sys


def main():
    if len(sys.argv) < 3 or not sys.argv[1].isdigit():
        print(__doc__, file=sys.stderr)
        return 125
    limit = int(sys.argv[1])
    # New process group (not a new session): on timeout we can kill the whole group,
    # and if someone kills our whole session from outside, the child still dies with it.
    # 另開進程組（不另開會話），超時能整組殺掉；外面殺整個會話時也照樣殺得到
    proc = subprocess.Popen(sys.argv[2:], preexec_fn=os.setpgrp)

    # Pass Ctrl-C / kill on to the child's group so it never outlives us.
    # 收到 Ctrl-C 或 kill 就轉給子進程組，不讓它比我們活得久。
    def forward(sig, _frame):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            pass
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, forward)
    try:
        return proc.wait(timeout=limit)
    except subprocess.TimeoutExpired:
        # Ask politely (TERM), wait 10 s, then force (KILL).  先 TERM，等 10 秒，再 KILL。
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(proc.pid, sig)
            except ProcessLookupError:
                break
            try:
                proc.wait(timeout=10)
                break
            except subprocess.TimeoutExpired:
                continue
        return 124


if __name__ == '__main__':
    sys.exit(main())

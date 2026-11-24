"""限時跑一個命令，給沒有 GNU timeout 的機器用（macOS 默認沒有）。

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
    # 另開進程組（不另開會話），超時能整組殺掉；外面殺整個會話時也照樣殺得到
    proc = subprocess.Popen(sys.argv[2:], preexec_fn=os.setpgrp)

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

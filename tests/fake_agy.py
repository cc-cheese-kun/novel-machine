#!/usr/bin/env python3
"""Fake `agy` (the writer CLI) for testing the pipeline without a real model.

It reads the role at the start of the prompt and writes the files that role
would write. FAKE_HANG=plan|write with FAKE_FLAG=FILE: drop a flag file and
sleep before (plan) or after (write) the writer saves, so a test can kill -9 it
to simulate a VM reboot. It deliberately goes out of scope once (edits chapter
31, leaves a script in tools/) to verify the scope guard restores it.
FAKE_SHORT=1 makes the first draft too short, to exercise the fix round.

假的 agy，只用來測流程：認提示開頭的角色，寫出對應的文件。
FAKE_HANG=plan|write 配 FAKE_FLAG=文件：在寫手落盤之前（plan）、或落盤之後（write）留下標記文件就睡著，給測試去 kill -9（模擬 VM 重啟）。
故意越界一次（改第 31 章、在 tools/ 留腳本），看守衛會不會還原。
FAKE_SHORT=1 時寫手第一稿故意寫短，測修稿。"""
import os, re, sys
args = sys.argv[1:]
prompt = args[args.index('-p') + 1]
root = args[args.index('--add-dir') + 1]
os.chdir(root)
m = re.search(r'第 (\d+) 章', prompt)
if not m:
    print('聊天：' + prompt[:40]); sys.exit(0)
n = int(m.group(1))
w = f'章节/第{n:03d}章'
han = '零一二三四五六七八九'
def hang():
    open(os.environ['FAKE_FLAG'], 'w').close()
    __import__('time').sleep(600)


if '【規劃師】' in prompt:
    assert os.path.exists(f'{w}/规划材料.md')
    if os.environ.get('FAKE_HANG') == 'plan':
        hang()
    bad = os.environ.get('FAKE_BAD_PLAN') and '上一版大綱沒過' not in prompt
    scenes = 3 if bad else 4
    title = '試跑' + ''.join(han[int(c)] for c in str(n))
    body = f'## 章名\n- {title}\n\n## 焦點\n- 改成：測試用的焦點，第{n}章後\n\n## 場次\n'
    kinds = ['日常', '大場面', '兩人', '收尾']
    body += ''.join(f'{i+1}. 【{kinds[i]}】中環｜下午｜一件事｜鐘｜吐槽\n' for i in range(scenes))
    body += '\n## 兩人的戲\n- 第三場，一起吃飯\n\n## 必須有\n- 讀者的走向\n\n## 不能有\n- 海上\n\n## 伏筆\n- 推進：伏筆 9\n\n## 結尾\n- 停在一杯茶上\n'
    open(f'{w}/大纲.md', 'w', encoding='utf-8').write(body)
    print('大綱寫好了')
elif '【寫手】' in prompt or '【修稿】' in prompt:
    if os.environ.get('FAKE_HANG') == 'plan' and '【寫手】' in prompt:
        hang()  # 還沒寫正文就被殺
    target = re.search(r'(正文/第\d+章_\S+?\.txt)', prompt).group(1)
    if '【寫手】' in prompt:
        target = target.replace('章名', '試跑' + ''.join(han[int(c)] for c in str(n)))
    assert os.path.exists(f'{w}/设定.md')
    g = __import__('glob').glob
    src = open((g('正文/第013章_*.txt') + g('往作/*/正文/第013章_*.txt') + g('tests/样本/第013章_*.txt'))[0], encoding='utf-8').read()
    extra = open((g('正文/第020章_*.txt') + g('往作/*/正文/第020章_*.txt') + g('tests/样本/第020章_*.txt'))[0], encoding='utf-8').read()
    if '【寫手】' in prompt:
        text = src if os.environ.get('FAKE_SHORT') else src + '\n\n' + extra[:4000].rsplit('。', 1)[0] + '。'
        # 越界：改別的章、在 tools/ 和根目錄留東西
        with open('作者意图.md', 'w', encoding='utf-8') as h: h.write('被覆蓋了')
        open('tools/make_ch.py', 'w').write('print(1)')
        open('scene1.txt', 'w').write('x')
    else:
        text = open(target, encoding='utf-8').read() + '\n\n' + extra[:4000].rsplit('。', 1)[0] + '。'
    import sys as _s; _s.path.insert(0, 'tools'); from check import FACE_SWITCH
    text = re.sub(r'沒有([^，。「」\n]{1,16})，(也)?沒有', r'少了\1，\2沒有', text)  # 第一部原文裡的總結句式，免得假稿被總結句檢查攔下
    text = re.sub(FACE_SWITCH, '', text)  # 第一部原文裡的換臉句，免得假稿被攔下
    text = re.sub(r'報銷|填表|審批|折舊|預算|發票|核銷|授權|核驗|責任報告|督察', '那筆錢', text)  # 第一部原文裡的公事詞，免得假稿被公事梗檢查攔下
    from gags import GAGS  # 假稿每章是同一段第一部原文，連章小梗檢查一定會攔，把這些梗詞抹掉
    for pattern in GAGS.values():
        text = re.sub(pattern, '那件事', text)
    open(target, 'w', encoding='utf-8').write(text)
    upd = (f'## 當前狀態\n\n- 對應章節：第{n}章\n- 時間：下午。\n- 地點：中環。\n- 傷勢：左肩貫穿傷癒合良好。\n- 概況：測試。\n\n'
           '## 誰知道什麼\n\n- 測試事實：子航、零知道。\n\n## 伏筆變動\n\n- 伏筆 9：推進。\n\n## 最新扣子\n\n- 測試扣子。\n')
    open('记忆/待更新.md', 'w', encoding='utf-8').write(upd)
    print(f'{target} 寫好了')
    if os.environ.get('FAKE_HANG') == 'write' and '【寫手】' in prompt:
        hang()  # 正文和待更新已落盤，進程被殺
else:
    print('聊天：' + prompt[:40])

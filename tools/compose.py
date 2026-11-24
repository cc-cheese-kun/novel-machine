"""The "composer": prepare per-chapter material for the writer model. Pure
script, no model call.

Usage: python3 tools/compose.py write N 'reader instruction'
1. Writes 章节/第NNN章/设定.md: the settings file trimmed for this chapter
   (drop sections for a later story period, drop the monster section on
   non-fight chapters, rotate small character habits).
2. Prints hint lines that bin/novel-call.sh appends to the writer's prompt:
   the next milestone, whether this chapter may contain a fight, what the
   previous chapter already did (scene order, opening, gags, recent places,
   titles, gear) so the writer does not repeat it.
Why a script and not more prompt rules: models follow "don't repeat the last
chapter" far better when they are told concretely what the last chapter was.

給寫手準備兩樣東西（純腳本，不調模型）：

用法：python3 tools/compose.py write N '讀者的指令'

1. 章节/第NNN章/设定.md：學院期剝掉執行官期才有的段落
2. 印出提示要加的【路標】（「繼續」時）和最近幾章的地點、章名

別的材料寫手照 AGENTS.md 自己讀（和第一部的寫法一樣）。
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from book import (FOCUS, FORESHADOW, INTENT, MILESTONES, PROGRESS, SETTING, SNAPSHOTS, STYLE,
                  bigrams, bullets, chapters, read, section, sections, title_of, workdir, write)
from gags import found as gags_found

# The writer reads only the last ~1500 characters of the previous chapter, never the whole book.
# 寫手只讀上一章末尾約 1500 字，不讀全書。
TAIL = 1500



def milestone(n):
    """Hint about the next reader-defined milestone in 路标.md.
    Hit it exactly on its chapter; before that, don't write it early and don't
    foreshadow it (models love to "warm up" a planned event several chapters ahead).
    路標提示：到那一章正面寫，之前不提前寫、不預熱。"""
    marks = []
    for line in read(MILESTONES).splitlines():
        m = re.match(r'\s*-\s*第0*(\d+)章\s*[：:]\s*(.+?)\s*$', line)
        if m and m.group(2).strip('…. '):
            marks.append((int(m.group(1)), m.group(2)))
    ahead = sorted(x for x in marks if x[0] >= n)
    if not ahead:
        return '沒有還沒到的路標，照當前焦點走。'
    at, what = ahead[0]
    if at == n:
        return f'這章就是讀者定的節點：「{what}」。把它寫成一場正面的戲，不靠匯報帶過。'
    if at - n <= 3:
        return f'讀者要在 {at - n} 章之後寫到「{what}」。這章不碰這個節點：不提前寫到，也不先替它鋪線索、預熱那種情緒，照當前焦點寫這章自己的事，留到那一章正面寫。'
    return f'讀者要在 {at - n} 章之後寫到「{what}」，還遠。照當前焦點寫，不要提前寫到，也不用每章往那裡鋪。'


def fight_hint(n, instruction):
    """Fights may be long but not frequent: only chapters tagged 【打怪】 in 路标.md fight.
    Returns the hint line telling the writer whether this chapter is a fight chapter.
    打架可以長、不可以密：只有路標標了【打怪】的章才打。"""
    fights = set()
    for line in read(MILESTONES).splitlines():
        m = re.match(r'\s*-\s*第0*(\d+)章\s*[：:].*【打怪】', line)
        if m:
            fights.add(int(m.group(1)))
    obey = '' if re.match(r'^(繼續|继续)', instruction) else '讀者的指令明說要打就照指令，'
    if n in fights:
        return '【打怪】這章是打怪章：一整章就打這一仗，從進場、試探、看出套路、吃虧、調整到抓住窗口，打長打透。只打這一隻，不加別的小怪。'
    ahead = sorted(k for k in fights if k > n)
    if ahead:
        return (f'【打怪】這章不打怪。{obey}不寫和怪物、敵人的戰鬥、追逐、槍戰，不派清怪任務（學院裡的比賽、對抗賽不算打怪；比賽過程要寫長寫細，一輪一輪寫出來，不要一句話交代結果）；'
                f'下一場仗在 {ahead[0] - n} 章之後，之前主線最多在日常裡露一點苗頭。')
    last = max((k for k in fights if k < n), default=0)
    if last and n - last < 6:
        return f'【打怪】這章不打怪。{obey}上一場仗才過去 {n - last} 章，寫日常和餘波。'
    return '【打怪】路標裡沒有標下一場仗。這章可以打一場，但只打一隻、打一整章；不打也行，照當前焦點。'


# A scene usually opens with a time word ("Morning, ...", "Next day, ..."); used to
# recover the previous chapter's scene order.  場次通常以時間詞開頭，用來還原上一章的場次順序。
SCENE_HEAD = r'^(?:清晨|早上|上午|正午|中午|午後|下午|傍晚|晚上|晚間|深夜|凌晨|午夜|週[一二三四五六日]|第二天)[^。\n]{0,30}。'


def last_chapter_hint(n):
    """Describe how the previous chapter went and where it stopped, so this one
    neither follows the same template (class -> canteen -> briefing -> test drive ->
    cooking -> bed) nor replays the same day.
    上一章怎麼走的、停在哪：免得每章同一個模子（上課→食堂→情報→試車→做飯→上樓），也免得同一天過兩遍。"""
    prev = chapters().get(n - 1)
    if not prev:
        return ''
    heads = []
    for line in read(prev).splitlines():
        m = re.match(SCENE_HEAD, line.strip())
        if m:
            heads.append(m.group(0).rstrip('。')[:30])
    tip = ''
    if heads:
        tip += '上一章的場次是：' + ' → '.join(heads) + '。這章不准照這個順序和這些地方再走一遍（不要又是上課、食堂、聽情報、試車、回家做飯、上樓看書那一套），換別的事、別的地方、別的時段。'
    time = re.search(r'-\s*時間[：:]\s*(.+)', section(read(PROGRESS), '當前狀態'))
    if time:
        tip += f'上一章停在「{time.group(1).strip()}」，這章從那之後開始，不准把同一天、同一段時間再過一遍；可以跳過幾天。'
    place = re.search(r'-\s*地點[：:]\s*(.+)', section(read(PROGRESS), '當前狀態'))
    if place and re.search(r'臥室|床', place.group(1)):
        tip += '上一章收在臥室床上，這章結尾換一個地方、換一件事收，不要又是兩人上床睡覺；也不要又安排四個人圍桌吃飯。'
    # Look only at the first few paragraphs; the word "professor" alone does not count
    # (it caused a false positive on chapter 6).
    # 只看開頭兩三段；「教授」不算（第 6 章開頭一句「古德里安教授塞給我的票」就被當成課堂開場）
    if re.search(r'教室|講台|上課|課上|課堂|點名', read(prev)[:300]):
        tip += '上一章是從課堂開場的，這章不准從課堂、被教授點名、粉筆頭砸人、在夢裡被吵醒開場；課堂戲全章最多一場。'
    prev_text = read(prev)
    if len(re.findall(r'賭|比賽|輸贏|較勁', prev_text)) >= 5 or prev_text.count('羅德里戈') >= 10:
        tip += '上一章有賭約、比賽或羅德里戈和子航鬥嘴，這章不寫這些，寫過日子的事（金羊毛會其他人當朋友出現可以）。'
    used = gags_found(prev_text)
    if used:
        tip += '上一章用過這些小梗：' + '、'.join(used) + '。這章一個都不用，笑點和小動作換這章自己的。'
    tip += '也別再走「一夥人出門→路上分頭→回家→兩個人單獨收尾」這個骨架，這章換一種走法。'
    tip += '結尾不要用「沒有警報，沒有任務」「平靜的日子在流淌」這類總結句收。'
    return '【' + tip + '】'


def fight_chapters():
    """Chapter numbers tagged 【打怪】 (fight) in 路标.md.  路標裡標了打怪的章號。"""
    fights = set()
    for line in read(MILESTONES).splitlines():
        m = re.match(r'\s*-\s*第0*(\d+)章\s*[：:].*【打怪】', line)
        if m:
            fights.add(int(m.group(1)))
    return fights


def setting_text(n=None):
    """Trim 设定.md for chapter n using HTML-comment markers in the file:
    <!-- 執行官期 --> later-period sections, <!-- 打怪 --> the monster section,
    <!-- 習慣 --> a list of small habits (only two per chapter, rotated).
    學院期不給執行官期才有的段落（<!-- 執行官期 --> 標著），免得寫手跑回分部；
    不打怪的章不給怪物那一節（<!-- 打怪 --> 標著），少讀一點，也免得日常章往打怪拐。"""
    text = read(os.path.join(SETTING, '设定.md'))
    if '學院期' in section(read(PROGRESS), '當前時期'):
        text = re.sub(r'<!-- 執行官期 -->.*?<!-- /執行官期 -->\n?', '', text, flags=re.S)
    if n is not None and n not in fight_chapters():
        text = re.sub(r'<!-- 打怪 -->.*?<!-- /打怪 -->\n?', '', text, flags=re.S)
    # Character habits: shown the full list, the writer mentions every item (chapter 1
    # used seven), so give two per chapter, rotating by chapter number.
    # 零的口味和習慣：寫手見到一整串就每樣點一遍（第 1 章點了七樣），每章只給兩條，按章號輪換
    def pick(m):
        items = [x for x in m.group(1).splitlines() if x.strip()]
        if n is None or len(items) <= 2:
            return '\n'.join(items) + '\n'
        k = (n * 2) % len(items)
        return '\n'.join((items + items)[k:k + 2]) + '\n'
    text = re.sub(r'<!-- 習慣 -->\n(.*?)\n<!-- /習慣 -->\n?', pick, text, flags=re.S)
    return re.sub(r'<!-- /?(執行官期|打怪) -->\n?', '', text)



    return {'wrap': '--wrap' in args, 'no_ling': '--no-ling' in args, 'long': '--long' in args}


# Gear model names (MCX, P320, UH-60...): used to stop the same gun or drone appearing
# every chapter.  裝備型號：大寫字母開頭帶數字或連字號（MCX、P320、UH-60），加幾個中文名
GEAR = (r'(?:SIG|HK|FN|Glock|CZ|Walther|Beretta|B&T|KRISS|Steyr|IWI|Barrett|Sako|Benelli|Mossberg|Remington|Taser|DJI)'
        r'\s?[A-Za-z0-9-]+(?:\s[A-Z0-9][A-Za-z0-9-]*)?|\b[A-Z]{1,4}-?\d{2,4}[A-Z0-9]*\b')


def compose(n, instruction):
    """Write the trimmed settings to the workspace and print all hint lines.
    學院期的設定剝掉執行官期段落，存到工作區；印出給提示用的路標和最近地點。"""
    write(os.path.join(workdir(n), '设定.md'), setting_text(n))
    hints = []
    # Give the milestone on rewrites too (including restarts after a crash): chapter 6
    # once lost a reader-defined plot point this way.
    # 重寫一章（包括沒跑完被收走重來的）也要給路標：第 6 章就這樣丟過讀者定的節點
    if re.match(r'^(繼續|继续|重寫這一章)', instruction):
        hints.append('【路標】' + milestone(n))
    hints.append(fight_hint(n, instruction))
    last = last_chapter_hint(n)
    if last:
        hints.append(last)
    places = []
    for k in range(max(1, n - 5), n):
        for line in read(os.path.join(SNAPSHOTS, f'第{k:03d}章后', '进度.md')).splitlines():
            if line.startswith('- 地點：'):
                places.append(line[5:].strip().rstrip('。')[:40])
                break
    titles = [title_of(p) for k, p in chapters().items() if k < n][-10:]
    tip = ''
    if places:
        tip += '最近幾章的地點：' + '／'.join(places) + '。這章換一個最近沒寫過的地方。'
    if titles:
        tip += '最近的章名：' + '、'.join(titles) + '，新章名不要跟這些重複或只換一個字。'
    if tip:
        hints.append('【' + tip + '】')
    used = []
    for k in range(max(1, n - 2), n):
        path = chapters().get(k)
        if path:
            for m in re.findall(GEAR, read(path)):
                if m not in used:
                    used.append(m)
    if used:
        hints.append('【最近兩章用過的裝備：' + '、'.join(used[:15]) + '。這章換別的，照 设定.md 的裝備庫挑。】')
    print('\n'.join(hints))
    return 0


def main():
    args = sys.argv[1:]
    if len(args) < 2 or args[0] != 'write' or not args[1].isdigit():
        print(__doc__)
        return 2
    rest = [a for a in args[2:] if not a.startswith('--')]
    return compose(int(args[1]), rest[0] if rest else '繼續')


if __name__ == '__main__':
    sys.exit(main())

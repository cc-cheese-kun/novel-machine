import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gags import found as gags_found

sys.stdout.reconfigure(encoding='utf-8')

BANNED = ['楚', '契約', '契约', '協議', '协议', '路明非', '舒棠', '程澄', '子涵', '子晏', '居然想哭', '這一刻他終於明白']
BACKSTAGE = ['會走的鐘', '鐘在它', '鐘在牠', '鐘在他', '這場戲的鐘', '伏筆', '伏笔', '主角團', '硬規則', '暫時壓著不寫', '暫不寫', '讀者', '專屬名刀', '人設', '子航.md', '设定.md', '封存']
# 楚子航的標誌物：模型看到「子航」會自動套成楚子航，這些一個都不准出現
# 凱撒的標誌物：競爭對手羅德里戈是原創人物，不是凱撒
CAESAR_TRAITS = ['加圖索', '諾諾', '沙漠之鷹', '學生會', '凱撒']
# 人名、地名寫錯：模型常寫錯，寫錯一次就判不過
WRONG_NAMES = {'羅德利戈': '羅德里戈', '罗德里戈': '羅德里戈', '罗德利戈': '羅德里戈', '伊莎貝爾': '伊莎貝拉',
               '安大略湖': '密歇根湖（學院在芝加哥郊外）'}
CHU_TRAITS = ['村雨', '君焰', '暴血', '爆血', '獅心會', '楚天驕', '夏彌', '仕蘭', '奧丁', '邁巴赫', '烈焰之刀', '高架橋上的雨夜']
# 子航被寫成冷面：這些詞和「子航」或「他」同句出現就算一次
COLD_VOICE = r'聲音冷靜|語氣平緩|聽不出情緒|神色平靜|面不改色|冷靜地|毫無波動|沒有任何放鬆|眼神微冷|眼神微凝|眼神微微一沉|淡淡地|語氣平淡|聲音平緩|聲音平靜|聲音低沉|神色沒有|面無表情|冷冷地|眼神平靜|不帶感情|一言不發'
COLD_LIMIT = 4
SCI_FI = ['全息', '量子', '光束', '能量護盾', '虛擬投影', '三維球形', '數據瀑布']
CLICHES = ['嘴角勾起', '嘴角牽起', '弧度', '一抹', '瞳孔微縮', '瞳孔驟縮', '倒吸', '冷笑', '不可遏制', '如同鬼魅', '宛如', '彷彿', '鋼澆鐵鑄', '玩味']
# 每千字上限，超过说明用词在打卡
RATE_LIMITS = {'極': 3.0, '瞬間': 1.0, '甚至': 1.0, '乾脆': 0.8, '精準': 0.6, '死死': 0.4, '猛地': 0.8, '像是': 2.0}
SIMPLIFIED = set(
    '们这说时对发经过没进还会个为学国给长开关门问见现里后动车东两从让应声实头间'
    '刚吗么们样么钟铁钱银锁锅镜错长队阶际难项须顺预领头题颜风飞饭馆马驾验鱼鸟龙'
    '爱罢备贝笔边变标别宾补参层产尝场彻陈称迟冲虫处传闯词从达带单当党导灯敌递'
    '电动断对吨夺儿尔发飞废费纷坟奋愤丰凤妇复盖赶钢纲岗个巩构购顾关观广归龟柜'
    '过汉号轰后护华画话怀坏欢环还换唤黄挥辉汇会获机鸡积极级挤记际继价驾坚间艰'
    '拣检减见舰将奖讲酱胶阶节劲进尽惊竞旧剧据绝军开垦恳块宽矿亏扩腊蜡来栏蓝'
    '劳乐类离礼丽历连联炼粮两辆疗辽猎临邻铃灵岭刘龙楼录陆驴虑乱论罗骡妈蚂买卖'
    '满猫贸门梦弥觅绵庙灭鸣谋亩脑闹内拟鸟宁农浓诺欧盘赔喷鹏骗飘频凭苹扑铺齐骑岂'
    '启气迁签浅枪墙抢桥窍亲轻倾庆穷区驱权劝确让扰热认荣软锐闰润伞丧扫杀纱晒伤'
    '赏烧绍摄设绅审婶渗声胜湿师诗时实势视试适释书输术树帅双谁顺说丝饲耸诉肃虽'
    '随岁孙态坛叹汤烫涛讨腾誊题体屉条铁听厅头图团椭袜湾弯网韦违围为伟纬卫稳问窝'
    '无吴务雾牺习戏细虾吓鲜闲显险现献县线宪厢镶乡详响项萧销晓协胁写泻谢锌兴'
    '许续绪轩悬选学寻训讯询压鸦鸭哑亚严盐艳验阳养样钥药爷页业叶医仪遗亿忆艺议'
    '阴荫隐樱鹰营蝇赢拥佣优忧邮犹鱼渔语誉渊园员圆远愿约跃钥云运酝杂灾载赃'
    '脏凿枣灶责择则贼赠闸诈斋债毡盏斩辗崭栈战张涨帐账胀赵这针侦诊镇阵争证'
    '织职执纸挚掷质钟终种肿众诸烛嘱瞩铸驻专砖转赚桩装妆壮状锥浊总纵钻'
)

# 死亡相關：主角團、配角、背景人物都不寫死亡。「死侍」「死死」「焊死」不在此列
DEATH = ['已經死了', '早就死了', '早死了', '去世', '過世', '逝世', '病逝', '歿', '殉職', '遇難',
         '身亡', '喪生', '陣亡', '斃命', '亡故', '死者', '屍體', '屍首', '遺體', '遺照', '遺孀', '遺言', '生前', '臨終']
# 結尾最後 200 字裡不准出現的昇華、總結字眼
SCENERY_END = r'窗外|陽光|晨光|夕陽|落日|月光|光暈|夜色|微風|秋風|晚風|樹冠|林梢|湖面|松濤|落葉|日光|暮色|樹影|燈火'
ENDING_BANNED = ['終於明白', '終於懂', '這就是', '從此', '從今以後', '命運', '意義', '或許', '也許', '慢慢洇開']
# 傷型詞：章節裡出現、但 进度.md「傷勢」一行沒有的，提示核對
WOUND_TYPES = ['貫穿傷', '擦傷', '刀傷', '槍傷', '燒傷', '凍傷', '骨折', '脫臼', '血槽', '割傷', '咬傷', '挫傷', '內傷', '縫針', '縫線']
# 外貌套話：零的髮色眸色、皮膚、手，每章都在重複
LOOKS = r'白皙|冰藍色的眸|眸子|淺金色的長髮|淺金色長髮|修長的手指|細膩的皮膚|溫熱的大手|寬厚的手掌|纖細的手|薄唇|精緻的|清冷的|清澈的眼'
LOOKS_LIMIT = 6
CROWD = r'整齊劃一|哄堂大笑|鴉雀無聲|全場譁然|一片譁然|唾沫橫飛|手舞足蹈|近乎癲狂|發出一聲慘叫|面面相覷|齊刷刷|倒抽一口冷氣'
ADVERBS = r'輕輕|淡淡|穩穩|緩緩|微微|漫不經心|慢條斯理'
FACE_SWITCH = r'(笑意|笑容|戲謔|散漫|懶散|漫不經心|玩世不恭)[^。，]{0,6}(收斂|斂去|褪去|消失|一收|收了起來)|收斂了[^。，]{0,6}(笑|戲謔|散漫|懶散|漫不經心)|神色一(凜|正|沉|肅)|臉色一(沉|冷)|眼神(一冷|驟冷|一凜|冷了下來|沉了下來|森寒)|深邃而冷峻|變得冷峻|眼神[^。，]{0,8}(變了|變得|徹底變)|氣勢[^。，]{0,4}(一變|驟變|陡變)|像換了(一個|個)人|判若兩人|整個人的氣質[^。，]{0,6}變'
# 裝備統稱，和「段落裡有型號」：英文字母加數字、全大寫縮寫、某年款、某式
GEAR = r'突擊步槍|自動步槍|狙擊步槍|衝鋒槍|霰彈槍|機槍|無人機|裝甲車|戰鬥機|運輸機|直升機|導彈|榴彈|火箭筒|潛艇|快艇'
MODEL = r'[A-Za-z]+[-\s]?\d+|[A-Z]{2,}|\d{2,4}年款|\d+式'
# 參數：型號、數值加單位
SPECS = r'[A-Z]{1,5}-?\d{1,4}[A-Z]?|\d+(?:\.\d+)?\s*(?:毫米|公分|公斤|噸|節|浬|馬力|千瓦|赫茲|轉|公升|毫升|度|兆帕|帕|伏|安培|倍)'
MIN_CHARS = 9000
MAX_CHARS = 15000
TARGET_CHARS = 10000


def count_chars(text):
    return len(re.findall(r'[一-鿿]', text))


CN_DIGITS = {'零': 0, '〇': 0, '一': 1, '二': 2, '兩': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
TIME_RE = re.compile(r'(凌晨|清晨|早上|上午|中午|下午|傍晚|晚上|深夜|半夜)?([零〇一二兩三四五六七八九十]{1,3}|\d{1,2})點(半|整|([零〇一二三四五六七八九十]{1,3}|\d{1,2})分)?')


def cn_number(word):
    if word.isdigit():
        return int(word)
    if '十' in word:
        left, _, right = word.partition('十')
        return (CN_DIGITS.get(left, 1) if left else 1) * 10 + (CN_DIGITS.get(right, 0) if right else 0)
    value = 0
    for char in word:
        value = value * 10 + CN_DIGITS.get(char, 0)
    return value


def narration_times(text):
    """只看敘述句裡的鐘點（對話裡常說未來的時間），換成當天分鐘數。"""
    times = []
    last_period = None
    for line in text.splitlines():
        line = re.sub(r'「[^」]*」', '', line)
        for match in TIME_RE.finditer(line):
            period, hour_word, minute_part, minute_word = match.groups()
            if not period and not minute_part:
                continue  # 單獨的「一點」「零點」多半是「一點點」「零點四秒」
            hour = cn_number(hour_word)
            if hour > 24:
                continue
            if period:
                last_period = period
            elif last_period in ('下午', '傍晚', '晚上', '深夜'):
                period = last_period
            if period in ('下午', '傍晚', '晚上', '深夜') and hour < 12:
                hour += 12
            if period == '中午' and hour < 6:
                hour += 12
            minute = 30 if minute_part == '半' else cn_number(minute_word) if minute_word else 0
            times.append((hour * 60 + minute, match.group(0)))
    return times


def repeated_phrases(text, size=14, limit=3):
    body = re.sub(r'[^一-鿿]', '', text)
    counts = {}
    for i in range(0, len(body) - size + 1):
        chunk = body[i:i + size]
        counts[chunk] = counts.get(chunk, 0) + 1
    return [chunk for chunk, n in counts.items() if n >= limit]


def sealed_keywords():
    """封存.md 裡每條線的「關鍵詞」，回傳 [(線名, 詞), ...]。"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result, current = [], None
    try:
        with open(os.path.join(root, '设定', '封存.md'), encoding='utf-8') as handle:
            for line in handle:
                if line.startswith('## '):
                    current = line[3:].strip()
                elif current and line.lstrip('- ').startswith('關鍵詞'):
                    words = re.split(r'[、，,\s]+', line.split('：', 1)[-1].strip())
                    result += [(current, word) for word in words if word]
    except OSError:
        pass
    return result


def wound_line():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(root, '记忆', '进度.md'), encoding='utf-8') as handle:
            for line in handle:
                if line.lstrip('- ').startswith('傷勢'):
                    return line
    except OSError:
        pass
    return None


def check(text, long_mode=False, no_ling=False, wrap=False, fed='', prev=''):
    problems = []
    warnings = []
    for word in DEATH:
        hits = text.count(word)
        if hits:
            problems.append(f'寫到死亡「{word}」出現 {hits} 次，改成失蹤、退居、沒回家一類')
    for word in CHU_TRAITS:
        hits = text.count(word)
        if hits:
            problems.append(f'寫成了楚子航：「{word}」出現 {hits} 次。子航不是楚子航，沒有言靈、沒有村雨，見 设定.md「子航不是楚子航」')
    for wrong, right in WRONG_NAMES.items():
        hits = text.count(wrong)
        if hits:
            problems.append(f'寫錯了：「{wrong}」出現 {hits} 次，應寫「{right}」')
    if '殿下' in text and '北冕' not in text:
        problems.append(f'「殿下」出現 {text.count("殿下")} 次：只有北冕基地的軍人這樣叫零，同學、老師、蘇恩曦、麻衣都叫「零」')
    for match in re.finditer(r'芬格爾[^。！？\n]{0,30}(?:肥|胖)|(?:肥|胖)[^。！？\n]{0,10}芬格爾', text):
        problems.append(f'芬格爾寫胖了：「{match.group(0)}」。他高個子、邋遢，不胖，見 设定.md「配角與對手」')
    for word in CAESAR_TRAITS:
        hits = text.count(word)
        if hits:
            problems.append(f'寫成了凱撒：「{word}」出現 {hits} 次。對手是羅德里戈和金羊毛會，見 设定.md「羅德里戈和金羊毛會」')
    for match in re.finditer(r'子航[^。！？\n]{0,20}言靈|言靈[^。！？\n]{0,8}子航', text):
        warnings.append(f'子航和言靈寫在一句裡：「{match.group(0)}」。子航沒有言靈，若寫他用言靈要改')
    cold = []
    for x in re.split(r'[。！？\n]', text):
        hit = re.search(COLD_VOICE, x) if '子航' in x else None
        if hit:
            cold.append(x[max(0, hit.start() - 12):hit.end() + 6])
    if len(cold) > COLD_LIMIT:
        warnings.append(f'子航被寫成冷面：冷描寫 {len(cold)} 處，上限 {COLD_LIMIT}，例：「{cold[0]}」。照 子航.md 改成他自己的口氣')
    elif len(cold) > 2:
        warnings.append(f'子航冷描寫 {len(cold)} 處，偏多，例：「{cold[0]}」')
    asks = len(re.findall(r'」子航問。', text))
    stiff = re.findall(r'子航(?:下令|叮囑道|匯報|沉聲道)', text)
    if asks >= 3:
        warnings.append(f'「……」子航問。出現 {asks} 次，子航只在提問，像審訊官；讓他問得帶態度')
    if stiff:
        warnings.append(f'公文腔「{stiff[0]}」等 {len(stiff)} 處，子航不這樣說話')
    narration = re.sub(r'「[^」]*」', '', text)
    bangs = narration.count('！')
    if bangs / max(count_chars(text) / 1000, 1) > 0.8:
        warnings.append(f'敘述句裡用了 {bangs} 個驚嘆號，旁白不喊，驚嘆號只留在對話裡')
    ling = len(re.findall(r'零(?![點下度])', text))
    if ling < 3 and not no_ling:
        problems.append(f'零整章只出現 {ling} 次，每章要有一段子航和零兩人的戲；讀者說了這章零不在場，就加 --no-ling 重跑，不要硬加零')
    together = [x for x in text.split('\n') if '零' in x and '子航' in x]
    medical = [x for x in together if re.search(r'傷口|繃帶|敷料|止血|測溫|體溫|注射', x)]
    if len(medical) > 3 and not no_ling:
        warnings.append(f'子航和零同框的段落裡 {len(medical)} 段在處理傷口，零不是護士，甜換別的入口')
    # 按段落找，不要求「子航」緊挨著動作：之前要求緊挨，模型就硬塞「，子航順著她…」湊檢查
    kind = re.compile(r'替她|給她|遞給她|幫她|讓著她|順著她|由著她|牽|拉住她|她的頭髮|給零')
    if not no_ling and not any('子航' in para and kind.search(para) for para in text.split('\n')):
        warnings.append('子航沒有主動對零好的地方，甜只有單向；照 子航.md「和零」加一處')
    plain = re.sub(r'「[^」]*」', '「」', text)
    doubled = [x.strip()[:30] for x in re.split(r'[。！？\n]', plain) if x.count('子航') >= 2]
    if len(doubled) >= 2:
        warnings.append(f'一句裡「子航」出現兩次 {len(doubled)} 處，例：「{doubled[0]}」；第二個改成「他」或刪掉')
    nick = text.count('小零')
    if nick > 4:
        warnings.append(f'「小零」出現 {nick} 次；子航平時叫她「零」，暱稱全章三四次就夠')
    boss = text.count('零長官')
    if boss >= 3:
        problems.append(f'「零長官」出現 {boss} 次；這種調侃全章最多一次，其餘改回「零」')
    elif boss == 2:
        warnings.append('「零長官」出現 2 次；全章最多一次')
    # XP-04 是純電車（设定.md）：同一段裡出現燃油車的東西就是寫錯了
    fuel = r'排氣管|排氣|渦輪增壓|雙渦輪|引擎|發動機|燃油|汽油|煤油|加油|油箱|點火開關|怠速|V8|V12'
    ev_wrong = [m.group(0) for para in text.split('\n') if 'XP-04' in para
                for m in re.finditer(r'(?<![沒冇無不])(%s)' % fuel, para)]
    if ev_wrong:
        warnings.append(f'XP-04 是純電車，同一段裡寫了「{"、".join(sorted(set(ev_wrong)))}」；聲音只寫電機、冷卻泵、輪胎，見 设定.md')
    # 人物不知道自己在小說裡：正文（標題行以外）不准出現章號和「上一章」這類說法
    body = text.split('\n', 1)[1] if text.startswith('第') else text
    meta = re.findall(r'第\s*[0-9０-９一二三四五六七八九十百]+\s*章|上一章|前一章|前幾章|前面幾章|下一章|本章|[一二兩三四五六七八九十幾0-9]+章之內', body)
    if meta:
        problems.append(f'正文裡寫了章號或「上一章」這類話：「{meta[0]}」等 {len(meta)} 處；人物不知道自己在小說裡，改成具體的時間或事件（例如「在老家那天」）')
    friends = '源稚生|烏鴉|昂熱|蘇恩曦|恩曦|麻衣|索科洛娃|戈爾傑耶夫|米沙'
    cowed = [m.group(0) for m in re.finditer(r'(%s)[^。！？\n]{0,25}(閉上了嘴|規規矩矩|不敢多|臉色發黑|臉色一白|縮了縮脖子|噤若寒蟬)' % friends, text)]
    if cowed:
        warnings.append(f'熟人被寫成怕子航的下人 {len(cowed)} 處，例：「{cowed[0]}」；熟人對他要隨性，見 子航.md「對熟人」')
    # 文風（只提醒）：Gemini 自己的網文腔，外貌套話和一段堆參數
    looks = re.findall(LOOKS, text)
    if len(looks) > LOOKS_LIMIT:
        top = sorted(set(looks), key=looks.count, reverse=True)[:4]
        warnings.append(f'外貌套話 {len(looks)} 處（{"、".join(top)}），上限 {LOOKS_LIMIT}；人物長相讀者早知道了，換成這一刻的動作')
    piled = [para.strip()[:24] for para in text.split('\n') if len(re.findall(SPECS, para)) >= 4]
    if piled:
        warnings.append(f'一段裡堆了四個以上參數 {len(piled)} 處，例：「{piled[0]}」；參數只留後面用得上的一個')
    # 一秒換臉：子航前一句嬉皮笑臉，下一句旁白宣佈他「笑意收斂、眼神一冷」
    faces = [x.strip()[:30] for x in re.split(r'[。！？\n]', re.sub(r'「[^」]*」', '', text))
             if re.search(FACE_SWITCH, x)]
    if len(faces) >= 1:
        problems.append(f'子航一秒換臉 {len(faces)} 處，例：「{faces[0]}」；正經起來寫在動作和話上（話變短、煙掐了），臉不換，露一手的時候也還是那副懶散樣，見 子航.md')
    # 東西沒名字：段落裡只有「突擊步槍」「無人機」這種統稱，沒有任何型號
    vague = sorted({w for para in text.split('\n') for w in re.findall(GEAR, para) if not re.search(MODEL, para)})
    if len(vague) >= 3:
        problems.append(f'裝備只寫了統稱：{"、".join(vague)}；第一次出場寫具體的現役型號（HK416、UH-60 這種），見 文风/卡片.md')
    elif vague:
        warnings.append(f'裝備只寫了統稱：{"、".join(vague)}；第一次出場寫具體型號')
    codes = re.findall(r'[A-Z]{2,}(?:-[A-Z0-9]{2,}){2,}', text)
    if len(codes) > 3:
        warnings.append(f'編號代碼念了 {len(codes)} 次（{"、".join(sorted(set(codes))[:3])}）；說一次就夠，之後用人話叫它')
    # 公事梗：報銷、填表、審批……讀者說每章都在吐槽這些
    office = re.findall(r'報銷|填表|審批|折舊|預算|發票|核銷|授權|核驗|責任報告|督察', text)
    if len(office) >= 4:
        problems.append(f'公事梗 {len(office)} 處（{"、".join(sorted(set(office)))}）；笑點從子航自己身上來（懶、出糗、嘴硬、被坑），不拿報銷、審批、督察這類公事寫戲，見 设定.md')
    elif len(office) >= 2:
        warnings.append(f'公事梗 {len(office)} 處（{"、".join(sorted(set(office)))}）；別每章都吐槽報銷審批')
    crowd = re.findall(CROWD, text)
    if len(crowd) >= 3:
        warnings.append(f'群體反應像動畫片 {len(crowd)} 處（{"、".join(sorted(set(crowd))[:4])}）；旁人是正常人，各忙各的，見 AGENTS.md 第 14 條')
    elif crowd:
        warnings.append(f'群體反應誇張：{"、".join(sorted(set(crowd)))}；旁人是正常人')
    adverbs = len(re.findall(ADVERBS, text))
    if adverbs / max(count_chars(text) / 1000, 1) > 2:
        warnings.append(f'「輕輕」「淡淡」這類副詞 {adverbs} 次，每千字超過 2 個；動作寫準了就不用副詞墊，見 文风/卡片.md')
    nar = [x for x in re.split(r'[。！？\n]', re.sub(r'「[^」]*」', '', text)) if count_chars(x) > 1]
    if nar and sum(map(count_chars, nar)) / len(nar) > 34:
        warnings.append(f'旁白平均一句 {sum(map(count_chars, nar)) // len(nar)} 字，偏長；長句蓄壓可以，但要長短交錯。拆句用逗號斷開，不要拿句號把一句話切碎')
    narration = re.sub(r'「[^」]*」', '', text)
    periods, commas = narration.count('。'), narration.count('，')
    if periods > 80 and periods > commas:
        problems.append(f'旁白句號 {periods} 個、逗號只有 {commas} 個：一句話被句號切成了碎片（「長髮挽在腦後。用一枚髮夾固定著。」）。'
                        '一個意思沒說完就用逗號接著，句號只放在一句話真正說完的地方')
    summary = re.findall(r'(?:^|(?<=[。！？\n]))\s*(沒有[^，。「」\n]{1,16}，(?:也)?沒有[^，。「」\n]{1,16})', narration, re.M)
    if summary:
        problems.append(f'總結句 {len(summary)} 處（「{summary[0]}……」）：旁白不替讀者總結「沒有任務沒有警報，只有……」，刪掉，停在動作或對白上')
    # 蘇恩曦、麻衣和零是平輩，只叫「零」或外號「三無」；「零師妹」是芬格爾的叫法
    for para in text.split('\n'):
        for quote in re.findall(r'「[^」]*零師妹[^」]*」', para):
            if re.search(r'蘇恩曦|麻衣|薯片|長腿', para) and '芬格爾' not in para:
                problems.append(f'蘇恩曦或麻衣叫零「零師妹」：「{quote[:24]}」；她們是平輩，叫「零」或「三無」，見 设定.md')
    # 上一章用過的小梗這章又用：連用一兩個提醒，三個以上判不過
    if prev:
        again = sorted(set(gags_found(prev)) & set(gags_found(text)))
        if len(again) >= 3:
            problems.append(f'上一章的小梗這章又用了 {len(again)} 個（{"、".join(again)}）；同一個梗不連著兩章用，換這章自己的笑點和小動作，見 规则.md')
        elif again:
            warnings.append(f'上一章的小梗這章又用了：{"、".join(again)}；同一個梗不連著兩章用')
    if fed:
        plain = lambda t: re.sub(r'[^一-鿿]', '', t)
        source, body = plain(fed), plain(text)
        chunks = {source[i:i + 12] for i in range(len(source) - 11)}
        copied = sorted({body[i:i + 12] for i in range(len(body) - 11)} & chunks)
        if copied:
            warnings.append(f'照抄了喂進去的文風段落：「{copied[0]}」等 {len(copied)} 處，那些段落只學寫法')
    wrap_words = re.findall(r'落下了?帷幕|畫上了?句號|塵埃落定|標誌著這場|至此徹底|結案報告|已經?徹底崩潰', text)
    if not wrap and (wrap_words or re.search(r'完結|終章|大結局', text[:40])):
        warnings.append(f'像在寫全書完結：{"、".join(sorted(set(wrap_words))) or "章名"}；讀者沒說要結局就別收線，伏筆要在戲裡收，見 规则.md「不要自己寫完結」')
    for thread, word in sealed_keywords():
        hits = text.count(word)
        if hits:
            problems.append(f'寫到了封存的{thread}：「{word}」出現 {hits} 次，這條線讀者還沒讓寫')
    tail = text.rstrip()[-200:]
    scenery = re.findall(SCENERY_END, text.rstrip()[-150:])
    if len(scenery) >= 3:
        problems.append(f'結尾又收在窗外的景上（{"、".join(scenery)}）；換一種收法：一句對白、一個動作、一個沒說完的念頭、一個小鉤子，見 规则.md')
    elif len(scenery) == 2:
        warnings.append(f'結尾偏景物收尾（{"、".join(scenery)}），別每章都這樣收')
    for word in ENDING_BANNED:
        if word in tail:
            warnings.append(f'結尾昇華「{word}」，結尾停在動作、對視或靜物上')
    ending = text.rstrip()[-1:] if text.strip() else ''
    if ending and ending not in '。」！？…』）—':
        problems.append(f'結尾停在「{text.rstrip()[-10:]}」，像是沒寫完，補完最後一句')
    times = narration_times(text)
    for (before, label_a), (after, label_b) in zip(times, times[1:]):
        if after < before and before - after < 12 * 60:
            warnings.append(f'時間倒流：「{label_a}」之後出現「{label_b}」，核對時間線')
    repeats = repeated_phrases(text)
    if repeats:
        warnings.append(f'同一段話重複 3 次以上：「{repeats[0]}」等 {len(repeats)} 處，刪掉重複的')
    wounds = wound_line()
    if wounds:
        for word in WOUND_TYPES:
            if word in text and word not in wounds:
                warnings.append(f'傷型「{word}」不在 进度.md 傷勢裡，若是主角的傷要改回原傷型')
    for word in BANNED:
        hits = text.count(word)
        if hits:
            problems.append(f'禁用詞「{word}」出現 {hits} 次')
    for label, words in (('後台信息漏進正文', BACKSTAGE), ('科幻詞', SCI_FI), ('套話', CLICHES)):
        for word in words:
            hits = text.count(word)
            if hits:
                warnings.append(f'{label}「{word}」出現 {hits} 次')
    fullwidth = re.findall(r'[０-９Ａ-Ｚａ-ｚ]', text)
    if fullwidth:
        warnings.append(f'全形英數 {len(fullwidth)} 個，改成半形')
    thousands = max(count_chars(text) / 1000, 1)
    for word, limit in RATE_LIMITS.items():
        hits = text.count(word)
        if hits / thousands > limit:
            warnings.append(f'「{word}」用了 {hits} 次，上限每千字 {limit} 次')
    # 「公里」「英里」「海里」「里程」「鄰里」裡的「里」繁體本來就這麼寫
    scan = re.sub(r'(公|英|海|千|萬|鄰|故|鄉|德)里|里程|里數', '', text)
    found = sorted({char for char in scan if char in SIMPLIFIED})
    if found:
        problems.append('疑似簡體字：' + ''.join(found))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    separators = sum(1 for line in lines if re.fullmatch(r'[-—–*＊=~·•]{3,}', line))
    if separators > 2:
        warnings.append(f'分界線 {separators} 道，上限 2 道')
    total = count_chars(text)
    if total < MIN_CHARS:
        problems.append(f'字數 {total}，低於 {MIN_CHARS}；加一到兩場有事發生的戲，不要拉長已寫的場')
    elif total < TARGET_CHARS:
        warnings.append(f'字數 {total}，剛過底線；目標 {TARGET_CHARS} 到 {MAX_CHARS}，{MIN_CHARS} 是底線不是目標')
    if total > MAX_CHARS and not long_mode:
        warnings.append(f'字數 {total}，高於 {MAX_CHARS}')
    half = len(text) // 2
    first, second = count_chars(text[:half]), count_chars(text[half:])
    if first and second / first < 0.8:
        warnings.append(f'後半明顯縮水：前半 {first} 字，後半 {second} 字')
    return total, problems, warnings


def main():
    args = sys.argv[1:]
    long_mode = '--long' in args
    no_ling = '--no-ling' in args
    wrap = '--wrap' in args
    fed = ''
    if '--fed' in args:
        i = args.index('--fed')
        try:
            with open(args[i + 1], encoding='utf-8') as handle:
                fed = handle.read()
        except (IndexError, OSError):
            pass
        del args[i:i + 2]
    args = [arg for arg in args if arg not in ('--long', '--no-ling', '--wrap')]
    if len(args) != 1:
        print('用法：python3 tools/check.py [--long] 章節文件')
        print('  --long：讀者說了「寫多點」時用，不設字數上限')
        print('  --no-ling：讀者說了這章零不在場時用，不查零的出場和甜')
        print('  --wrap：讀者說了這章把劇情寫完、不留扣子時用，不查完結腔')
        print('  --fed 文件：這章喂進去的文風段落，查有沒有照抄')
        return 2
    with open(args[0], encoding='utf-8') as handle:
        text = handle.read()
    prev = ''
    m = re.match(r'第(\d+)章', os.path.basename(args[0]))
    if m:
        folder = os.path.dirname(os.path.abspath(args[0]))
        want = f'第{int(m.group(1)) - 1:03d}章'
        for name in sorted(os.listdir(folder)):
            if name.startswith(want) and name.endswith('.txt'):
                with open(os.path.join(folder, name), encoding='utf-8') as handle:
                    prev = handle.read()
                break
    total, problems, warnings = check(text, long_mode, no_ling, wrap, fed, prev)
    print(f'字數：{total}')
    for problem in problems:
        print('FAIL', problem)
    for warning in warnings:
        print('WARN', warning)
    if not problems:
        print('PASS')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())

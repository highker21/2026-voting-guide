import json,os,re
SC='/private/tmp/claude-501/-Users-highker-claudecode/448a02b8-57b3-449e-a12d-74a66c9bd512/scratchpad/'
BAD=re.compile(r'之子|之女|配偶|丈夫|太太|妻子|父親|母親|兒子|女兒|胞妹|胞弟|胞姊|胞兄|外甥|姪|前科|判刑|涉嫌|涉案|起訴|定讞|性騷擾|貪污|賄選|酒駕|收押|羈押|偵辦')
SAFE_NOTE={'林聖峰':'依2022年里長公報之姓名、行政區與所屬團體比對，無2026年報導可再核對','黃麗香':'依2018年市議員公報之姓名、行政區比對','陳又新':'公報為2018年填報，當時登記推薦政黨為社會民主黨','謝閔弘':'學歷經歷取自2022年里長選舉公報','紀建漢':'部分項目取自2022年里長選舉公報','李易儒':'部分項目取自2022年里長選舉公報','賴俊翰':'學歷依本人更正後說法', '侯陸太':'資料取自2023年立委登記報導，與2026年參選人是否同一人未完全確認','李秉倫':'學歷報導用語不一（行政管理學系碩士／公共行政碩士）','蕭漍華':'碩士報導稱預計2026年9月取得','周宏昌':'職稱取自2023年報導'}
DROP={'陳力新'}
def merge(extra,city):
    p=SC+f'{city}_news.json'
    if not os.path.exists(p): return
    dropped=[]
    for n,v in json.load(open(p)).items():
        k=re.sub(r'[A-Za-z．\.].*','',n)
        if k in extra: continue
        items=[]
        if k in DROP: v={'items':[]}
        for i in v['items']:
            if BAD.search(i[0]): dropped.append((k,i[0])); continue
            items.append(tuple(i))
        note=SAFE_NOTE.get(k,'')
        if not items: note='查無公開學經歷'
        elif not note and not any(re.search(r'畢業|碩士|博士|學士|大學|學院|學系|研究所|高中|專科|國中',i[0]) for i in items): note='未查得學歷'
        extra[k]={'items':items,'note':note}
    if dropped: print('dropped',city,dropped)

import json,re
from build import ROOT
RAW=ROOT+'crawler/raw/bio_council/'
def norm(n): return re.sub(r'[\s　]','',n).replace('黄','黃').replace('(歿)','')
S3=re.compile(r'議員|議長|立法委員|立委|鄉長|鎮長|市長|區長|縣長|里長|代表|局長|處長|主委|主任委員|秘書長|執行長|主任|總幹事|黨部|黨團|召集人|副秘書|常務')
S2=re.compile(r'秘書|助理|特助|理事長|會長|校長|教授|講師|律師|醫師|董事長|總經理|記者|主持人|創辦|創會|顧問|發言人')
def pick_exp(items,k=4):
    items=[x for x in items if x and len(x)<=60]
    sc=[(3 if S3.search(x) else 2 if S2.search(x) else 1) for x in items]
    order=sorted(range(len(items)),key=lambda i:(-sc[i],i))[:k]
    return [items[i] for i in sorted(order)]
def edu_score(x):
    for p,s in [(r'博士',9),(r'碩士|研究所|EMBA|碩專|在職專班',8),(r'學士|大學|學院|系|學系',6),(r'專科|二專|五專|三專|專',5),(r'高中|高工|高商|高職|高級|中學|女中|商工|工商|工農|家商',4),(r'國中|初中|國民中學',3),(r'國小|國民小學',2)]:
        if re.search(p,x): return s
    return 1
def pick_edu(items,prefer_first=True):
    items=[x for x in items if x]
    if not items: return []
    best=max(edu_score(x) for x in items)
    c=[x for x in items if edu_score(x)==best]
    return [c[0] if prefer_first else c[-1]]

def clean_item(t):
    t=re.sub(r'^\s*[\(（]?\d{1,2}\s*[\.．、\)）]\s*','',t.strip())
    t=re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff、，（）])','',t)
    t=re.sub(r'(?<=[、，])\s+','',t)
    return t.strip().rstrip('。；;，,')

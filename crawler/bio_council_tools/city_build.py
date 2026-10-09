import json,sys,re,os
from build import *
from official import *
# 各縣市 official 來源載入
def load_official(city):
    out={}
    if city=='taipei':
        for s,v in json.load(open(RAW+'tp/all.json')).items():
            out[norm(v['name'])]=dict(edu=v['edu'],exp=v['exp'],first=True,title=f"臺北市議會 現任議員 {v['name']}",url=f'https://www.tcc.gov.tw/Councilor_Content.aspx?n=13898&s={s}')
    elif city=='taichung':
        for k,v in json.load(open(RAW+'tc/all.json')).items():
            z,c=k.split('_')
            out[norm(v['name'])]=dict(edu=v['edu'],exp=v['exp'],first=False,title=f"臺中市議會 議員資訊 {v['name']}",url=f'https://www.tccc.gov.tw/main.asp?uno=14&cno={c}&zno={z}')
    elif city=='tainan':
        for m,v in json.load(open(RAW+'tn/all.json')).items():
            out[norm(v['name'])]=dict(edu=v['edu'],exp=v['exp'],first=False,title=f"臺南市議會 議員資訊網 {v['name']}",url=f'https://www.tncc.gov.tw/councilorpage.asp?mainid={m}')
    elif city=='keelung':
        for l,v in json.load(open(RAW+'kl/all.json')).items():
            out[norm(v['name'])]=dict(edu=[],exp=v['exp'],first=True,title=f"基隆市議會 議員資訊 {v['name']}",url=v['url'])
    return out
def official_entry(o):
    items=[clean_item(x) for x in pick_edu(o['edu'],o['first'])+pick_exp(o['exp'],4 if o['edu'] else 5)]
    items=[x for x in items if x]
    return [dict(text=t,tier='official',src_title=o['title'],src_url=o['url'],src_date='') for t in items]
def keyn(n): return norm(re.sub(r'[A-Za-z．\.].*','',n)).replace('啓','啟')
def find(off,name):
    k=keyn(name); 
    idx={keyn(n):o for n,o in off.items()}
    return idx.get(k)

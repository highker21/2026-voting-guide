import json,os,re,urllib.parse,sys
sys.path.insert(0,os.path.dirname(__file__))
ROOT='/Users/highker/claudecode/repos/2026-voting-guide/'
OUT=ROOT+'crawler/bio_council.json'
BASE='https://bulletin.cec.gov.tw/'
def bulletin(year,city_dir,fname,title):
    p=f'01選舉公報/05直轄市議員/{year}年/{city_dir}/{fname}'
    return dict(src_title=title,src_url=BASE+urllib.parse.quote(p),src_date={'111':'2022-11-26','107':'2018-11-24'}[year])
def mk(items,src,tier='official'):
    return [dict(text=t,tier=tier,**src) for t in items]
def load(): 
    return json.load(open(OUT)) if os.path.exists(OUT) else {}
def save(d): json.dump(d,open(OUT,'w'),ensure_ascii=False,indent=1)
def distkey(rname): return re.sub(r'^.*?議員\s*','',rname)

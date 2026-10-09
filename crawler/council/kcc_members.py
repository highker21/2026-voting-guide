"""高雄市議會：逐位現任議員抓 Frame_Councilor（提案/質詢列名）與 DealData（市政總質詢）原始頁，存 raw。"""
import sys,os,json,urllib.parse
sys.path.insert(0,os.path.dirname(__file__))
from kcc_lib import *
R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/高雄市/'
os.makedirs(R+'frames',exist_ok=True); os.makedirs(R+'deal',exist_ok=True)
inc=json.load(open(R+'../incumbents.json'))['高雄市']
ALIAS={'高忠德Takiludun．Anu':'高忠德'}
for n in inc:
    c=ALIAS.get(n,n); q=urllib.parse.quote(c)
    for kind,url in [('frames','https://cissearch.kcc.gov.tw/Frame_Councilor.aspx?cname='+q),('deal','https://cissearch.kcc.gov.tw/System/MunicipalQuestion/DealData.aspx?councilorfullname='+q)]:
        f=R+kind+'/'+c+'.html'
        if os.path.exists(f) and os.path.getsize(f)>2000: continue
        open(f,'w').write(get(url))
    print(c,flush=True)

"""臺北市議會議案進階查詢：逐位現任議員查提案者（結案屆次=第14屆 與 未結案 兩種條件取聯集），存 raw。"""
import sys,os,json; sys.path.insert(0,os.path.dirname(__file__))
from tcc_lib import *
R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/臺北市/'
inc=json.load(open(R+'../incumbents.json'))['臺北市']
out=json.load(open(R+'rows.json')) if os.path.exists(R+'rows.json') else {}
for n in inc:
    if n in out: continue
    ma,a=parse(query(n,{'useCOTE':'useCOTE','sele_DETR':'14'}))
    mb,b=parse(query(n,{'useunFi':'on','sele_DETR':'14'}))
    out[n]={'closed14':a,'unclosed':b,'ma':ma,'mb':mb}
    json.dump(out,open(R+'rows.json','w'),ensure_ascii=False)
    print(n,ma,mb and mb[0],flush=True)

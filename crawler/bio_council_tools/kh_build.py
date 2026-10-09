import json
from build import *
from kh_items import KH
EXTRA={}   # name -> (items, src, tier, note)  (web 來源補充)
try:
    from kh_extra import EXTRA
except ImportError: pass
d=json.load(open(ROOT+'data/kaohsiung.json'))
fn={'12':'高雄市第12.13.14.15選區.pdf'}
res={}
for r in d['races']:
    if not r['id'].startswith('council-'): continue
    dk=distkey(r['name']); res[dk]={}
    for c in r['candidates']:
        nm=re.sub(r'(Salizan|Takiludun).*','',c['name']).strip('．')
        e={'bio':[],'note':''}
        if nm in KH:
            f,items=KH[nm]
            fname=fn.get(f,f'高雄市第{f}選區.pdf')
            e['bio']=mk(items,bulletin('111','06高雄市',fname,f'中選會 高雄市議會第4屆議員選舉公報 第{f}選區' if f!='12' else '中選會 高雄市議會第4屆議員選舉公報 第12.13.14.15選區'))
        elif nm in EXTRA:
            items,src,tier,note=EXTRA[nm]
            e['bio']=mk(items,src,tier) if items else []; e['note']=note
        else: e['note']='查無公開學經歷'
        res[dk][c['name']]=e
out=load(); out['高雄市']=res; save(out)
print(sum(len(v) for v in res.values()),sum(1 for v in res.values() for e in v.values() if e['bio']))

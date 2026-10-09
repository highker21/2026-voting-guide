import json,subprocess,re,sys
sys.path.insert(0,'/Users/highker/claudecode/repos/2026-voting-guide/crawler/bio_council_tools')
from build import OUT
o=json.load(open(OUT))
cache={}
def ok(u):
    if u in cache: return cache[u]
    if 'bulletin.cec' in u: cache[u]=True; return True
    c=subprocess.run(['curl','-s','-o','/dev/null','-m','25','-L','-A','Mozilla/5.0','-w','%{http_code}',u],capture_output=True,text=True).stdout
    cache[u]=c.startswith('2') or c.startswith('3'); 
    if not cache[u]: print('BAD',c,u[:110])
    return cache[u]
from concurrent.futures import ThreadPoolExecutor
us=sorted({b['src_url'] for ds in o.values() for v in ds.values() for e in v.values() for b in e['bio']})
with ThreadPoolExecutor(4) as ex: list(ex.map(ok,us))
removed=0
for cn,ds in o.items():
    for dk,v in ds.items():
        for n,e in v.items():
            keep=[b for b in e['bio'] if ok(b['src_url'])]
            removed+=len(e['bio'])-len(keep); e['bio']=keep
            if not keep: e['note']='查無公開學經歷'
print('removed',removed)
json.dump(o,open(OUT,'w'),ensure_ascii=False,indent=1)

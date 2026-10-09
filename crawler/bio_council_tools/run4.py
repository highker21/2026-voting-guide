import sys,json
from city_build import *
CN={'taipei':'臺北市','taichung':'臺中市','tainan':'臺南市','keelung':'基隆市'}
def build(city):
    off=load_official(city); d=json.load(open(ROOT+f'data/{city}.json'))
    try:
        import importlib; ex=importlib.import_module(f'{city}_extra').EXTRA
    except ImportError: ex={}
    res={}
    for r in d['races']:
        if r['type']!='議員': continue
        dk=distkey(r['name']); res[dk]={}
        for c in r['candidates']:
            e={'bio':[],'note':''}
            o=find(off,c['name'])
            key=re.sub(r'[A-Za-z．\.].*','',c['name']).strip()
            if o: e['bio']=official_entry(o)
            elif key in ex:
                x=ex[key]; e['bio']=[dict(text=t,tier=tier,src_title=st,src_url=su,src_date=sd) for t,tier,st,su,sd in x['items']]; e['note']=x.get('note','')
                if not e['bio'] and not e['note']: e['note']='查無公開學經歷'
            else: e['note']='待補' if not c['incumbent'] else '查無公開學經歷'
            res[dk][c['name']]=e
    out=load(); out[CN[city]]=res; save(out)
    n=sum(len(v) for v in res.values()); f=sum(1 for v in res.values() for e in v.values() if e['bio'])
    print(city,n,f,'待補',sum(1 for v in res.values() for e in v.values() if e['note']=='待補'))
if __name__=='__main__':
    for c in sys.argv[1:]: build(c)

import re,sys,glob,os
def load(f):
    out=[]
    for l in open(f,encoding='utf8'):
        p=l.rstrip('\n').split('\t')
        if len(p)<5: continue
        out.append((int(p[0]),int(p[1]),int(p[2]),int(p[3]),p[4]))
    return out
def N(s): return re.sub(r'[\s　]','',s)
HE=lambda s: N(s) in('學歷','學歴','學麼','學厯')
HX=lambda s: N(s) in('經歷','經歴','經厯')
HP=lambda s: N(s)=='政見'
HN=lambda s: '號次' in N(s) and '姓名' in N(s)
def parse(f):
    R=load(f)
    he=[r for r in R if HE(r[4])]; hx=[r for r in R if HX(r[4])]; hp=[r for r in R if HP(r[4])]; hn=[r for r in R if HN(r[4])]
    cards=[]
    for e in he:
        xs=[x for x in hx if abs(x[1]-e[1])<30 and x[0]>e[0]]
        if not xs: continue
        x=min(xs,key=lambda x:x[0])
        ce=e[0]+e[2]/2; cx=x[0]+x[2]/2; b=(ce+cx)/2
        left=ce-(b-ce); right=cx+(cx-b)
        ps=[p for p in hp if p[1]>e[1]+30 and left<=p[0]+p[2]/2<=right]
        if not ps: continue
        p=min(ps,key=lambda p:p[1])
        ns=[n for n in hn if abs(n[1]-e[1])<30 and n[0]<e[0]]
        n0=max(ns,key=lambda n:n[0]) if ns else None
        cards.append(dict(y0=e[1],y1=p[1],left=left,b=b,right=right,n0=n0,he=e))
    # card bottom (for name search): next header row below in same column or page end
    for c in cards:
        below=[d['y0'] for d in cards if d['y0']>c['y0']+100 and abs(d['left']-c['left'])<60]
        c['ybot']=min(below) if below else 10**6
    res=[]
    for c in cards:
        nx0=(c['n0'][0]-40) if c['n0'] else c['left']-250
        names=[r for r in R if nx0<=r[0]<c['left']-10 and c['y0']<r[1]<min(c['ybot'],c['y0']+900) and r[3]>=28 and re.fullmatch(r'[一-鿿·．]{2,5}',N(r[4])) and '推薦' not in r[4] and '個人' not in r[4]]
        edu=sorted([r for r in R if c['left']<=r[0]<c['b']-5 and c['y0']+25<r[1]<c['y1']-10],key=lambda r:(r[1],r[0]))
        exp=sorted([r for r in R if c['b']-5<=r[0]<c['right'] and c['y0']+25<r[1]<c['y1']-10],key=lambda r:(r[1],r[0]))
        res.append(dict(name=N(names[0][4]) if names else '',cands=[N(n[4]) for n in names],edu=[r[4] for r in edu],exp=[r[4] for r in exp]))
    return res
if __name__=='__main__':
    for r in parse(sys.argv[1]): print(r)

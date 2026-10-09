import re,sys,json
W=re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>')
def load(f):
    s=open(f).read()
    pages=[]
    for pg in s.split('<page ')[1:]:
        pages.append([(float(a),float(b),float(c),float(d),t.replace('&amp;','&').replace('&lt;','<').replace('&gt;','>')) for a,b,c,d,t in W.findall(pg)])
    return pages
def header(ws):
    # find 學 歷 經 歷 政 見 pairs on same line near top
    cand={}
    for k in ('學','經','政','號','姓'):
        cand[k]=[w for w in ws if w[4]==k]
    for h in cand['學']:
        y=h[1]
        ex=[w for w in cand['經'] if abs(w[1]-y)<8]
        po=[w for w in cand['政'] if abs(w[1]-y)<8]
        if not ex or not po: continue
        l1=[w for w in ws if w[4]=='歷' and abs(w[1]-y)<8 and w[0]>h[0]]
        l1.sort()
        if len(l1)<2: continue
        e1=l1[0]; ex=ex[0]; e2=[w for w in l1 if w[0]>ex[0]]
        if not e2: continue
        po=po[0]
        ce=(h[0]+e1[2])/2; cx=(ex[0]+e2[0][2])/2
        nm=[w for w in cand['姓'] if w[0]<h[0] and abs(w[1]-y)<60]
        hao=[w for w in cand['號'] if w[0]<h[0] and abs(w[1]-y)<60]
        return dict(y=y,ce=ce,cx=cx,name_x=nm[0][0] if nm else None,hao_x=hao[0][0] if hao else None,pol_x=po[0])
    return None
def parse(f):
    pages=load(f); hd=None; rows=[]
    for pi,ws in enumerate(pages):
        h=header(ws) or hd
        if not h: continue
        hd=h
        b1=(h['ce']+h['cx'])/2
        el=h['ce']-(b1-h['ce']); xr=h['cx']+(h['cx']-b1)
        anchors=[w for w in ws if re.fullmatch(r'\d{1,2}',w[4]) and h['hao_x'] is not None and abs(w[0]-h['hao_x'])<20 and w[1]>h['y']+15]
        anchors.sort(key=lambda w:w[1])
        if not anchors: continue
        R=[dict(page=pi+1,num=a[4],y=(a[1]+a[3])/2,name=[],edu=[],exp=[]) for a in anchors]
        def near(y): return min(R,key=lambda r:abs(r['y']-y))
        for w in ws:
            if w[1]<h['y']+15: continue
            yc=(w[1]+w[3])/2; xc=(w[0]+w[2])/2
            if h['name_x'] and h['name_x']-15<=w[0]<=h['name_x']+25 and w[4] and not re.fullmatch(r'[\d年月日男女]',w[4]) and len(w[4])<=4:
                near(yc)['name'].append((w[1],w[4]))
            elif el-8<=w[0]<b1-5: near(yc)['edu'].append((w[1],w[0],w[4]))
            elif b1-5<=w[0]<xr-6 and w[2]<=xr+40 and len(w[4])<=40: near(yc)['exp'].append((w[1],w[0],w[4]))
        rows+=R
    out=[]
    for r in rows:
        nm=''.join(t for _,t in sorted(r['name']))
        def lines(items):
            items=sorted(items); L=[];cur=[];cy=None
            for y,x,t in items:
                if cy is None or abs(y-cy)>8:
                    if cur:L.append(''.join(cur))
                    cur=[t];cy=y
                else: cur.append(t)
            if cur:L.append(''.join(cur))
            return L
        out.append(dict(page=r['page'],num=r['num'],name=nm,edu=lines(r['edu']),exp=lines(r['exp'])))
    return out
if __name__=='__main__':
    for r in parse(sys.argv[1]): print(json.dumps(r,ensure_ascii=False))

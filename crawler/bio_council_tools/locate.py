import sys,json,glob,re
from build import ROOT
from cardparse import load,N
RAW=ROOT+'crawler/raw/bio_council/'
def targets(city,only_non_inc=True):
    d=json.load(open(ROOT+f'data/{city}.json')); out=[]
    for r in d['races']:
        if r['type']!='議員': continue
        for c in r['candidates']:
            if c['incumbent'] and only_non_inc: continue
            out.append((r['id'],c['name'],c['party']))
    return out
def build_index(prefixes):
    idx={}  # name-> list of (file,page,x,y,text)
    for f in sorted(glob.glob(RAW+'ocr/*.tsv')):
        b=f.split('/')[-1]
        if not any(b.startswith(p) for p in prefixes): continue
        R=load(f)
        for r in R:
            idx.setdefault(b,[]).append(r)
    return idx
def find(idx,name):
    nm=re.sub(r'[A-Za-z．\.].*','',name)
    hits=[]
    for b,R in idx.items():
        for r in R:
            t=N(r[4])
            if nm in t and len(t)<=len(nm)+8: hits.append((b,r[0],r[1],r[4]))
        # vertical stacked: consecutive single-char lines
        sing=sorted([r for r in R if len(N(r[4]))==1],key=lambda r:(round(r[0]/40),r[1]))
        for i,r in enumerate(sing):
            s=N(r[4]); k=i+1
            while len(s)<len(nm) and k<len(sing) and abs(sing[k][0]-r[0])<25 and 0<sing[k][1]-sing[k-1][1]<120:
                s+=N(sing[k][4]); k+=1
            if s==nm: hits.append((b,r[0],r[1],'(vertical)'+s))
    return hits
if __name__=='__main__':
    city=sys.argv[1]; pref=sys.argv[2].split(',')
    idx=build_index(pref)
    for rid,name,party in targets(city):
        h=find(idx,name)
        print(rid,name,party,[(x[0].replace('.tsv','')[:34],x[1],x[2]) for x in h][:3])

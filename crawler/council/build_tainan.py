import json,glob,re,collections
B='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/臺南市/'
inc=json.load(open(B+'../incumbents.json'))['臺南市']
def load(k):
    r=[]
    for f in sorted(glob.glob(B+'full_k%d_p*.json'%k)): r+=json.load(open(f))
    return r
norm=lambda s:re.sub(r'\s+','',s)
def cnt(rows):
    c=collections.Counter()
    for x in rows:
        for n in set(norm(y) for y in re.split(r'[、,，]',x['OrgTitle']) if y.strip()): c[n]+=1
    return c
a=cnt(load(4)); b=cnt(load(5))
recs={}
for n in inc:
    k=norm(n); X=a[k]; Y=b[k]
    recs[n]=[{'text':'第4屆提案 %d 件（議員提案 %d、臨時動議 %d）'%(X+Y,X,Y),'src_url':'https://www.tncc.gov.tw/motion1.asp'}]
json.dump(recs,open(B+'tainan_records.json','w'),ensure_ascii=False,indent=1)
print(len(recs),[n for n in inc if a[norm(n)]+b[norm(n)]==0],recs[inc[0]])

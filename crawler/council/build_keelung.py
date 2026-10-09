import json,re,collections
B='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/基隆市/'
inc=json.load(open(B+'../incumbents.json'))['基隆市']
rows=json.load(open(B+'m20.json'))['data']
def names(s):
    out=set()
    for x in re.split(r'[\r\n、,，]+',s or ''):
        x=x.strip()
        x=re.sub(r'(副議長|議長|議員)$','',x)
        if x: out.add(x)
    return out
P=collections.Counter(); T=collections.Counter(); J=collections.Counter()
for r in rows:
    for n in names(r['sm1_1c']):
        (P if r['sm1_seqkd']=='1' else T)[n]+=1
    for n in names(r['sm1_2c']): J[n]+=1
U='https://www.kmc.gov.tw/kmcweb/#/motion'
recs={n:[{'text':'第20屆提案 %d 件（定期會 %d、臨時會 %d）'%(P[n]+T[n],P[n],T[n]),'src_url':U},{'text':'第20屆連署提案 %d 件'%J[n],'src_url':U}] for n in inc}
json.dump(recs,open(B+'keelung_records.json','w'),ensure_ascii=False,indent=1)
print(len(recs),recs['陳冠羽'],[n for n in inc if P[n]+T[n]==0])

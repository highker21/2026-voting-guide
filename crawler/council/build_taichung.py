import json,re,collections
B='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/臺中市/'
inc=json.load(open(B+'../incumbents.json'))['臺中市']
rows=[]
for p in range(1,5): rows+=json.load(open(B+'p%d.json'%p))['data']['data']
c4=[r for r in rows if str(r['session']).startswith('第4屆')]
sp=collections.Counter(); tmp=collections.Counter(); js=collections.Counter()
unk=collections.Counter()
for r in c4:
    names=[x.strip() for x in re.split(r'[、,，]',r['sponsor']) if x.strip()]
    if r['billType']=='議員提案':
        for n in set(names): sp[n]+=1
    elif r['billType']=='臨時動議案':
        for n in set(names): tmp[n]+=1
    if r['billType'] in('議員提案','臨時動議案'):
        for x in set(x.strip() for x in re.split(r'[、,，]',r['jointSignatory']) if x.strip()): js[x]+=1
allnames=set(sp)|set(tmp)
print('not matched incumbents:',[n for n in inc if n not in allnames])
print('sponsor names not incumbent (sample):',[n for n in allnames if n not in inc][:15])
recs={}
for n in inc:
    t='第4屆提案 %d 件（議員提案 %d、臨時動議 %d）'%(sp[n]+tmp[n],sp[n],tmp[n])
    recs[n]=[{'text':t,'src_url':'https://yishi.tccc.gov.tw/proposals'}]
    if js[n]: recs[n].append({'text':'第4屆連署提案 %d 件'%js[n],'src_url':'https://yishi.tccc.gov.tw/proposals'})
    else: recs[n].append({'text':'第4屆連署提案 0 件','src_url':'https://yishi.tccc.gov.tw/proposals'})
json.dump(recs,open(B+'taichung_records.json','w'),ensure_ascii=False,indent=1)
print(len(recs),recs[inc[0]],max(c4,key=lambda r:r['session'])['session'])

import json,collections
R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/臺北市/'
rows=json.load(open(R+'rows.json'))
recs={}; extra=0; kinds=collections.Counter()
for n,v in rows.items():
    seen={}
    for r in v['closed14']+v['unclosed']:
        if r[2].startswith('14'): seen[r[1]]=r
    if len({r[1] for r in v['closed14'] if r[2].startswith('14')})!=len(seen): extra+=1
    c=collections.Counter(r[3].replace(' ','') for r in seen.values()); kinds.update(c)
    X=c['議員提案']; Y=c['臨時提案']; Z=c['市法規']
    t='第14屆議員提案 %d 件'%X
    items=[{'text':t,'src_url':'https://ifddoc2.tcc.gov.tw/TCCMIS_Front/Adv_SearchInput.aspx'}]
    items.append({'text':'第14屆市法規案（自治條例等）提案 %d 件'%Z,'src_url':'https://ifddoc2.tcc.gov.tw/TCCMIS_Front/Adv_SearchInput.aspx'})
    recs[n]=items
json.dump(recs,open(R+'taipei_records.json','w'),ensure_ascii=False,indent=1)
print(len(recs),'members w/ unclosed extra:',extra,kinds)
print(recs[list(recs)[0]], sum(1 for r in recs.values() if r[0]['text'].startswith('第14屆議員提案 0')))

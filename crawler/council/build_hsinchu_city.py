import json,re
R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/新竹市/'
d=json.load(open(R+'prop_all.json'))
inc=json.load(open(R+'../incumbents_2.json'))['新竹市']
U='https://www.hsinchu-cc.gov.tw/tc/proposal.aspx?mid=42'
members={}
for n in inc:
    pp=d[n]['pp']; pc=d[n]['pc']
    assert len({r['no'] for r in pp})==len(pp) and len({r['no'] for r in pc})==len(pc)
    dq=sum('定期會' in r['meeting'] for r in pp); lq=len(pp)-dq
    members[n]=[{'text':'第11屆議員提案 %d 件（定期會 %d、臨時會 %d；含與他人共同列名之提案）'%(len(pp),dq,lq),'src_url':U},
                {'text':'第11屆列名連署 %d 件'%len(pc),'src_url':U}]
out={'新竹市':{'src_title':'新竹市議會「提案資料」查詢（第11屆，含第1-7次定期會、第1-24次臨時會）；提案數＝系統「提案人」欄列名，連署＝「連署人」欄列名；質詢紀錄因第7次定期會尚未上架，未列','src_url':U,'period':'第11屆（2022-12-25～2026-10-09）；系統最新提案日 2026-07-09','members':members}}
json.dump(out,open(R+'hsinchu_city_records.json','w'),ensure_ascii=False,indent=1)
print(len(members),members['黃文政'],members['彭昆耀'])

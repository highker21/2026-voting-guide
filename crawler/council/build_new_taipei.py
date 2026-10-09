import json,re,collections
R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/新北市/'
inc=json.load(open(R+'../incumbents_2.json'))['新北市']
U='https://bms1.ntp.gov.tw/billsystem/councilbillquery'
members={}; chk=[]
for full in inc:
    pp=json.load(open(R+f'm/{full}_pp.json')); pc=json.load(open(R+f'm/{full}_pc.json'))
    assert pp['n']==len(pp['rows']), (full,pp['n'],len(pp['rows']))
    key=re.sub(r'‧','．',full)   # 系統以全形中點「．」列名
    rows=pp['rows']
    keys=[(r[1],r[2],r[3],r[4]) for r in rows]
    assert len(set(keys))==len(keys),(full,'dup')
    names=[x.strip() for r in rows for x in [r[6]]]
    ok=[key in [t.strip() for t in r[6].split(',')] for r in rows]
    if not all(ok): chk.append((full,len(rows)-sum(ok)))
    cnt=collections.Counter(r[3] for r in rows)
    parts=[f'{k} {v}' for k,v in sorted(cnt.items(),key=lambda x:-x[1])]
    members[full]=[{'text':'第4屆提案 %d 件（%s；含與他人共同列名之提案）'%(len(rows),'、'.join(parts)),'src_url':U},
                   {'text':'第4屆列名連署 %d 件'%pc['n'],'src_url':U}]
print(chk)
out={'新北市':{'src_title':'新北市議會議案查詢系統（第4屆）；提案數＝系統「提案人」欄列名之議案筆數（依會期＋審查會＋案別＋案號計，共同提案每位列名者各計），連署＝「連署人／附議人」查詢之筆數','src_url':U,'period':'第4屆（2022-12-25～2026-10-09）；含第8次定期會（議案至 2026-10-07）','members':members}}
json.dump(out,open(R+'new_taipei_records.json','w'),ensure_ascii=False,indent=1)
print(len(members)); print(members['黃桂蘭'])

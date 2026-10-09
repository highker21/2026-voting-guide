import re,json,html,glob,collections
R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/新竹縣/'
rows=[]
for f in sorted(glob.glob(R+'pages/p*.html')):
    h=open(f).read()
    for b in re.findall(r'<ul class="schedule-detail-container__box sch-det--color.*?</ul>',h,flags=re.S):
        c=[html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',x))).strip() for x in re.findall(r'<li class="schedule-det-detail[^>]*>(.*?)</li>',b,flags=re.S)]
        art=re.search(r'article=(\d+)',b)
        rows.append(dict(date=c[0],cat=c[1],title=c[2],prop=c[3],cos=c[4],art=art.group(1) if art else None))
json.dump(rows,open(R+'proposals.json','w'),ensure_ascii=False,indent=0)
print(len(rows),len({r['art'] for r in rows}))
print(min(r['date'] for r in rows),max(r['date'] for r in rows))
print(collections.Counter(r['date'][:7] for r in rows).most_common(60)[:5])
multi=[r['prop'] for r in rows if re.search(r'[、,，&\s]',r['prop'])]; print('multi',len(multi),multi[:5])

# ---- 輸出 ----
inc=json.load(open(R+'../incumbents_2.json'))['新竹縣']
rr=[x for x in rows if x['date'].replace('.','-')>='2022-12-25']   # 排除 2022-11 的 7 筆（第19屆任期內，非 2022-12-25 起）
print('excluded pre-term',len(rows)-len(rr))
sess=[('2806','第1次'),('2930','第2次'),('3034','第3次'),('3115','第4次'),('3234','第5次'),('3400','第6次'),('3420','第7次')]
def qlist(n):
    out=[]
    for a,s in sess:
        h=open(R+f'q/a{a}.html').read()
        t=re.sub(r'<script.*?</script>|<style.*?</style>','',h,flags=re.S); t=re.sub(r'<[^>]+>',' ',t); t=re.sub(r'\s+',' ',t)
        seg=t[t.find('質詢內容'):t.find('回上一頁')]
        if n in seg: out.append(s)
    return out
U='https://www.hcc.gov.tw/porposal?lang=&program=197&council_type=22'
members={}
for n in inc:
    p=sum(n in re.split(r'[、&]',x['prop']) for x in rr); c=sum(n in re.split(r'[、&]',x['cos']) for x in rr)
    q=qlist(n)
    members[n]=[
      {'text':'第20屆議員提案 %d 件（含與他人共同列名之提案）'%p,'src_url':U},
      {'text':'第20屆列名連署 %d 件'%c,'src_url':U},
      {'text':'第20屆議員質詢頁列名 %d 個定期會（共 7 個定期會）'%len(q),'src_url':'https://www.hcc.gov.tw/question?lang=&program=198&council_type=22'}]
    print(n,p,c,q)
out={'新竹縣':{'src_title':'新竹縣議會「議員提案」「議員質詢」查詢（第二十屆）；提案數＝系統「提案人」欄列名（共同提案每位列名者各計1件），連署＝「連署人」欄列名；質詢＝各定期會「質詢內容」頁列名','src_url':'https://www.hcc.gov.tw/porposal?lang=&program=197','period':'第20屆（2022-12-25～2026-10-09）；提案至 2026-09-08、質詢頁至第7次定期會','members':members}}
json.dump(out,open(R+'hsinchu_county_records.json','w'),ensure_ascii=False,indent=1)

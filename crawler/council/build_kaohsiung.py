import re,json,os,html,collections
R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/高雄市/'
inc=json.load(open(R+'../incumbents.json'))['高雄市']
ALIAS={'高忠德Takiludun．Anu':'高忠德'}
def T(h): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',re.sub(r'<script.*?</script>|<style.*?</style>|<option.*?</option>','',h,flags=re.S))))
raw=json.load(open(R+'proposals_raw.json'))
lst=collections.Counter()
for v,m in raw.items():
    for row in m['議員提案']:
        for p in row[2].split(','):
            if p.strip(): lst[p.strip()]+=1
out={}; chk=[]
for n in inc:
    c=ALIAS.get(n,n)
    f=T(open(R+'frames/%s.html'%c).read()); d=T(open(R+'deal/%s.html'%c).read())
    a=int(re.search(r'議員提案 \((\d+)\)',f).group(1)); b=int(re.search(r'議員臨時提案 \((\d+)\)',f).group(1))
    if a!=lst[c]: chk.append((c,a,lst[c]))
    # 市政總質詢：DealData 第4屆列
    z=len(re.findall(r'\d+ 第[4４]屆 第\S+ '+c+' ',d))
    # 質詢答復譯文稿列名（Frame_Councilor，第4屆）
    seg=f[f.find('市政總質詢資料'):]
    ents=re.findall(r'\d+ \d{4}/\d\d/\d\d (\S+) (第[4４]屆\S+?) (.*?)(?= \d+ \d{4}/\d\d/\d\d |$)',seg)
    cnt=collections.Counter(e[0] for e in ents if c in e[2].split(' ')[-1].replace('、',' ').split())
    out[n]=dict(prop=a,temp=b,zong=z,biz=cnt.get('各部門業務質詢及答復',0),mayor=cnt.get('市長施政報告質詢及答復',0),ents=len(ents))
json.dump(out,open(R+'kaohsiung_counts.json','w'),ensure_ascii=False,indent=1)
print('mismatch',chk)
for n,v in list(out.items())[:8]: print(n,v)
print(sorted(set(v['zong'] for v in out.values())), sorted(set(v['temp'] for v in out.values())))

# ---- 組 records（市政總質詢排除尚未進行的排定日）----
import urllib.parse
CUT=(115,10,9)
def done(d):
    y,m,dd=map(int,d.split('/')); return (y,m,dd)<=CUT
recs={}
for n in inc:
    c=ALIAS.get(n,n); q=urllib.parse.quote(c)
    d=T(open(R+'deal/%s.html'%c).read())
    ds=re.findall(r'\d+ 第[4４]屆 第\S+ '+c+' (\d+/\d+/\d+)',d)
    ok=sum(done(x) for x in ds); fut=len(ds)-ok
    o=out[n]
    items=[{'text':'第4屆提案 %d 件（議員提案 %d、臨時提案 %d）'%(o['prop']+o['temp'],o['prop'],o['temp']),
            'src_url':'https://cissearch.kcc.gov.tw/Frame_Councilor.aspx?cname='+q}]
    if ds:
        t='第4屆市政總質詢 %d 次'%ok
        if fut: t+='（另已排定 %d 次尚未進行）'%fut
    else:
        t='第4屆市政總質詢 0 次（議事系統無紀錄；現任議長）' if n=='康裕成' else '第4屆市政總質詢 0 次'
    items.append({'text':t,'src_url':'https://cissearch.kcc.gov.tw/System/MunicipalQuestion/DealData.aspx?councilorfullname='+q})
    recs[n]=items
json.dump(recs,open(R+'kaohsiung_records.json','w'),ensure_ascii=False,indent=1)
print(recs['林富寶'],recs['康裕成'],recs['張博洋'],sep='\n')
print(collections.Counter(r[1]['text'] for r in recs.values()))

# 新竹市議會 提案資料：按提案人(pp)／連署人(pc)逐人抓取第11屆，1 秒間隔；原始 HTML 存 raw/council/新竹市/prop/
import sys,json,os,re; sys.path.insert(0,'/Users/highker/claudecode/repos/2026-voting-guide/crawler/council')
from hsc_lib import *; from hsc_parse import *
R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/新竹市/'
os.makedirs(R+'prop',exist_ok=True)
h=open(R+'prop_c11.html').read()
sel=re.search(r'<select[^>]*id="ddlProposal".*?</select>',h,flags=re.S).group(0)
ids={n:i for i,n in re.findall(r'value="(\d+)"[^>]*>([^<]*)',sel)}
inc=json.load(open(R+'../incumbents_2.json'))['新竹市']
miss=[n for n in inc if n not in ids]; print('missing in dropdown',miss,flush=True)
def page(kind,pid,pn):
    f=R+f'prop/{kind}_{pid}_{pn}.html'
    if os.path.exists(f): return open(f).read()
    q=f'proposal.aspx?pn={pn}&mid=42&cc=11&c=&m=&pp={pid if kind=="pp" else ""}&pc={pid if kind=="pc" else ""}&r=5&kk=&key=&cchk='
    t=get(q); open(f,'w').write(t); return t
res={}
for n in inc:
    if n in miss: continue
    res[n]={}
    for kind in ['pp','pc']:
        allr=[]; h1=page(kind,ids[n],1); lp=lastpage(h1); allr+=rows(h1)
        for pn in range(2,lp+1): allr+=rows(page(kind,ids[n],pn))
        res[n][kind]=allr
    print(n,len(res[n]['pp']),len(res[n]['pc']),flush=True)
json.dump(res,open(R+'prop_all.json','w'),ensure_ascii=False,indent=0)

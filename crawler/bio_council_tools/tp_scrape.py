import re,html,subprocess,time,json,os
R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/bio_council/tp/'
def curl(u): return subprocess.run(['curl','-s','-m','25','-L','-A','Mozilla/5.0',u],capture_output=True).stdout.decode('utf8','ignore')
idx=curl('https://www.tcc.gov.tw/Councilor_Search1.aspx?n=13869')
ids=sorted(set(re.findall(r's=(\d+)',curl('https://www.tcc.gov.tw/'))))
ids=sorted(set(re.findall(r'Councilor_Content\.aspx\?n=13898&s=(\d+)',idx+curl('https://www.tcc.gov.tw/'))))
print(len(ids))
out={}
for s in ids:
    f=R+s+'.html'
    if not os.path.exists(f):
        open(f,'w').write(curl(f'https://www.tcc.gov.tw/Councilor_Content.aspx?n=13898&s={s}')); time.sleep(1)
    h=open(f).read()
    h=re.sub(r'<(script|style).*?</\1>','',h,flags=re.S)
    t=html.unescape(re.sub(r'<[^>]+>','\n',h)); L=[x.strip() for x in t.split('\n') if x.strip()]
    try:
        N=lambda x:re.sub(r'[\s\u00a0\u3000]','',x)
        i=L.index('議員'); name=L[i-1]; sec=L[i+1]
        a=[k for k,x in enumerate(L) if N(x)=='學歷'][0]
        b=[k for k,x in enumerate(L) if N(x)=='經歷'][0]
        c=[k for k,x in enumerate(L) if N(x)=='政見'][0]
        edu=[x.lstrip('• ').strip() for x in L[a+1:b]]; exp=[x.lstrip('• ').strip() for x in L[b+1:c]]
        out[s]=dict(name=name,sec=sec,edu=edu,exp=exp)
    except Exception as e: out[s]=dict(err=str(e))
json.dump(out,open(R+'all.json','w'),ensure_ascii=False,indent=1)
print(sum(1 for v in out.values() if 'err' in v))

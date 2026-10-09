import re,html,subprocess,time,json,os
R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/bio_council/tn/'
B='https://www.tncc.gov.tw/'
def curl(u):
    return subprocess.run(['curl','-s','-m','25','-L','-A','Mozilla/5.0',u],capture_output=True).stdout.decode('utf8','ignore')
def clean(h):
    h=re.sub(r'<(script|style).*?</\1>','',h,flags=re.S)
    t=html.unescape(re.sub(r'<[^>]+>','\n',h)); return [x.strip() for x in t.split('\n') if x.strip()]
home=curl(B+'subhome.asp?orcaid=C56635AE-3C35-4233-8561-7B2CAA2DF01F')
subs=sorted(set(re.findall(r"orcaid2=([0-9A-F-]{36})",home)))
print(len(subs))
ids={}
for o in subs:
    h=curl(B+f'subhome.asp?orcaid=C56635AE-3C35-4233-8561-7B2CAA2DF01F&orcaid2={o}'); time.sleep(1)
    for m in re.findall(r'councilorpage\.asp\?mainid=([0-9A-F-]{36})',h): ids.setdefault(m,o)
print(len(ids))
out={}
for m in ids:
    f=R+m+'.html'
    if not os.path.exists(f): open(f,'w').write(curl(B+'councilorpage.asp?mainid='+m)); time.sleep(1)
    L=clean(open(f).read())
    try:
        a=L.index('學歷'); i=max(k for k in range(a) if L[k]=='議員資訊網'); name=L[i+1]
        b=L.index('經歷'); p=L.index('政見')
        out[m]=dict(name=name,edu=L[a+1:b],exp=L[b+1:p])
    except Exception as e: out[m]=dict(err=str(e))
json.dump(out,open(R+'all.json','w'),ensure_ascii=False,indent=1)
print(len(out),sum('err' in v for v in out.values()),[v.get('name') for v in out.values()])

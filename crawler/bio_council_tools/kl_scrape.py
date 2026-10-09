import re,html,subprocess,time,json,os
R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/bio_council/kl/'
B='https://www.kmc.gov.tw'
def curl(u): return subprocess.run(['curl','-s','-m','25','-L','-A','Mozilla/5.0',u],capture_output=True).stdout.decode('utf8','ignore')
def clean(h):
    h=re.sub(r'<(script|style).*?</\1>','',h,flags=re.S)
    t=html.unescape(re.sub(r'<[^>]+>','\n',h)); return [x.strip() for x in t.split('\n') if x.strip()]
home=curl(B+'/index.php/mac/mi')
links=sorted(set(re.findall(r"href=['\"](/index.php/mac/mi/[a-z]+/\d+-[a-z]+-\d+)['\"]",home)))
print(len(links))
out={}
for l in links:
    f=R+l.split('/')[-1]+'.html'
    if not os.path.exists(f): open(f,'w').write(curl(B+l)); time.sleep(1)
    L=clean(open(f).read())
    try:
        k=[i for i,x in enumerate(L) if x.endswith(' 議員') and i>20][0]
        name=re.sub(r'[\s　]','',L[k][:-3])
        a=L.index('議員經歷'); p=L.index('議員政見')
        sec=[x for x in L if x.startswith('●\xa0選區')]
        out[l]=dict(name=name,sec=sec[0] if sec else '',exp=[x.lstrip('●\xa0 ').strip() for x in L[a+1:p]],url=B+l)
    except Exception as e: out[l]=dict(err=str(e))
json.dump(out,open(R+'all.json','w'),ensure_ascii=False,indent=1)
print(len(out),sum('err' in v for v in out.values()),[v.get('name') for v in out.values()])

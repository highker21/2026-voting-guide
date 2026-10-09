import re,html,subprocess,time,json,os
R='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/bio_council/tc/'
def curl(u):
    b=subprocess.run(['curl','-s','-m','25','-L','-A','Mozilla/5.0',u],capture_output=True).stdout
    try: return b.decode('utf8')
    except: return b.decode('big5','ignore')
def clean(h):
    h=re.sub(r'<(script|style).*?</\1>','',h,flags=re.S)
    t=html.unescape(re.sub(r'<[^>]+>','\n',h)); return [x.strip() for x in t.split('\n') if x.strip()]
out={}
for z in range(95,112):
    lst=curl(f'https://www.tccc.gov.tw/wb_introduction03.asp?uno=&zno={z}'); time.sleep(1)
    cnos=sorted(set(re.findall(r'cno=(\d+)&zno=%d'%z,lst)))
    for c in cnos:
        f=R+f'{z}_{c}.html'
        if not os.path.exists(f):
            open(f,'w').write(curl(f'https://www.tccc.gov.tw/wb_introduction02.asp?uno=&zno={z}&cno={c}')); time.sleep(1)
        L=clean(open(f).read())
        try:
            nm=[x for x in L if re.search(r'選區(副)?議[員長]',x)][0]; 
            m=re.search(r'選區(?:副)?議[員長](.+)',nm); name=m.group(1).strip()
            sec=[x for x in L if re.fullmatch(r'第.+選區',x)][0]
            a=L.index('學歷'); b=L.index('經歷'); p=L.index('政見') if '政見' in L else len(L)
            cur=[x for x in L if x.startswith('現任') or x.startswith('曾任')][:1]
            out[f'{z}_{c}']=dict(name=name,sec=sec,edu=L[a+1:b],exp=L[b+1:p],cur=cur)
        except Exception as e: out[f'{z}_{c}']=dict(err=str(e),f=f)
json.dump(out,open(R+'all.json','w'),ensure_ascii=False,indent=1)
print(len(out),sum('err' in v for v in out.values()))

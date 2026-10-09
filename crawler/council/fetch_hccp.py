# 新竹縣議會 議員提案 全抓（第20屆 council_type=22），1 秒間隔
import subprocess,time,os,re
B='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/新竹縣/pages/'
os.makedirs(B,exist_ok=True)
def get(p):
    f=B+'p%03d.html'%p
    if os.path.exists(f) and os.path.getsize(f)>5000: return open(f).read()
    h=subprocess.run(['curl','-s','--max-time','30',f'https://www.hcc.gov.tw/porposal?lang=&program=197&council_type=22&page={p}'],capture_output=True).stdout.decode()
    open(f,'w').write(h); time.sleep(1); return h
h=get(1)
last=max(int(x) for x in re.findall(r'chg_page\((\d+)\)',h))
print('last',last,flush=True)
for p in range(2,last+1): get(p)
print('done')

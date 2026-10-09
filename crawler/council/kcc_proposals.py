"""高雄市議會 議事資訊整合查詢系統：抓第4屆各會議「議員提案」「議員臨時提案」清單，存 raw。"""
import sys,re,json,os
sys.path.insert(0,os.path.dirname(__file__))
from kcc_lib import *
U='https://cissearch.kcc.gov.tw/System/Proposal/Default.aspx'
P='ctl00$ContentPlaceHolder1$'
OUT='/Users/highker/claudecode/repos/2026-voting-guide/crawler/raw/council/高雄市/'
h=get(U)
h=post2(U,h,{'__EVENTTARGET':P+'uscPeriodSessionMeeting$ddlSession',P+'uscPeriodSessionMeeting$ddlPeriod':'07',P+'uscPeriodSessionMeeting$ddlSession':'0704'})
sel=re.search(r'<select name="[^"]*ddlMeeting"[^>]*>(.*?)</select>',h,flags=re.S).group(1)
meetings=[(v,n) for v,n in re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)',sel) if v]
print(meetings)
def rows(r,gid):
    m=re.search(r'<table[^>]*id="ContentPlaceHolder1_%s".*?</table>'%gid,r,flags=re.S)
    out=[]
    if not m: return out
    for tr in re.findall(r'<tr.*?</tr>',m.group(0),flags=re.S):
        c=[re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',x))).strip() for x in re.findall(r'<td.*?</td>',tr,flags=re.S)]
        if len(c)>=6 and c[1].isdigit(): out.append(c[1:6])
    return out
res={}
for v,n in meetings:
    base={P+'uscPeriodSessionMeeting$ddlPeriod':'07',P+'uscPeriodSessionMeeting$ddlSession':'0704',P+'ddlCategory':'',P+'ddlProposalKind':'0',P+'ddlPetitionCouncilor':'',P+'ddlState':'',P+'uscPeriodSessionMeeting$ddlMeeting':v,P+'ddlCouncilor':'','__EVENTTARGET':P+'LinkButton1'}
    r=post2(U,h,base)
    tabs=dict(re.findall(r'(議員提案|議員臨時提案) \((\d+)\)',text(r)))
    res[v]={'name':n,'tabs':tabs}
    for key,gid,btn,pg in [('議員提案','gvIndex4','btnGo4','DataPager4'),('議員臨時提案','gvIndex5','btnGo5','DataPager5')]:
        k=int(tabs.get(key,0))
        if not k: res[v][key]=[]; continue
        d=dict(base); d['__EVENTTARGET']=P+btn; d[P+pg+'$ctl02$txtCurrentPage']='1'; d[P+pg+'$ctl02$txtPageSize']='3000'
        r2=post2(U,r,d)
        rr=rows(r2,gid); res[v][key]=rr
        print(n,key,k,len(rr),flush=True)
json.dump(res,open(OUT+'proposals_raw.json','w'),ensure_ascii=False)

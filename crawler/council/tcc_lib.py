import requests,re,time,urllib3,html
urllib3.disable_warnings()
S=requests.Session(); S.headers['User-Agent']='Mozilla/5.0'; S.verify=False
U='https://ifddoc2.tcc.gov.tw/TCCMIS_Front/Adv_SearchInput.aspx'
_l=[0]
def _w():
    d=1.3-(time.time()-_l[0])
    if d>0: time.sleep(d)
    _l[0]=time.time()
def hid(h): return {n:v for n,v in re.findall(r'name="(__[A-Z]+)"[^>]*value="([^"]*)"',h)}
def query(name,extra):
    _w(); h=S.get(U,timeout=60).text
    d=hid(h)
    d.update({'ChkAll':'on','ChkOM':'on','ChkSR':'on','ChkYk':'on','sele_DETR':'','sele_DETM':'','sele_DETP':'','sele_DEMT':'','councilorSelect':name,'searchWord':'','btnSubmit':'查詢','useMen':'on'})
    d.update(extra); _w(); r=S.post(U,data=d,timeout=90); return r.text
def parse(h):
    m=re.search(r'共(\d+)筆；檢索條件：([^<]*)',h)
    rows=[]
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',h,flags=re.S):
        c=[re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',x))).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>',tr,flags=re.S)]
        if len(c)>=7 and c[1].isdigit(): rows.append(c[1:7])
    return (int(m.group(1)),m.group(2)) if m else None, rows

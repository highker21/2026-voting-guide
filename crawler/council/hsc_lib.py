import requests,re,time
U='https://www.hsinchu-cc.gov.tw/tc/'
S=requests.Session(); S.headers['User-Agent']='Mozilla/5.0'; S.verify=False
import urllib3; urllib3.disable_warnings()
def hid(h): return {k:(re.search(r'name="%s"[^>]*value="([^"]*)"'%k,h) or re.search(r'id="%s"[^>]*value="([^"]*)"'%k,h)).group(1) for k in ['__VIEWSTATE','__VIEWSTATEGENERATOR','__EVENTVALIDATION']}
def get(page):
    time.sleep(1); return S.get(U+page,timeout=60).text
def post(page,h,extra):
    d=hid(h); d.update(extra); time.sleep(1); return S.post(U+page,data=d,timeout=60).text

import re,time,requests,html
S=requests.Session(); S.headers['User-Agent']='Mozilla/5.0'; S.verify=False
import urllib3; urllib3.disable_warnings()
_last=[0]
def _wait():
    d=1.2-(time.time()-_last[0])
    if d>0: time.sleep(d)
    _last[0]=time.time()
def get(url):
    _wait(); r=S.get(url,timeout=60); r.raise_for_status(); return r.text
def hidden(h):
    return {m.group(1):html.unescape(m.group(2)) for m in re.finditer(r'<input[^>]*type="hidden"[^>]*name="([^"]*)"[^>]*value="([^"]*)"',h)}
def post(url,h,extra,keep=None):
    d=hidden(h); d.update(extra); _wait(); r=S.post(url,data=d,timeout=90); r.raise_for_status(); return r.text

def post2(url,h,extra):
    d={k:v for k,v in hidden(h).items() if 'gvIndex' not in k and 'hidCount' not in k}
    d.update(extra); _wait(); r=S.post(url,data=d,timeout=90); r.raise_for_status(); return r.text
def text(h):
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',re.sub(r'<script.*?</script>|<style.*?</style>|<option.*?</option>','',h,flags=re.S)))

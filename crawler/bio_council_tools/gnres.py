import sys,re,json,subprocess,urllib.parse
def curl(args): return subprocess.run(["curl","-s","-m","25","-A","Mozilla/5.0"]+args,capture_output=True).stdout.decode('utf8','ignore')
def resolve(url):
    gid=url.split('/articles/')[-1].split('?')[0]
    h=curl([f"https://news.google.com/rss/articles/{gid}?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"])
    sg=re.search(r'data-n-a-sg="([^"]+)"',h); ts=re.search(r'data-n-a-ts="([^"]+)"',h)
    if not sg: return None
    inner=json.dumps(["garturlreq",[["X","X",["X","X"],None,None,1,1,"US:en",None,1,None,None,None,None,None,0,1],"X","X",1,[1,1,1],1,1,None,0,0,None,0],gid,int(ts.group(1)),sg.group(1)])
    body="f.req="+urllib.parse.quote(json.dumps([[["Fbv4je",inner,None,"generic"]]]))
    r=curl(["-X","POST","-H","Content-Type: application/x-www-form-urlencoded;charset=UTF-8","-d",body,"https://news.google.com/_/DotsSplashUi/data/batchexecute"])
    m=re.search(r'garturlres\\",\\"(.*?)\\"',r)
    return m.group(1).encode().decode('unicode_escape') if m else None
if __name__=='__main__': print(resolve(sys.argv[1]))

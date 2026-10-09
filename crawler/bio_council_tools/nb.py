import sys,re,html,subprocess,urllib.parse,time
sys.path.insert(0,'/tmp')
from gnres import resolve,curl
def search(q,n=5):
    s=curl(["https://news.google.com/rss/search?hl=zh-TW&gl=TW&ceid=TW:zh-Hant&q="+urllib.parse.quote(q)])
    out=[]
    for it in re.findall(r'<item>(.*?)</item>',s,flags=re.S)[:n]:
        t=html.unescape(re.search(r'<title>(.*?)</title>',it,re.S).group(1)); l=re.search(r'<link>(.*?)</link>',it,re.S).group(1); d=re.search(r'<pubDate>(.*?)</pubDate>',it)
        out.append((t,l,d.group(1)[5:16] if d else ''))
    return out
KW=re.compile(r'學歷|經歷|畢業|碩士|博士|學士|曾任|現任|肄業|擔任|出身|簡歷')
def text_of(u):
    h=curl([u])
    h=re.sub(r'<(script|style).*?</\1>','',h,flags=re.S)
    t=html.unescape(re.sub(r'<[^>]+>','\n',h))
    return [x.strip() for x in t.split('\n') if len(x.strip())>8]
if __name__=='__main__':
    name=sys.argv[1]; q=sys.argv[2]; n=int(sys.argv[3]) if len(sys.argv)>3 else 4
    for t,l,d in search(q,n+2)[:n]:
        u=resolve(l); print('##',t,d,u); time.sleep(1)
        if not u: continue
        L=text_of(u)
        idx=[i for i,x in enumerate(L) if name in x]
        hits=[];seen=set()
        for i in idx[:12]:
            for j in range(max(0,i-1),min(len(L),i+5)):
                x=L[j]
                if j not in seen and KW.search(x) and len(x)<400 and (x.count('（')+x.count('('))<3 and x.count('、')<9 and not re.search(r'蔣萬安|沈伯洋|登記',x): seen.add(j);hits.append(x)
        for x in hits[:5]: print('   ',x[:260])

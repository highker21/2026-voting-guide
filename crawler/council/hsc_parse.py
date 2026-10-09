import re,html
def rows(h):
    out=[]
    for m in re.finditer(r'<ul id="htmlAA".*?</ul>',h,flags=re.S):
        b=m.group(0)
        f=[html.unescape(re.sub(r'\s+',' ',x)).strip() for x in re.findall(r'<li class="proposal-detail[^>]*>(.*?)</li>',b,flags=re.S)]
        f=[re.sub(r'<[^>]+>','',x).strip() for x in f]
        out.append(dict(cls=f[0],meeting=f[1],no=f[2],date=f[3],title=f[4],proposers=f[5],cosigners=f[6]))
    return out
def lastpage(h):
    m=re.search(r'\?pn=(\d+)&[^"]*"[^>]*title="最後頁"',h)
    return int(m.group(1)) if m else (max([int(x) for x in re.findall(r'\?pn=(\d+)&',h)] or [1]))

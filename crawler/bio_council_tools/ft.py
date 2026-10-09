import sys,re
sys.path.insert(0,'/tmp')
from nb import text_of,KW
name,u=sys.argv[1],sys.argv[2]
L=text_of(u); idx=[i for i,x in enumerate(L) if name in x]
seen=set()
for i in idx[:15]:
    for j in range(max(0,i-1),min(len(L),i+4)):
        if j not in seen and len(L[j])<500 and (KW.search(L[j]) or j==i): seen.add(j); print(L[j][:300])

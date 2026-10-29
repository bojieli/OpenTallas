# Which die clock nets did GRT put on M8/M9 vs signal layers only, split by "has FF CLK loads" (OpenROAD leaf-clock rule).
import collections, json
from openroad import Design, Tech
t=Tech(); d=Design(t); d.readDb("/n/grt/grt.odb"); b=d.getBlock()
ff={}; 
for n in b.getNets():
    if n.getSigType()=="CLOCK": ff[n.getName()]=sum(1 for j in n.getITerms() if j.getMTerm().getName()=="CLK")
G=collections.defaultdict(lambda: [set(),0])
cur=None
for l in open("/n/grt/route.guide"):
    l=l.strip()
    if l in ("(",")"): 
        if l==")": cur=None
        continue
    p=l.split()
    if len(p)==1: cur=p[0] if p[0] in ff else None; continue
    if cur:
        x0,y0,x1,y1=map(int,p[:4]); G[cur][0].add(p[4]); G[cur][1]=max(G[cur][1],max(x1-x0,y1-y0))
res=collections.Counter(); ex=[]
for n,k in ff.items():
    ly,ext=G[n]; hi=bool(ly&{"M8","M9"}); long=ext>21600
    res[(("leaf" if k else "nonleaf"),("M8M9" if hi else "sigonly"),("long" if long else "short"))]+=1
    if k and not hi and long and len(ex)<5: ex.append((n,k,sorted(ly),ext/1000))
print(json.dumps({" ".join(k):v for k,v in sorted(res.items())},indent=0)); print(ex)

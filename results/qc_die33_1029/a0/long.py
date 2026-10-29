import sys,re,json
from collections import Counter,defaultdict,deque
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot')
import geom_rules as G
geom,anch,out=sys.argv[1:4]
D=G.Design(geom)
A={}
for l in open(anch):
    n,x,y=l.rstrip('\n').split('\t');A[n.replace('\\','')]=(float(x),float(y))
seq={c for c,v in D.cells.items() if v[0]=='S'}
comb={c for c,v in D.cells.items() if v[0] in 'BLK'}
# per capture: all launching flops via comb (exact sets; reverse BFS per long-capture candidate is heavy -> forward sets limited)
# forward: per comb cell keep set of source flops (bounded) -- compute via topological
succ=defaultdict(list);indeg=Counter()
for c in comb:
    for n in D.drives.get(c,[]):
        for s in D.nets[n][2]:
            if s[0]=='i' and not s[2] and s[1] in comb: succ[c].append(s[1]);indeg[s[1]]+=1
src=defaultdict(set);caps=defaultdict(set)
for c in seq:
    for n in D.drives.get(c,[]):
        for s in D.nets[n][2]:
            if s[0]!='i' or s[2]: continue
            if s[1] in seq: caps[s[1]].add(c)
            elif s[1] in comb: src[s[1]].add(c)
dq=deque(c for c in comb if indeg[c]==0)
while dq:
    c=dq.popleft();e=src.get(c,set())
    for n in D.drives.get(c,[]):
        for s in D.nets[n][2]:
            if s[0]!='i' or s[2]: continue
            if s[1] in seq: caps[s[1]]|=e
            elif s[1] in comb: src[s[1]]|=e
    for t in succ.get(c,[]):
        indeg[t]-=1
        if indeg[t]==0: dq.append(t)
    if len(e)>5000: pass
ctr=lambda c:G.ctr(D.cells[c])
nm=lambda c:D.cells[c][6].replace('\\','')
fam=lambda s:re.sub(r'\[\d+\]','[]',s)
long=[]
for cap,ss in caps.items():
    cx,cy=ctr(cap);best=None
    for s in ss:
        sx,sy=ctr(s);d=abs(sx-cx)+abs(sy-cy)
        if d>405 and (best is None or d>best[0]): best=(d,s)
    if best:
        d,s=best;long.append(dict(d=round(d,2),src=nm(s),cap=nm(cap),sxy=[round(v,2) for v in ctr(s)],cxy=[round(v,2) for v in ctr(cap)],src_anch=A.get(nm(s)),cap_anch=A.get(nm(cap)),nsrc=len(ss)))
long.sort(key=lambda r:-r['d'])
print('long captures',len(long),'max',long[0]['d'] if long else 0)
pc=Counter((fam(r['src']),fam(r['cap'])) for r in long)
for k,v in pc.most_common(40): print(v,k)
print('anchored src',sum(r['src_anch'] is not None for r in long),'anchored cap',sum(r['cap_anch'] is not None for r in long))
# anchor drift: how far anchored cells are from their targets
dr=[]
for c in seq:
    n=nm(c)
    if n in A:
        x,y=ctr(c);ax,ay=A[n];dr.append(abs(x-ax)+abs(y-ay))
dr.sort();print('anchored seq',len(dr),'drift p50/p90/max',dr[len(dr)//2],dr[int(.9*len(dr))],dr[-1])
print('seq total',len(seq),'unanchored',len(seq)-len(dr))
json.dump(long,open(out,'w'),indent=0)

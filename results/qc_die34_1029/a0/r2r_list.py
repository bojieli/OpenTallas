# ICG enable reach on a placed geom.tsv: launch FF -> ICG legs through comb cones (graph as DIE-QC-33 solve.py), L1 um.
import sys,json
from collections import Counter,defaultdict,deque
sys.path.insert(0,sys.argv[2])
import geom_rules as G
D=G.Design(sys.argv[1])
seq={c for c,v in D.cells.items() if v[0]=="S"}
icg={c for c,v in D.cells.items() if v[0]=="K" and v[1].startswith("ICG")}
comb={c for c,v in D.cells.items() if v[0] in "BLK"}-icg
src=defaultdict(set);succ=defaultdict(list);indeg=Counter();E=set()
for c in comb:
    for n in D.drives.get(c,[]):
        for s in D.nets[n][2]:
            if s[0]=="i" and not s[2] and s[1] in comb: succ[c].append(s[1]);indeg[s[1]]+=1
for c in seq:
    for n in D.drives.get(c,[]):
        for s in D.nets[n][2]:
            if s[0]!="i" or s[2]: continue
            if s[1] in seq or s[1] in icg: E.add((c,s[1]))
            elif s[1] in comb: src[s[1]].add(c)
dq=deque(c for c in comb if indeg[c]==0)
while dq:
    c=dq.popleft();e=src.get(c,set())
    for n in D.drives.get(c,[]):
        for s in D.nets[n][2]:
            if s[0]!="i" or s[2]: continue
            if s[1] in seq or s[1] in icg:
                for a in e: E.add((a,s[1]))
            elif s[1] in comb: src[s[1]]|=e
    for t in succ.get(c,[]):
        indeg[t]-=1
        if indeg[t]==0: dq.append(t)
L=sorted(((abs(G.ctr(D.cells[a])[0]-G.ctr(D.cells[b])[0])+abs(G.ctr(D.cells[a])[1]-G.ctr(D.cells[b])[1])),D.cells[a][6],D.cells[b][6]) for a,b in E)[::-1]
print(json.dumps({"icg":len(icg),"enable_legs":len(L),"max":round(L[0][0],2),"gt405":sum(d>405 for d,_,_ in L),"worst":[[round(d,2),a,b] for d,a,b in L[:60]]},indent=0))

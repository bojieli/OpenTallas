"""KV-FT 10-24: do same-outline partition swaps (origins only) lower the ft crossings?  BFS crossing model on the
abutment graph.  usage (from the repo root): python3 physical/die_plan/qwen_kvsys/ft_swap_search_v39.py PLAN.json FT_LANES.json
(FT_LANES.json = ft_audit_v39.py --out DIR -> DIR/ft_lanes.json).  Result on v3.8x: no swap lowers crossings."""
import sys,json,collections,itertools
import numpy as np
from scipy.sparse.csgraph import shortest_path
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools', 'die_plan'))
import schema
p=json.load(open(sys.argv[1]))
P=schema.Plan(p)
names=list(P.parts); idx={n:i for i,n in enumerate(names)}
rect={n:P.rect(n) for n in names}
slots=[tuple(rect[n]) for n in names]  # slot i initially holds names[i]
def adj(slots):
    n=len(slots); A=np.zeros((n,n))
    for i in range(n):
        a=slots[i]
        for j in range(i+1,n):
            b=slots[j]; E=1e-3
            if (abs(a[2]-b[0])<E or abs(b[2]-a[0])<E) and min(a[3],b[3])-max(a[1],b[1])>1: A[i,j]=A[j,i]=1
            elif (abs(a[3]-b[1])<E or abs(b[3]-a[1])<E) and min(a[2],b[2])-max(a[0],b[0])>1: A[i,j]=A[j,i]=1
    return A
A=adj(slots); D=shortest_path(A,unweighted=True)
rows=json.load(open(sys.argv[2]))
L=[(idx[r['src']],idx[r['dst']],r['w'],r['nx']) for r in rows if r['src'] in idx and r['dst'] in idx]
src=np.array([l[0] for l in L]); dst=np.array([l[1] for l in L]); w=np.array([l[2] for l in L]); nx=np.array([l[3] for l in L])
def cost(D,pos):
    d=D[pos[src],pos[dst]]-1; d=np.maximum(d,0)
    return d.sum(), (d*w).sum()
pos=np.arange(len(names))  # part -> slot
c0=cost(D,pos); print('BFS model baseline crossings',c0,'actual',nx.sum(),(nx*w).sum())
# exceed: lanes whose actual > bfs
d=np.maximum(D[src,dst]-1,0); print('lanes actual>bfs',(nx>d).sum(),'excess',(nx-d).sum())
size=collections.defaultdict(list)
for n in names:
    r=rect[n]; size[(round(r[2]-r[0],2),round(r[3]-r[1],2))].append(n)
cands=[(a,b) for g in size.values() for a,b in itertools.combinations(g,2)]
print('swap candidates',len(cands))
best=[]
for a,b in cands:
    q=pos.copy(); q[idx[a]],q[idx[b]]=pos[idx[b]],pos[idx[a]]
    c=cost(D,q); best.append((c[0]-c0[0],c[1]-c0[1],a,b))
best.sort()
print('best by crossings',best[:10])
best.sort(key=lambda t:t[1]); print('best by bit-crossings',best[:10])

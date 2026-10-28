"""DIE-HBM-9 ESTIMATE: die-level region re-tree for the HBM local fish map (CLK-LOCAL-EST-1 ff58db4baa feed + crossings).
Edge delay parent->child = the CHECKED estimate value where the edge exists (crossings tree-edge unshared), else
Manhattan(parent feed tap -> child feed tap) x v (365.9 ps/mm) + child region insertion offset as in the feed row.
Unshared(link a,b) = sum of edge delays from LCA(a,b) down to a and to b. Greedy re-parent search over the regions
whose links exceed the window; candidate parents = regions that share a crossing with the child (locality)."""
import csv,sys,json,collections,itertools
feed=list(csv.DictReader(open(sys.argv[1]),delimiter="\t")); xs=list(csv.DictReader(open(sys.argv[2]),delimiter="\t"))
V=0.3659
par={};tap={};ins={}
for r in feed:
    par[r["child_region"]]=r["parent_region"] if r["parent_region"]!="ROOT" else "ROOT"
    tap[r["child_region"]]=json.loads(r["feed_tap_xy_um"]) if r["feed_tap_xy_um"] else None; ins[r["child_region"]]=float(r["ins_ps"])
tap["ROOT"]=[14199.84,8570.88]
meas={}
for r in xs:
    if r["class"]=="tree-edge":
        a,b,n=r["src_region"],r["dst_region"],r["tree_node_region"]
        ch=b if n==a else a
        meas[(n,ch)]=float(r["unshared_ps"])
def ed(p,c):
    if (p,c) in meas: return meas[(p,c)]
    pt=tap.get(p) or tap["ROOT"]; ct=tap[c] or pt
    return (abs(pt[0]-ct[0])+abs(pt[1]-ct[1]))*V
links=collections.defaultdict(int)
for r in xs: links[tuple(sorted((r["src_region"],r["dst_region"])))]+=int(r["bits"])
def anc(P,a):
    out=[a]
    while out[-1]!="ROOT":
        out.append(P[out[-1]])
        if len(out)>200: return None
    return out
def evaluate(P):
    worst=0;over=0;bits=0;rows=[]
    for (a,b),n in links.items():
        A=anc(P,a);B=anc(P,b)
        if A is None or B is None: return None
        sB=set(B); l=next(x for x in A if x in sB)
        u=sum(ed(P[x],x) for x in A[:A.index(l)])+sum(ed(P[x],x) for x in B[:B.index(l)])
        hops=A.index(l)+B.index(l)
        rows.append((u,a,b,n,hops,l)); worst=max(worst,u)
        if u>float(sys.argv[3]): over+=1;bits+=n
    rows.sort(reverse=True); return worst,over,bits,rows
base=evaluate(par)
nb=collections.defaultdict(set)
for (a,b) in links: nb[a].add(b);nb[b].add(a)
P=dict(par);moves=[]
FORCE=json.loads(sys.argv[5]) if len(sys.argv)>5 else {}
for c,p in FORCE.items(): moves.append(dict(child=c,old=P[c],new=p,forced=True)); P[c]=p
cur=evaluate(P); assert cur is not None, "forced tree has a cycle"
if FORCE: moves[-1].update(worst_ps=round(cur[0],1),over=cur[1])
for it in range(40):
    best=None
    for c in [r[1] for r in cur[3][:12]]+[r[2] for r in cur[3][:12]]:
        if c=="ROOT": continue
        for p in nb[c]|{par[c]}:
            if p==c or p==P[c]: continue
            Q=dict(P);Q[c]=p;e=evaluate(Q)
            if e is None: continue
            k=(e[1],e[0])
            if best is None or k<best[0]: best=(k,c,p,e)
    if best is None or (best[0]>=(cur[1],cur[0])): break
    _,c,p,e=best; moves.append(dict(child=c,old=P[c],new=p,worst_ps=round(e[0],1),over=e[1])); P[c]=p;cur=e
out=dict(scope="ESTIMATE only; CLK-LOCAL-EST-1 HBM map, window "+sys.argv[3]+" ps unshared",
         base=dict(worst_ps=round(base[0],1),over=base[1],over_bits=base[2],top=[[round(r[0]),*r[1:]] for r in base[3][:12]]),
         moves=moves,after=dict(worst_ps=round(cur[0],1),over=cur[1],over_bits=cur[2],top=[[round(r[0]),*r[1:]] for r in cur[3][:12]]),
         parents_changed={c:[par[c],P[c]] for c in P if P[c]!=par[c]})
json.dump(out,open(sys.argv[4],"w"),indent=1);print(json.dumps({k:out[k] for k in ("base","moves","after")},indent=0)[:4000])

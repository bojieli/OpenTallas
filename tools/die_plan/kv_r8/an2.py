import json,sys,collections,re
B=sys.argv[1]; C=sys.argv[2]
P=json.load(open(f"{B}/place.json")); N=json.load(open(f"{B}/nets.json"))["nets"]
M=json.load(open(f"{B}/mesh.json"))
arr={}
for l in open(f"{B}/tree_{C}.txt"):
    t=l.split(); arr[t[1]]=float(t[2])
par={}
for n in N:
    for ld in n["loads"]: par[ld]=n["drv"]
# node arrival per level
lv=collections.defaultdict(list)
for k,v in arr.items():
    m=re.match(r"ckm_n(\d+)_",k)
    if m: lv[int(m.group(1))].append((v,k))
prev=None
for L in sorted(lv):
    vs=sorted(lv[L]); print(f"L{L:2d} n={len(vs):5d} min {vs[0][0]:8.1f} max {vs[-1][0]:8.1f} spread {vs[-1][0]-vs[0][0]:6.1f}  min@{vs[0][1]} max@{vs[-1][1]}")
# per level: leg delay = node arrival - parent node arrival; spread of leg delays and leg lengths/segments
H={h["node"]:h for h in M["htree"] if "node" in h}
def parent_node(n):
    c=n
    while True:
        c=par.get(c)
        if c is None or c.startswith("port:"): return None
        if re.match(r"ckm_n\d+_|ckm_n0$",c): return c
print("per-level leg: delay spread vs len, nseg, rep slides")
for L in sorted(lv):
    rows=[]
    for v,k in lv[L]:
        p=parent_node(k)
        if p is None or p not in arr: continue
        h=H.get(k,{})
        rows.append((v-arr[p],h.get("len_um"),h.get("n_seg"),max([r["slide_um"] for r in h.get("reps",[])]+[0]),h.get("node_move_um"),k))
    if not rows: continue
    rows.sort(); lens=collections.Counter((r[1],r[2]) for r in rows)
    print(f"L{L:2d} leg delay {rows[0][0]:7.2f}..{rows[-1][0]:7.2f} (spread {rows[-1][0]-rows[0][0]:5.1f}) len/nseg {dict(lens.most_common(6))} maxslide {max(r[3] for r in rows)} maxmove {max((r[4] or 0) for r in rows)}")
# driver stage: driver input arrival - L10 parent
rows=[]
for k,v in arr.items():
    if k.startswith("ckm_d_"):
        p=parent_node(k); rows.append((v-arr[p],k,p))
rows.sort(); print("drv leg",rows[0],rows[-1], "spread",rows[-1][0]-rows[0][0])
# chain from parent node to driver: cells
k=rows[-1][1]; c=k; ch=[]
while c!=rows[-1][2]: ch.append((c,P[c]["x"],P[c]["y"],arr.get(c))); c=par[c]
print("slowest chain",ch[:12])
k=rows[0][1]; c=k; ch=[]
while c!=rows[0][2]: ch.append((c,P[c]["x"],P[c]["y"],arr.get(c))); c=par[c]
print("fastest chain",ch[:12])

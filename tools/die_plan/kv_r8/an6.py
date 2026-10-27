import json,sys,collections,numpy as np
B=sys.argv[1]; C=sys.argv[2]
N=json.load(open(f"{B}/nets.json"))["nets"]
arr={l.split()[1]:float(l.split()[2]) for l in open(f"{B}/tree_{C}.txt")}
par={}
for n in N:
    for ld in n["loads"]: par[ld]=n["drv"]
g=collections.defaultdict(list)
for d in arr:
    if d.startswith("ckm_d_"): g[par[d]].append(arr[d])
w=[max(v)-min(v) for v in g.values()]; m=[np.mean(v) for v in g.values()]
print(C,"L10 nets",len(g),"within-net spread p50 %.1f p90 %.1f max %.1f"%(np.median(w),np.percentile(w,90),max(w)),"net-mean spread %.1f"%(max(m)-min(m)))
# L9 groups: within L9 subtree
def anc(c,k):
    for _ in range(k): c=par[c]
    return c
for up in (2,3,4,5):
    g2=collections.defaultdict(list)
    for d in arr:
        if d.startswith("ckm_d_"): g2[anc(d,up)].append(arr[d])
    w=[max(v)-min(v) for v in g2.values()]; m=[np.mean(v) for v in g2.values()]
    print(" up",up,"groups",len(g2),"within max %.1f p50 %.1f"%(max(w),np.median(w)),"mean spread %.1f"%(max(m)-min(m)))

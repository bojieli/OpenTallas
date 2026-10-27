"""S81-CORE-LAT-R6 GEOM render: placed l0r sinks (GEO) + plan W-face pins + core_infra_htree 2x2 legs. usage: GEO PINS HTREE.json OUT.png"""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
geo, pins, ht, out = sys.argv[1:5]
S=[l.split() for l in open(geo) if l.startswith("SINK")]
d=json.load(open(ht)); nodes=d["nodes"]
leg={}
import collections
fig,ax=plt.subplots(figsize=(9,9))
ax.scatter([float(s[1]) for s in S],[float(s[2]) for s in S],s=0.3,c="0.6",label="13,238 placed sinks (GPL)")
P=json.load(open(pins))["pins"]
ax.scatter([p["x"] for p in P],[p["y"] for p in P],s=2,c="tab:red",marker="s",label="737 plan W pins (M4)")
pos={n[0]:n[2] for n in nodes}
col={"T00":"tab:blue","T01":"tab:green","T10":"tab:orange","T11":"tab:purple"}
for n in nodes:
    nm,par,xy,_,kind=n
    if par and par in pos:
        c=col.get(nm[:3],"k"); ax.plot([pos[par][0],xy[0]],[pos[par][1],xy[1]],c=c,lw=0.6)
    if kind=="leaf": ax.plot(xy[0],xy[1],".",c=col.get(nm[:3],"k"),ms=3)
ax.plot(*d["entry"],"k*",ms=14,label="centre entry")
ax.set_xlim(-3,271);ax.set_ylim(-3,271);ax.set_aspect("equal");ax.legend(loc="upper right",fontsize=8)
p=d["pred"];ax.set_title(f"dsdv_gunit_l0r 267.84 sq: 2x2 H-tree {d['splits']} PLAN MODEL TT {p['TT']['mean']}/w{p['TT']['window']} FF {p['FF']['mean']}/w{p['FF']['window']} (UNCHECKED)",fontsize=8)
fig.savefig(out,dpi=110)

import json,sys,statistics as S,collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan,sz,out=sys.argv[1:4]
P=json.load(open(plan)); Z=json.load(open(sz)); pt=P["partition_types"]; W,H=P["die"]["outline_um"]
Tz={r["type"]:r for r in Z["types"]}
fams=sorted({r["family"] for r in Z["types"]}); cm=plt.get_cmap("tab20"); fc={f:cm(i%20) for i,f in enumerate(fams)}
fig,ax=plt.subplots(figsize=(18,14.5),dpi=110); ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.5))
for p in P["partitions"]:
    r=Tz[p["type"]]; x,y=p["origin_um"]
    ax.add_patch(Rectangle((x,y),r["old_w"],r["old_h"],fill=False,ec="grey",lw=0.3,ls=":"))
    ax.add_patch(Rectangle((x,y),r["need_w"],r["need_h"],fc=fc[r["family"]],alpha=0.7,ec="k",lw=0.3))
ax.set_xlim(0,W);ax.set_ylim(0,H);ax.set_aspect("equal")
ax.set_title("S81 ready12f: content-sized tile (filled) inside its current lattice slot (dotted). Filled = cores bbox + 43.2 street margin (leaf) / lane bands + 2 streets (slice_station) / unchanged (others)")
ax.legend([Rectangle((0,0),1,1,fc=fc[f]) for f in fams],fams,fontsize=6,loc="upper left",ncol=3,bbox_to_anchor=(1.0,1.0))
fig.savefig(out+"/die_pertile_content_vs_slot.png",bbox_inches="tight")
by=collections.defaultdict(list)
for r in Z["types"]: by[r["family"]].append(r)
for f,rs in sorted(by.items()):
    if f not in("ot_s81sl_leaf","slice_station","ot_s81sl_kv_leaf"): continue
    nw=[r["need_w"] for r in rs];nh=[r["need_h"] for r in rs]
    print(f,len(rs),"need_w min/med/max %.0f/%.0f/%.0f need_h %.0f/%.0f/%.0f; area frac of slot med %.2f"%(min(nw),S.median(nw),max(nw),min(nh),S.median(nh),max(nh),S.median([r["need_w"]*r["need_h"]/(r["old_w"]*r["old_h"]) for r in rs])))
    big=[r for r in rs if r["need_w"]*r["need_h"]/(r["old_w"]*r["old_h"])<0.15]
    print("  types needing <15%% of slot: %d"%len(big), [r["type"] for r in big][:40])

import json,sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle
O=sys.argv[1]; out=sys.argv[2]; win=[float(v) for v in sys.argv[3].split(",")] if len(sys.argv)>3 else None
t=json.load(open(O+"/kit/clock/tree.json")); N={n["id"]:n for n in t["nodes"].values()}
p=json.load(open(O+"/die_plan_r98.json")); W,H=p["die"]["outline_um"]
fig,ax=plt.subplots(figsize=(16,12.4),dpi=110)
for q in (p["partitions"].values() if isinstance(p["partitions"],dict) else p["partitions"]):
    r=q.get("rect_um") or q.get("rect")
    if r: ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fill=False,lw=0.3,ec="0.6"))
for d in p["die"].get("pg",{}).get("domains",[]):
    r=d.get("phy_macro_um")
    if r: ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc="#f4c0c0",ec="r",lw=0.4))
for c in p["die"].get("channels",[]):
    r=c["rect_um"]; ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc="#e0e0ff",ec="b",lw=0.3))
segs={"feed":[],"rt":[],"o":[],"long":[]}
for n in N.values():
    if n["parent"] is None: continue
    a=N[n["parent"]]; s=[(a["x"],a["y"]),(n["x"],n["y"])]
    L=abs(a["x"]-n["x"])+abs(a["y"]-n["y"])
    k="long" if L>450 else ("feed" if n.get("feed") else ("rt" if n.get("rtree") else "o"))
    segs[k].append(s)
for k,c,w in (("o","0.5",0.2),("rt","g",0.3),("feed","b",0.8),("long","r",2.0)):
    ax.add_collection(LineCollection(segs[k],colors=c,linewidths=w))
tx=[v[0] if isinstance(v,(list,tuple)) else v.get("x") for v in (t["taps"].values() if isinstance(t["taps"],dict) else t["taps"])] if False else None
ax.set_xlim(*(win[0:2] if win else (0,W))); ax.set_ylim(*(win[2:4] if win else (0,H))); ax.set_aspect("equal")
ax.set_title("S81 link_fishbone feed (blue) + region H-trees (green), legs>450um red (%d); PHY macros red fill, channels blue"%len(segs["long"]))
fig.savefig(out,bbox_inches="tight")
print("OK",{k:len(v) for k,v in segs.items()})

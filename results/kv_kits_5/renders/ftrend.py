import json,sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan,tn,out=sys.argv[1:4]
r=json.load(open(plan)); t=r["partition_types"][tn]; W,H=t["outline_um"]
fig,ax=plt.subplots(figsize=(10,10*H/W+.6),dpi=150)
for c in t.get("hard_cores",[])+[c for c in t.get("contents",[]) if c.get("lef") and "origin_um" in c]:
    x,y=c["origin_um"]; w,h=c["outline_um"]; ax.add_patch(Rectangle((x,y),w,h,fc="#ddd",ec="#888",lw=.4))
cm=plt.get_cmap("tab20"); ns=0; nb=0
for i,s in enumerate(t.get("ft_slots",[])):
    if not s.get("bit_sites_um"): continue
    col=cm(i%20); ns+=1
    for st in s["bit_sites_um"]:
        xs=[p[0] for p in st]; ys=[p[1] for p in st]; nb+=len(st)
        ax.scatter(xs,ys,s=.4,color=col,linewidths=0)
    rg=s.get("regs_um",[])
    ax.plot([p[0] for p in rg],[p[1] for p in rg],"-",color=col,lw=.5)
ax.set_xlim(0,W); ax.set_ylim(0,H); ax.set_aspect("equal")
ax.set_title(f"{tn} FT stations (KV-KITS-5 lanes delta): {ns} sited slots, {nb} bit sites; grey=macros",fontsize=8)
fig.savefig(out,bbox_inches="tight"); print(ns,nb)

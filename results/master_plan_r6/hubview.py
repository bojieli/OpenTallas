import json,sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=json.load(open(sys.argv[1])); tn=sys.argv[2]; out=sys.argv[3]
t=P["partition_types"][tn]; W,H=t["outline_um"]
fig,ax=plt.subplots(figsize=(20,20*H/W+1))
ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1))
for h in t["hard_cores"]:
    x,y=h["origin_um"]; w,hh=h["outline_um"]
    ax.add_patch(Rectangle((x,y),w,hh,fc="#9ab",ec="k",lw=0.4))
    ax.text(x+w/2,y+hh/2,h["inst"],fontsize=4,ha="center",va="center")
xs=[];ys=[]
for s in t["internal_stations"]:
    for r in s["regs_um"]: xs.append(r[0]); ys.append(r[1])
ax.plot(xs,ys,'r.',ms=0.6)
ax.set_xlim(-50,W+50); ax.set_ylim(-50,H+50); ax.set_aspect("equal")
plt.savefig(out,dpi=110,bbox_inches="tight")

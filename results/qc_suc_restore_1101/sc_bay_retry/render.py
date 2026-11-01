from pathlib import Path
import json,matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).resolve().parent;m=json.load(open(r/"model.json"));reserved=json.load(open(r/"original_reserved_corridors.json"));targets=json.load(open(r/"FT_targets.json"));body=m["body_um"]
fig,ax=plt.subplots(figsize=(7,12));ax.add_patch(Rectangle((0,0),613.44,1339.2,fill=False,lw=2))
moved={g["prefix"] for g in m["reset_relocation_proposal"]}
for g in reserved["landing_groups"]:
 if g["prefix"] in moved:continue
 b=g["rect_um"];ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],color="#dddddd",alpha=.6))
for s in reserved["ft_target_envelopes"]:
 if s["slot"] in targets:continue
 for st in s["stages"]:
  b=st["ideal_bbox_um"];ax.plot([b[0],b[2]],[b[1],b[3]],color="#999999",lw=1)
ax.plot([],[],c="#999999",label="Unchanged reserved groups/FT targets")
ax.add_patch(Rectangle((body[0]-4.32,body[1]-4.32),body[2]-body[0]+8.64,body[3]-body[1]+8.64,fill=False,edgecolor="#d1495b",ls="--"))
ax.add_patch(Rectangle((body[0],body[1]),body[2]-body[0],body[3]-body[1],facecolor="#f4d6a0",alpha=.65,edgecolor="#aa7a24"))
for (slot,s),col in zip(targets.items(),["#00798c","#8a4fff","#d1495b"]):
 for st in s["stages"]:
  pts=st["bit_sites_um"];ax.scatter([p[0] for p in pts],[p[1] for p in pts],s=.6,c=col)
 for i in [0,s["bits"]//2,s["bits"]-1]:
  pts=[st["bit_sites_um"][i] for st in s["stages"]];ax.plot([p[0] for p in pts],[p[1] for p in pts],c=col,lw=.8,alpha=.6)
 ax.plot([],[],c=col,label=slot)
for g in m["reset_relocation_proposal"]:
 x,y=g["target_group_center_um"];ax.add_patch(Rectangle((x-2.16,y-2.16),4.32,4.32,facecolor="blue"))
ax.plot([],[],c="blue",label="Same-depth reset group proposals")
ax.scatter([311.04],[673.92],marker="+",s=100,c="black",label="Existing parent clock/reset")
ax.scatter([467.88],[905.04],marker="+",s=100,c="red",label="Proposed child center clock")
ax.text(468,1090,"SC2 native child\n281,884 std\n30.9% fill",ha="center",fontsize=10)
ax.set(xlim=(-15,630),ylim=(-15,1360),aspect="equal",xlabel="um",ylabel="um")
ax.set_title("SC bay refinement | PROPOSAL / parent HOLD\nSame FT stages/cycles | .4 reserved FF packing | old conflicting targets replaced\nActual source anchors/reset graph/clock/internal child timing pending",fontsize=10)
ax.legend(loc="upper center",bbox_to_anchor=(.5,-.06),fontsize=8,ncol=2)
fig.savefig(r/"proposal.png",dpi=150,bbox_inches="tight")

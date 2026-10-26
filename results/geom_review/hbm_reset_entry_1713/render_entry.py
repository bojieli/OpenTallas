from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).resolve().parent
p=json.loads((r/"plan/die_plan.json").read_text());o=json.loads((r/"offsets_geometry.json").read_text());fix=json.loads((r/"repair.json").read_text());t=p["partition_types"]["root"];w,h=t["outline_um"];rt=o["types"]["root"]
fig,(a,b)=plt.subplots(1,2,figsize=(12,9),gridspec_kw={"width_ratios":[1.3,1]})
a.add_patch(Rectangle((0,0),w,h,fill=False,color="black"))
for c in t.get("hard_cores",[]):
 x,y=c["origin_um"];cw,ch=c["outline_um"]
 if c.get("orient")in("R90","R270","MXR90","MYR90"):cw,ch=ch,cw
 a.add_patch(Rectangle((x,y),cw,ch,facecolor="#dde5ed",edgecolor="#64748b",linewidth=.4))
for n,x,y in rt["outs"]:
 a.plot(x,y,"o",color="#e07020",ms=4)
 if n=="rst_o_2":out=(x,y)
x,y=rt["in_um"];a.plot(x,y,"+",color="#0076bd",ms=12,mew=2)
a.set(xlim=(-70,w+70),ylim=(-60,h+60),xlabel="type X (µm)",ylabel="type Y (µm)",title="Root: cores and physical reset pins");a.set_aspect("equal")
for n,q,col in [("rst_o_2",out,"#e07020"),("arst_n",rt["in_um"],"#0076bd")]:
 b.add_patch(Rectangle((q[0]-.016,q[1]-.384),.032,.768,facecolor=col,edgecolor=col))
 b.annotate(f"{n}\n({q[0]:.3f}, {q[1]:.3f})",q,xytext=(q[0]-2.8,q[1]),arrowprops={"arrowstyle":"->","color":col},color=col,fontsize=10)
old=fix["old_entry"];b.plot(*old,"x",color="#bc2a35",ms=8);b.annotate("old entry overlapped output",old,xytext=(old[0]-3.3,old[1]+1),fontsize=9,color="#bc2a35")
b.axvline(w,color="black");b.set(xlim=(x-4,w+.5),ylim=(y-2,out[1]+2),xlabel="type X (µm)",ylabel="type Y (µm)",title="M7 pin rectangles: 0.032 × 0.768 µm");b.set_aspect("equal");b.grid(alpha=.2)
fig.suptitle("Explicit reset.in_sites repair — G0 PASS, max release 91; no route/SIGNED claim",fontsize=12)
fig.tight_layout();fig.savefig(r/"reset_entry_review.png",dpi=160)
print(r/"reset_entry_review.png")

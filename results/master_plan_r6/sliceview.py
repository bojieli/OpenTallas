import json,sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
s=json.load(open(sys.argv[1])); out=sys.argv[2]
win=[float(v) for v in sys.argv[3].split(",")] if len(sys.argv)>3 else None
W,H=s["outline_um"]
cr=[(h["origin_um"][0],h["origin_um"][1],h["origin_um"][0]+h["outline_um"][0],h["origin_um"][1]+h["outline_um"][1],h["inst"]) for h in s["hard_cores"]]
def ov(a,b): return a[0]<b[2]-1e-6 and b[0]<a[2]-1e-6 and a[1]<b[3]-1e-6 and b[1]<a[3]-1e-6
x0,y0,x1,y1=win if win else (0,0,W,H)
fig,ax=plt.subplots(figsize=(18,18*(y1-y0)/(x1-x0)+1))
ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1))
for c in cr:
    ax.add_patch(Rectangle((c[0],c[1]),c[2]-c[0],c[3]-c[1],fc="#9ab",ec="k",lw=0.4))
    if win: ax.text((c[0]+c[2])/2,(c[1]+c[3])/2,c[4],fontsize=6,ha="center")
nb=nbad=0
for b in s["bays"]:
    r=b["rect_um"]; bad=any(ov(r,c) for c in cr); nb+=1; nbad+=bad
    ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc=("red" if bad else "green"),ec="none",alpha=0.5))
for i in s.get("islands",[]):
    r=i["rect_um"]; ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc="magenta",ec="k",lw=0.5))
ax.set_xlim(x0-20,x1+20); ax.set_ylim(y0-20,y1+20); ax.set_aspect("equal")
ax.set_title(f"{s['type']} bays {nb}, over-core {nbad} (red), ok green; islands magenta")
plt.savefig(out,dpi=110,bbox_inches="tight"); print(s["type"],nb,nbad)

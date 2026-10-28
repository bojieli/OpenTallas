import json, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
R=sys.argv[1]; sys.path.insert(0,R+"/tools/die_plan")
import schema as S
from pathlib import Path
def draw(ax, f, ttl):
    raw=json.load(open(f)); P=S.Plan(raw,Path(f))
    t=raw["partition_types"]["kv3_hub_Wi"]; w,h=t["outline_um"]; x0,y0,_,_=P.rect("hub_Wi")
    ax.add_patch(plt.Rectangle((0,0),w,h,fill=False,ec="k"))
    for c in t["hard_cores"]:
        x,y=c["origin_um"]; a,b=c["outline_um"]; ax.add_patch(plt.Rectangle((x,y),a,b,fc="#f9c",ec="k",lw=.4))
    for s in t["ft_slots"]:
        cw,ch=s.get("bit_site_cell_um",[0,0])
        for st in s.get("bit_sites_um",[]):
            if not st: continue
            bx=(min(p[0] for p in st),min(p[1] for p in st),max(p[0] for p in st)+cw,max(p[1] for p in st)+ch)
            ax.add_patch(plt.Rectangle(bx[:2],max(bx[2]-bx[0],3),max(bx[3]-bx[1],3),fc="b",ec="b",alpha=.6))
    for pid,pr in P.ports.items():
        if "hub_Wi" not in (pr["src"]["part"],pr["dst"]["part"]): continue
        for b0,b1,wn in S.port_segments(pr):
            n=b1-b0; d=n/max(wn[1]-wn[0],.05); col="r" if d>8.0+1e-6 else "g"
            other=pr["dst"]["part"] if pr["src"]["part"]=="hub_Wi" else pr["src"]["part"]
            if other=="hub_C": ax.plot([w+8,w+8],[wn[0]-y0,wn[1]-y0],col,lw=5)
            elif other=="hub_Wo": ax.plot([-8,-8],[wn[0]-y0,wn[1]-y0],col,lw=5)
            else: ax.plot([wn[0]-x0,wn[1]-x0],[h+8,h+8],col,lw=5)
    ax.set_title(ttl+" (face windows: red >8 b/um, green <=8; blue = FT stations)",fontsize=9); ax.set_aspect("equal"); ax.set_xlim(-30,w+30); ax.set_ylim(-30,h+30)
fig,axs=plt.subplots(1,2,figsize=(18,12))
draw(axs[0],sys.argv[2],"D9a hm_r26q9"); draw(axs[1],sys.argv[3],"D9b hm_r26q9b")
plt.tight_layout(); plt.savefig(sys.argv[4],dpi=80)

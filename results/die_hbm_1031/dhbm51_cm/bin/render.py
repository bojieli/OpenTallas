import sys,json
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/die-hbm-49/tools/die_plan")
import kit_contract as K
ISL=json.load(open("/srv/opentallas-scratch2/claude/die-hbm-49/macros/islands.json"))
out=Path(sys.argv[1])
for kd in map(Path,sys.argv[2:]):
    fz=json.load(open(kd/"freeze.json")); mod=fz["module"]; W,H=fz["outline_um"]
    boxes,_=K.macro_boxes(kd); sites=[]; K.macro_boxes(kd,sites_out=sites)
    names=[l.split("{")[1].split("}")[0] for l in (kd/"macro_placement.tcl").read_text().splitlines() if l.strip().startswith("{")]
    s=8/max(W,H); fig,ax=plt.subplots(figsize=(max(4,W*s)+1.5,max(4,H*s)+1))
    ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.5,ec="k"))
    ax.add_patch(Rectangle((4.32,4.32),W-8.64,H-8.64,fill=False,lw=0.6,ls="--",ec="gray"))
    for i,b in enumerate(boxes):
        ax.add_patch(Rectangle((b[1],b[2]),b[3]-b[1],b[4]-b[2],fc="#7fa7d9",ec="#1f4e8c",lw=0.6))
        ax.add_patch(Rectangle((b[1]-4.32,b[2]-4.32),b[3]-b[1]+8.64,b[4]-b[2]+8.64,fill=False,ec="#1f4e8c",lw=0.3,ls=":"))
        if len(boxes)<=30:
            n=names[i].replace("\\","") if i<len(names) else b[0]
            ax.text((b[1]+b[3])/2,(b[2]+b[4])/2,n.split(".")[-3:] and ".".join(n.split(".")[-3:]),ha="center",va="center",fontsize=5)
    for xy,isl in ISL.get(mod,[]):
        ax.add_patch(Rectangle((isl[0],isl[1]),isl[2]-isl[0],isl[3]-isl[1],fc="red",alpha=0.6,ec="red"))
        ax.plot(*xy,"k+",ms=6)
    ps=json.load(open(kd/"pins.json")); col={"N":"g","S":"m","E":"orange","W":"c","I":"r"}
    for p in ps:
        f=p["face"]
        if f=="I": ax.plot(p["x"],p["y"],"r.",ms=2); continue
        x,y=p["x"],p["y"]; L=0.012*max(W,H)
        seg={"N":((x,x),(H,H-L)),"S":((x,x),(0,L)),"E":((W,W-L),(y,y)),"W":((0,L),(y,y))}[f]
        ax.plot(*seg,color=col[f],lw=0.3)
    cnt={f:sum(1 for p in ps if p["face"]==f) for f in "NSEWI"}
    ax.set_title(f"{kd.name}  {W:g}x{H:g}  macros {len(boxes)}\npins {cnt}  red=plan clock island",fontsize=7)
    ax.set_xlim(-5,W+5); ax.set_ylim(-5,H+5); ax.set_aspect("equal"); ax.tick_params(labelsize=6)
    fig.tight_layout(); fig.savefig(out/f"{mod}__{kd.name.rsplit(chr(95),1)[-1]}_macros.png",dpi=130); plt.close(fig)
    print("png",mod)

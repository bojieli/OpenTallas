import sys,json
sys.path.insert(0,"tools/die_plan")
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import schema as S, die_trial as DT
from pathlib import Path
pp="physical/die_plan/qwen_compute/die_plan_sliceclk.json"
P=S.Plan(S.load(pp),Path(pp)); site=DT.SiteMap(P)
T=json.load(open(sys.argv[1]+"/tree.json")); N={int(k):v for k,v in T["nodes"].items()}
def draw(ax,win):
    for r in site.forb:
        if r[2]>win[0] and r[0]<win[2] and r[3]>win[1] and r[1]<win[3]:
            ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color="0.85",lw=0))
    for rn,r in T["meta"]["slice_spine"]["regions"].items():
        b=r["box"]; ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,ec="k",lw=0.6))
    for i,n in N.items():
        if n["parent"] is None: continue
        p=N[n["parent"]]
        c="red" if n.get("spine")=="top" else "blue" if n.get("spine")=="column" else "green" if n.get("strip_root") else "0.4"
        lw=1.6 if n.get("spine") else 0.4
        ax.plot([p["x"],n["x"],n["x"]],[p["y"],p["y"],n["y"]],color=c,lw=lw)
    ax.set_xlim(win[0],win[2]); ax.set_ylim(win[1],win[3]); ax.set_aspect("equal")
fig,ax=plt.subplots(1,2,figsize=(22,10),gridspec_kw=dict(width_ratios=[1.2,1]))
draw(ax[0],(0,0,P.W,P.H)); ax[0].set_title("QC slice-spine probe: red top spine, blue slice columns, green strip legs, grey local; grey fill = cores+halo")
draw(ax[1],(16390,10000,18861,16000)); ax[1].set_title("E0 (std_bg_0_0) y 10-16 mm zoom: column + top spine")
fig.tight_layout(); fig.savefig(sys.argv[2],dpi=110)

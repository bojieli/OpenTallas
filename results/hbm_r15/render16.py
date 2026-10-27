import json,sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d=sys.argv[1]; p=json.load(open(d+"/die_plan.json"))
views=[("q_hub_nw",(0,0,1500,1300)),("q_hub_nw",(3900,0,5100,1300)),("NW_io",None),("q_spb0",None)]
fig,axs=plt.subplots(1,4,figsize=(24,8))
for ax,(tn,win) in zip(axs,views):
    t=p["partition_types"][tn]; W,H=t["outline_um"]
    ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1))
    for c in t.get("hard_cores",[]):
        x,y=c["origin_um"]; w,h=c["outline_um"]
        hl=c["module"] in ("ot_hfd_coll_q3_edge_core","hfd_ep_static")
        ax.add_patch(Rectangle((x,y),w,h,fc="tab:red" if hl else "tab:blue",alpha=.5 if hl else .25,ec="k",lw=.5))
        if win is None or (win[0]<=x<=win[2] and win[1]<=y<=win[3]): ax.text(x+2,y+h/2,c["inst"][:22],fontsize=6)
    for e in t.get("internal_stations",[]) or []:
        for r in e.get("regs_um",e.get("stations_um",[])) or []:
            if isinstance(r,(list,tuple)) and len(r)>=2: ax.plot(r[0],r[1],".",ms=1,color="g")
    if win: ax.set_xlim(win[0],win[2]); ax.set_ylim(win[1],win[3])
    else: ax.set_xlim(0,W); ax.set_ylim(0,H)
    ax.set_aspect("equal"); ax.set_title(f"{tn} C16 (red = re-lot q3 edge / EP)")
plt.tight_layout(); plt.savefig(sys.argv[2],dpi=110)

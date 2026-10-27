import sys,json,numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=json.load(open(sys.argv[1])); V=json.load(open(sys.argv[2])); Q=json.load(open(sys.argv[3])); out=sys.argv[4]
X0,X1,Y0,Y1=7000,17000,0,8000
fig,axs=plt.subplots(1,2,figsize=(22,9))
for ax,PL,tt in ((axs[0],P,"g0fix c6b5e29a + GRT congestion.rpt cells (red, size~overflow)"),(axs[1],Q,"B5 aef178ea (GRT0) same window")):
    for p in PL["partitions"]:
        t=PL["partition_types"][p["type"]]; w,h=t["outline_um"]; x,y=p["origin_um"]
        if x>X1 or x+w<X0 or y>Y1 or y+h<Y0: continue
        ax.add_patch(Rectangle((x,y),w,h,fill=True,fc="#e8eef8",lw=0.6,ec="#3060a0"))
        for c in t.get("hard_cores") or []:
            cx,cy=c["origin_um"]; cw,ch=c["outline_um"]
            o=p.get("orient","R0")
            if o in("MX","R180"): cy=h-cy-ch
            if o in("MY","R180"): cx=w-cx-cw
            ax.add_patch(Rectangle((x+cx,y+cy),cw,ch,color="0.75",lw=0))
        ax.text(x+w/2,y+h/2,p["name"],fontsize=7,ha="center",va="center",color="#102050")
    ax.set_xlim(X0,X1); ax.set_ylim(Y0,Y1); ax.set_aspect("equal"); ax.set_title(tt)
xs=[v["bb"][0] for v in V]; ys=[v["bb"][1] for v in V]; s=[2+v["ov"] for v in V]; c=["r" if v["dir"]=="Horizontal" else "m" for v in V]
axs[0].scatter(xs,ys,s=s,c=c,alpha=.6,linewidths=0)
fig.tight_layout(); fig.savefig(out,dpi=100)

import sys,json
from pathlib import Path
R=sys.argv[1]; sys.path.insert(0,R+"/tools/die_plan"); sys.path.insert(0,R)
import schema as S
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
P=S.Plan(S.load(sys.argv[2]),Path(sys.argv[2]))
parts=sys.argv[3].split(","); out=sys.argv[4]
fig,ax=plt.subplots(figsize=(14,10))
for part in parts:
    x0,y0,x1,y1=P.rect(part); ax.add_patch(plt.Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec="k",lw=1.5)); ax.text(x0+5,y1-30,part,fontsize=9)
    for bx in S.placed_macro_boxes(P.ptype(part)).values():
        p1=P.to_die(part,(bx[0],bx[1]));p2=P.to_die(part,(bx[2],bx[3]))
        ax.add_patch(plt.Rectangle((min(p1[0],p2[0]),min(p1[1],p2[1])),abs(p2[0]-p1[0]),abs(p2[1]-p1[1]),fc="#f4a",ec="none",alpha=.6))
    for s in P.ptype(part).get("ft_slots",[]):
        w,h=s.get("bit_site_cell_um",(1.4,.27))
        for st in s.get("bit_sites_um",[]):
            xs=[P.to_die(part,(x,y)) for x,y in st[::25]]
            ax.plot([q[0] for q in xs],[q[1] for q in xs],",",color="b")
for pid,pr in P.ports.items():
    if pr["src"]["part"] in parts or pr["dst"]["part"] in parts:
        for b,l,c in P.port_pins(pid)[::20]:
            part=P.face_part(pid); x0,y0,x1,y1=P.rect(part); f=pr["face"]
            xy={"E":(x1,c),"W":(x0,c),"N":(c,y1),"S":(c,y0)}[f]
            ax.plot(*xy,".",ms=2,color="g" if "_d6_" in pid else "0.5")
ax.set_aspect("equal"); ax.autoscale(); plt.tight_layout(); plt.savefig(out,dpi=110)

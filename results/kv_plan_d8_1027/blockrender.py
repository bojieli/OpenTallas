"""KV-PLAN-DELTA-8: render the W hroot move corridor (hub row + row 7) with hard cores, existing port windows on the
pv_S_7|hgi_WS_7 and hgi_WS_7|hg_WS_7 faces, and the >=140-um core-clear windows a 1118-bit bundle needs at 8 b/um."""
import sys
from pathlib import Path
R=sys.argv[1]; sys.path.insert(0,R+"/tools/die_plan"); sys.path.insert(0,R)
import schema as S
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=S.Plan(S.load(sys.argv[2]),Path(sys.argv[2])); out=sys.argv[3]
parts=["hub_Wo","hub_Wi","hub_C","hg_WS_7","hgi_WS_7","pv_S_7","hg_WS_6","hgi_WS_6","pv_S_6"]
fig,ax=plt.subplots(figsize=(14,10))
for n in parts:
    if n not in P.parts: continue
    x0,y0,x1,y1=P.rect(n); ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,lw=1.5,ec="k"))
    ax.text((x0+x1)/2,y1-60,f"{n}\n{P.parts[n]['type']}",ha="center",va="top",fontsize=8)
    for bx in S.placed_macro_boxes(P.ptype(n)).values():
        p1=P.to_die(n,(bx[0],bx[1]));p2=P.to_die(n,(bx[2],bx[3]))
        a,b=min(p1[0],p2[0]),min(p1[1],p2[1]); ax.add_patch(Rectangle((a,b),abs(p2[0]-p1[0]),abs(p2[1]-p1[1]),fc="0.75",ec="0.5",lw=.3))
for a,b in (("pv_S_7","hgi_WS_7"),("hgi_WS_7","hg_WS_7"),("hub_C","pv_S_7"),("hg_WS_7","hub_Wo")):
    for pid,pr in P.ports.items():
        if {pr["src"]["part"],pr["dst"]["part"]}=={a,b}:
            pins=P.port_pins(pid); cs=[c for _,_,c in pins]
            ax0,ay0,ax1,ay1=P.rect(a); bx0,by0,bx1,by1=P.rect(b)
            if abs(ax0-bx1)<1e-3 or abs(ax1-bx0)<1e-3:
                x=ax0 if abs(ax0-bx1)<1e-3 else ax1; ax.plot([x,x],[min(cs),max(cs)],lw=6,c="tab:blue",solid_capstyle="butt")
                if len(cs)>200: ax.text(x+15,(min(cs)+max(cs))/2,f"{pid} {len(cs)}b",fontsize=7,color="tab:blue")
            else:
                y=ay0 if abs(ay0-by1)<1e-3 else ay1; ax.plot([min(cs),max(cs)],[y,y],lw=6,c="tab:blue",solid_capstyle="butt")
# free >=140 um core-clear windows (facediag output passed as argv[4:] "x lo hi")
for spec in sys.argv[4:]:
    x,lo,hi=map(float,spec.split(":")); ax.plot([x,x],[lo,hi],lw=10,c="tab:green",alpha=.5,solid_capstyle="butt")
    ax.text(x-15,(lo+hi)/2,f"free {hi-lo:.0f}um",fontsize=7,color="green",ha="right")
ax.set_xlim(1850,6700); ax.set_ylim(9050,13900); ax.set_aspect("equal")
ax.set_title("KV-PLAN-DELTA-8: W hroot move corridor on hm_r26q5c39 (grey=hard cores, blue=existing port windows, green=core-clear free face spans)",fontsize=9)
fig.tight_layout(); fig.savefig(out,dpi=110); print(out)

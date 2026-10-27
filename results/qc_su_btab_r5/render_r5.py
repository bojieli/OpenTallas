# QC-SU-BTAB-R5 render: plan (render_r3 layers) over the r5 3_place std cells (grey dots; macro-pin flops orange; r5_e_logic
# read-mux members blue) + the planned M2-M5 corner keep-offs (black boxes, from pre_grt_r5.tcl geometry).
import json,sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=json.load(open(sys.argv[1])); cells=sys.argv[2]; out=sys.argv[3]; mem=set(open(sys.argv[4]).read().split()) if len(sys.argv)>4 else set()
fig,ax=plt.subplots(figsize=(14,10))
xs={"o":[],"mpf":[],"m":[],"ff":[]}
for l in open(cells):
    n,m,k,x,y,w=l.rstrip("\n").split("\t")
    kk="m" if n in mem else ("mpf" if k=="mpf" else ("ff" if k=="ff" else "o"))
    xs[kk].append((float(x),float(y)))
for kk,c,s in (("o","#999",0.6),("ff","#2a2",0.8),("mpf","orange",0.6),("m","blue",1.0)):
    if xs[kk]: ax.scatter([a for a,b in xs[kk]],[b for a,b in xs[kk]],s=s,c=c,lw=0,label=f"{kk} {len(xs[kk])}")
mac=[]
for line in open(r["geo"]):
    f=line.split()
    if f and f[0]=="CORE": c=list(map(float,f[1:5])); ax.add_patch(Rectangle((c[0],c[1]),c[2]-c[0],c[3]-c[1],fill=False))
    if f and f[0]=="MACRO":
        x0,y0,x1,y1=map(float,f[3:7]); mac.append((x0,y0,x1,y1)); ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc="#ddd",ec="k",alpha=0.6)); ax.plot(float(f[8]),float(f[9]),"k^",ms=6)
for x0,y0,x1,y1 in mac:
    for xa in (x1, x0-1.08):
        for ya in (y1-0.30, y0-2.16): ax.add_patch(Rectangle((xa,ya),1.08,2.46,fc="black",ec="black"))
for q in r["gates"]["G5_sram_structure"]["pin_columns_um"]:
    ax.add_patch(Rectangle((q[0],q[1]),q[2]-q[0]+4.32,q[3]-q[1],fc="orange",alpha=0.12,ec="orange",ls="--"))
col={"L1":"red","L2":"blue","L3":"green"}
for e in r["gates"]["G4_detour_sites"]["edges"]:
    p=r["edge_paths_um"].get(e["edge"])
    if p: ax.plot([a[0] for a in p],[a[1] for a in p],"-",color=col[e["level"]],lw=1.8 if e["level"]=="L1" else 0.9)
    for rp in e.get("repeaters",[]): ax.plot(*rp["xy"],"s",color="purple",ms=4)
for i in r["gates"]["G2_island_rows"]["islands"]:
    R=i["rect_um"]; ax.add_patch(Rectangle((R[0],R[1]),R[2]-R[0],R[3]-R[1],fc="magenta",ec="k"))
p=r["gates"]["P_asbuilt"]
ax.legend(loc="upper left",fontsize=7,markerscale=8); ax.set_aspect("equal")
ax.set_title(f"{r['name']} k={r['k']} {r['verdict']}  as-built pred TT {p['TT']['mean']} w{p['TT']['window']}  FF early {p['FF_early']['mean']} w{p['FF_early']['window']} (plan model, UNCHECKED)\n"
  "r5 3_place: grey logic, orange macro-pin flops, blue E read-mux (region x255-340 at GPL), green other flops; dashed = leg keep-off (pin column +4.32); black = M2-M5 corner keep-offs",fontsize=8)
plt.savefig(out,dpi=110,bbox_inches="tight")

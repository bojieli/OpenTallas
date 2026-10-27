import json,sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=json.load(open(sys.argv[1])); geo=r["geo"]
fig,ax=plt.subplots(figsize=(13,9.5))
for line in open(geo):
    f=line.split()
    if f and f[0]=="CORE": c=list(map(float,f[1:5])); ax.add_patch(Rectangle((c[0],c[1]),c[2]-c[0],c[3]-c[1],fill=False))
    if f and f[0]=="MACRO":
        x0,y0,x1,y1=map(float,f[3:7]); ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc="#bbb",ec="k")); ax.plot(float(f[8]),float(f[9]),"k^",ms=6)
for q in r["gates"]["G5_sram_structure"]["pin_columns_um"]:
    ax.add_patch(Rectangle((q[0],q[1]),q[2]-q[0],q[3]-q[1],fc="orange",alpha=0.3,ec="none"))
col={"L1":"red","L2":"blue","L3":"green"}
for e in r["gates"]["G4_detour_sites"]["edges"]:
    p=r["edge_paths_um"].get(e["edge"])
    if p: ax.plot([a[0] for a in p],[a[1] for a in p],"-",color=col[e["level"]],lw=1.6 if e["level"]=="L1" else 0.9)
    for rp in e.get("repeaters",[]): ax.plot(*rp["xy"],"s",color="purple",ms=4)
for i in r["gates"]["G2_island_rows"]["islands"]:
    R=i["rect_um"]; ax.add_patch(Rectangle((R[0],R[1]),R[2]-R[0],R[3]-R[1],fc="magenta",ec="k"))
for v in r["gates"]["G3_cell_rows"].get("illegal",[]): ax.plot(*v["xy"],"rx",ms=8)
p=r["gates"].get("P_phys")
ax.set_aspect("equal"); ax.set_title(f"{r['name']} k={r['k']} {r['verdict']}  uf_phys TT rise {p['TT_rise']['mean']} w{p['TT_rise']['window']}  FF early {p['FF_early']['mean']} w{p['FF_early']['window']}\nL1 red, L2 blue, L3 green (maze legs), repeaters purple, islands magenta, SRAM clock-pin columns orange (node keepout)",fontsize=9)
plt.savefig(sys.argv[2],dpi=110,bbox_inches="tight")

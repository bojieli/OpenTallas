"""DIE-QC-50/gen47b GEOM review crop: fresh island-holed lower OBS (red, from the bound-source export), clock cells grey,
provider FF green / comb orange, partitions blue. usage: PLACEMENTS FRESH_CONSTRAINTS PLAN OUT.png STAGE|cx,cy HALF_UM"""
import json,sys,matplotlib
matplotlib.use("Agg");import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
PL,CON,PLAN,OUT,where,half=sys.argv[1:7];half=float(half)
p=json.load(open(PL));D=p["dbu"];g=json.load(open(CON));plan=json.load(open(PLAN))
if "," in where: cx,cy=map(float,where.split(","))
else:
  cc=[c["bbox_dbu"] for c in p["cells"] if c["stage"]==where];cx=sum(r[0]+r[2] for r in cc)/2/len(cc)/D;cy=sum(r[1]+r[3] for r in cc)/2/len(cc)/D
lim=[cx-half,cy-half,cx+half,cy+half]
def inb(r): return r[2]>=lim[0] and r[0]<=lim[2] and r[3]>=lim[1] and r[1]<=lim[3]
f,ax=plt.subplots(figsize=(11,11))
for q in plan["partitions"]:
  w,h=plan["partition_types"][q["type"]]["outline_um"]
  if q.get("orient") in ("R90","R270","MXR90","MYR90"): w,h=h,w
  ax.add_patch(plt.Rectangle(tuple(q["origin_um"]),w,h,fill=False,lw=1.5,ec="tab:blue"))
ob=[plt.Rectangle((r[2]/D,r[3]/D),(r[4]-r[2])/D,(r[5]-r[3])/D) for r in g["actual_lower_OBS"] if inb([v/D for v in r[2:6]])]
ax.add_collection(PatchCollection(ob,fc=(1,0,0,.18),ec="none"))
ex=[plt.Rectangle((e[2]/D,e[3]/D),(e[4]-e[2])/D,(e[5]-e[3])/D) for e in g["existing_cells"] if inb([v/D for v in e[2:6]])]
ax.add_collection(PatchCollection(ex,fc="0.55",ec="0.2",lw=.3))
ff=[];cb=[]
for c in p["cells"]:
  r=[v/D for v in c["bbox_dbu"]]
  if inb(r): (ff if c["sequential"] else cb).append(plt.Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1]))
ax.add_collection(PatchCollection(ff,fc="tab:green",ec="k",lw=.2));ax.add_collection(PatchCollection(cb,fc="tab:orange",ec="k",lw=.2))
ax.set_xlim(lim[0],lim[2]);ax.set_ylim(lim[1],lim[3]);ax.set_aspect("equal")
ax.set_title(f"gen47b fresh source {where} @({cx:.1f},{cy:.1f}) +-{half}um: red=abstract M1-M3 OBS, grey=clock, green=FF, orange=comb\n({len(ff)} FF, {len(cb)} comb, {len(ex)} clock, {len(ob)} OBS rects)",fontsize=9)
f.tight_layout();f.savefig(OUT,dpi=100);print("ok",len(ff),len(cb),len(ex),len(ob))

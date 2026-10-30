"""Render a crop of the gen47 provider placement proposal: provider cells (FF green / comb orange), clock cells grey, partitions."""
import json,sys,matplotlib
matplotlib.use("Agg");import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
PL,CON,PLAN,OUT=sys.argv[1:5];cx,cy,half=map(float,sys.argv[5:8])
p=json.load(open(PL));D=p["dbu"];g=json.load(open(CON));plan=json.load(open(PLAN))
lim=[cx-half,cy-half,cx+half,cy+half]
def inb(r): return r[2]>=lim[0] and r[0]<=lim[2] and r[3]>=lim[1] and r[1]<=lim[3]
f,ax=plt.subplots(figsize=(11,11))
for q in plan["partitions"]:
  w,h=plan["partition_types"][q["type"]]["outline_um"]
  if q.get("orient") in ("R90","R270","MXR90","MYR90"): w,h=h,w
  ax.add_patch(plt.Rectangle(tuple(q["origin_um"]),w,h,fill=False,lw=1,ec="tab:blue"))
ex=[]
for e in g.get("existing",g.get("existing_cells",[])):
  r=[v/D for v in e[2:6]]
  if inb(r): ex.append(plt.Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1]))
ax.add_collection(PatchCollection(ex,fc="0.6",ec="0.3",lw=.3))
ff=[];cb=[]
for c in p["cells"]:
  r=[v/D for v in c["bbox_dbu"]]
  if inb(r): (ff if c["sequential"] else cb).append(plt.Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1]))
ax.add_collection(PatchCollection(ff,fc="tab:green",ec="k",lw=.2));ax.add_collection(PatchCollection(cb,fc="tab:orange",ec="k",lw=.2))
ax.set_xlim(lim[0],lim[2]);ax.set_ylim(lim[1],lim[3]);ax.set_aspect("equal")
ax.set_title(f"gen47 provider proposal crop @({cx},{cy}) +-{half}um: grey=clock cells, green=FF, orange=comb ({len(ff)} FF, {len(cb)} comb, {len(ex)} clock)")
f.tight_layout();f.savefig(OUT,dpi=100);print("ok",len(ff),len(cb),len(ex))

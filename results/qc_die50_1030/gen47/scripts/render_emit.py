"""Render gen47 START stages (emitted sites) + START edges over the die, plus a zoom crop."""
import json,sys,matplotlib
matplotlib.use("Agg");import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
EM,BIND,PROOF,PLAN,OUT=sys.argv[1:6]
st=json.load(open(EM+"/start_stages.json"))["stages"];by={s["region"]:s for s in st}
sp=json.load(open(BIND))["start_ports"];taps={t["port"]:t for t in json.load(open(PROOF))["taps"]}
plan=json.load(open(PLAN))
def xy(reg,tap):
  if reg in by:r=by[reg]["rect_um"];return (r[0],r[1])
  return tuple(taps[tap]["xy_um"])
segs=[];long=[]
for pid,c in sp.items():
  a=xy(c["src"],c.get("launch"));b=xy(c["dst"],c.get("capture"));segs.append([a,b])
  if abs(a[0]-b[0])+abs(a[1]-b[1])>380: long.append([a,b])
def draw(ax,lim=None):
  for p in plan["partitions"]:
    w,h=plan["partition_types"][p["type"]]["outline_um"]
    if p.get("orient") in ("R90","R270","MXR90","MYR90"): w,h=h,w
    ax.add_patch(plt.Rectangle(tuple(p["origin_um"]),w,h,fill=False,lw=.3,ec="0.6"))
  ax.add_collection(LineCollection(segs,lw=.3,colors="tab:blue"))
  ax.add_collection(LineCollection(long,lw=.8,colors="tab:red"))
  xs=[s["rect_um"][0] for s in st];ys=[s["rect_um"][1] for s in st]
  ax.scatter(xs,ys,s=1.5 if lim is None else 8,c=["k" if s["root"] else ("tab:orange" if s["flops"]==5 else "tab:green") for s in st])
  tx=[t["xy_um"][0] for t in taps.values()];ty=[t["xy_um"][1] for t in taps.values()]
  ax.scatter(tx,ty,s=.5 if lim is None else 4,c="tab:purple",marker="x")
  if lim: ax.set_xlim(lim[0],lim[2]);ax.set_ylim(lim[1],lim[3])
  else: ax.set_xlim(0,31216.32);ax.set_ylim(0,26265.6)
  ax.set_aspect("equal")
f,ax=plt.subplots(1,2,figsize=(22,10));draw(ax[0]);ax[0].set_title("gen47 START stages (green=retime 7FF, orange=branch 5FF, black=root) + START edges (red >380um), purple x = native taps")
r=by["st:h"]["rect_um"];draw(ax[1],[r[0]-1500,r[1]-1500,r[0]+1500,r[1]+1500]);ax[1].set_title("zoom 3x3 mm around root stage")
f.tight_layout();f.savefig(OUT,dpi=110);print("ok",len(segs),len(long))

import json,sys
from pathlib import Path
import matplotlib;matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
B=Path(sys.argv[1]);C=json.load(open(B/"place.json"));R=json.load(open(B/"REPAIR.json"))
base=json.load(open(B.parent/"p128_bankrepair"/"REPAIR.json"))
fig,axs=plt.subplots(1,3,figsize=(16,7))
rects=[[14567.04,18048.96,14904,18463.68],[17046.72,17323.2,17383.68,17737.92],[18489.6,17314.56,18826.56,17729.28]]
for ax,rec,r in zip(axs,base["repairs"],rects):
 name=rec["cell"];a,b,c,d=r;ax.add_patch(Rectangle((a,b),c-a,d-b,color="gray",alpha=.4))
 selected=[name]+[n for b in rec["banks"] for n in C if n.startswith("gb_"+b["site"]+"_")]
 for n in selected:
  q=C[n];ax.add_patch(Rectangle((q["x"],q["y"]),1.62,.27,color="crimson" if n==name else "blue"))
  if n!=name:ax.plot([C[name]["x"]+1.728,q["x"]+.162],[C[name]["y"]+.135,q["y"]+.135],color="green",linewidth=.25)
 ax.set_xlim(a-80,c+80);ax.set_ylim(b-230,d+100);ax.set_aspect("equal");ax.set_title(name+"\nreal soft-channel node + compact banks",fontsize=9)
fig.suptitle("S81 graded clock joint placement; gray actual macro; green pin-to-pin distances <=405um\nGeometry only: no timing/routing claim; full metal encoder and RCX remain open")
fig.tight_layout();fig.savefig(B/"joint_geometry.png",dpi=160)

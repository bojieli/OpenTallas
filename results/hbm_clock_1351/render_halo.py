import json
from pathlib import Path
import matplotlib;matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d=Path(__file__).parent;p=json.loads((d/"vmdel_centre_halo.tcl.json").read_text());q=json.loads((d/"candidate.json").read_text())
fig,ax=plt.subplots(figsize=(10,8))
ax.add_patch(Rectangle((0,0),142.56,112.32,fill=False,color="black"))
ax.add_patch(Rectangle((4.32,4.32),133.92,103.68,fill=False,ls=":",ec="gray"))
for l,b,r,t in q["macros"]:
 ax.add_patch(Rectangle((l-4.32,b-4.32),r-l+8.64,t-b+8.64,fill=False,ls="--",ec="orange"))
 ax.add_patch(Rectangle((l,b),r-l,t-b,fc="orange",alpha=.35,ec="brown"))
pts=[m["planned"] for m in q["moves"]];ax.scatter(*zip(*pts),s=1,c="gray",label="planned FF demand positions")
ax.scatter(*zip(*[n[2] for n in p["nodes"]]),s=10,c="blue",label="planned clock nodes")
ax.scatter(71.28,56.16,marker="*",s=150,c="red",label="proposedM5clock entry")
ax.text(71.28,58, "2.676um after4.32um halos",ha="center",fontsize=8)
ax.legend(fontsize=8,loc="upper left")
ax.set(aspect="equal",xlim=(-3,146),ylim=(-3,116),xlabel="um",ylabel="um")
ax.set_title("Vmdel142.56x112.32 candidate: PLANNED demand, not actual placement\n2SRAM unchanged; centralclockcorridor; 2201FF; noRTL/cyclechange")
fig.savefig(d/"vmdel_centre_halo.png",dpi=150,bbox_inches="tight")

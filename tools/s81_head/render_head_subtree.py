import json
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plan=json.load(open(sys.argv[1]))
fig,axes=plt.subplots(2,1,figsize=(14,9))
for ax,bank in zip(axes,plan["banks"]):
    x0,y0,x1,y1=bank["macro_box"]
    ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,color="0.9"))
    ax.text((x0+x1)/2,y0+30,f"ROM{bank['bank']}\nmacro CK9.3458fF",ha="center")
    root=bank.get("root_legal_xy",bank["root_desired_xy"])
    ax.scatter(*root,c="black",marker="s",s=70,zorder=5)
    ax.text(root[0],root[1]-3,"common local root",ha="center")
    for side,color in (("left","#2966a0"),("right","#c96729")):
        sr=bank.get(f"{side}_legal_xy",bank["side_roots"][side])
        ax.plot([root[0],sr[0],sr[0]],[root[1],root[1],sr[1]],c=color,lw=2)
        leaves=[n for n in bank["leaves"] if n["side"]==side]
        ax.scatter(*sr,c=color,marker="s",s=50,zorder=5)
        for n in leaves:
            xy=n.get("legal_xy",n["desired_xy"])
            ax.plot([sr[0],sr[0],xy[0]],[sr[1],xy[1],xy[1]],c=color,alpha=.5,lw=.8)
            ax.scatter(*xy,c=color,marker="D" if n["kind"]=="macro" else "o",s=35,zorder=6)
            ax.annotate(f"{len(n['sinks'])} {n['kind']} / {n['load_ff']:.2f}fF",xy,
                xytext=(-4 if side=="left" else 4,4),textcoords="offset points",
                fontsize=6,ha="right" if side=="left" else "left")
        ax.text(sr[0],sr[1]-7,f"{len(leaves)} buffered leaves\nimmediate Cin {bank.get('immediate_side_loads_ff',{}).get(side,0):.2f}fF +wire RC\ndescendant sinks {sum(n['load_ff'] for n in leaves):.2f}fF",
            color=color,ha="center",fontsize=9)
    ax.set_xlim(40,240);ax.set_ylim(y0-22,y0+45);ax.set_aspect("equal");ax.grid(alpha=.15)
    ax.set_title(f"ROM{bank['bank']}: actual 256 capture +12 address +1 CE +macro; planned equal-depth buffered grouping")
fig.suptitle("HEAD structural successor proposal — candidate sites clear actual rows/cells/6um halo; master sizing/TT/FF/CPPR NOT approved",fontsize=12)
fig.tight_layout(rect=(0,0,1,.96));fig.savefig(sys.argv[2],dpi=160)

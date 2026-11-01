import json,matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
r=Path(__file__).resolve().parent
s=json.load(open(r/"red_ref/slices/qfd_dv_s5_red2_leaf.json"));p=json.load(open(r/"red_ref/pins.json"))
fig,ax=plt.subplots(figsize=(10,10));ax.add_patch(Rectangle((0,0),276.48,276.48,fill=False,lw=2))
nodes={n["name"]:n for n in s["core_tree"]["nodes"]}
for n in nodes.values():
 if n["parent"] in nodes:
  a=nodes[n["parent"]]["xy_um"];b=n["xy_um"];ax.plot([a[0],b[0]],[a[1],b[1]],color="#b8c5d2",lw=.35,zorder=1)
for label,key,size,col in [("Root","root",65,"#d1495b"),("8 trunks","t",28,"#e08e45"),("64 regional","r",12,"#00798c"),("576 leaves (59/60 FF)","l",4,"#30638e")]:
 ns=[n for n in nodes.values() if (n["name"] == "red_ck_root" if key == "root" else n["name"].startswith("red_ck_"+key) and n["name"] != "red_ck_root")]
 ax.scatter([n["xy_um"][0] for n in ns],[n["xy_um"][1] for n in ns],s=size,c=col,label=label,zorder=3)
for side,col,label in [("E","#6b8e23","160 E inputs"),("W","#8f5b88","132 W inputs"),("S","#333333","60 S outputs")]:
 ns=[n for n in p["pins"] if n["face"]==side and n["name"] not in ["ck","rst_n"]]
 ax.scatter([n["x"] for n in ns],[n["y"] for n in ns],s=4,c=col,label=label,zorder=4)
ax.scatter([138.252],[138.24],s=160,marker="+",c="red",label="Centered M5 ck (M9 to M5 entry)",zorder=5)
ax.add_patch(Rectangle((133.92,133.92),8.64,8.64,fill=False,edgecolor="red"))
ax.annotate("center root / entry",(138.24,138.24),(145,151),fontsize=9)
ax.set(xlim=(-12,289),ylim=(-12,289),xlabel="um",ylabel="um",aspect="equal")
ax.set_title("RED HARD_PINREG=1 | 276.48 x 276.48 um | 207,601 mapped std cells\n352/352 registered data pins | 34,225 clock sinks | 649-buffer 4-level tree\n250 TT / 202.5 FF ps TARGET ONLY; placement and NLDM timing pending")
ax.legend(loc="upper center",bbox_to_anchor=(.5,-.08),ncol=2,fontsize=9)
fig.savefig(r/"red_child_center_plan.png",dpi=150,bbox_inches="tight")

import json,sys,matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,axs=plt.subplots(2,1,figsize=(14,15))
mac=[(69.12,57.888),(172.8,57.888),(276.48,57.888),(69.12,108),(172.8,108),(276.48,108)]
for ax,(f,W,ex,title) in zip(axs,[("old.json",440.64,220.32,"d31s 440.64x207.36"),("new.json",414.72,207.36,"d35a 414.72x207.36")]):
    P=json.load(open(f))
    ax.add_patch(Rectangle((0,0),W,207.36,fill=False,lw=2))
    for x,y in mac: ax.add_patch(Rectangle((x,y),94.824,41.064,color="#bbb"))
    ax.add_patch(Rectangle((ex-4.32,99.36),8.64,8.64,color="orange"))
    for q in P:
        n=q["name"]; c="red" if n.startswith("clk") else ("magenta" if n.startswith("rst") else ("green" if n.startswith("strap") else "blue"))
        ax.plot(q["x"],q["y"],".",ms=3 if c=="blue" else 7,color=c)
    ax.set_xlim(-10,450); ax.set_ylim(-10,217); ax.set_aspect("equal"); ax.set_title(title+"  red=clk magenta=rst green=strap orange=clock entry island grey=SRAM")
plt.tight_layout(); plt.savefig("lane_exp0_id_pins.png",dpi=80)

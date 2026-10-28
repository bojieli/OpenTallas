import json,re,sys,matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=json.load(open("plan_rs_fb1.json"))
ty=P["partition_types"]
fig,axs=plt.subplots(1,2,figsize=(20,11))
col={"landing_mon":"red","fwd_clock":"blue","reset_start":"green"}
G=open("out_TT/route_TT.guide").read().split("\n")
segs={k:[] for k in col}; cnt={k:0 for k in col}
i=0
while i<len(G):
    l=G[i].strip()
    m=re.match(r"n\d+_(\w+)$",l)
    if m and i+1<len(G) and G[i+1].strip()=="(":
        k=m.group(1); i+=2
        while G[i].strip()!=")":
            if k in col:
                x0,y0,x1,y1,ln=G[i].split(); segs[k].append((float(x0)/1000,float(y0)/1000,float(x1)/1000,float(y1)/1000,ln))
            i+=1
        if k in col: cnt[k]+=1
    i+=1
xs=[p["origin_um"][0]+max(ty[p["type"]]["outline_um"]) for p in P["partitions"]]
ys=[p["origin_um"][1]+max(ty[p["type"]]["outline_um"]) for p in P["partitions"]]
for ax,zoom in zip(axs,[None,(7000,10500,1000,4500)]):
    for p in P["partitions"]:
        w,h=ty[p["type"]]["outline_um"]
        ax.add_patch(Rectangle(p["origin_um"],w,h,fill=False,lw=0.3,ec="0.5"))
    for k,c in col.items():
        for x0,y0,x1,y1,ln in segs[k]:
            ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,color=c,alpha=0.6,lw=0))
    if zoom: ax.set_xlim(zoom[0],zoom[1]); ax.set_ylim(zoom[2],zoom[3])
    else: ax.set_xlim(0,max(xs)); ax.set_ylim(0,max(ys))
    ax.set_aspect("equal")
axs[0].set_title("HEAD real-netlist GRT TT guides: landing_mon(red) %d fwd_clock(blue) %d reset_start(green) %d"%(cnt["landing_mon"],cnt["fwd_clock"],cnt["reset_start"]))
axs[1].set_title("zoom sp5/host area")
plt.savefig("guides_landing.png",dpi=90,bbox_inches="tight")
print(cnt,{k:len(v) for k,v in segs.items()})

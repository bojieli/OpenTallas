import json,sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
d=sys.argv[1]; p=json.load(open(d+"/die_plan.json")); t=p["partition_types"]["root"]
fig,ax=plt.subplots(figsize=(6,18)); W,H=t["outline_um"]
ax.add_patch(plt.Rectangle((0,0),W,H,fill=False,lw=2))
for c in t["contents"]:
    if c["inst"]=="u_tkm_SW" or "origin_um" not in c: continue
    x,y=c["origin_um"]; w,h=c["outline_um"]; ax.add_patch(plt.Rectangle((x,y),w,h,fc="#ddd",ec="#999",lw=.5,ls="--")); ax.text(x+2,y+2,c["inst"][2:],fontsize=4,color="#666")
for c in t["hard_cores"]:
    x,y=c["origin_um"]; w,h=c["outline_um"]; tk="tkm" in c["inst"]
    fc="#9cf" if "tile" in c["inst"] else ("#f96" if tk else "#cfc")
    ax.add_patch(plt.Rectangle((x,y),w,h,fc=fc,ec="k",lw=.6))
    lab=c["inst"].replace("u_tkm_SW_","").replace("u_","")+("/"+c["orient"] if c.get("orient") else "")
    ax.text(x+w/2,y+h/2,lab,fontsize=5,ha="center",va="center")
for s in t["internal_stations"]:
    pts=[s["from_um"]]+s["regs_um"]+[s["to_um"]]
    tk="tkm" in s["conn"]
    ax.plot([q[0] for q in pts],[q[1] for q in pts],"-",lw=.8 if tk else .3,color="r" if tk else "#7a7",alpha=.9 if tk else .4)
    ax.plot([q[0] for q in s["regs_um"]],[q[1] for q in s["regs_um"]],".",ms=3 if tk else 1,color="r" if tk else "#7a7")
R=[(c["origin_um"][0],c["origin_um"][1],c["outline_um"][0],c["outline_um"][1]) for c in t["hard_cores"]]
nbad=0
for s_ in t["internal_stations"]:
    for q in s_["regs_um"]:
        if any(r[0]<q[0]<r[0]+r[2] and r[1]<q[1]<r[1]+r[3] for r in R):
            ax.plot(q[0],q[1],"x",ms=5,color="k",mew=1.2); nbad+=1
for b,(y,txt) in {"L80m":(414,"L80m"),"L12m":(712,"L12m"),"L74m":(1203,"L74m"),"L64m":(1664,"L64m"),"L89m":(1909,"L89m"),"L13m":(2196,"L13m"),"L62m":(3529,"L62m")}.items():
    ax.annotate(txt,(1382.4,y),(1420,y),fontsize=5,color="b",arrowprops=dict(arrowstyle="->",color="b",lw=.5))
for nm,(y0,y1) in {"L12 W(B2p)":(430.9,992.8),"L74 W(B2p)":(993.3,1412.0),"L13 W(B2p)":(1915.4,2477.3)}.items():
    ax.plot([-14,-14],[y0,y1],lw=3,color="green"); ax.text(-20,(y0+y1)/2,nm,fontsize=5,rotation=90,ha="right",va="center",color="green")
for nm,(y0,y1) in {"named L74":(1728.5,2147.2),"named L12":(2169.8,2731.7),"named L13":(2732.2,3294.1)}.items():
    ax.plot([-30,-30],[y0,y1],lw=1.5,color="orange",ls=":"); ax.text(-36,(y0+y1)/2,nm,fontsize=4,rotation=90,ha="right",va="center",color="orange")
for f in t["ft_slots"]:
    r=f["regs_um"]; ax.plot([q[0] for q in r],[q[1] for q in r],"-o",ms=1.5,lw=.6,color="darkorange",alpha=.8)
for nm,(y0,y1) in {"L4 FT":(2486.9,3494.5),"L150 FT":(4193.3,4395.1),"L9/L63 FT":(3646.3,4146.7)}.items():
    ax.plot([W+6,W+6],[y0,y1],lw=2,color="darkorange"); ax.plot([-6,-6],[y0,y1],lw=2,color="darkorange")
    ax.text(W+10,(y0+y1)/2,nm,fontsize=4,color="darkorange",va="center")
ax.set_title(f"root B2p_r3 (R3 re-pack, no outline change): {nbad} station sites in hard cores; FT sites drawn as orange dots",fontsize=6)
for tp in t["clock"]["taps"]:
    ax.plot(*tp["xy"],"^",ms=3,color="purple")
ax.plot(*t["clock"]["tap_um"],"*",ms=10,color="purple")
ax.set_aspect("equal"); ax.set_xlim(-80,W+110); ax.set_ylim(-20,H+20); fig.savefig(sys.argv[2],dpi=130,bbox_inches="tight")

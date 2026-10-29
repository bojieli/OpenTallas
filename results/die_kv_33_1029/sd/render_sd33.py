import json,sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt; from matplotlib.patches import Rectangle
plan=json.load(open(sys.argv[1])); rep=json.load(open(sys.argv[2])); out=sys.argv[3]
fig,axs=plt.subplots(2,1,figsize=(22,26))
for ax,tn in zip(axs,("kv3_sys_SD","kv3_sys_SD_v1")):
    t=plan["partition_types"][tn]; w,h=t["outline_um"]; c=t["contents"][0]; (ox,oy),(cw,ch)=c["origin_um"],c["outline_um"]
    ax.add_patch(Rectangle((0,0),w,h,fill=False,ec="k",lw=1.5))
    ax.add_patch(Rectangle((ox,oy),cw,ch,fc="#d8d8f0",ec="b",lw=1)); ax.text(ox+cw/2,oy+ch/2,f"PHY {c['physical_master']}\n{cw}x{ch} @({ox},{oy})",ha="center",fontsize=12)
    for x0,y0,x1,y1 in rep["types"][tn]["macro_blockage"]: ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec="b",ls="--"))
    isl=t["clock"].get("die_islands_um",[])
    for x0,y0,x1,y1 in isl: ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc="orange",ec="orange"))
    for bus,b in t["clock"]["landing_contract"]["bands"].items():
        x0,y0,x1,y1=b["rect_um"]; ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc="#7fd37f",ec="g",lw=1.5)); ax.text(x0-5,(y0+y1)/2,f"band {bus}\n{x1-x0:.2f}x{y1-y0:.1f}",ha="right",fontsize=10,color="g")
        if "resized_from_um" in b:
            x0,y0,x1,y1=b["resized_from_um"]; ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec="r",ls=":",lw=1.5))
    for x,y in rep["types"][tn]["old_local_taps"]: ax.plot(x,y,"rx",ms=10,mew=2)
    for x,y in rep["types"][tn]["local_taps"]: ax.plot(x,y,"m^",ms=11)
    for r in rep["types"][tn]["relays"]: ax.plot(r["xy"][0],r["xy"][1],"k.",ms=5)
    for p in t["clock"]["landing_contract"]["pins"]: ax.plot(*p["xy_um"],"cs",ms=5)
    ax.set_xlim(-60,w+60); ax.set_ylim(-30,h+30); ax.set_aspect("equal")
    ax.set_title(f"{tn}: PHY macro (blue) + halo, NEW bands (green) / OLD bands (red dotted), NEW local reset taps (magenta ^) / OLD (red x), reset relays (black), landing pins (cyan), die clock islands (orange, {len(isl)})",fontsize=11)
plt.tight_layout(); plt.savefig(out,dpi=60)
# zoom E channel
fig,ax=plt.subplots(1,1,figsize=(8,22)); tn="kv3_sys_SD"; t=plan["partition_types"][tn]; c=t["contents"][0]; (ox,oy),(cw,ch)=c["origin_um"],c["outline_um"]
ax.add_patch(Rectangle((ox,oy),cw,ch,fc="#d8d8f0",ec="b")); ax.add_patch(Rectangle((0,0),1900.8,1036.8,fill=False,ec="k"))
for x0,y0,x1,y1 in rep["types"][tn]["macro_blockage"]: ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec="b",ls="--"))
for bus,b in t["clock"]["landing_contract"]["bands"].items():
    x0,y0,x1,y1=b["rect_um"]; ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc="#7fd37f",ec="g")); ax.text(x0+1,(y0+y1)/2,bus,rotation=90,fontsize=9)
for x,y in rep["types"][tn]["local_taps"]: ax.plot(x,y,"m^",ms=12)
for r in rep["types"][tn]["relays"]: ax.plot(r["xy"][0],r["xy"][1],"k.",ms=8)
for p in t["clock"]["landing_contract"]["pins"]: ax.plot(*p["xy_um"],"cs",ms=6)
ax.axvline(1883.52,color="gray",ls=":"); ax.set_xlim(1800,1905); ax.set_ylim(0,1040); ax.set_title("kv3_sys_SD E channel zoom (x1800-1905); gray = band margin 1883.52",fontsize=10)
plt.tight_layout(); plt.savefig(out.replace(".png","_E.png"),dpi=60)

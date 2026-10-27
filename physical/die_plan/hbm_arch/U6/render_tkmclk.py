import json,sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
d=sys.argv[1]; p=json.load(open(d+"/die_plan.json")); t=p["partition_types"]["root"]; r=json.load(open(d+"/tkm_clk_report.json"))
fig,ax=plt.subplots(figsize=(7,14)); W,H=t["outline_um"]
ax.add_patch(plt.Rectangle((0,0),W,H,fill=False,lw=2))
for c in t["hard_cores"]:
    x,y=c["origin_um"]; w,h=c["outline_um"]
    if y>4700: continue
    tk=c["inst"].startswith("u_tkm_SW_")
    ax.add_patch(plt.Rectangle((x,y),w,h,fc="#9cf" if "tile" in c["inst"] else ("#f96" if tk else "#cfc"),ec="k",lw=.6))
    ax.text(x+w/2,y+h/2,c["inst"].replace("u_tkm_SW_","").replace("u_","")+("/"+c["orient"] if c.get("orient") else ""),fontsize=6,ha="center",va="center")
for f in t["ft_slots"]:
    q=f["regs_um"]; ax.plot([a[0] for a in q],[a[1] for a in q],"-",lw=.5,color="darkorange",alpha=.6)
for pr in r["cts_hop_table"]["pairs"]:
    a,b,dd=pr["tap_launch"],pr["tap_capture"],pr["tap_dist_um"]
    col="g" if dd<=360 else ("orange" if dd<=410 else "r")
    ax.plot([a[0],b[0]],[a[1],b[1]],"-",lw=1.6,color=col); ax.text((a[0]+b[0])/2+6,(a[1]+b[1])/2,f"{dd:.0f}",fontsize=5,color=col)
for tp in t["clock"]["taps"]:
    if tp["name"].startswith("u_tkm_SW_"): ax.plot(*tp["xy"],"^",ms=4,color="purple")
ax.plot(*t["clock"]["tap_um"],"*",ms=10,color="purple")
c=r["cts_hop_table"]
ax.set_title(f"root R1 TKM clock pins E-mid M6: pair tap dist max {c['worst_tap_dist_um']} (turn {c['worst_turn_um']}, column {c['worst_column_um']}); before 853.4/673.9\ngreen <=360, orange <=410, red = L4-corridor column hops (one master: need shared leaf driver)",fontsize=6)
ax.set_aspect("equal"); ax.set_xlim(-40,W+40); ax.set_ylim(900,4700); fig.savefig(sys.argv[2],dpi=150,bbox_inches="tight")

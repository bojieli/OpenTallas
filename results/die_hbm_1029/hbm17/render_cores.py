import json,sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=sys.argv[1]; out=sys.argv[2]
d=json.load(open(P+"/die_plan.json")); cm=json.load(open(P+"/core_macros.json"))["cores"]
views=[("q_hub_nw","sfus","u_sfus_Q__q0"),("q_hub_nw","sfus","u_sfus_Q__q1"),("q_hub_ne","sfus","u_sfus_Q__q0"),("q_hub_ne","sfus","u_sfus_Q__q1"),
       ("q_hub_nw","sucore","u_sucore_Q__q1"),("q_hub_ne","sucore","u_sucore_Q__q1"),("q_hub_nw","vmdel","u_vmdel_Q2"),("q_hub_ne","qctl","u_hb_idx__qctl_Q__q0")]
fig,axs=plt.subplots(2,4,figsize=(28,14))
for ax,(t,key,inst) in zip(axs.flat,views):
  pt=d["partition_types"][t]; cores=pt["hard_cores"]
  c=[h for h in cores if h["inst"]==inst][0]; cx=c["origin_um"][0]+c["outline_um"][0]/2; cy=c["origin_um"][1]+c["outline_um"][1]/2; wd=900
  for h in cores:
    x,y=h["origin_um"]; w,hh=h["outline_um"]
    if x+w<cx-wd/2 or x>cx+wd/2 or y+hh<cy-wd/2 or y>cy+wd/2: continue
    hl=key in h["inst"]
    ax.add_patch(Rectangle((x,y),w,hh,fill=False,ec="red" if hl else "k",lw=1.6 if hl else .7))
    ax.add_patch(Rectangle((x-4.32,y-4.32),w+8.64,hh+8.64,fill=False,ec="#bbb",lw=.3,ls=":"))
    ax.text(x+2,y+2,h["inst"][-16:]+f"\n{w:.2f}x{hh:.2f}",fontsize=5)
    for m in cm.get(h["module"],{}).get("macros",[]):
      a,b,cc,e=m["rect_um"]; ax.add_patch(Rectangle((x+a,y+b),cc-a,e-b,fc="orange" if hl else "#ddd",alpha=.6))
  st=[s for s in pt.get("internal_stations",[])]
  xs=[];ys=[]
  for s in st:
    for xy in s.get("regs_um",[]):
      if abs(xy[0]-cx)<wd/2 and abs(xy[1]-cy)<wd/2: xs.append(xy[0]);ys.append(xy[1])
  ax.plot(xs,ys,".",ms=1.5,color="blue")
  ax.set_xlim(cx-wd/2,cx+wd/2); ax.set_ylim(cy-wd/2,cy+wd/2); ax.set_aspect("equal"); ax.set_title(f"{t} {inst} (stations blue: {len(xs)})",fontsize=9)
plt.tight_layout(); plt.savefig(out,dpi=95)

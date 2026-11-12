import json,sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
A=json.load(open("types_vF.json")); B=json.load(open("types_vH1.json"))
for tn in ("kv3_hg_v1","kv3_hg_v3"):
  fig,axs=plt.subplots(1,2,figsize=(20,13))
  for ax,(nm,T) in zip(axs,(("vF",A),("vH1 (EX1..3 hard)",B))):
    t=T[tn]; W,H=t["outline_um"]
    ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.5))
    for h in t["hard_cores"]:
      x,y=h["origin_um"]; w,hh=h["outline_um"]
      ex=h["module"]=="qkd_astk_ex_s"
      ax.add_patch(Rectangle((x,y),w,hh,fc="tab:red" if ex else "tab:blue",alpha=.55 if ex else .25,ec="k",lw=.5))
      ax.text(x+w/2,y+hh/2,h["inst"][-12:] if ex else h["module"].replace("kv3_head_eighth_","h").replace("qkd_",""),ha="center",va="center",fontsize=6)
    lc=t["clock"].get("landing_contract",{})
    for n,b in (lc.get("bands") or {}).items():
      r=b["rect_um"]; ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc="tab:green",alpha=.3,lw=0))
    for r in t["clock"].get("die_islands_um",[]): ax.plot((r[0]+r[2])/2,(r[1]+r[3])/2,"m.",ms=3)
    rl=(lc.get("collector_tree") or {}).get("relays",[])
    ax.plot([r["xy"][0] for r in rl],[r["xy"][1] for r in rl],"k+",ms=4)
    for c in t["contents"]:
      for pp in c.get("physical_parts",[]) or []:
        if "origin_um" in pp:
          x,y=pp["origin_um"];w,hh=pp["outline_um"];ax.add_patch(Rectangle((x,y),w,hh,fc="orange",alpha=.5,lw=0))
    for tp in t["clock"]["taps"]:
      ax.plot(*tp["xy"],"c^" if tp.get("kind")=="core" else "c.",ms=4)
    ax.set_xlim(-10,W+10); ax.set_ylim(-10,H+10); ax.set_aspect("equal"); ax.set_title(f"{tn} {nm}: red=EX hard, blue=hard cores, green=landing bands, orange=SRAM, +=reset relays, m.=die clock islands, ^=core taps",fontsize=8)
  fig.tight_layout(); fig.savefig(f"{tn}_vF_vs_vH1.png",dpi=110)
print("ok")

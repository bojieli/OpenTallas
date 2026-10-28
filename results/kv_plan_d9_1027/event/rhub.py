import json,sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig,axs=plt.subplots(1,2,figsize=(16,10))
for ax,(f,ttl) in zip(axs,[(sys.argv[1],"base hm_r26q5c39"),(sys.argv[2],"D9a hm_r26q9")]):
    t=json.load(open(f))["partition_types"]["kv3_hub_Wi"]; w,h=t["outline_um"]
    ax.add_patch(plt.Rectangle((0,0),w,h,fill=False,ec="k"))
    for c in t["hard_cores"]:
        x,y=c["origin_um"]; a,b=c["outline_um"]
        ax.add_patch(plt.Rectangle((x,y),a,b,fc="#f9c" if "host_qm" not in c["module"] else "r",ec="k",lw=.5))
        ax.text(x+3,y+b/2,c["module"].replace("qkd_hr_",""),fontsize=7)
    for tp in t["clock"]["taps"]:
        k=tp["kind"]; ax.plot(*tp["xy"],"o" if k=="core" else "^",ms=6,color={"core":"b","landed":"orange"}.get(k,"g"))
    ax.set_title(ttl+"  (blue o = die-clock core tap, orange ^ = landed)"); ax.set_aspect("equal"); ax.set_xlim(-20,w+20); ax.set_ylim(-20,h+20)
plt.tight_layout(); plt.savefig(sys.argv[3],dpi=90)

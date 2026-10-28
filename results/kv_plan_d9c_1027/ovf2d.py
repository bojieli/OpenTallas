"""2D (layer-summed) GRT congestion from congestion.rpt: totals, top slots, map with hub_Wi cores + stations"""
import re, sys, json, collections
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
R=sys.argv[1]; sys.path.insert(0,R+"/tools/die_plan")
import schema as S
from pathlib import Path
out=sys.argv[2]; runs=sys.argv[3:]   # each run: label=coupon_dir=plan
fig,axs=plt.subplots(1,len(runs),figsize=(9*len(runs),12)); axs=axs if len(runs)>1 else [axs]
summ={}
for ax,r in zip(axs,runs):
    lab,d,plan=r.split("=")
    txt=open(d+"/grt/congestion.rpt").read().split("violation type: ")[1:]
    raw=json.load(open(plan)); P=S.Plan(raw,Path(plan)); x0,y0,_,_=P.rect("hub_Wi"); t=raw["partition_types"]["kv3_hub_Wi"]
    tot={"H":0,"V":0}; slots=collections.Counter(); pts=[]
    for e in txt:
        k="H" if e.startswith("Horizontal") else "V"
        c=int(re.search(r"congestion:(\d+)",e).group(1)); tot[k]+=c
        a,b,_,_=map(float,re.search(r"bbox = \((\S+), (\S+)\) - \((\S+), (\S+)\)",e).groups())
        pts.append((a-x0+5.4,b-y0+5.4,c,k))
        for s_ in set(re.findall(r"net:ft_hub_Wi__(ft\d+)_",e)): slots[s_]+=c
    summ[lab]=dict(H=tot["H"],V=tot["V"],gcells=len(pts),top_slots=slots.most_common(8))
    for c in t["hard_cores"]:
        x,y=c["origin_um"]; a,b=c["outline_um"]; ax.add_patch(plt.Rectangle((x,y),a,b,fc="#eee",ec="k",lw=.4))
    for s in t["ft_slots"]:
        for st in s.get("bit_sites_um",[]):
            if st: ax.plot(sum(p[0] for p in st)/len(st),sum(p[1] for p in st)/len(st),"g^",ms=3)
    for k,col in (("H","r"),("V","b")):
        q=[p for p in pts if p[3]==k]
        ax.scatter([p[0] for p in q],[p[1] for p in q],s=[2+p[2] for p in q],c=col,alpha=.5,label=f"2D {k} overflow (size=ovf)")
    ax.set_title(f"{lab}: 2D overflow H {tot['H']} V {tot['V']} ({len(pts)} gcells); green ^ = FT stations",fontsize=10)
    ax.set_aspect("equal"); ax.set_xlim(-20,t["outline_um"][0]+20); ax.set_ylim(-20,t["outline_um"][1]+20); ax.legend(loc="upper right",fontsize=8)
plt.tight_layout(); plt.savefig(out,dpi=70)
print(json.dumps(summ))

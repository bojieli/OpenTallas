import json,sys,matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=json.load(open(sys.argv[1]))["partition_types"]; D=json.load(open(sys.argv[2])); B=json.load(open(sys.argv[3])); out=sys.argv[4]
types=list(D)
fig,axs=plt.subplots(2,len(types),figsize=(4.2*len(types),8.4))
for j,tn in enumerate(types):
    t=P[tn]; W,H=t["outline_um"]
    for i,ax in enumerate(axs[:,j]):
        d=D[tn] if i else {}
        ax.add_patch(Rectangle((0,0),W,H,fill=False,ec="k"))
        for h in t["hard_cores"]:
            o=d.get(h["inst"],h["origin_um"])[:2]
            ax.add_patch(Rectangle(o,*h["outline_um"],fc="#9ecae1" if h["inst"] in d else "#ddd",ec="#333",lw=.6))
            ax.text(o[0]+3,o[1]+3,h["inst"].split(".")[-1],fontsize=5)
        for e in t["contents"]:
            if "origin_um" not in e or not e.get("lef"): continue
            o=d.get(e["inst"],e["origin_um"])[:2]; mv=e["inst"] in d
            c="#e6550d" if "rom" in e.get("module","") else ("#756bb1" if "2c_" in e.get("module","") else "#31a354")
            ax.add_patch(Rectangle(o,*e["outline_um"],fc=c,alpha=.9 if mv else .35,ec="r" if mv else "none",lw=.6))
        bands=dict((k,v["rect_um"]) for k,v in t["clock"].get("landing_contract",{}).get("bands",{}).items() if v.get("rect_um"))
        if i: bands.update(B.get(tn,{}))
        for k,r in bands.items():
            ax.add_patch(Rectangle(r[:2],r[2]-r[0],r[3]-r[1],fc="none",ec="m",lw=.8,ls="--"))
        ax.set_xlim(-10,W+10); ax.set_ylim(-10,H+10); ax.set_aspect("equal"); ax.tick_params(labelsize=5)
        ax.set_title(("AFTER " if i else "BEFORE ")+tn.replace("dsdv_slice_",""),fontsize=7)
fig.suptitle("SLICE-C S-ring form (CPL-S81-SLICE-3): cap/xr moved (blue), contents moved (red edge); green S256, orange ROM, purple EX; magenta dashed = landing bands",fontsize=8)
plt.tight_layout(); plt.savefig(out,dpi=110)

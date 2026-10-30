import json,sys,matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
parts=json.load(open("parts.json"))
OPT={"S0 (d40h now)":{},
"L1 = Sa + C2":{"NW_b112":0.0,"NW_b113":1209.6,"NW_su00":3067.2,"NW_su01":5175.36,"NW_spu0":7110.72,"NW_su10":8795.52,"NW_su11":10998.72,"NW_b110":0.0,"NW_b111":414.72,"NW_su20":1218.24,"NW_su21":3222.72,"NW_spu1":5114.88,"NW_su30":6583.68,"NW_su31":8648.64,"NW_b103":10480.32,"NW_b102":11188.8}}
def col(n):
    if n in ("NW_b110","NW_b111","NW_b112","NW_b113"): return "#e4572e"
    if n in ("NW_b100","NW_b101","NW_b102","NW_b103"): return "#2e86ab"
    if "_su" in n and "spu" not in n: return "#a8d5a2"
    if "spu" in n or "spt" in n or "spb" in n: return "#dddddd"
    if n.endswith("hub"): return "#f3d35b"
    return "#f4f4f4"
fig,axs=plt.subplots(2,1,figsize=(15,22))
for ax,(t,ov) in zip(axs,OPT.items()):
    for n,x,y,w,h in parts:
        if not (n.startswith("NW") or n=="root"): continue
        if y>12000: continue
        if n in ov: x=ov[n]
        ax.add_patch(Rectangle((x,y),w,h,fc=col(n),ec="k",lw=0.8))
        ax.text(x+w/2,y+h/2,n.replace("NW_",""),ha="center",va="center",fontsize=9,rotation=90 if w<900 else 0)
    ax.set_xlim(0,15100);ax.set_ylim(0,12000);ax.set_aspect("equal");ax.set_title(t+"  (NW half, y<12000; red=SFU strips, blue=IDX s_NW strips)")
plt.tight_layout();plt.savefig("hbmloc1_rows.png",dpi=70)

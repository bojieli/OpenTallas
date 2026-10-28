import csv, sys, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
W,H=760.32,725.76; B=4.0
g={}; 
for k in ("std","ff","buf"): g[k]=np.zeros((int(H/B)+1,int(W/B)+1))
mac=[]; mp=[]; pins=[]
for r in csv.DictReader(open(sys.argv[1])):
    k=r["kind"]; x=float(r["x"]); y=float(r["y"]); w=float(r["w"]); h=float(r["h"])
    if k=="macro": mac.append((r["name"],x,y,w,h))
    elif k=="pin": pins.append((x,y))
    elif k in g:
        g[k][int((y+h/2)/B),int((x+w/2)/B)]+=w*h
        if r["name"].startswith("mp_"): mp.append((x,y))
fig,ax=plt.subplots(1,2,figsize=(20,10))
tot=(g["std"]+g["ff"]+g["buf"])/(B*B)
im=ax[0].imshow(tot,origin="lower",extent=(0,W,0,H),cmap="viridis",vmax=1.0); fig.colorbar(im,ax=ax[0],fraction=.04)
ax[0].set_title("lanes__canon _c20ek2m_m5w1 4_cts: std-cell area density (4 um bins)")
ff=g["ff"]/(B*B); ax[1].imshow(ff,origin="lower",extent=(0,W,0,H),cmap="magma",vmax=.4); ax[1].set_title("flop density + planned mp_ island cells (cyan) + pins (red)")
for a in ax:
    for n,x,y,w,h in mac: a.add_patch(Rectangle((x,y),w,h,fill=False,ec="white",lw=1.2))
    a.set_xlim(0,W); a.set_ylim(0,H)
if mp: ax[1].scatter(*zip(*mp),s=12,c="cyan",marker="s")
if pins: ax[1].scatter(*zip(*pins),s=1,c="red")
plt.tight_layout(); plt.savefig(sys.argv[2],dpi=70)
print(len(mac),"macros",len(mp),"mp",tot.max())

import csv, json, sys, re
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
def colo(k):
    d={}
    for net,s in (("VDD",1),("VSS",0)):
        for r in csv.DictReader(open(k+"/psm/ir_%s.csv"%net)):
            v=(0.7-float(r["Voltage"]) if s else float(r["Voltage"]))*1e3; n=r["Instance"]
            x,y=float(r["X location"]),float(r["Y location"])
            a=d.setdefault(n,[x,y,0,0]); a[2+ (0 if s else 1)]=max(a[2+(0 if s else 1)],v)
    return d
def bumps(k):
    t=open(k+"/psm/bumps.tcl").read()
    return [(float(a),float(b)) for a,b in re.findall(r"ot_pad \S+ \d+ ([\d.]+) ([\d.]+)",t)]
fig,ax=plt.subplots(1,len(sys.argv)-2,figsize=(7*(len(sys.argv)-2),6))
for i,k in enumerate(sys.argv[2:]):
    d=colo(k); xs=[v[0] for v in d.values()]; ys=[v[1] for v in d.values()]; c=[v[2]+v[3] for v in d.values()]
    sc=ax[i].scatter(xs,ys,c=c,s=4,cmap="inferno",vmin=0,vmax=max(c)); plt.colorbar(sc,ax=ax[i],label="VDD+VSS mV")
    b=bumps(k); 
    if b: ax[i].scatter([p[0] for p in b],[p[1] for p in b],s=6,marker="s",facecolors="none",edgecolors="cyan",lw=.5)
    ax[i].set_xlim(0,700); ax[i].set_title(k.split("/")[-2]+"/"+k.split("/")[-1]+" max %.1f"%max(c)); ax[i].set_aspect("equal")
plt.tight_layout(); plt.savefig(sys.argv[1],dpi=110)

import json,sys,math,collections,os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan,tt,out,label=sys.argv[1:5]
P=json.load(open(plan)); T={r["type"]:r for r in json.load(open(tt))}
pt=P["partition_types"]; parts=P["partitions"]; W,H=P["die"]["outline_um"]
G=8.64
up=lambda v:math.ceil(v/G-1e-9)*G
MARG=43.2      # street/abut margin each side around the content (STREET-RULE-1 street_min)
MIN_STATION=172.8
def need(t):
    r=T[t]; w,h=r["w"],r["h"]; f=r["family"]
    if f in("ot_s81sl_leaf","ot_s81sl_kv_leaf"):
        # cores keep their shape: bbox + street margin; bands must fit
        nw=max(r["bbox_w"]+MARG, r["band_ns"]+MARG)
        nh=max(r["bbox_h"]+MARG, r["band_ew"]+MARG)
        return min(w,up(nw)),min(h,up(nh)),"cores bbox+street margin"
    if f=="slice_station":
        nw=max(MIN_STATION, r["band_ns"]+2*MARG); nh=max(MIN_STATION, r["band_ew"]+2*MARG)
        return min(w,up(nw)),min(h,up(nh)),"lane bands only (ft N/S width, E/W width) + 2 streets"
    return w,h,"keep (macro/hard content or PHY)"
# lattice
xs=sorted({round(p["origin_um"][0],1) for p in parts}); ys=sorted({round(p["origin_um"][1],1) for p in parts})
def span(a0,a1,arr):
    return [i for i,a in enumerate(arr) if a>=a0-1 and a<a1-1]
colw=[0.0]*len(xs); rowh=[0.0]*len(ys); collim=[None]*len(xs); rowlim=[None]*len(ys)
rec=[]
for p in parts:
    t=p["type"]; w,h=pt[t]["outline_um"]; x,y=p["origin_um"]
    nw,nh,why=need(t)
    cs=span(x,x+w,xs); rs=span(y,y+h,ys)
    for i in cs:
        v=nw/len(cs)
        if v>colw[i]+1e-6: colw[i]=v; collim[i]=(p["name"],T[t]["family"])
    for j in rs:
        v=nh/len(rs)
        if v>rowh[j]+1e-6: rowh[j]=v; rowlim[j]=(p["name"],T[t]["family"])
    rec.append((p,cs,rs,nw,nh,why))
# also keep non-lattice extra gap between lattice columns (die channels): preserve original gaps
oldw=[(xs[i+1]-xs[i]) if i+1<len(xs) else W-xs[i] for i in range(len(xs))]
oldh=[(ys[j+1]-ys[j]) if j+1<len(ys) else H-ys[j] for j in range(len(ys))]
gapx=[max(0,oldw[i]-0) for i in range(len(xs))]
# new origins: cumulative with preserved gaps beyond tile width (gap = oldw - max tile width in col)
def gaps(old,need_arr):
    return [max(0.0,o-max(1e-9,n)) if False else 0.0 for o,n in zip(old,need_arr)]
newx=[];acc=0.0
for i in range(len(xs)):
    newx.append(acc); acc+=min(oldw[i], up(colw[i]) if colw[i]>0 else oldw[i])
newW=acc
newy=[];acc=0.0
for j in range(len(ys)):
    newy.append(acc); acc+=min(oldh[j], up(rowh[j]) if rowh[j]>0 else oldh[j])
newH=acc
print("lattice: %d columns x %d rows ; old die %.0f x %.0f = %.1f mm2 ; new die %.0f x %.0f = %.1f mm2 (%.1f%%)"%(len(xs),len(ys),W,H,W*H/1e6,newW,newH,newW*newH/1e6,100*(newW*newH-W*H)/(W*H)))
print("col width old->new and limiter:")
for i in range(len(xs)):
    print("  col%02d x=%7.0f old %7.1f new %7.1f  %s"%(i,xs[i],oldw[i],min(oldw[i],up(colw[i])),collim[i]))
print("row height old->new and limiter:")
for j in range(len(ys)):
    print("  row%02d y=%7.0f old %7.1f new %7.1f  %s"%(j,ys[j],oldh[j],min(oldh[j],up(rowh[j])),rowlim[j]))
# per type table
tab=[]
for t,r in T.items():
    nw,nh,why=need(t); tab.append(dict(type=t,family=r["family"],n_inst=r["n_inst"],old_w=r["w"],old_h=r["h"],need_w=nw,need_h=nh,reason=why,band_ns=r["band_ns"],band_ew=r["band_ew"],bbox_w=r["bbox_w"],bbox_h=r["bbox_h"]))
json.dump(dict(types=tab,cols=[dict(i=i,x=xs[i],old=oldw[i],new=min(oldw[i],up(colw[i])),limiter=collim[i]) for i in range(len(xs))],rows=[dict(j=j,y=ys[j],old=oldh[j],new=min(oldh[j],up(rowh[j])),limiter=rowlim[j]) for j in range(len(ys))],old_die=[W,H],new_die=[newW,newH]),open(out+"/sizing_%s.json"%label,"w"),indent=1)
# per-family reclaim if each tile took its own need (upper bound, ignoring lattice)
fam=collections.defaultdict(float)
for t,r in T.items():
    nw,nh,_=need(t); fam[r["family"]]+=(r["w"]*r["h"]-nw*nh)*r["n_inst"]
print("per-tile reclaim upper bound (mm2, ignores lattice):",{k:round(v/1e6,1) for k,v in fam.items() if v>1e5})
# after render
fams=sorted({r["family"] for r in T.values()}); cm=plt.get_cmap("tab20"); fc={f:cm(i%20) for i,f in enumerate(fams)}
fig,ax=plt.subplots(figsize=(18,14.5),dpi=110)
ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1,ls="--",ec="grey"))
ax.add_patch(Rectangle((0,0),newW,newH,fill=False,lw=1.5))
for (p,cs,rs,nw,nh,why) in rec:
    x0=newx[cs[0]];x1=newx[cs[-1]]+min(oldw[cs[-1]],up(colw[cs[-1]]) if colw[cs[-1]]>0 else oldw[cs[-1]])
    y0=newy[rs[0]];y1=newy[rs[-1]]+min(oldh[rs[-1]],up(rowh[rs[-1]]) if rowh[rs[-1]]>0 else oldh[rs[-1]])
    ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc=fc[T[p["type"]]["family"]],alpha=0.55,ec="k",lw=0.3))
ax.set_xlim(0,W);ax.set_ylim(0,H);ax.set_aspect("equal")
ax.set_title("S81 PROPOSED lattice (cores keep shape; slice_station tiles sized to lane bands; leaf to bbox+43.2 street margin; column widths = max need). dashed = current die %.0fx%.0f; new %.0fx%.0f"%(W,H,newW,newH))
hs=[Rectangle((0,0),1,1,fc=fc[f]) for f in fams]; ax.legend(hs,fams,fontsize=6,loc="upper left",ncol=3,bbox_to_anchor=(1.0,1.0))
fig.savefig(out+"/die_proposed_%s.png"%label,bbox_inches="tight")

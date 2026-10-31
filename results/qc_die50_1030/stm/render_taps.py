import json,sys,matplotlib
matplotlib.use("Agg");import matplotlib.pyplot as plt
P=json.load(open(sys.argv[1]));R=json.load(open(sys.argv[2]));bd=sys.argv[3];out=sys.argv[4]
Ts=list(R['types'])
fig,ax=plt.subplots(1,len(Ts),figsize=(2.2*len(Ts),6.2))
for a,T in zip(ax,Ts):
    t=P['partition_types'][T];w,h=t['outline_um'];b=json.load(open(f"{bd}/{T}.json"));u=b['bin_um']
    xs=[x for x,y,n in b['bins']];ys=[y for x,y,n in b['bins']];ns=[n for x,y,n in b['bins']]
    a.scatter(xs,ys,c=ns,s=2,marker='s',cmap='Greys',vmin=0,vmax=max(ns))
    for r in t['clock']['landing_contract']['bands'].values():
        x0,y0,x1,y1=r['rect_um'];a.add_patch(plt.Rectangle((x0,y0),x1-x0,y1-y0,fc='orange',alpha=.35,ec='none'))
    for hc in t.get('hard_cores',[]):
        (x0,y0),(ww,hh)=hc['origin_um'],hc['outline_um'];a.add_patch(plt.Rectangle((x0,y0),ww,hh,fc='none',ec='b'))
    tx=[x for n,x,y in R['types'][T]['tap_xy']];ty=[y for n,x,y in R['types'][T]['tap_xy']]
    a.plot(tx,ty,'r+',ms=5);a.add_patch(plt.Rectangle((0,0),w,h,fc='none',ec='k'))
    a.set_xlim(-10,w+10);a.set_ylim(-10,h+10);a.set_aspect('equal');a.set_title(f"{T[:22]}\n{len(tx)} taps {b['n']} sinks",fontsize=6);a.tick_params(labelsize=5)
plt.tight_layout();plt.savefig(out,dpi=130)

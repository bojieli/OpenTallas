import json,sys
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/die-hbm-43/tools/die_plan')
import schema as S
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=S.Plan(json.load(open(sys.argv[1]))); out=sys.argv[2]
lids=['L730','L731','L732','L733','L734','L735','L736']
cols=dict(zip(lids,['red','blue','green','magenta','orange','cyan','purple']))
fig,ax=plt.subplots(1,1,figsize=(24,14),dpi=100)
ax.set_aspect('equal'); ax.set_xlim(-100,15200); ax.set_ylim(-100,12200)
ax.set_title('d41v NW: V-A hop-chain stations L730-L736 (macros grey)')
for n in P.parts if hasattr(P,'parts') else []:
    pass
names=[p['name'] for p in json.load(open(sys.argv[1]))['partitions'] if p['name'].startswith('NW_') or p['name']=='root']
for n in names:
    x0,y0,x1,y1=P.rect(n)
    if y0>12200: continue
    ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec='k',lw=0.8)); ax.text(x0+30,(y0+y1)/2,n,fontsize=8,color='grey')
    try:
        for bx0,by0,bx1,by1 in S.placed_macro_boxes(P.ptype(n)).values():
            c0=P.to_die(n,(bx0,by0)); c1=P.to_die(n,(bx1,by1))
            ax.add_patch(Rectangle((min(c0[0],c1[0]),min(c0[1],c1[1])),abs(c1[0]-c0[0]),abs(c1[1]-c0[1]),fc='0.88',ec='0.6',lw=0.3))
    except Exception as e: print('macro',n,e)
for lid in lids:
    pts=[]
    for part,slot,_,_ in P.lane_crossings(lid):
        s=P.slot(part,slot)
        for r in s.get('regs_um',[]):
            q=P.to_die(part,r); pts.append(q)
    print(lid,len(pts))
    ax.plot([p[0] for p in pts],[p[1] for p in pts],'o-',color=cols[lid],ms=5,mec='k',lw=0.8,label=lid)
ax.legend(); plt.tight_layout(); plt.savefig(out)

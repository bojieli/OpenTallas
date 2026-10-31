import json,sys
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/die-hbm-42/tools/die_plan')
import schema as S
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=S.Plan(json.load(open(sys.argv[1]))); P0=S.Plan(json.load(open(sys.argv[2]))); out=sys.argv[3]
views=[('NW su20|su21|hub: new L724 (red) on L59 corridor, widened L59 (blue)',(2100,6300,4400,6400),['NW_su20','NW_su21','NW_hub'],['L724','L59','L48','L53','L38']),
       ('NW su00|su01|hub: widened L102 (red) L55 (blue)',(1700,6100,10200,12100),['NW_su00','NW_su01','NW_hub'],['L102','L55'])]
fig,axs=plt.subplots(1,2,figsize=(26,11),dpi=110)
cols={'L724':'red','L59':'blue','L48':'green','L53':'orange','L38':'purple','L102':'red','L55':'blue'}
for ax,(title,win,parts,lids) in zip(axs,views):
    ax.set_title(title,fontsize=9); ax.set_aspect('equal'); ax.set_xlim(win[0],win[1]); ax.set_ylim(win[2],win[3])
    for n in parts:
        x0,y0,x1,y1=P.rect(n); ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec='k',lw=0.8)); ax.text(max(x0,win[0])+30,(y0+y1)/2,n,fontsize=8,color='grey')
        if n=='NW_hub': continue
        for bx0,by0,bx1,by1 in S.placed_macro_boxes(P.ptype(n)).values():
            c0=P.to_die(n,(bx0,by0)); c1=P.to_die(n,(bx1,by1))
            ax.add_patch(Rectangle((min(c0[0],c1[0]),min(c0[1],c1[1])),abs(c1[0]-c0[0]),abs(c1[1]-c0[1]),fc='0.88',ec='0.6',lw=0.3))
    # all port windows on the faces between the parts: old (thin black offset) vs new (thick grey / lane colour)
    for PP,off,lw in ((P0,-25,2),(P,25,4)):
        for pid,pr in PP.ports.items():
            if not ({pr['src']['part'],pr['dst']['part']}<=set(parts)) or 'window_um' not in pr: continue
            lid=pid.rsplit('_',1)[0]; c=cols.get(lid,'0.4') if PP is P else 'k'
            a,b=pr['window_um']; x0,y0,x1,y1=PP.rect(PP.face_part(pid)); f=pr['face']
            if f in 'EW':
                x=(x1 if f=='E' else x0)+off; ax.plot([x,x],[a,b],color=c,lw=lw)
            else:
                y=(y1 if f=='N' else y0)+off; ax.plot([a,b],[y,y],color=c,lw=lw)
    for lid in lids:
        for part,slot,_,_ in P.lane_crossings(lid):
            s=P.slot(part,slot)
            for r in s.get('regs_um',[]):
                q=P.to_die(part,r); ax.plot(q[0],q[1],'o',color=cols[lid],ms=6,mec='k')
            if lid in ('L724','L102'):
                for st in s.get('bit_sites_um',[]):
                    xs=[P.to_die(part,p) for p in st[::5]]; ax.scatter([q[0] for q in xs],[q[1] for q in xs],s=0.3,color=cols[lid])
plt.tight_layout(); plt.savefig(out)

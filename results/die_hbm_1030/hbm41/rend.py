import json,sys
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/die-hbm-41/tools/die_plan')
import schema as S
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
raw=json.load(open(sys.argv[1])); P=S.Plan(raw); out=sys.argv[2]
views=[('NW hub<->spb0 L720/L722/L723 + sm3 L721',(5000,13500,0,10600),['L720','L722','L723','L721']),
       ('NE mirror',(14800,23400,0,10600),['L720m','L722m','L723m','L721m']),
       ('NW_b100 L721 (new) vs L123/L70',(11700,12200,5900,12100),['L721','L123','L70']),
       ('NW_su01 L120x1 widened bit sites (zoom stage 1)',None,['L120'])]
fig,axs=plt.subplots(1,4,figsize=(30,9),dpi=110)
cols=['red','blue','green','magenta']
for ax,(title,win,lids) in zip(axs,views):
    ax.set_title(title,fontsize=9); ax.set_aspect('equal')
    parts=set()
    for lid in lids:
        hp=[P.ports[q] for q in P.lanes[lid]['ports']]
        parts|={hp[0]['src']['part']}|{x['dst']['part'] for x in hp}
    for n in P.parts:
        x0,y0,x1,y1=P.rect(n)
        if win and (x1<win[0] or x0>win[1] or y1<win[2] or y0>win[3]): continue
        if not win and n not in parts: continue
        ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec='k',lw=0.6))
        ax.text((x0+x1)/2,(y0+y1)/2,n,fontsize=6,ha='center',color='grey')
        if n in parts:
            for bx0,by0,bx1,by1 in S.placed_macro_boxes(P.ptype(n)).values():
                c0=P.to_die(n,(bx0,by0)); c1=P.to_die(n,(bx1,by1))
                ax.add_patch(Rectangle((min(c0[0],c1[0]),min(c0[1],c1[1])),abs(c1[0]-c0[0]),abs(c1[1]-c0[1]),fc='0.85',ec='0.6',lw=0.3))
    for i,lid in enumerate(lids):
        hp=[P.ports[q] for q in P.lanes[lid]['ports']]
        pts=[]
        for x in hp:
            lo,hi=x['window_um']; c=(lo+hi)/2
            sx0,sy0,sx1,sy1=P.rect(x['src']['part'])
            pt={'N':(c,sy1),'S':(c,sy0),'E':(sx1,c),'W':(sx0,c)}[x['face']]
            pts.append(pt)
            ax.plot([pt[0]-(hi-lo)/2*(x['face'] in 'NS'),pt[0]+(hi-lo)/2*(x['face'] in 'NS')],[pt[1]-(hi-lo)/2*(x['face'] in 'EW'),pt[1]+(hi-lo)/2*(x['face'] in 'EW')],color=cols[i%4],lw=3)
        for part,slot,_,_ in P.lane_crossings(lid):
            if not slot: continue
            s=P.slot(part,slot)
            regs=[P.to_die(part,tuple(r)) for r in s.get('regs_um',[])]
            ax.plot([r[0] for r in regs],[r[1] for r in regs],'o',color=cols[i%4],ms=3)
            if s.get('bit_sites_um') and not win:
                st=s['bit_sites_um'][1]; d=[P.to_die(part,(x+0.7,y+0.135)) for x,y in st]
                ax.plot([p[0] for p in d[:10]],[p[1] for p in d[:10]],'s',color='blue',ms=4,label='existing 9+epoch (orig)')
                ax.plot([p[0] for p in d[9:-1]],[p[1] for p in d[9:-1]],'s',color='red',ms=4,label='new 37')
                ax.plot([d[-1][0]],[d[-1][1]],'*',color='k',ms=8,label='epoch')
                # all other sites of the type near
                cx=sum(p[0] for p in d)/len(d); cy=sum(p[1] for p in d)/len(d)
                for s2 in P.ptype(part).get('ft_slots',[]):
                    if s2['name']==slot: continue
                    for st2 in s2.get('bit_sites_um') or []:
                        for x,y in st2:
                            q=P.to_die(part,(x+0.7,y+0.135))
                            if abs(q[0]-cx)<25 and abs(q[1]-cy)<25: ax.plot([q[0]],[q[1]],'.',color='0.5',ms=3)
                ax.set_xlim(cx-25,cx+25); ax.set_ylim(cy-25,cy+25); ax.legend(fontsize=6)
        ax.plot([], [], color=cols[i%4], label=lid)
    if win: ax.set_xlim(win[0],win[1]); ax.set_ylim(win[2],win[3]); ax.legend(fontsize=7)
plt.tight_layout(); plt.savefig(out)

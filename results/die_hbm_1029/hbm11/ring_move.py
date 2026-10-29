"""DIE-HBM-11 plan event (COORD ruling YES 10-29): move u_hb_coll_Q_ring_ag__q1 next to the GQ east face in
q_hub_nw and q_hub_ne (hub-local origin 4527.36, 2626.56, orient unchanged), 0 cycles, no RTL.
NE: u_ctl_Q_p15 collides -> re-sited to the nearest hard-free 4.32-lattice slot (4.32 clearance) minimising its
station wire. Stations with an endpoint on a moved core, or a register inside a moved core's new halo, are
re-routed with the shared hub_repack.route_station (360-um internal hop, register count kept when possible).
usage: ring_move.py SRC_PLAN_DIR OUT_DIR REPO_TOOLS_DIE_PLAN"""
import json,sys,os,shutil,hashlib
from pathlib import Path
src,out,tools=map(Path,sys.argv[1:4]);sys.path.insert(0,str(tools))
import hub_repack as HR
G=4.32;RING='u_hb_coll_Q_ring_ag__q1';CTL='u_ctl_Q_p15';NEW=(4527.36,2626.56)
P=json.loads((src/'die_plan.json').read_text());T=P['partition_types']
rect=lambda h:(h['origin_um'][0],h['origin_um'][1],h['origin_um'][0]+h['outline_um'][0],h['origin_um'][1]+h['outline_um'][1])
def clear(r,others,c=G):return all(r[2]+c<=o[0] or o[2]+c<=r[0] or r[3]+c<=o[1] or o[3]+c<=r[1] for o in others)
rep=dict(schema='die-hbm-11.ring_move.v1',source_plan_sha256=hashlib.sha256((src/'die_plan.json').read_bytes()).hexdigest(),types={})
for tn in ('q_hub_nw','q_hub_ne'):
    t=T[tn];W,H=t['outline_um'];hc={h['inst']:h for h in t['hard_cores']};old={k:rect(h) for k,h in hc.items()}
    moves={}
    r=hc[RING];w,h=r['outline_um'];nr=(NEW[0],NEW[1],NEW[0]+w,NEW[1]+h)
    hits=[k for k,o in old.items() if k!=RING and not clear(nr,[o])]
    moves[RING]=(NEW[0]-r['origin_um'][0],NEW[1]-r['origin_um'][1])
    info=dict(ring_old=r['origin_um'],ring_new=list(NEW),ring_hits=hits)
    assert set(hits)<= {CTL},(tn,hits)
    if hits:
        c=hc[CTL];cw,ch=c['outline_um'];others=[o for k,o in old.items() if k not in (CTL,RING)]+[nr]
        sts=[s for s in t['internal_stations'] if CTL in s['conn']]
        best=None;ox,oy=c['origin_um']
        for di in range(-120,121):
            for dj in range(-120,121):
                x,y=round(ox+di*G,3),round(oy+dj*G,3)
                if x<0 or y<0 or x+cw>W or y+ch>H:continue
                q=(x,y,x+cw,y+ch)
                if not clear(q,others):continue
                cost=0
                for s in sts:
                    for a,b in ((s['from_um'],s['to_um']),(s['to_um'],s['from_um'])):
                        if old[CTL][0]-.5<=a[0]<=old[CTL][2]+.5 and old[CTL][1]-.5<=a[1]<=old[CTL][3]+.5:
                            cost+=s['bits']*(abs(a[0]+x-ox-b[0])+abs(a[1]+y-oy-b[1]))
                cost+=1e-3*(abs(x-ox)+abs(y-oy))
                if best is None or cost<best[0]:best=(cost,x,y)
        assert best,tn
        moves[CTL]=(best[1]-ox,best[2]-oy);info.update(ctl_old=[ox,oy],ctl_new=[best[1],best[2]])
    for k,(dx,dy) in moves.items():
        h_=hc[k];h_['origin_um']=[round(h_['origin_um'][0]+dx,3),round(h_['origin_um'][1]+dy,3)]
        h_['note']=h_.get('note','')+f' | DIE-HBM-11 C25c ring-move (COORD 10-29 YES): origin moved by ({dx:.3f},{dy:.3f}), 0 cycles'
        for c in t.get('contents',[]):
            if c.get('inst')==k and 'origin_um' in c:c['origin_um']=list(h_['origin_um'])
        for tp in (t.get('clock') or {}).get('taps',[]):
            if tp.get('name','').split('.')[0]==k:tp['xy']=[round(tp['xy'][0]+dx,3),round(tp['xy'][1]+dy,3)]
        rt=(t.get('reset') or {})
        for tp in rt.get('taps',[]) if isinstance(rt.get('taps'),list) else []:
            if tp.get('name','').split('.')[0]==k and 'xy' in tp:tp['xy']=[round(tp['xy'][0]+dx,3),round(tp['xy'][1]+dy,3)]
    newr={k:rect(hc[k]) for k in moves}
    R=HR.Raster(W,H,[rect(h_) for h_ in t['hard_cores']])
    def follow(p):
        for k,(dx,dy) in moves.items():
            o=old[k]
            if o[0]-.5<=p[0]<=o[2]+.5 and o[1]-.5<=p[1]<=o[3]+.5:return (round(p[0]+dx,3),round(p[1]+dy,3)),True
        return tuple(p),False
    def inhalo(q):return any(r_[0]-G<q[0]<r_[2]+G and r_[1]-G<q[1]<r_[3]+G for r_ in newr.values())
    st=dict(stations=len(t['internal_stations']),regenerated=0,regs_old=0,regs_new=0,latency_up=[],padded_short=[],failed=[],max_hop_new=0.0)
    for i,s in enumerate(t['internal_stations']):
        a,ma=follow(s['from_um']);b,mb=follow(s['to_um'])
        bad=any(inhalo(q) for q in s.get('regs_um',[]))
        if not(ma or mb or bad):continue
        n_old=len(s.get('regs_um',[]));st['regs_old']+=n_old
        res=None;rch=405.0 if s['conn'].startswith('bus:') else 360.0
        if not(ma or mb):
            # endpoints fixed, only registers inside a moved core's new halo: re-site just those registers
            regs=[tuple(q) for q in s['regs_um']];okk=True
            md0=lambda p,q:abs(p[0]-q[0])+abs(p[1]-q[1]);p0=[a]+regs+[b]
            lim=405.0 if s['conn'].startswith('bus:') else min(405.0,max(360.0,max(md0(p,q) for p,q in zip(p0,p0[1:]))))
            md=lambda p,q:abs(p[0]-q[0])+abs(p[1]-q[1])
            for j,q in enumerate(regs):
                if inhalo(q):
                    pv=a if j==0 else regs[j-1];nx=b if j==len(regs)-1 else regs[j+1]
                    bx,by=round(q[0]/G),round(q[1]/G);best=None
                    for di in range(-70,71):
                        for dj in range(-70,71):
                            c=(round((bx+di)*G,3),round((by+dj)*G,3))
                            if not R.free(*c) or inhalo(c):continue
                            k=(max(md(pv,c),md(c,nx)),md(c,q))
                            if best is None or k<best[0]:best=(k,c)
                    if best:regs[j]=best[1]
            pts=[a]+regs+[b];hop=max(md(p,q) for p,q in zip(pts,pts[1:]))
            if hop<=lim and not any(inhalo(q) for q in regs):res=dict(kind='local_resite',regs=regs,length_um=None)
        if res is None:
            rch=405.0 if s['conn'].startswith('bus:') else 360.0
            res=HR.route_station(R,a,b,n_old,rch)
        if res is not None and len(res['regs'])!=n_old:
            ea,eb=HR.escape(R,a),HR.escape(R,b);poly=HR.astar(R,ea,eb)
            if poly:
                la=abs(ea[0]-a[0])+abs(ea[1]-a[1]);lb=abs(eb[0]-b[0])+abs(eb[1]-b[1])
                rg,nm=HR.place_regs(R,poly,la,lb,n_old,rch)
                if rg is not None and len(rg)==n_old:res=dict(kind='astar_keep',regs=rg,length_um=None)
        if res is None:
            st['failed'].append(dict(i=i,conn=s['conn'],from_um=list(a),to_um=list(b)));st['regs_new']+=n_old;continue
        st['regenerated']+=1;st['regs_new']+=len(res['regs'])
        if len(res['regs'])>n_old:st['latency_up'].append(dict(i=i,conn=s['conn'],old=n_old,new=len(res['regs'])))
        if len(res['regs'])<n_old:st['padded_short'].append(dict(i=i,conn=s['conn'],old=n_old,new=len(res['regs'])))
        pts=[a]+[tuple(q) for q in res['regs']]+[b]
        st['max_hop_new']=max(st['max_hop_new'],max(abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(pts,pts[1:])))
        s['from_um'],s['to_um']=list(a),list(b);s['regs_um']=[list(q) for q in res['regs']]
        s['note']=s.get('note','')+f" | DIE-HBM-11 ring-move regenerated ({res['kind']}, {res['length_um']} um, {len(res['regs'])} st)"
    st['max_hop_new']=round(st['max_hop_new'],3)
    info['stations']=st;rep['types'][tn]=info
    t['note']=t.get('note','')+' | DIE-HBM-11 C25c ring_ag__q1 moved next to GQ east face (COORD 10-29 YES, 0 cycles)'
if out.exists():shutil.rmtree(out)
shutil.copytree(src,out,copy_function=os.link)
(out/'die_plan.json').unlink();(out/'die_plan.json').write_text(json.dumps(P,indent=1)+'\n')
rep['plan_sha256']=hashlib.sha256((out/'die_plan.json').read_bytes()).hexdigest()
(out/'ring_move_report.json').write_text(json.dumps(rep,indent=1)+'\n')
for tn,i in rep['types'].items():
    s=i['stations'];print(tn,{k:v for k,v in i.items() if k!='stations'},'regen',s['regenerated'],'regs',s['regs_old'],'->',s['regs_new'],'up',len(s['latency_up']),'short',len(s['padded_short']),'failed',len(s['failed']),'maxhop',s['max_hop_new'])
print(rep['plan_sha256'])

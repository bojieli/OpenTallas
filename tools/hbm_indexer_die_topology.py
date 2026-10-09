"""Source-pinned native R25I placement and full-shape endpoint pin plans.

The endpoint contract is a reservation until service/controller wrapper bindings
and measured timing are supplied. Historical R25 remains replayable.
"""
import json
from pathlib import Path


def install(m, fp):
    from hbm_indexer_r25i_model import hbm_indexer_r25i_physical_model
    root = fp.ROOT / 'physical/hbm_accel_die_views/index/native'
    master = 'hfd_idx_score_native_c2' if m['variant'].get('indexer_large_slot') else 'hfd_idx_score_native'
    scores = {}
    fixed = m.setdefault('fixed_ports', {})
    def add(name, mn, x, y, orient, kind):
        rec = json.loads((root / mn / 'ports.json').read_text())
        it = fp.Inst(name, mn, x, y, rec['w_um'], rec['h_um'], orient,
                     kind=kind, region='hub', domain='stream_1p2')
        m['insts'].append(it)
        def pins(mst, k=1, rec=rec):
            spec, order = {}, []
            for pn, port in rec['ports'].items():
                ps = port['pins']; first, last = ps[0], ps[-1]
                x0,y0=(first[2]+first[4])/2,(first[3]+first[5])/2
                if pn in ('ck','rst'):
                    spec[pn]=('area', 'M7', x0,y0,0.064,0.288)
                else:
                    face=port['face']; along0=y0 if face in 'WE' else x0
                    along1=(last[3]+last[5])/2 if face in 'WE' else (last[2]+last[4])/2
                    pitch=round((along1-along0)/(len(ps)-1)/0.048) if len(ps)>1 else 2
                    spec[pn]=('face',len(ps),face,port['layer'],
                              along0+len(ps)*pitch*0.048/2,pitch)
                order.append(pn)
            if k>1:
                fp._bundle_pack(mst,spec,order,k)
            mst.ports,mst.order=spec,order
        fixed[mn]=pins
        m.setdefault('master_notes',{})[mn]='Full-shape native indexer; exact and physical verdicts tracked separately'
        return it
    h=json.loads((root/master/'ports.json').read_text())['h_um']
    g=m['geo']
    # Reserve inner side bands outside all eight stack SM footprints. Origins
    # align to the M7 mirrored pin lattice and the 2.16um placement row lattice.
    for st,group in m['groups'].items():
        side,half=st
        x=10732.608 if half=='W' else 16994.88
        y=1596.24 if side=='S' else round(g['H']-1596.24-h,6)
        orient={'SW':'R0','SE':'MY','NW':'MX','NE':'R180'}[st]
        scores[st]=add('idx_score_'+st,master,x,y,orient,'hub')
    sel=add('idx_selector','hfd_idx_sel',14164.416,17169.84,'R0','spine')
    m['indexer_native']=dict(scores=scores, selector=sel,
        model=hbm_indexer_r25i_physical_model(),
        qualification='OPT_IN_NATIVE_RESERVATION; service joins and whole-die routing not yet qualified')
    m['notes'].append('R25I reserves four full16-lane scorers and captured-SRAM T1/LA7 selector; historical placeholder key/top-k nets require replacement before adoption.')


def networks(m, fp, buses, paths, chain):
    """Install actual scorer/selector and service line/credit boundaries.

    Native query/config and final selector producer/consumer joins are supplied
    by their source owner separately. They are never narrowed to old envelopes.
    """
    native=m['indexer_native']; sel=native['selector']; root=fp.ROOT/'physical/hbm_accel_die_views/index/native'
    def point(it, port, lo=0, count=None):
        rec=json.loads((root/it.master/'ports.json').read_text());pins=rec['ports'][port]['pins']
        ps=pins[lo:lo+count] if count is not None else pins
        x=sum((p[2]+p[4])/2 for p in ps)/len(ps);y=sum((p[3]+p[5])/2 for p in ps)/len(ps)
        if it.orient in ('MY','R180'):x=it.w-x
        if it.orient in ('MX','R180'):y=it.h-y
        return it.x+x,it.y+y
    def route(cid,bits,src,dst,pts):
        jogged=[pts[0]]
        for a,b in zip(pts,pts[1:]):
            if abs(a[0]-b[0])>1e-6 and abs(a[1]-b[1])>1e-6:
                jogged.append((b[0],a[1]))
            jogged.append(b)
        chain(cid,'index_native',bits,src,dst,jogged,path=cid,fc=(bits,),
              local_src=True,meso_end=True,dom='stream')
    for q,(st,score) in enumerate(native['scores'].items()):
        side,half=st;svc=m['groups'][st]['svc'];sgn=1 if side=='S' else -1
        startface='N' if side=='S' else 'S'
        # Each service eighth owns a physically distributed output station.
        # Native line storage still gathers all32PCs, per the packed136B ABI.
        for p in range(8):
            split=json.loads((fp.ROOT/m['variant']['split_x_masters']).read_text())
            band=split['bands'][split['parents'][svc.master]['bands'][p]]
            a=fp._cxy(svc,startface,(band['x0_um']+band['w_um']/2)/svc.w)
            b=point(score,'ik',p*1099,1099)
            gutter=svc.y+svc.h+40 if side=='S' else svc.y-40
            # Only two full line bundles occupy the service gap; five use the
            # real SM interrow channel and one uses the hub-edge channel.
            group=m['groups'][st];sms=group['sms']
            row0=next(i for i in sms if i.sm['row']==0)
            row1=next(i for i in sms if i.sm['row']==1)
            cxs=[group['x']+fp.CH/2+c*(row0.w+fp.SHAVE+fp.CH) for c in range(5)]
            col=min(cxs,key=lambda x:abs(x-a[0]))
            if p<2:
                cross=gutter+sgn*(10+24*p)
            elif p<7:
                mid=row0.y+row0.h+fp.SHAVE+fp.CH/2 if side=='S' else row0.y-fp.CH/2
                cross=mid+sgn*((p-4)*72)
            else:
                cross=row1.y+row1.h+fp.SHAVE+fp.CH/2 if side=='S' else row1.y-fp.CH/2
            outer=score.x-80-12*p if half=='W' else score.x+score.w+80+12*p
            pts=[a,(a[0],gutter),(col,gutter),(col,cross),(outer,cross),(outer,b[1]),b]
            route(f'idx_key_{st}_{p}',1099,(svc.name,f'ki{p}'),
                  (score.name,f'ik@{p*1099}:{(p+1)*1099-1}'),pts)
            c=point(score,'ikc',p,1)
            route(f'idx_key_credit_{st}_{p}',1,(score.name,f'ikc@{p}:{p}'),
                  (svc.name,f'kc{p}'),[c,(outer,c[1]),(outer,gutter),a])
        # Separate unidirectional data and credit preserve ownership exactly.
        # Query pin is the T1 direct quarter output, with no T4 column taps.
        a=point(sel,'qo',q*571,571);b=point(score,'q')
        lane=sel.x-160-32*q if half=='W' else sel.x+sel.w+160+32*q
        exit_y=score.y+score.h+100 if side=='S' else score.y-100
        route(f'idx_query_{st}',571,(sel.name,f'qo@{q*571}:{(q+1)*571-1}'),
              (score.name,'q'),[a,(lane,a[1]-80),(lane,exit_y),(b[0],exit_y),b])
        a=point(score,'s');b=point(sel,'si',q*610,610)
        route(f'idx_score_{st}',610,(score.name,'s'),
              (sel.name,f'si@{q*610}:{(q+1)*610-1}'),
              [a,(a[0]+(80 if half=='W' else -80),a[1]),
               (lane,exit_y),(lane,b[1]+80),b])
        a=point(sel,'sc',q,1);b=point(score,'sc')
        route(f'idx_score_credit_{st}',1,(sel.name,f'sc@{q}:{q}'),
              (score.name,'sc'),[a,(lane,a[1]-80),(lane,exit_y),(b[0],exit_y),b])
    native['unbound_producer_ports']=['fs90','qb1048','qbr1','kin345']
    native['unbound_consumer_ports']=['to612','toc1','co72','coc1','ev2','4xst4']
    native['qualification']='NATIVE_BOUNDARY_TOPOLOGY; source wrapper joins and exact pin routes remain unqualified'

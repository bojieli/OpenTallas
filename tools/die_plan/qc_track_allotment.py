"""Deterministic trunk allotment using the actual PG-aware TrackRouter.

This module orders logical driver nets without changing their cells, units,
masters, NDRs or endpoints. A trunk-only allotment is not a physical build PASS:
pin access, drops, ties and native geometry remain the builder's authority.
"""
from collections import defaultdict
import math


def order_nets(nets,cells,ndr_rules,default_ndr,row_y=.27):
    """Wide/long trunks first, preserving branches of each logical driver net.

    Pass the same cells/proxies used by the physical builder. Returned net
    dictionaries are copies; only their list/branch order changes.
    """
    import die_clock_128 as C
    def rank_piece(n,e):
        nd=ndr_rules[e.get('ndr',default_ndr)]
        d=n['drv'];loads=e.get('loads',n.get('loads',[]));span=0.
        if d in cells:
            p=C.pin_xy(cells,d,'Y',row_y)
            for u in loads:
                if u in cells:
                    q=C.pin_xy(cells,u,'A',row_y);span=max(span,abs(q[0]-p[0])+abs(q[1]-p[1]))
        return (-nd['width'],-span,str(e.get('edge',n['name'])))
    out=[]
    for n in nets:
        nn=dict(n);pieces=n.get('plan_connections')
        if pieces:
            nn['plan_connections']=sorted(pieces,key=lambda e:rank_piece(n,e))
            key=min(rank_piece(n,e) for e in pieces)
        else:key=rank_piece(n,{})
        out.append((key,str(n['name']),nn))
    return [n for _,_,n in sorted(out,key=lambda v:(v[0],v[1]))]


def _rules(router,request):
    if not router.ix.pairwise:
        raise ValueError('mixed-width allotment requires actual per-pair NDR spacing')
    router.nd=request['ndr'];router.ix.space=router.nd['space']
    import die_clock_128 as C
    router.wide_merge_um=request.get('wide_merge_um',router.nd.get('wide_merge_um',C.WIDE_MERGE_UM))


def candidates(router,r):
    """Exact PG/fixed-occupancy candidate tracks within the declared window."""
    _rules(router,r);tr=router.tracks[r['layer']];pitch=tr['pitch_um'];offset=tr['offset_um']
    lo,hi=r.get('keep',(r['ideal']-router.max_move,r['ideal']+router.max_move))
    lo=max(lo,r['ideal']-router.max_move);hi=min(hi,r['ideal']+router.max_move)
    first=math.ceil((lo-offset-1e-9)/pitch);last=math.floor((hi-offset+1e-9)/pitch)
    legal=[]
    for k in range(first,last+1):
        c=round(offset+k*pitch,4)
        got,mode,ext=router.place(r['layer'],c,*r['interval'],r['owner'],keep=(c,c),avoid=r.get('avoid',()),dry=True)
        if got is not None and not (mode=='drawn' and ext is None):
            legal.append(dict(track=got,mode=mode,extension=ext))
    return sorted(legal,key=lambda p:(abs(p['track']-r['ideal']),p['track']))


def allot(requests,router_factory):
    """Atomic driver-net packing, wide first and scarce/long next.

    Requests declare id, owner, layer, ideal, interval, ndr (actual rule dict),
    and optional keep. The factory must return a fresh router with the exact
    actual PG/mesh occupancy and per-pair spacing enabled. No synthetic gap
    capacity is substituted for actual legal track candidates.
    """
    static=router_factory();capacity={r['id']:candidates(static,r) for r in requests}
    groups=defaultdict(list)
    for r in requests:groups[r['owner']].append(r)
    def rank(r):return (-r['ndr']['width'],len(capacity[r['id']]),-abs(r['interval'][1]-r['interval'][0]),str(r['id']))
    owners=sorted(groups,key=lambda n:(min(rank(r) for r in groups[n]),str(n)))
    router=router_factory();placed=[];failed=[]
    for owner in owners:
        start=len(router.ix.shapes);moves=len(router.moves);old_modes=dict(router.modes);pending=[];bad=None
        for r in sorted(groups[owner],key=rank):
            _rules(router,r)
            c,mode,ext=router.place(r['layer'],r['ideal'],*r['interval'],owner,keep=r.get('keep'),avoid=r.get('avoid',()))
            if c is None or (mode=='drawn' and ext is None):
                overlaps=[p['owner'] for p in placed if p['layer']==r['layer'] and min(p['interval'][1],r['interval'][1])>max(p['interval'][0],r['interval'][0])]
                bad=dict(owner=owner,request=r['id'],static_candidates=len(capacity[r['id']]),candidate_tracks=[p['track'] for p in capacity[r['id']]],overlapping_allocated_owners=sorted(set(overlaps)),reason='no actual tied track in declared window')
                break
            pending.append(dict(owner=owner,request=r['id'],layer=r['layer'],interval=list(r['interval']),track=c,mode=mode,extension=ext,ndr=dict(r['ndr'])))
        if bad:
            router.ix.truncate(start);del router.moves[moves:];router.modes.clear();router.modes.update(old_modes);failed.append(bad)
        else:placed.extend(pending)
    runs={}
    for r in requests:
        pitch=static.tracks[r['layer']]['pitch_um'];rr=[]
        for p in sorted(capacity[r['id']],key=lambda v:v['track']):
            if rr and p['mode']==rr[-1]['mode'] and abs(p['track']-rr[-1]['last']-pitch)<1e-6:
                rr[-1]['last']=p['track'];rr[-1]['tracks']+=1
            else:rr.append(dict(first=p['track'],last=p['track'],tracks=1,mode=p['mode']))
        runs[r['id']]=rr
    return dict(status='TRUNK_ONLY_INCOMPLETE' if failed else 'TRUNKS_ALLOCATED_ACCESS_NOT_CHECKED',scope='Ordering/allotment proposal; pin stacks, drops, ties, body legality and full native dry build NOT CHECKED',owner_order=owners,assigned=placed,failures=failed,static_capacity={k:len(v) for k,v in capacity.items()},gap_runs=runs)


def fixed_occupancy_router(router):
    """Snapshot exact PG+mesh before/after routing, excluding tree pressure.

    Cache once per builder run. This is a diagnostic copy, never the active
    router. All actual fixed rectangles and their per-pair spacing are retained.
    """
    import die_clock_128 as C
    fixed=C.TrackRouter(dict(router.nd),router.shield,router.tracks,
                        max_move=router.max_move,wide_merge_um=router.wide_merge_um)
    fixed.ix.pairwise=router.ix.pairwise
    fixed.reserve([s for s in router.ix.shapes if s[2] in ('pg','mesh')])
    return fixed


def failure_witness(fixed,active,layer,ideal,a0,a1,net,keep=None,avoid=()):
    """Serialize an EXACT failed place() call for future full-run diagnostics.

    Invoke only after the active call failed, using its unchanged arguments.
    It probes cached fixed occupancy, never mutates active geometry or retries a
    build. Zero tied candidates distinguishes a static geometry/tie limitation
    from a failure caused by occupied tracks on this very interval/window.
    """
    fixed.max_move=active.max_move
    r=dict(id=net,owner=net,layer=layer,ideal=ideal,interval=sorted((a0,a1)),
           ndr=dict(active.nd),wide_merge_um=active.wide_merge_um,avoid=list(avoid))
    if keep is not None:r['keep']=list(keep)
    legal=candidates(fixed,r)
    return dict(request=r,static_candidate_count=len(legal),static_candidates=legal,
                classification='STATIC_UNAVAILABLE' if not legal else 'ROUTE_PRESSURE_ON_EXACT_CALL',
                scope='Exact failed interval/keep/avoid; tied static PG+mesh candidates only; not full build PASS')

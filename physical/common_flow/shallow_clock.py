"""Plan a bounded-depth clock trunk on free physical sites, before local CTS.

The existing density tap buffers are leaves. All leaves have the same number
of trunk stages; only the local tap nets go through TritonCTS afterwards.
Geometry uses native OpenDB DBU throughout. No RTL or cycle count changes.
"""
import argparse
import bisect
import json
import math
from pathlib import Path


def load_geometry(path):
    g = dict(rows=[], cells=[], taps=[])
    orientations={}
    for line in Path(path).read_text().splitlines():
        f = line.split()
        if not f or f[0].startswith('#'):
            continue
        k = f.pop(0)
        if k == 'DBU': g['dbu'] = int(f[0])
        elif k == 'CORE': g['core'] = list(map(int, f[:4]))
        elif k == 'ROOT': g['root'] = list(map(int, f[:2]))
        elif k == 'ROOT_NAME': g['root_name'] = f[0]
        elif k == 'MASTER': g['master'], g['width'], g['height'] = f[0], int(f[1]), int(f[2])
        elif k == 'ROW': g['rows'].append(list(map(int, f[:5])) + [f[5] if len(f)>5 else 'R0'])
        elif k == 'ROW_ORIENT': orientations[(int(f[1]),int(f[2]))]=f[3]
        elif k == 'CELL': g['cells'].append([f[0]]+list(map(int, f[1:6])))
        elif k == 'TAP': g['taps'].append(dict(name=f[0], xy=list(map(int,f[1:3])), nets=f[3:5]))
    for row in g['rows']:row[5]=orientations.get((row[0],row[1]),row[5])
    for k in ('dbu','core','root','master','width','height'):
        if k not in g: raise ValueError(f'missing physical geometry {k}')
    if not g['taps'] or not g['rows']: raise ValueError('missing taps or legal rows')
    return g


class FreeSites:
    def __init__(self, g):
        self.w, self.h = g['width'], g['height']
        self.rows = g['rows']
        self.busy = [[] for _ in self.rows]
        ordered = sorted((r[1],i) for i,r in enumerate(self.rows))
        ys = [y for y,i in ordered]
        maxrh=max(r[3] for r in self.rows)
        for name,x0,y0,x1,y1,block in g['cells']:
            # Every occupied footprint counts, including movable logic/F6 FFs.
            lo = bisect.bisect_right(ys,y0-maxrh)
            hi = bisect.bisect_left(ys,y1)
            for y,i in ordered[lo:hi]:
                if y+self.rows[i][3]>y0: self.busy[i].append((x0,x1))
        for i in range(len(self.rows)): self.busy[i].sort()

    def legal(self, xy, reserve=True):
        tx,ty=xy[0]-self.w/2,xy[1]-self.h/2
        best=None
        for i in sorted(range(len(self.rows)),key=lambda i:(abs(self.rows[i][1]-ty),i)):
            rx,y,sw,rh,ns,orient=self.rows[i]
            if rh != self.h: continue
            if best is not None and abs(y-ty)>best[0]: break
            end=rx+sw*ns
            intervals=[]
            for a,b in self.busy[i]:
                if b<=rx or a>=end: continue
                if intervals and a<=intervals[-1][1]: intervals[-1]=(intervals[-1][0],max(b,intervals[-1][1]))
                else: intervals.append((max(rx,a),min(end,b)))
            start=rx
            for a,b in intervals+[(end,end)]:
                left=math.ceil((start-rx)/sw)
                right=math.floor((a-self.w-rx)/sw)
                if left<=right:
                    ix=min(max(round((tx-rx)/sw),left),right)
                    x=rx+ix*sw
                    v=(abs(x-tx)+abs(y-ty),i,x,y,orient)
                    if best is None or v<best: best=v
                start=max(start,b)
        if best is None: raise ValueError('no free row-legal clock buffer footprint')
        _,i,x,y,orient=best
        if reserve: bisect.insort(self.busy[i],(x,x+self.w))
        return dict(ll=[x,y],xy=[x+self.w/2,y+self.h/2],orient=orient,row=i)

    def take(self, site):
        """Reserve an already chosen footprint (island site) on its row."""
        bisect.insort(self.busy[site['row']],(site['ll'][0],site['ll'][0]+self.w))

    def release(self, site):
        self.busy[site['row']].remove((site['ll'][0],site['ll'][0]+self.w))

    def island(self, xy, k, span, step, reach):
        """CLOCK-RESET S1b: k compact free footprints (max pairwise Manhattan
        distance of their centres <= span DBU) for one cluster's leg-start
        buffers, centred as near xy as the existing placement allows.  Searched
        on square rings of pitch step out to reach DBU; the reservation is
        made on the frozen placement (white space only, nothing moves).  Falls
        back to the most compact candidate seen."""
        best=None
        rings=int(reach//step)
        for r in range(rings+1):
            cands=[(0,0)] if r==0 else [(dx,dy) for dx in range(-r,r+1) for dy in range(-r,r+1) if max(abs(dx),abs(dy))==r]
            for dx,dy in sorted(cands,key=lambda q:(abs(q[0])+abs(q[1]),q)):
                c=[xy[0]+dx*step,xy[1]+dy*step]
                got=[]
                try:
                    for _ in range(k): got.append(self.legal(c,reserve=True))
                except ValueError:
                    pass
                for s_ in got: self.release(s_)
                if len(got)<k: continue
                sp=max((_man(a['xy'],b['xy']) for a in got for b in got),default=0)
                off=_man([sum(s_['xy'][0] for s_ in got)/k,sum(s_['xy'][1] for s_ in got)/k],xy)
                v=(sp>span,sp if sp>span else off,off)
                if best is None or v<best[0]: best=(v,got)
            if best is not None and not best[0][0]: break
        if best is None: raise ValueError('no free clock buffer island')
        return best[1]


def split(points, count):
    ax=max((0,1),key=lambda j:(max(p['xy'][j] for p in points)-min(p['xy'][j] for p in points),-j))
    pts=sorted(points,key=lambda p:(p['xy'][ax],p['xy'][1-ax],p['name']))
    count=min(count,len(pts))
    return [pts[len(pts)*i//count:len(pts)*(i+1)//count] for i in range(count)]


def corridor_router(helper=None):
    """Use the existing clock visibility-grid router, copied beside kit script."""
    import importlib.util
    paths=([Path(helper)] if helper else [])+[Path(__file__).parent/'clock_corridor.py',
        Path(__file__).parent.parent.parent/'tools/die_plan/clock_corridor.py']
    path=next((p for p in paths if p.is_file()),None)
    if path is None:
        raise ValueError('macro-aware clock trunk requires clock_corridor.py beside the kit script')
    spec=importlib.util.spec_from_file_location('_ot_clock_corridor',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod.route


def split_spatial_2d(points):
    """Balanced 2x2 spatial cuts instead of four long one-axis slabs.

    E5's SRAM columns make a slab span both opposite macro faces. Two orthogonal
    count cuts keep each child spatially compact while retaining equal tree depth.
    """
    if len(points)<4:
        return split(points,min(4,len(points)))
    ax=max((0,1),key=lambda j:max(p['xy'][j] for p in points)-min(p['xy'][j] for p in points))
    pts=sorted(points,key=lambda p:(p['xy'][ax],p['xy'][1-ax],p['name']))
    halves=[pts[:len(pts)//2],pts[len(pts)//2:]]
    groups=[]
    for h in halves:
        q=sorted(h,key=lambda p:(p['xy'][1-ax],p['xy'][ax],p['name']))
        groups.extend([q[:len(q)//2],q[len(q)//2:]])
    return [g for g in groups if g]


def plan(g, fanout=4, leaf_fanout=8, max_hop_um=400):
    if fanout<2 or leaf_fanout<1: raise ValueError('invalid clock fanout')
    a,b,c,d=g['core']
    if any(not (a<=t['xy'][0]<=c and b<=t['xy'][1]<=d) for t in g['taps']):
        raise ValueError('tap buffer lies outside the physical core')
    level=0
    while leaf_fanout*fanout**level<len(g['taps']): level+=1
    sites=FreeSites(g)
    nodes=[]; edges=[]
    def build(pts,parent,remaining,depth,desired=None):
        nm=f'ot_dtsh_{len(nodes)}'
        xy=desired or [sum(p['xy'][j] for p in pts)/len(pts) for j in (0,1)]
        node=dict(name=nm,parent=parent,depth=depth,**{k_:v_ for k_,v_ in sites.legal(xy).items() if k_!='row'})
        nodes.append(node)
        if parent: edges.append([parent,nm])
        if remaining:
            for group in split(pts,fanout): build(group,nm,remaining-1,depth+1)
        else:
            for t in pts: edges.append([nm,t['name']])
    # One common lead from the physical pin to the spatial tree. It is common
    # to every tap, instead of making four long high-load branches at the pin.
    lead=dict(name='ot_dtsh_0',parent=None,depth=1,**{k_:v_ for k_,v_ in sites.legal(g['root']).items() if k_!='row'})
    nodes.append(lead)
    build(g['taps'],lead['name'],level,2)
    xy={n['name']:n['xy'] for n in nodes}|{t['name']:t['xy'] for t in g['taps']}
    max_hop=max(abs(xy[a][0]-xy[b][0])+abs(xy[a][1]-xy[b][1]) for a,b in edges)/g['dbu']
    stub=sum(abs(a-b) for a,b in zip(nodes[0]['xy'],g['root']))/g['dbu']
    max_hop=max(max_hop,stub)
    if max_hop>max_hop_um: raise ValueError(f'planned clock edge {max_hop:.3f} um exceeds {max_hop_um}')
    p=dict(nodes=nodes,edges=edges,taps=g['taps'],root=g['root'],root_name=g.get('root_name',''),
           dbu=g['dbu'],core=g['core'],master=g['master'],width=g['width'],height=g['height'],
           obstacles=[c[1:5] for c in g['cells'] if c[5]],
           summary=dict(new_buffers=len(nodes),tap_buffers=len(g['taps']),trunk_levels=level+3,
                        max_hop_um=max_hop,port_stub_um=stub,fanout=fanout,leaf_fanout=leaf_fanout,
                        added_cycles=0,added_area_um2=len(nodes)*g['width']*g['height']/g['dbu']**2))
    validate(p)
    return p


# ---------------------------------------------------------------------------
# CLOSED-LOOP structured spine (CLOCK-TRUNK 10-25, MSCTS practice).
# Every tree edge is a private buffered LEG: a leg-start buffer next to the
# parent cluster point, n repeaters along a (possibly detoured) path, and a
# 2-pin wire into the child (the child cluster's leg-start buffers, or the
# density-tap input).  All legs of one level have the same repeater count, so
# every tap has the same stage count; every segment is <= rmax_um.  The open-
# loop geometry is only the start point: OpenROAD measures the tap arrivals
# (TT + FF, its own parasitic estimate) and cl_step() re-targets each leg's
# length bottom-up until the tap spread meets the target.
# ---------------------------------------------------------------------------
def _man(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])


def plan_legs(g, fanout=4, leaf_fanout=2, rmax_um=100.0, slack=1.0, min_rep=1, topology='bisect', levels=0, depth0=False, island_um=0.0, island_reach_um=40.0, leg_extra_um=None, spatial_2d=False, avoid_macros=False, corridor_helper=None):
    """topology 'htree' (default): symmetric 2x2 H-tree over the tap region,
    pruned where a quadrant has no tap; every tap gets a private leg from its
    H-tree leaf.  'bisect': count-balanced geometric bisection (fanout/leaf)."""
    if fanout<2 or leaf_fanout<1: raise ValueError('invalid clock fanout')
    if not isinstance(min_rep,int) or min_rep<0: raise ValueError('min_rep must be a nonnegative integer')
    a,b,c,d=g['core']; u=g['dbu']
    if any(not (a<=t['xy'][0]<=c and b<=t['xy'][1]<=d) for t in g['taps']):
        raise ValueError('tap buffer lies outside the physical core')
    clusters=[]; legs=[]
    def cent(pts): return [sum(p['xy'][j] for p in pts)/len(pts) for j in (0,1)]
    def add_taps(cid,pts,level):
        for t in pts:
            legs.append(dict(id=len(legs),level=level+1,parent=cid,child=['tap',t['name']]))
            clusters[cid]['legs'].append(legs[-1]['id'])
    def link(cid,ch,level):
        legs.append(dict(id=len(legs),level=level+1,parent=cid,child=['cluster',ch]))
        clusters[cid]['legs'].append(legs[-1]['id']); clusters[ch]['in_leg']=legs[-1]['id']
    if topology=='bisect':
        depth=0
        while leaf_fanout*fanout**depth<len(g['taps']): depth+=1
        def medoid(pts):
            c0=cent(pts);return list(min(pts,key=lambda t:(_man(t['xy'],c0),t['name']))['xy'])
        def build(pts,level):
            cid=len(clusters); clusters.append(dict(id=cid,level=level,point=medoid(pts),taps=[t['name'] for t in pts],legs=[]))
            if level<depth:
                groups=split_spatial_2d(pts) if spatial_2d and fanout==4 else split(pts,fanout)
                for grp in groups: link(cid,build(grp,level+1),level)
            else: add_taps(cid,pts,level)
            return cid
        # depth0 (opt-in OT_DTSH_DEPTH0=1): count bisections from zero so a terminal
        # cluster holds <= leaf_fanout taps.  Legacy start 1 leaves fanout*leaf_fanout
        # (E5: 8) tap legs on one cluster net, whose 8 leg-start BUFx24 the legaliser
        # spreads along one row (76-112 um) -> 87-175 ps trunk-input slew (CLOCK-RESET S1).
        build(g['taps'],0 if depth0 else 1)
    elif topology=='htree':
        xs=[t['xy'][0] for t in g['taps']]; ys=[t['xy'][1] for t in g['taps']]
        box=[min(xs),min(ys),max(xs),max(ys)]
        depth=levels
        if not depth:
            depth=1
            while ((box[2]-box[0])+(box[3]-box[1]))/2**(depth+1)/u>1.25*rmax_um: depth+=1
        def build(pts,r,level):
            cid=len(clusters); clusters.append(dict(id=cid,level=level,point=[(r[0]+r[2])/2,(r[1]+r[3])/2],
                                                   taps=[t['name'] for t in pts],legs=[],rect=r))
            if level<=depth:
                mx,my=(r[0]+r[2])/2,(r[1]+r[3])/2
                for q in ([r[0],r[1],mx,my],[mx,r[1],r[2],my],[r[0],my,mx,r[3]],[mx,my,r[2],r[3]]):
                    sub=[t for t in pts if q[0]<=t['xy'][0]<(q[2] if q[2]<r[2] else q[2]+1) and q[1]<=t['xy'][1]<(q[3] if q[3]<r[3] else q[3]+1)]
                    if sub: link(cid,build(sub,q,level+1),level)
            else: add_taps(cid,pts,level)
            return cid
        build(g['taps'],box,1)
    else: raise ValueError(f'unknown trunk topology {topology}')
    # cluster points on legal free logic sites (a centre may fall on a macro).
    # H-tree: keep the symmetry -- among free sites near the ideal centre pick
    # the one whose distance from the (already placed) parent is closest to
    # the nominal level distance, so one snapped quadrant does not force every
    # sibling leg to be padded to its length.
    probe=FreeSites(g)
    ideal={cl['id']:list(cl['point']) for cl in clusters}
    par={}
    for L in legs: par[L['child'][1]]=L['parent'] if L['child'][0]=='cluster' else None
    for cl in sorted(clusters,key=lambda c:c['level']):
        pid=par.get(cl['id'])
        if topology!='htree' or pid is None:
            cl['point']=probe.legal(cl['point'],reserve=False)['xy'];continue
        P=clusters[pid]['point'];I=ideal[cl['id']];dn=_man(ideal[pid],I)
        r=cl['rect'];hw,hh=(r[2]-r[0])/2,(r[3]-r[1])/2
        best=None
        for fx in [i/8 for i in range(-6,7)]:
            for fy in [i/8 for i in range(-6,7)]:
                q=probe.legal([I[0]+fx*hw,I[1]+fy*hh],reserve=False)['xy']
                cost=4*max(0.0,_man(P,q)-dn)+_man(q,I)
                if best is None or cost<best[0]: best=(cost,q)
        cl['point']=best[1]
    # S1b (opt-in island_um > 0): reserve a compact island of free footprints for
    # every cluster's leg-start buffers (one per out-leg) at the cluster point, so
    # the cluster net (parent leg -> k leg starts) is a short fan, not k buffers
    # legalised up to ~100 um apart along a row.  The cluster point becomes the
    # island centre; the islands are reserved first in every realize().
    if island_um>0:
        isl=FreeSites(g)
        for cl in sorted(clusters,key=lambda c:(c['level'],c['id'])):
            sites_=isl.island(cl['point'],len(cl['legs']),island_um*u,max(1.0,island_um/2)*u,island_reach_um*u)
            for s_ in sites_: isl.take(s_)
            cl['island']=[dict(ll=s_['ll'],xy=s_['xy'],orient=s_['orient'],row=s_['row']) for s_ in sites_]
            cl['island_span_um']=max((_man(a['xy'],b['xy']) for a in sites_ for b in sites_),default=0)/u
            cl['point']=[sum(s_['xy'][0] for s_ in sites_)/len(sites_),sum(s_['xy'][1] for s_ in sites_)/len(sites_)]
    lead=dict(id=len(legs),level=0,parent=None,child=['cluster',0]); legs.append(lead); clusters[0]['in_leg']=lead['id']
    tapxy={t['name']:t['xy'] for t in g['taps']}
    router=corridor_router(corridor_helper) if avoid_macros else None
    obstacles=[cc[1:5] for cc in g['cells'] if cc[5]]
    for L in legs:
        L['A']=list(g['root']) if L['parent'] is None else clusters[L['parent']]['point']
        L['C']=clusters[L['child'][1]]['point'] if L['child'][0]=='cluster' else tapxy[L['child'][1]]
        if router:
            L['path']=[list(x) for x in router(L['A'],L['C'],obstacles,[g['core'][2],g['core'][3]])]
            L['d']=sum(_man(a,b) for a,b in zip(L['path'],L['path'][1:]))
        else:
            L['d']=_man(L['A'],L['C'])
    reps={}
    tl=max(L['level'] for L in legs)
    for lv in sorted({L['level'] for L in legs}):
        dm=max(L['d'] for L in legs if L['level']==lv)/u
        if lv==0: reps[lv]=max(0,math.ceil(dm/rmax_um)-1)
        elif lv==tl: reps[lv]=max(min_rep,math.ceil(dm*slack/rmax_um)-1)   # tap legs: always detour-capable
        else: reps[lv]=max(0,math.ceil(dm*slack/rmax_um)-1)
    k=0
    for L in sorted(legs,key=lambda L:(L['level'],L['id'])):
        L['n']=reps[L['level']]
        L['xmax']=max(0.0,2*rmax_um*u-2*L['d']/(L['n']+1)) if L['level'] and L['n'] else 0.0
        # Explicit geometric cap on compensation wire. Intrinsic local-tree
        # insertion must be fixed locally rather than hidden in long trunk legs.
        if leg_extra_um is not None:
            if not math.isfinite(leg_extra_um) or leg_extra_um < 0:
                raise ValueError('leg_extra_um must be finite and nonnegative')
            L['xmax'] = min(L['xmax'], leg_extra_um * u)
        if avoid_macros: L['xmax']=0.0  # no blind ellipse may leave the legal repeater corridor
        # equal-length start: every leg of a level as long as its longest
        dm=max(M['d'] for M in legs if M['level']==L['level'])
        L['x']=min(L['xmax'],float(dm-L['d'])) if L['level'] else 0.0
        L['bufs']=[f'ot_dtsh_{k+i}' for i in range(L['n']+1)]; k+=L['n']+1
        L['hist']=[]
    p=dict(mode='closed_loop',topology=topology,clusters=clusters,legs=legs,taps=g['taps'],root=g['root'],root_name=g.get('root_name',''),
           dbu=u,core=g['core'],master=g['master'],width=g['width'],height=g['height'],
           obstacles=[cc[1:5] for cc in g['cells'] if cc[5]],rmax_um=rmax_um,reps=reps,iters=[],
           fanout=fanout,leaf_fanout=leaf_fanout,avoid_macros=avoid_macros,corridor_helper=str(corridor_helper) if corridor_helper else None)
    realize(p,g)
    return p


def leg_path(A,C,T,core,side=1,axis=None):
    """Manhattan polyline A->C of length T (>= |A-C|): L-shape, or a U-detour
    beyond the bounding box (on the minor axis by default) when T exceeds the
    distance."""
    dx,dy=abs(A[0]-C[0]),abs(A[1]-C[1])
    ax=(1 if dx>=dy else 0) if axis is None else axis   # ax = detour axis
    e=max(0.0,(T-dx-dy)/2)
    lo,hi=min(A[ax],C[ax]),max(A[ax],C[ax])
    cands=[hi+e,lo-e] if side>0 else [lo-e,hi+e]
    w=A[ax]
    if e>0:
        w=None
        for v in cands:
            if core[ax]<=v<=core[ax+2]: w=v;break
        if w is None: w=min(max(cands[0],core[ax]),core[ax+2])
    def pt(v_ax,v_other):
        q=[0,0];q[ax]=v_ax;q[1-ax]=v_other;return q
    return [list(A),pt(w,A[1-ax]),pt(w,C[1-ax]),list(C)]


def along(poly,s):
    for a,b in zip(poly,poly[1:]):
        l=_man(a,b)
        if s<=l and l>0:
            f=s/l;return [a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f]
        s-=l
    return list(poly[-1])


def ellipse_pick(sites,B,C,R,prev,core,rmax,u,rays=20):
    """Free site q with |B-q|+|q-C| ~= R (an L1 ellipse around B,C), both
    halves <= rmax, nearest to the previous choice (continuity)."""
    M=[(B[0]+C[0])/2,(B[1]+C[1])/2]
    def f(q): return _man(B,q)+_man(q,C)
    cands=[]
    if R<=_man(B,C)+1: cands.append(M)
    else:
        for k in range(rays):
            th=2*math.pi*k/rays;dv=(math.cos(th),math.sin(th))
            lo,hi=0.0,R
            def at(t): return [min(max(M[0]+t*dv[0],core[0]),core[2]),min(max(M[1]+t*dv[1],core[1]),core[3])]
            if f(at(hi))<R: continue
            for _ in range(30):
                mid=(lo+hi)/2
                if f(at(mid))<R: lo=mid
                else: hi=mid
            cands.append(at(hi))
        if not cands: cands.append(M)
    best=None
    for q in cands:
        s=sites.legal(q,reserve=False)['xy']
        over=max(0.0,max(_man(B,s),_man(s,C))-rmax*u)
        cost=abs(f(s)-R)+25*over+(0.25*_man(s,prev) if prev else 0)
        if best is None or cost<best[0]: best=(cost,s)
    return best[1]


def realize(p,g):
    """Legal free-site positions for every leg buffer; top-down order.  The
    first n-1 repeaters sit on the direct L-path; the last one is the leg's
    length knob: a free site on the L1 ellipse of the requested length."""
    sites=FreeSites(g); nodes=[]; edges=[]
    last={}; u=p['dbu']
    pool={}
    for cl in p['clusters']:
        if cl.get('island'):
            for s_ in cl['island']: sites.take(s_)
            pool[cl['id']]=[dict(ll=list(s_['ll']),xy=list(s_['xy']),orient=s_['orient']) for s_ in cl['island']]
    for L in sorted(p['legs'],key=lambda L:(L['level'],L['id'])):
        n=L['n'];A,C=L['A'],L['C'];d=L['d']
        poly=L.get('path') or leg_path(A,C,d,p['core'])
        parent=None if L['parent'] is None else last[('cl',L['parent'])]
        pos=[]
        for i,nm in enumerate(L['bufs']):
            if i==0: xy=A
            elif i<n or L.get('path'): xy=along(poly,d*i/(n+1))
            else:
                B=pos[-1]
                done=sum(_man(a,b) for a,b in zip(pos,pos[1:]))
                R=max(_man(B,C),L['d']+L['x']-done)
                xy=ellipse_pick(sites,B,C,R,L.get('qprev'),p['core'],p['rmax_um'],u)
            if i==0 and L['parent'] is not None and pool.get(L['parent']):
                site=pool[L['parent']].pop(0)
            else:
                site={k_:v_ for k_,v_ in sites.legal(xy).items() if k_!='row'}
            node=dict(name=nm,parent=parent,depth=L['level'],leg=L['id'],**site)
            pos.append(node['xy'])
            nodes.append(node)
            if parent: edges.append([parent,nm])
            parent=nm
        if n: L['qprev']=pos[-1]
        L['T']=sum(_man(a,b) for a,b in zip(pos,pos[1:]))+_man(pos[-1],C)
        L['seg_um']=max(_man(a,b) for a,b in zip(pos,pos[1:]+[C]))/u
        if L['child'][0]=='cluster': last[('cl',L['child'][1])]=parent
        else: edges.append([parent,L['child'][1]])
    p['nodes']=nodes; p['edges']=edges
    xy={n['name']:n['xy'] for n in nodes}|{t['name']:t['xy'] for t in p['taps']}
    if p.get('avoid_macros'):
        route=corridor_router(p.get('corridor_helper'))
        p['wire_paths']={'|'.join((a,b)):[list(z) for z in route(xy[a],xy[b],p['obstacles'],[p['core'][2],p['core'][3]])] for a,b in edges}
        hop=max(sum(_man(a,b) for a,b in zip(q,q[1:])) for q in p['wire_paths'].values())/p['dbu']
    else:
        hop=max(_man(xy[a],xy[b]) for a,b in edges)/p['dbu']
    p['summary']=dict(mode='closed_loop',new_buffers=len(nodes),tap_buffers=len(p['taps']),
                      trunk_levels=sum(n+1 for n in p['reps'].values()),reps={str(k):v for k,v in p['reps'].items()},
                      max_hop_um=hop,rmax_um=p['rmax_um'],added_cycles=0,
                      island_span_max_um=max((cl.get('island_span_um',0) for cl in p['clusters']),default=0),
                      added_area_um2=len(nodes)*p['width']*p['height']/p['dbu']**2)
    validate(p)
    return p


def read_meas(path):
    tap={};buf={}
    for line in Path(path).read_text().splitlines():
        f=line.split()
        if len(f)<4: continue
        if f[0]=='T': tap[f[1]]=(float(f[2]),float(f[3]))
        elif f[0]=='B': buf[f[1]]=(float(f[2]),float(f[3]))
    return tap,buf


def spread(tap):
    tt=[v[0] for v in tap.values()];ff=[v[1] for v in tap.values()]
    return max(tt)-min(tt),max(ff)-min(ff)


def cl_step(p,tap,buf,damp=0.8,k0=0.2,kmin=0.04,kmax=1.5):
    """One closed-loop update from MEASURED arrivals (ps) at tap inputs (TT,FF)
    and leg-buffer inputs.  Bottom-up: inside each cluster every child leg is
    re-targeted so the child subtrees' mean arrival is equal and the shortest
    leg is direct (x=0); predicted subtree means feed the level above."""
    u=p['dbu']
    tt=[v[0] for v in tap.values()];ff=[v[1] for v in tap.values()]
    r=(sum(tt)/len(tt))/(sum(ff)/len(ff))
    m={t:(v[0]+r*v[1])/2 for t,v in tap.items()}
    mb={b:(v[0]+r*v[1])/2 for b,v in buf.items()}
    legs={L['id']:L for L in p['legs']}; cl=p['clusters']
    def child_in(L):
        if L['child'][0]=='tap': return m[L['child'][1]]
        ins=[mb[legs[j]['bufs'][0]] for j in cl[L['child'][1]]['legs'] if legs[j]['bufs'][0] in mb]
        return sum(ins)/len(ins) if ins else None
    # per-leg sensitivity (ps per um of leg length), secant over history
    for L in p['legs']:
        D=None
        if L['bufs'][0] in mb:
            ci=child_in(L)
            if ci is not None: D=ci-mb[L['bufs'][0]]
        L['hist'].append([L['T']/u,D])
        h=[q for q in L['hist'] if q[1] is not None]
        k=L.get('k',k0)
        if len(h)>=2 and abs(h[-1][0]-h[-2][0])>2:
            k=(h[-1][1]-h[-2][1])/(h[-1][0]-h[-2][0])
        L['k']=min(kmax,max(kmin,k))
    pred={}
    def visit(cid):
        vals=[]
        for j in cl[cid]['legs']:
            L=legs[j]
            v=m[L['child'][1]] if L['child'][0]=='tap' else visit(L['child'][1])
            vals.append((L,v))
        # common target: the latest child at its shortest legal length
        tau=max(v-L['k']*L['x']/u for L,v in vals)
        out=[]
        for L,v in vals:
            want=L['x']+damp*(tau-v)/L['k']*u
            xn=min(L['xmax'],max(0.0,want))
            if want>xn: L['_res']=L['k']*(want-xn)/u
            out.append(v+L['k']*(xn-L['x'])/u); L['x']=xn
        pred[cid]=sum(out)/len(out)
        return pred[cid]
    visit(0)
    # a clipped leg (no repeater / at its length cap) cannot carry its share:
    # push the residual into every leg of the child subtree instead
    def push(cid,r):
        for j in cl[cid]['legs']:
            L=legs[j];xn=min(L['xmax'],L['x']+damp*r/L['k']*u)
            res=r-L['k']*(xn-L['x'])/u;L['x']=xn
            if res>0.5 and L['child'][0]=='cluster': push(L['child'][1],res)
    for L in p['legs']:
        res=L.pop('_res',0)
        if res>0.5 and L['child'][0]=='cluster': push(L['child'][1],res)
    s=spread(tap)
    if 'best' not in p or max(s)<p['best']['spread']:
        p['best']=dict(iter=len(p['iters'])+1,spread=max(s),nodes=[[n['name'],n['ll'],n['orient']] for n in p['nodes']])
    p['iters'].append(dict(tt_spread=s[0],ff_spread=s[1],tt=[min(tt),max(tt)],ff=[min(ff),max(ff)],
                           capped=sum(1 for L in p['legs'] if L['level'] and L['x']>=L['xmax']-1)))
    return s


def emit_moves(p,out):
    import re
    lines=['# closed-loop trunk re-placement (same names/topology); native DBU','ot_dtsh::relocate_begin']
    for n in p['nodes']:
        if not re.fullmatch(r'ot_dtsh_\d+',n['name']):raise ValueError('unsafe trunk name')
        x,y=n['ll'];lines.append(f"ot_dtsh::relocate {n['name']} {x} {y} {n['orient']}")
    lines.append('ot_dtsh::relocate_end')
    Path(out).write_text('\n'.join(lines)+'\n')


def _strip(p):
    return {k:v for k,v in p.items() if k not in ('obstacles',)}


def validate(p):
    names={n['name'] for n in p['nodes']}
    taps={t['name'] for t in p['taps']}
    parents={}
    for a,b in p['edges']:
        if a not in names or b not in names|taps or b in parents: raise ValueError('broken trunk ownership')
        parents[b]=a
    roots=names-set(parents)
    if len(roots)!=1 or not taps<=set(parents): raise ValueError('missing root or tap clock driver')
    depths=[]
    for t in taps:
        seen=set();n=t
        while n in parents:
            if n in seen: raise ValueError('clock trunk cycle')
            seen.add(n);n=parents[n]
        depths.append(len(seen)+1)
    if len(set(depths))!=1: raise ValueError('unequal clock trunk levels')


def render(p,out):
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(7,7))
    from matplotlib.patches import Rectangle
    u=p['dbu']; xy={n['name']:n['xy'] for n in p['nodes']}|{t['name']:t['xy'] for t in p['taps']}
    for x0,y0,x1,y1 in p.get('obstacles',[]):ax.add_patch(Rectangle((x0/u,y0/u),(x1-x0)/u,(y1-y0)/u,color='#ddd'))
    for a,b in p['edges']:
        route=p.get('wire_paths',{}).get('|'.join((a,b)))
        if route:
            ax.plot([q[0]/u for q in route],[q[1]/u for q in route],color='#4878a8',lw=.6)
        else:
            x,y=xy[a];xx,yy=xy[b]
            ax.plot([x/u,xx/u,xx/u],[y/u,y/u,yy/u],color='#4878a8',lw=.6)
    ax.scatter([t['xy'][0]/u for t in p['taps']],[t['xy'][1]/u for t in p['taps']],s=12,label='existing tap buffer')
    ax.scatter([n['xy'][0]/u for n in p['nodes']],[n['xy'][1]/u for n in p['nodes']],marker='s',s=25,label='planned trunk buffer')
    ax.scatter([p['root'][0]/u],[p['root'][1]/u],marker='*',s=100,color='black',label='actual clock pin')
    a,b,c,d=p['core'];rx,ry=p['root'];ax.set_xlim(min(a,rx)/u-3,max(c,rx)/u+3);ax.set_ylim(min(b,ry)/u-3,max(d,ry)/u+3);ax.set_aspect('equal')
    ax.set_title(f"{p['summary']['tap_buffers']} tap clock: {p['summary']['trunk_levels']} trunk levels, max edge {p['summary']['max_hop_um']:.1f} um")
    ax.legend(fontsize=7);fig.savefig(out,dpi=130,bbox_inches='tight')


def emit_apply(p,out):
    import re
    validate(p)
    lines=['# Generated bounded-depth clock trunk; native DBU coordinates.']
    for n in p['nodes']:
        if not re.fullmatch(r'ot_dtsh_\d+',n['name']):raise ValueError('unsafe trunk name')
        x,y=n['ll'];parent=n['parent'] or '@root'
        lines.append(f"ot_dtsh::node {n['name']} {x} {y} {n['orient']} {parent}")
    taps={t['name'] for t in p['taps']}
    for a,b in p['edges']:
        if b in taps:
            if not re.fullmatch(r'ot_dtap_\d+',b):raise ValueError('unsafe tap name')
            lines.append(f'ot_dtsh::leaf {b} {a}')
    Path(out).write_text('\n'.join(lines)+'\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('geometry');ap.add_argument('--out',required=True);ap.add_argument('--image');ap.add_argument('--apply')
    ap.add_argument('--closed-loop',action='store_true',help='structured spine of private buffered legs (re-targeted by --cl-step)')
    ap.add_argument('--cl-step',metavar='MEAS',help='measured arrivals TSV; updates --out plan in place and writes --apply moves')
    ap.add_argument('--target-ps',type=float,default=20.0)
    ap.add_argument('--new-phase',metavar='TAG',help='start a new measured phase (other metric): clear best + leg histories')
    ap.add_argument('--restore-best',action='store_true',help='write --apply moves back to the best measured iteration')
    a=ap.parse_args();g=load_geometry(a.geometry)
    env=__import__('os').environ
    if a.new_phase:
        p=json.loads(Path(a.out).read_text())
        p.pop('best',None);p['phase']=a.new_phase
        for L in p['legs']: L['hist']=[]
        p['iters'].append(dict(phase=a.new_phase))
        Path(a.out).write_text(json.dumps(p,indent=1)+'\n')
        print(json.dumps(dict(phase=a.new_phase)));return
    if a.restore_best:
        p=json.loads(Path(a.out).read_text())
        b=p['best'];pos={nm:(ll,o) for nm,ll,o in b['nodes']}
        same=all(pos[n['name']]==(n['ll'],n['orient']) for n in p['nodes'])
        for n in p['nodes']: n['ll'],n['orient']=pos[n['name']]
        if not same and a.apply: emit_moves(p,a.apply)
        Path(a.out).write_text(json.dumps(p,indent=1)+'\n')
        print(json.dumps(dict(restore=not same,best_iter=b['iter'],best_spread=round(b['spread'],2))))
        return
    if a.cl_step:
        p=json.loads(Path(a.out).read_text())
        p['reps']={int(k):v for k,v in p['reps'].items()}
        tap,buf=read_meas(a.cl_step)
        s=cl_step(p,tap,buf,damp=float(env.get('OT_DTSH_CL_DAMP','0.8')))
        done=max(s)<=a.target_ps
        if not done:
            realize(p,g)
            if a.apply: emit_moves(p,a.apply)
        Path(a.out).write_text(json.dumps(p,indent=1)+'\n')
        if a.image: render(p,a.image)
        print(json.dumps(dict(iter=len(p['iters']),tt_spread=round(s[0],2),ff_spread=round(s[1],2),done=done,
                              capped=p['iters'][-1]['capped'],buffers=len(p['nodes']))))
        return
    if a.closed_loop:
        p=plan_legs(g,fanout=int(env.get('OT_DTSH_FANOUT','4')),leaf_fanout=int(env.get('OT_DTSH_LEAF_FANOUT','2')),
                    rmax_um=float(env.get('OT_DTSH_RMAX_UM','100')),min_rep=int(env.get('OT_DTSH_MIN_REP','1')),topology=env.get('OT_DTSH_TOPOLOGY','bisect'),
                    levels=int(env.get('OT_DTSH_HTREE_LEVELS','0')),depth0=env.get('OT_DTSH_DEPTH0','')=='1',
                    island_um=float(env.get('OT_DTSH_ISLAND_UM','0')),island_reach_um=float(env.get('OT_DTSH_ISLAND_REACH_UM','40')),
                    leg_extra_um=float(env['OT_DTSH_LEG_EXTRA_UM']) if 'OT_DTSH_LEG_EXTRA_UM' in env else None,
                    spatial_2d=env.get('OT_DTSH_SPATIAL_2D','')=='1',avoid_macros=env.get('OT_DTSH_AVOID_MACROS','')=='1',
                    corridor_helper=env.get('OT_DTSH_CORRIDOR_HELPER'))
    else:
        p=plan(g)
    Path(a.out).write_text(json.dumps(p,indent=1)+'\n')
    if a.image:render(p,a.image)
    if a.apply:emit_apply(p,a.apply)
    print(json.dumps(p['summary']))

if __name__=='__main__':main()

"""Exact-bit FT siting; callers supply a row-legal bulk allocator.

Returns explicit CELL CENTRES per station/bit separately from the schema's
station centroid list, and writes their lower-left sites into the slot. The kit
consumes those exact sites; the old grid-step spiral is not equivalent.
"""
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from collections import deque
import numpy as np
import schema as S
from gen_phys import type_pins


def _extent(points, xy):
    u=points[:,0]+points[:,1];v=points[:,0]-points[:,1]
    a=xy[:,0]+xy[:,1];b=xy[:,0]-xy[:,1]
    return np.maximum.reduce([abs(a-u.min()),abs(a-u.max()),abs(b-v.min()),abs(b-v.max())])


def _visible(source, targets, boxes):
    """True when at least one Manhattan L between each point pair avoids cores.

    Legal station endpoints alone are insufficient: the connecting wire can cut
    across a core whose only free M6/M7 tracks cannot carry the wide bundle.
    Preserve both L orders so narrow channels remain usable without moving a
    core or increasing the reach budget.
    """
    source=np.asarray(source);targets=np.asarray(targets)
    x0,y0=source[...,0],source[...,1];x1,y1=targets[...,0],targets[...,1]
    xl,xh=np.minimum(x0,x1),np.maximum(x0,x1)
    yl,yh=np.minimum(y0,y1),np.maximum(y0,y1)
    xy=np.ones(np.broadcast_shapes(np.shape(x0),np.shape(x1)),dtype=bool)
    yx=xy.copy()
    for a,b,c,d in boxes:
        h0=(b<y0)&(y0<d)&(xl<c)&(xh>a)
        h1=(b<y1)&(y1<d)&(xl<c)&(xh>a)
        v0=(a<x0)&(x0<c)&(yl<d)&(yh>b)
        v1=(a<x1)&(x1<c)&(yl<d)&(yh>b)
        xy &= ~(h0|v1);yx &= ~(v0|h1)
    return xy|yx


def _path(free,first,last,budget,radius,min_stages,boxes=(),first_point=None,last_point=None):
    parent=np.full(len(free),-2,dtype=np.int64)
    start_ok=first+radius<=budget
    if boxes and first_point is not None:start_ok &= _visible(first_point,free,boxes)
    end_ok=last+radius<=budget
    if boxes and last_point is not None:end_ok &= _visible(free,last_point,boxes)
    starts=np.flatnonzero(start_ok)
    queue=deque(map(int,starts));parent[starts]=-1;end=None
    while queue:
        current=queue.popleft()
        if end_ok[current]:
            end=current;break
        distance=np.abs(free-free[current]).sum(axis=1)
        near=np.flatnonzero((distance<=budget-2*radius)&(parent==-2))
        if boxes and len(near):near=near[_visible(free[current],free[near],boxes)]
        near=near[np.argsort(last[near])];parent[near]=current;queue.extend(map(int,near))
    if end is None:raise ValueError('no reach-bounded station-target chain')
    solution=[]
    while end>=0:
        solution.append(int(end));end=int(parent[end])
    solution.reverse()
    # A shorter legal corridor must retain the old statically priced register depth.
    # Insert distinct legal target sites along existing visible edges; never
    # change an endpoint, remove a stage or borrow reach from a different leg.
    while len(solution)+1<min_stages:
        chosen=None
        vertices=[np.asarray(first_point) if first_point is not None else free[solution[0]],
                  *[free[i] for i in solution],
                  np.asarray(last_point) if last_point is not None else free[solution[-1]]]
        edges=sorted(range(len(solution)+1),key=lambda j:-float(np.abs(vertices[j+1]-vertices[j]).sum()))
        for edge in edges:
            left,right=vertices[edge],vertices[edge+1]
            left_dist=np.abs(free-left).sum(axis=1);right_dist=np.abs(free-right).sum(axis=1)
            ok=(start_ok.copy() if edge==0 else left_dist<=budget-2*radius)
            ok &= (end_ok if edge==len(solution) else right_dist<=budget-2*radius)
            ok[solution]=False
            if boxes:
                if edge>0:ok &= _visible(left,free,boxes)
                if edge<len(solution):ok &= _visible(free,right,boxes)
            candidates=np.flatnonzero(ok)
            if not len(candidates):continue
            midpoint=(left+right)/2
            rank=np.abs(free[candidates]-midpoint).sum(axis=1)
            chosen=(edge,int(candidates[np.argmin(rank)]));break
        if chosen is None:raise ValueError('no distinct legal corridor targets preserve existing stage depth')
        solution.insert(*chosen)
    return solution


def l_route_clear(origin, ends, blocked):
    """Either rectilinear L route must stay outside every blocked rectangle."""
    origin=np.asarray(origin);ends=np.asarray(ends)
    ax,ay=origin[...,0],origin[...,1];bx,by=ends[...,0],ends[...,1]
    xlo,xhi=np.minimum(ax,bx),np.maximum(ax,bx)
    ylo,yhi=np.minimum(ay,by),np.maximum(ay,by)
    hv=np.ones(len(ends),bool);vh=hv.copy()
    for x0,y0,x1,y1 in blocked:
        horizontal=(xlo<x1)&(xhi>x0)
        vertical=(ylo<y1)&(yhi>y0)
        hv &= ~((horizontal&(ay>y0)&(ay<y1))|(vertical&(bx>x0)&(bx<x1)))
        vh &= ~((vertical&(ax>x0)&(ax<x1))|(horizontal&(by>y0)&(by<y1)))
    return hv|vh


def _all_routes_clear(points,ends,blocked):
    ok=np.ones(len(ends),bool)
    for p in points:
        ok &= l_route_clear(p,ends,blocked)
    return ok


def _path_strict(free,first,last,budget,radius,min_stages,blocked=(),first_ok=None,last_ok=None):
    parent=np.full(len(free),-2,dtype=np.int64)
    first_ok=np.ones(len(free),bool) if first_ok is None else first_ok
    last_ok=np.ones(len(free),bool) if last_ok is None else last_ok
    starts=np.flatnonzero((first+radius<=budget)&first_ok)
    queue=deque(map(int,starts));parent[starts]=-1;end=None
    while queue:
        current=queue.popleft()
        if last[current]+radius<=budget and last_ok[current]:
            end=current;break
        distance=np.abs(free-free[current]).sum(axis=1)
        near=np.flatnonzero((distance<=budget-2*radius)&(parent==-2))
        if blocked:
            near=near[l_route_clear(free[current],free[near],blocked)]
        near=near[np.argsort(last[near])];parent[near]=current;queue.extend(map(int,near))
    if end is None:raise ValueError('no reach-bounded station-target chain')
    solution=[]
    while end>=0:
        solution.append(int(end));end=int(parent[end])
    solution.reverse()
    # A lane equalisation pass may have deliberately added more pipeline stages
    # than reach alone needs. Preserve those cycles, spreading the existing
    # stages along the legal target chain instead of silently shortening it.
    while len(solution)+1<min_stages:
        pairs=list(zip(solution,solution[1:]))
        if not pairs:
            current=solution[0]
            distance=np.abs(free-free[current]).sum(axis=1)
            ok=(distance<=budget-2*radius)&(last+radius<=budget)&last_ok
            if blocked:ok &= l_route_clear(free[current],free,blocked)
            ids=np.flatnonzero(ok)
            if not len(ids):raise ValueError('cannot spread excess stages in legal channels')
            solution.append(int(ids[np.argmax(distance[ids])]))
            continue
        a,b=max(pairs,key=lambda ab:float(np.abs(free[ab[0]]-free[ab[1]]).sum()))
        mid=(free[a]+free[b])/2
        legal=(np.abs(free-free[a]).sum(axis=1)<=budget-2*radius)&(np.abs(free-free[b]).sum(axis=1)<=budget-2*radius)
        if blocked:
            legal &= l_route_clear(free[a],free,blocked)&l_route_clear(free[b],free,blocked)
        ids=np.flatnonzero(legal)
        if not len(ids):raise ValueError('cannot preserve old station count within legal reach')
        chosen=int(ids[np.argmin(np.abs(free[ids]-mid).sum(axis=1))])
        solution.insert(solution.index(a)+1,chosen)
    return solution




def bit_ordered(a,points,b):
    """Bit-ordered stations (QC-PLAN 10-25, PROTO sle_su_l0): RowAllocator returns a stage's sites nearest-first, so
    bit k landed on an arbitrary cell of the cluster and the bundle's legs crossed each other (local GRT overflow at
    every station cluster). Re-assign each stage's sites to bits by rank along the axis across the hop's travel
    direction, matched to the previous stage's bit order, so a bus stays a parallel ribbon (industry bit-sliced
    placement). Only the bit -> site map changes; the site set, stage count and endpoints stay."""
    out=[];prev=np.asarray(a,float)
    for k,pts in enumerate(points):
        pts=np.asarray(pts,float);nxt=np.asarray(points[k+1] if k+1<len(points) else b,float)
        d=np.abs(nxt.mean(axis=0)-prev.mean(axis=0)) if k+1<len(points) else np.abs(pts.mean(axis=0)-prev.mean(axis=0))
        cross=0 if d[1]>=d[0] else 1             # vertical travel -> order across x; horizontal -> across y
        rp=np.lexsort((prev[:,1-cross],prev[:,cross]));rs=np.lexsort((pts[:,1-cross],pts[:,cross]))
        new=np.empty_like(pts);new[rp]=pts[rs]
        out.append(new);prev=new
    return out


# PATH-QC-PLAN-D3 10-25 (G2 slw_su_l1 STRUCTURAL ov 2191, slw_su_c ov 1): a slot whose plan layers are M7 ONLY with
# opposite N/S faces is a straight transit the plan routes OVER the hard cores on M7 (gen_plan _lay_free_spans: the SU
# face has no macro-free span left for it; core OBS stops below M7).  Strict mode demanded a core-free L for every leg,
# so its stations could only sit in the 17-um W edge strip (x 4-15), with every leg running down that strip (M3 hot).
# Its stations go in the macro-free GAP ROWS under the M7 ribbon instead: targets are restricted to the ribbon's x band
# (window span, M7_BAND_PAD), legs are straight V within that band over the cores (no core-free L demanded), and
# station cells stay outside every core + halo (allocator blocked boxes, unchanged).  All other slots stay strict.
M7_BAND_PAD=0.0    # targets under the ribbon itself (window span)
M7_PLAN_RADIUS=12.0   # planning radius of a 517-cell station cluster (~10 um measured); actual hops re-verified


def m7_gap_rows(targets,boxes,blo,bhi):
    """targets in the ribbon band whose y lies in a GAP ROW: outside the y span of every core (+halo) under the band."""
    ok=(targets[:,0]>=blo)&(targets[:,0]<=bhi)
    for x0,y0,x1,y1 in boxes:
        if x1>blo and x0<bhi:
            ok &= ~((targets[:,1]>y0)&(targets[:,1]<y1))
    return targets[ok]


def m7_over_core(slot):
    return list(slot.get('layers') or [])==['M7'] and {slot.get('in_face'),slot.get('out_face')}=={'N','S'}


def m7_band(a,b,pad=M7_BAND_PAD):
    return (min(a[:,0].min(),b[:,0].min())-pad,max(a[:,0].max(),b[:,0].max())+pad)


def ribbon_allocate(al,target_y,px,boxes,max_rows=200):
    """PATH-QC-PLAN-D3 (G2 slw_su_l1 ov 8,795 M6-H with blob clusters): an M7 over-core station is a RIBBON under its
    bus: bit k (by pin x) takes the k-th free legal site in (column, row) order of a row band at target_y across the
    bus x span, so every bit's site sits within ~a column pitch of its own pin x and its legs are straight V on M7
    (the blob allocator shifted bits up to ~50 um in x, and GRT put those H jogs over the cores: M2/M4/M6 obstructed).
    The band grows row by row (alternately up / down) inside the gap row (no row may enter a core + halo box)."""
    px=np.asarray(px,float);n=len(px);order=np.argsort(px,kind='stable')
    lo=max(al.ix0,math.floor((px.min()-al.ox-al.cw/2)/al.cp));hi=min(al.ix1,math.ceil((px.max()-al.ox-al.cw/2)/al.cp))
    ix=np.arange(lo,hi+1);xs=al.ox+ix*al.cp+al.cw/2
    r0=min(max(al.iy0,int(round((target_y-al.oy-al.ch/2)/al.rp))),al.iy1)
    rows=[];step=0;picked=[]
    while len(picked)<n:
        cand=[r0+step] if step==0 else [r0+step,r0-step]
        step+=1
        if step>max_rows:raise ValueError(f'ribbon: only {len(picked)} sites for {n} at y {target_y:.2f}')
        for iy in cand:
            if not al.iy0<=iy<=al.iy1:continue
            y=al.oy+iy*al.rp+al.ch/2
            ok=np.ones(len(ix),bool)
            for a,b,c,d in boxes:
                if b-1e-8<y+al.ch/2 and y-al.ch/2<d+1e-8:ok &= ~((xs-al.cw/2<c)&(xs+al.cw/2>a))
            ids=(iy-al.iy0)*al.nx+(ix-al.ix0)
            if al.used:ok &= np.fromiter((int(k) not in al.used for k in ids),bool,count=len(ids))
            rows.append(iy);picked += [(int(i),int(iy)) for i,good in zip(ix,ok) if good]
    picked.sort()                                                 # (column, row) order = x-monotone ribbon
    # keep the n sites nearest the band centre row while preserving column-major order
    rank=sorted(range(len(picked)),key=lambda k:(abs(picked[k][1]-r0),picked[k]))[:n]
    chosen=sorted(picked[k] for k in rank)
    sites=np.empty((n,2))
    for k,(i,iy) in zip(order,chosen):
        sites[k]=(al.ox+i*al.cp+al.cw/2,al.oy+iy*al.rp+al.ch/2)
    al.used.update((iy-al.iy0)*al.nx+i-al.ix0 for i,iy in chosen)
    return sites,dict(count=n,ribbon_rows=len(set(r for _,r in chosen)),span_um=[float(np.ptp(sites[:,0])+al.cw),
                                                                               float(np.ptp(sites[:,1])+al.ch)])


def _place_strict(raw,allocator_cls,types=None,reach_um=405.,margin=.98,max_radius_um=40.,avoid_core_routes=True,bit_order=False):
    """Strict actual-bit mode (QC 906dca298): EVERY bit leg keeps an L route outside all core halos,
    row-allocation corner cuts are backtracked, and a short direct leg keeps station0 only."""
    model=S.Plan(raw);selected=set(types) if types else set(model.types);ledger=[];explicit={}
    for tn,ty in model.types.items():
        if tn not in selected or not ty.get('ft_slots'):continue
        boxes=list(S.placed_macro_boxes(ty, halo=8.64).values())
        if not boxes:continue
        w,h=ty['outline_um'];pins={(b,i):(x,y) for b,i,_,x,y,_ in type_pins(model,tn)}

        allocator=allocator_cls((4.32,4.32,w-4.32,h-4.32),blocked=boxes,
                                cell_size=(1.404,.27),column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
        xs=np.arange(8.64,w-4.32,8.64);ys=np.arange(8.64,h-4.32,8.64)
        x,y=np.meshgrid(xs,ys);grid=np.column_stack((x.ravel(),y.ravel()));ok=np.ones(len(grid),bool)
        for a,b,c,d in boxes:ok &= ~((grid[:,0]>a)&(grid[:,0]<c)&(grid[:,1]>b)&(grid[:,1]<d))
        targets=grid[ok];explicit[tn]=[]
        for slot in sorted(ty['ft_slots'],key=lambda s:-s['width']):
            name=slot['name'];width=slot['width']+1
            a=np.array([pins[(name+'_i',i)] for i in range(width)])
            b=np.array([pins[(name+'_o',i)] for i in range(width)])
            budget=reach_um*margin-2.0 # reserve actual D/Q pin offsets from cell centres
            direct=float(np.abs(b-a).sum(axis=1).max())
            over=avoid_core_routes and m7_over_core(slot)
            rboxes=() if over or not avoid_core_routes else boxes   # leg-route constraint
            if over:
                blo,bhi=m7_band(a,b);tset=m7_gap_rows(targets,boxes,blo,bhi)
            else:
                tset=targets
            if slot['stations']==1 and direct<=budget and (not rboxes or l_route_clear(a,b,rboxes).all()):
                # Station0 is already the input-face register. Do not add a
                # gratuitous internal pipeline stage to a short direct leg.
                for key in ('regs_um','bit_sites_um','bit_site_cell_um'):
                    slot.pop(key,None)
                ledger.append(dict(type=tn,slot=name,stations=[1,1],worst_paired_bit_um=round(direct,4),
                                   budget_um=budget,cell_size_um=[1.404,.27],max_radius_um=max_radius_um))
                continue
            blocked_targets=set();base_used=set(allocator.used);done=False
            first_ok=_all_routes_clear(a,tset,rboxes) if rboxes else None
            last_ok=_all_routes_clear(b,tset,rboxes) if rboxes else None
            for attempt in range(100):
                allocator.used=set(base_used)
                free=tset[[i not in blocked_targets for i in range(len(tset))]]
                ids=np.array([i for i in range(len(tset)) if i not in blocked_targets])
                path=_path_strict(free,_extent(a,free),_extent(b,free),budget,
                           M7_PLAN_RADIUS if over else max_radius_um,slot['stations'],
                           blocked=rboxes,
                           first_ok=first_ok[ids] if first_ok is not None else None,
                           last_ok=last_ok[ids] if last_ok is not None else None)
                points=[];stats=[]
                for index in path:
                    try:
                        if over:p,st=ribbon_allocate(allocator,free[index][1],(a[:,0]+b[:,0])/2,boxes)
                        else:p,st=allocator.allocate(free[index],width,max_radius_um=max_radius_um)
                    except ValueError:blocked_targets.add(int(ids[index]));break
                    points.append(p);stats.append(st)
                else:
                    # A legal target-centre route can still cut a corner after
                    # row allocation spreads the cells. Backtrack that target,
                    # not the immutable failed verdict or the route constraint.
                    chain=[a,*points,b]
                    if over:
                        # planned with the smaller cluster radius: back off the target of the worst over-reach leg
                        hl=[float(np.abs(q-p).sum(axis=1).max()) for p,q in zip(chain,chain[1:])]
                        if max(hl)>budget+1e-6:
                            blocked_targets.add(int(ids[path[min(int(np.argmax(hl)),len(path)-1)]]))
                            continue
                    if rboxes:
                        bad=[j for j,(p,q) in enumerate(zip(chain,chain[1:]))
                             if not l_route_clear(p,q,rboxes).all()]
                        if bad:
                            blocked_targets.add(int(ids[path[min(bad[0],len(path)-1)]]))
                            continue
                    done=True;break
            if not done:raise ValueError(f'{tn}/{name}: no row-legal allocation after100 target alternatives')
            ordered=False
            if bit_order and points and not over:
                cand=bit_ordered(a,points,b);cc=[a,*cand,b]
                ch=[float(np.abs(q-p).sum(axis=1).max()) for p,q in zip(cc,cc[1:])]
                if max(ch)<=budget+1e-6 and (not rboxes or all(l_route_clear(p,q,rboxes).all() for p,q in zip(cc,cc[1:]))):
                    points=cand;ordered=True
            chain=[a,*points,b];hops=[float(np.abs(q-p).sum(axis=1).max()) for p,q in zip(chain,chain[1:])]
            if max(hops)>budget+1e-6:raise ValueError(f'{tn}/{name}: actual paired-bit hop {max(hops)} >{budget}')
            if rboxes and any(not l_route_clear(p,q,rboxes).all() for p,q in zip(chain,chain[1:])):
                raise ValueError(f'{tn}/{name}: allocated bit leg leaves the macro-free channels')
            if over and any(((p[:,0]<blo-max_radius_um)|(p[:,0]>bhi+max_radius_um)).any() for p in points):
                raise ValueError(f'{tn}/{name}: M7 over-core station left the ribbon band')
            old=slot['stations'];slot['stations']=len(points)+1
            slot['regs_um']=[a.mean(axis=0).round(4).tolist()]+[free[index].round(4).tolist() for index in path]
            slot['bit_site_cell_um']=[1.404,.27]
            slot['bit_sites_um']=[(p-np.array([.702,.135])).round(6).tolist() for p in points]
            for stage,p in enumerate(points,1):
                explicit[tn].append(dict(slot=name,stage=stage,sites_um=p.round(5).tolist(),stats=stats[stage-1]))
            ledger.append(dict(type=tn,slot=name,stations=[old,slot['stations']],worst_paired_bit_um=round(max(hops),4),
                               budget_um=budget,cell_size_um=[1.404,.27],max_radius_um=max_radius_um,
                               core_free_routes=bool(rboxes),m7_over_core_band=([round(blo,4),round(bhi,4)] if over else None),
                               bit_ordered=ordered))
    return ledger,explicit




def place(raw,allocator_cls,types=None,reach_um=405.,margin=.98,max_radius_um=40.,avoid_core_routes=False,bit_order=False):
    """Default (S81 adopt178 exact sites): centroid-visible core-free corridors.
    avoid_core_routes=True selects the strict per-bit mode (_place_strict) used by QC bit_stations."""
    if avoid_core_routes:
        return _place_strict(raw,allocator_cls,types=types,reach_um=reach_um,margin=margin,max_radius_um=max_radius_um,
                             bit_order=bit_order)
    model=S.Plan(raw);selected=set(types) if types else set(model.types);ledger=[];explicit={}
    for tn,ty in model.types.items():
        if tn not in selected or not ty.get('ft_slots'):continue
        boxes=list(S.placed_macro_boxes(ty, halo=8.64).values())
        if not boxes:continue
        w,h=ty['outline_um'];pins={(b,i):(x,y) for b,i,_,x,y,_ in type_pins(model,tn)}

        allocator=allocator_cls((4.32,4.32,w-4.32,h-4.32),blocked=boxes,
                                cell_size=(1.404,.27),column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
        xs=np.arange(8.64,w-4.32,8.64);ys=np.arange(8.64,h-4.32,8.64)
        x,y=np.meshgrid(xs,ys);grid=np.column_stack((x.ravel(),y.ravel()));ok=np.ones(len(grid),bool)
        for a,b,c,d in boxes:ok &= ~((grid[:,0]>a)&(grid[:,0]<c)&(grid[:,1]>b)&(grid[:,1]<d))
        targets=grid[ok];explicit[tn]=[]
        for slot in sorted(ty['ft_slots'],key=lambda s:-s['width']):
            name=slot['name'];width=slot['width']+1
            a=np.array([pins[(name+'_i',i)] for i in range(width)])
            b=np.array([pins[(name+'_o',i)] for i in range(width)])
            budget=reach_um*margin-2.0 # reserve actual D/Q pin offsets from cell centres
            blocked_targets=set();base_used=set(allocator.used);done=False
            for attempt in range(100):
                allocator.used=set(base_used)
                free=targets[[i not in blocked_targets for i in range(len(targets))]]
                ids=np.array([i for i in range(len(targets)) if i not in blocked_targets])
                path=_path(free,_extent(a,free),_extent(b,free),budget,max_radius_um,slot['stations'],
                           boxes=boxes,first_point=a.mean(axis=0),last_point=b.mean(axis=0))
                points=[];stats=[]
                for index in path:
                    try:p,st=allocator.allocate(free[index],width,max_radius_um=max_radius_um)
                    except ValueError:blocked_targets.add(int(ids[index]));break
                    points.append(p);stats.append(st)
                else:
                    done=True;break
            if not done:raise ValueError(f'{tn}/{name}: no row-legal allocation after100 target alternatives')
            if bit_order and points:
                cand=bit_ordered(a,points,b);cc=[a,*cand,b]
                if max(float(np.abs(q-p).sum(axis=1).max()) for p,q in zip(cc,cc[1:]))<=budget+1e-6:points=cand
            chain=[a,*points,b];hops=[float(np.abs(q-p).sum(axis=1).max()) for p,q in zip(chain,chain[1:])]
            if max(hops)>budget+1e-6:raise ValueError(f'{tn}/{name}: actual paired-bit hop {max(hops)} >{budget}')
            old=slot['stations'];slot['stations']=len(points)+1
            slot['regs_um']=[a.mean(axis=0).round(4).tolist()]+[free[index].round(4).tolist() for index in path]
            slot['bit_site_cell_um']=[1.404,.27]
            slot['bit_sites_um']=[(p-np.array([.702,.135])).round(6).tolist() for p in points]
            for stage,p in enumerate(points,1):
                explicit[tn].append(dict(slot=name,stage=stage,sites_um=p.round(5).tolist(),stats=stats[stage-1]))
            ledger.append(dict(type=tn,slot=name,stations=[old,slot['stations']],worst_paired_bit_um=round(max(hops),4),
                               budget_um=budget,cell_size_um=[1.404,.27],max_radius_um=max_radius_um))
    return ledger,explicit



def reuse(raw, previous, types=None):
    """Reuse exact sites only when the complete type and slot geometry matches.

    Committed generated plans are a placement seed, like the core placement
    candidates. A changed outline/core/pin/clock/reset/internal-station contract
    invalidates the seed. Old depths may be retained but never reduced below
    the newly generated minimum. Unmatched types must run the allocator.
    """
    import copy
    selected=set(types) if types is not None else set(raw['partition_types'])
    policy=lambda p: (tuple(p.get('die',{}).get(k) for k in ('period_ps','reach_um','grid_um')),
                      p.get('budgets',{}).get('ft_station_max_um'))
    if policy(raw)!=policy(previous):return []
    reused=[]
    derived={'stations','regs_um','bit_sites_um','bit_site_cell_um'}
    for name,ty in raw['partition_types'].items():
        old=previous.get('partition_types',{}).get(name)
        if name not in selected or not old or not ty.get('ft_slots'):continue
        if {k:v for k,v in ty.items() if k!='ft_slots'}!={k:v for k,v in old.items() if k!='ft_slots'}:continue
        slots=ty['ft_slots'];prior=old.get('ft_slots',[])
        if len(slots)!=len(prior):continue
        valid=True
        for slot,seed in zip(slots,prior):
            if {k:v for k,v in slot.items() if k not in derived}!={k:v for k,v in seed.items() if k not in derived}:
                valid=False;break
            sites=seed.get('bit_sites_um');cell=seed.get('bit_site_cell_um')
            if sites is None or not cell or seed['stations']<slot['stations'] or len(sites)!=seed['stations']-1:
                valid=False;break
            if any(len(stage)!=seed['width']+1 for stage in sites):valid=False;break
        if not valid:continue
        for slot,seed in zip(slots,prior):
            for key in derived:slot[key]=copy.deepcopy(seed[key])
        reused.append(name)
    return reused


def main():
    import argparse
    import json
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools.die_trial.legal_sites import RowAllocator
    ap=argparse.ArgumentParser(description='Refresh exact per-bit FT sites in an existing plan, preserving all other fields.')
    ap.add_argument('plan');ap.add_argument('--out',required=True);ap.add_argument('--ledger',required=True)
    ap.add_argument('--types',help='comma-separated type names; default all frame col_ types')
    ap.add_argument('--all-core-types',action='store_true',help='select every type with hard cores and FT slots')
    ap.add_argument('--reuse',help='previous generated plan with exact sites; reuse only identical complete type contracts')
    a=ap.parse_args();raw=json.loads(Path(a.plan).read_text())
    if a.types and a.all_core_types:ap.error('--types and --all-core-types are mutually exclusive')
    selected=([n for n,t in raw['partition_types'].items() if (t.get('hard_cores') or any(c.get('lef') for c in t.get('contents', []))) and t.get('ft_slots')]
              if a.all_core_types else a.types.split(',') if a.types else [n for n in raw['partition_types'] if n.startswith('col_')])
    reused=reuse(raw,json.loads(Path(a.reuse).read_text()),types=selected) if a.reuse else []
    ledger,_=place(raw,RowAllocator,types=[n for n in selected if n not in reused])
    Path(a.out).write_text(json.dumps(raw,indent=0)+'\n')
    Path(a.ledger).write_text(json.dumps(ledger,indent=1)+'\n')
    worst=max((v['worst_paired_bit_um'] for v in ledger),default=0.)
    print(f'Reused {len(reused)} unchanged exact types; placed {len(ledger)} FT slots; max new actual paired-bit hop {worst:.2f} um')

if __name__=='__main__':
    main()

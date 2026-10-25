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


def place(raw,allocator_cls,types=None,reach_um=405.,margin=.98,max_radius_um=40.):
    model=S.Plan(raw);selected=set(types) if types else set(model.types);ledger=[];explicit={}
    for tn,ty in model.types.items():
        if tn not in selected or not ty.get('hard_cores') or not ty.get('ft_slots'):continue
        w,h=ty['outline_um'];pins={(b,i):(x,y) for b,i,_,x,y,_ in type_pins(model,tn)}
        boxes=[]
        for c in ty['hard_cores']:
            x,y=c['origin_um'];cw,ch=c['outline_um'];dx,dy=c.get('track_offset_um',[0,0]);halo=8.64
            boxes.append((x+dx-halo,y+dy-halo,x+dx+cw+halo,y+dy+ch+halo))
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
    selected=([n for n,t in raw['partition_types'].items() if t.get('hard_cores') and t.get('ft_slots')]
              if a.all_core_types else a.types.split(',') if a.types else [n for n in raw['partition_types'] if n.startswith('col_')])
    reused=reuse(raw,json.loads(Path(a.reuse).read_text()),types=selected) if a.reuse else []
    ledger,_=place(raw,RowAllocator,types=[n for n in selected if n not in reused])
    Path(a.out).write_text(json.dumps(raw,indent=0)+'\n')
    Path(a.ledger).write_text(json.dumps(ledger,indent=1)+'\n')
    worst=max((v['worst_paired_bit_um'] for v in ledger),default=0.)
    print(f'Reused {len(reused)} unchanged exact types; placed {len(ledger)} FT slots; max new actual paired-bit hop {worst:.2f} um')

if __name__=='__main__':
    main()

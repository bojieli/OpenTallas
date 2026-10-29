"""Private fallback: per-bit registered street paths with unchanged hop gates.

Nearest-point projection can switch sides of a wide macro, so adding stages to
that same projected ribbon never creates a connected chain. This constructor
uses the existing hub_repack street raster/path planner for each actual bit,
then legalizes distinct FF cells. Equal stage count is retained/padded across
all bits. A successful result is a constructive witness, never a routed claim.
"""
import math
import numpy as np
import hub_repack as H


def construct(module,slot,a,b,fin,fout,w,h,boxes,alloc,budget,**kwargs):
    if getattr(module,'_street_phy_hold',False):
        raise ValueError(slot['name']+': street fallback held on physical PHY domains')
    base=set(alloc.used);R=H.Raster(w,h,list(boxes),halo=0)
    # The street graph may use a partition boundary as a proposal. Actual
    # FF footprints are always legalized inside the original RowAllocator
    # bounds; its 40um displacement is included in the unchanged hop budget.
    cache={};keys=[];margin=40.;planning=budget-2*margin
    if planning<=0:raise ValueError('no physical hop after legalization allowance')
    def key(pa,pb):return tuple(round(float(v)/H.G) for v in (*pa,*pb))
    def path(pa,pb,n):
        result=H.route_station(R,pa,pb,n,planning)
        if result is None:
            aa,bb=H.escape(R,pa),H.escape(R,pb)
            if not R.free(*aa) or not R.free(*bb):return None
            poly=H.astar(R,aa,bb,step=1)
            if poly is None:return None
            la=abs(pa[0]-aa[0])+abs(pa[1]-aa[1]);lb=abs(pb[0]-bb[0])+abs(pb[1]-bb[1])
            regs,nmin=H.place_regs(R,poly,la,lb,n,planning)
            if regs is None:return None
            result=dict(regs=regs,n_min=nmin,length_um=sum(abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(poly,poly[1:]))+la+lb)
        return result
    count=max(0,int(slot['stations'])-1)
    for bit,(pa,pb) in enumerate(zip(a,b)):
        k=key(pa,pb);keys.append(k)
        if k in cache:continue
        result=path(pa,pb,count)
        if result is None:raise ValueError(f'{slot["name"]}: no per-bit street chain at bit {bit}')
        cache[k]=(pa,pb,result);count=max(count,len(result['regs']))
    # Every bit retains exactly the same number of FF stages; a longer bit
    # path raises the whole bundle depth and is reported to the model.
    for k,(pa,pb,result) in list(cache.items()):
        if len(result['regs'])<count:
            result=path(pa,pb,count)
            if result is None:raise ValueError(f'{slot["name"]}: cannot pad per-bit street chain')
        regs=list(result['regs'])
        if not regs and count:
            q=H.escape(R,pa)
            if not R.free(*q):raise ValueError(f'{slot["name"]}: no free padded target')
            regs=[q]
        while len(regs)<count:regs.append(regs[-1])
        result['regs']=regs;cache[k]=(pa,pb,result)
    targets=np.array([cache[k][2]['regs'] for k in keys],float) if count else np.empty((len(a),0,2))
    actual=[]
    try:
        for stage in range(count):
            points=np.zeros((len(a),2));order=np.lexsort((targets[:,stage,0],targets[:,stage,1]))
            for bit in order:
                target=targets[bit,stage];previous=a[bit] if stage==0 else actual[-1][bit];following=b[bit] if stage==count-1 else targets[bit,stage+1]
                candidates=[target]
                # Legal alternate free lattice targets around the planned
                # bank, constrained by both adjacent actual physical hops.
                for delta in (H.G,2*H.G,4*H.G,8*H.G):
                    candidates.extend(target+np.array([dx,dy]) for dx,dy in ((delta,0),(-delta,0),(0,delta),(0,-delta)))
                chosen=None
                for q in candidates:
                    if np.abs(q-previous).sum()+margin>budget+1e-6:continue
                    if np.abs(q-following).sum()+margin>budget+1e-6:continue
                    keep=set(alloc.used)
                    try:xy,_=alloc.allocate(q,1,max_radius_um=margin)
                    except ValueError:continue
                    p=xy[0]
                    if np.abs(p-previous).sum()>budget+1e-6 or np.abs(p-following).sum()+margin>budget+1e-6:
                        alloc.used=keep;continue
                    chosen=p;break
                if chosen is None:raise ValueError(f'{slot["name"]}: per-bit street legalization failed stage {stage+1} bit {bit}')
                points[bit]=chosen
            actual.append(points)
        chain=[a,*actual,b];hops=[float(np.abs(q-p).sum(axis=1).max()) for p,q in zip(chain,chain[1:])]
        if max(hops)>budget+1e-6:raise ValueError(f'{slot["name"]}: actual street hop {max(hops)} exceeds {budget}')
    except Exception:alloc.used=base;raise
    slot['stations']=count+1;cents=[q.mean(axis=0) for q in actual];pathline=[a.mean(axis=0),*cents,b.mean(axis=0)]
    return actual,cents,pathline,dict(method='per_bit_street_raster',len_um=round(max((v[2]['length_um'] for v in cache.values()),default=0),3),stations=count+1,hops_um=[round(v,4) for v in hops],unique_bit_paths=len(cache),planning_hop_um=planning,row_legalization_radius_um=margin)


def install(module,direct=False):
    original=module.place_slot
    def fallback(slot,a,b,fin,fout,w,h,boxes,alloc,budget,**kwargs):
        base=set(alloc.used)
        if not direct:
            try:return original(slot,a,b,fin,fout,w,h,boxes,alloc,budget,**kwargs)
            except ValueError:alloc.used=set(base)
        return construct(module,slot,a,b,fin,fout,w,h,boxes,alloc,budget,**kwargs)
    module.place_slot=fallback

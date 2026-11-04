"""Opt-in vector evaluation of the existing per-bit FT greedy move.

Candidate order and fallback reach tests are unchanged. All candidate geometry
is immutable; dynamic row allocation remains outside this helper.
"""
import numpy as np
import ft_sites_unblock as F


def points_at(route, position):
    remaining=np.asarray(position,float).copy()
    out=np.tile(np.asarray(route[-1],float),(len(remaining),1))
    active=np.ones(len(remaining),bool)
    for p,q in zip(route,route[1:]):
        length=abs(p[0]-q[0])+abs(p[1]-q[1])
        here=active & (remaining<=length+F.C.EPS)
        fraction=np.zeros(np.count_nonzero(here)) if length==0 else remaining[here]/length
        out[here,0]=p[0]+fraction*(q[0]-p[0]);out[here,1]=p[1]+fraction*(q[1]-p[1])
        active[here]=False;remaining[active]-=length
    return out


def move(pts,bits,k,grow,free,budget,tn,name):
    moved=0
    sorted_x=(len(free)<2 or np.all(free[1:,0]>=free[:-1,0]))
    for bit in bits:
        ia,ib,route,length,ps=pts[bit]
        for stage in range(len(ps)):
            if not F.inside(ps[stage],grow):continue
            prev=ia if stage==0 else ps[stage-1]
            nxt=ib if stage==len(ps)-1 else ps[stage+1]
            dt=np.arange(-length/(2*k),length/(2*k)+1e-9,1.08)
            dt=dt[np.argsort(np.abs(dt),kind='stable')]
            candidates=points_at(route,np.clip(length*(stage+1)/k+dt,0,length))
            ok=np.ones(len(candidates),bool)
            for a,b,c,d in grow:
                ok &= ~((candidates[:,0]>a)&(candidates[:,0]<c)&(candidates[:,1]>b)&(candidates[:,1]<d))
            ok &= (np.abs(candidates-prev).sum(1)<=budget)&(np.abs(candidates-nxt).sum(1)<=budget)
            indices=np.flatnonzero(ok)
            if len(indices):best=candidates[indices[0]]
            else:
                # Preserve original free-array order (and therefore argmin ties).
                local=free
                if sorted_x:
                    lo=max(prev[0]-budget,nxt[0]-budget);hi=min(prev[0]+budget,nxt[0]+budget)
                    first,last=np.searchsorted(free[:,0],[lo,hi],side='left')
                    last=np.searchsorted(free[:,0],hi,side='right');local=free[first:last]
                low=max(prev[1]-budget,nxt[1]-budget);high=min(prev[1]+budget,nxt[1]+budget)
                local=local[(local[:,1]>=low)&(local[:,1]<=high)]
                ok=(np.abs(local-prev).sum(1)<=budget)&(np.abs(local-nxt).sum(1)<=budget)
                if not ok.any():
                    pts[bit]=(ia,ib,route,length,F.layered(ia,ib,ps,k,grow,budget,tn,name,bit))
                    moved+=len(ps);break
                local=local[ok];best=local[np.argmin(np.abs(local-ps[stage]).sum(1))]
            ps[stage]=(float(best[0]),float(best[1]));moved+=1
    return moved

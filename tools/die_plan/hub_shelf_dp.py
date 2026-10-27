"""Opt-in complete shelf-count feasibility search after the historical <=5-shelf heuristic fails.
No rotation, outline growth, missing cores or relaxed streets. Each shelf remains a contiguous interval of the
original y ordering; columns/stacking and physical realization use hub_repack's existing exact primitives.
Dynamic programming minimizes total shelf height for each shelf count, avoiding n-choose-k enumeration.
This is a candidate geometry search, not a cut/reach/clock/route verdict.
"""
import math
import hub_repack as HR


def pack_hub_dp(W,H,cores,lanes=(51.84,43.2,34.56,25.92,17.28),shelves=None,conns=None,reach=360.0):
    if conns:
        raise ValueError('DP fallback does not replace connection-scored packing')
    C=sorted(cores,key=lambda c:(c['ocy'],c['ocx']));n=len(C)
    if not n:raise ValueError('empty core set')
    for lane in lanes:
        interval={}
        for a in range(n):
            height=0
            for b in range(a+1,n+1):
                height=max(height,HR.ce(C[b-1]['h']))
                if height+2*lane>H+1e-6:continue
                packed=HR._pack_shelf(C[a:b],height,lane)
                if packed[1]<=W+1e-6:interval[a,b]=(height,packed)
        prev={0:(0.0,())}
        allowed=set(shelves) if shelves is not None else set(range(1,n+1))
        for count in range(1,min(n,max(allowed,default=0))+1):
            cur={}
            for end in range(count,n+1):
                best=None
                for start in range(count-1,end):
                    if start not in prev or (start,end) not in interval:continue
                    ph,pcuts=prev[start];h,_=interval[start,end]
                    candidate=(ph+h,pcuts+(end,))
                    if best is None or candidate<best:best=candidate
                if best is not None:cur[end]=best
            if count in allowed and n in cur and cur[n][0]+(count+1)*lane<=H+1e-6:
                total,ends=cur[n];bounds=(0,)+ends
                hs=[interval[a,b][0] for a,b in zip(bounds,bounds[1:])]
                packed=[interval[a,b][1] for a,b in zip(bounds,bounds[1:])]
                place,streets=HR._realise(W,H,hs,packed,lane)
                disp=sum(abs(place[c['inst']][0]+c['w']/2-c['ocx'])+abs(place[c['inst']][1]+c['h']/2-c['ocy']) for c in C)
                return place,dict(lane_um=lane,shelves=count,shelf_heights_um=[HR.r3(x) for x in hs],
                    shelf_cuts_old_y_order=list(ends[:-1]),est_added_regs_initial=0.0,est_added_regs=0.0,
                    local_search_moves=0,displacement_um_total=HR.r3(disp),displacement_um_mean=HR.r3(disp/n),
                    streets=streets,packing_search='DP minimum shelf height; cut/reach/clock/route gates still required')
            prev=cur
            if not prev:break
    raise ValueError('hub cores do not fit any shelf count at the fixed outline and street widths')

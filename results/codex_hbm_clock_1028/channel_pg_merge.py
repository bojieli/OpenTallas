"""HBM prototype: embed inter-street merges on physical horizontal channels.

The adapter changes no plan pins/clock contract. Native physical_leg is still
responsible for every emitted stage, reach, polarity and body/site check. All
routing costs are computed on the same preselected corridor polyline.
"""
import math

def install(D, P, part='NW_sm3'):
    ox,oy=P.parts[part]['origin_um']; typ=P.types[P.parts[part]['type']]
    cores=typ['hard_cores']; ys=sorted({float(c['origin_um'][1]) for c in cores} | {float(c['origin_um'][1])+float(c['outline_um'][1]) for c in cores})
    # The two abutting row halves are one wall; only real gaps >2 halos
    # are horizontal channels. The top edge is outside the last wall.
    intervals=[]
    for lo,hi in zip(ys,ys[1:]):
        if not any(c['origin_um'][1] < (lo+hi)/2 < c['origin_um'][1]+c['outline_um'][1] for c in cores):
            intervals.append((lo,hi))
    channels=[round(round((oy+(lo+hi)/2)/.54)*.54,6) for lo,hi in intervals if hi-lo>6]
    channels.append(round(math.ceil((oy+max(ys)+3.24)/.54)*.54,6))
    channels=[round(1.08+2.16*round((v-1.08)/2.16),6)for v in channels]
    W=typ['outline_um'][0]; original_leg=D.physical_leg
    stats={'part':part,'channel_rows_um':channels,'merges':[]}
    def physical(site,a,b,rep_um,points=None):
        if points is not None:return original_leg(site,a,b,rep_um,[tuple(a)]+[site.nearest(q)for q in points[1:-1]]+[tuple(b)])
        a,b=tuple(a),tuple(b)
        key=(a,b,rep_um)
        cache=getattr(site,'_channel_leg_cache',None)
        if cache is None:cache=site._channel_leg_cache={}
        if key in cache:return cache[key]
        poly=D.legal_detour(site,a,b)
        if poly is None:raise ValueError('no corridor path between clock nodes')
        L=D.polyline_points(poly,[])[1]
        if L<1e-8:return original_leg(site,a,b,rep_um,[a,a,b])
        n=max(2,int(math.ceil(L/rep_um)));n+=n%2
        raw,_=D.polyline_points(poly,[i/n for i in range(1,n)])
        points=[a]+[D.round_legal(site,site.nearest(q))for q in raw]+[b]
        out=original_leg(site,a,b,rep_um,points)
        cache[key]=out;return out
    D.physical_leg=physical
    def merge(site,c1,s1,c2,s2,rep_um,radius_um=800.,step=1.08,extra_ps_um=.03):
        # All wide cross-column merges are constructed on channel rows;
        # same-street merges may run vertically inside that street.
        md=D._man; horiz=abs(c1[0]-c2[0])>150.
        pool=set(); xs=sorted({c1[0],c2[0],(c1[0]+c2[0])/2})
        def legal(q):
            q=site.nearest(q)
            if site.legal(q):pool.add(q);return q
        for y in channels:
            lo=max(ox+2.16,min(c1[0],c2[0])-180);hi=min(ox+W-2.16,max(c1[0],c2[0])+180)
            for j in range(17):legal((lo+(hi-lo)*j/16,y))
        if not horiz:
            for x in xs:
                lo=max(oy+2.16,min(c1[1],c2[1])-180);hi=min(oy+max(ys)+3.24,max(c1[1],c2[1])+180)
                for j in range(25):legal((x,lo+(hi-lo)*j/24))
            for q in (c1,c2):legal(q)
        def measure(q):
            try:
                la=physical(site,q,c1,rep_um);lb=physical(site,q,c2,rep_um)
                imbalance=abs(la['delay_ps']+s1-lb['delay_ps']-s2)
                wire=la['wire_um']+lb['wire_um'];extra=wire-md(c1,c2)
                return imbalance+extra_ps_um*max(0,extra),wire,imbalance
            except ValueError:return (math.inf,math.inf,math.inf)
        if not pool:raise ValueError('no legal channel merge candidate')
        best=min(pool,key=measure)
        # Refine along the selected channel/street; no illegal in-array
        # horizontal merge can enter during refinement.
        for delta in (45.,10.8,2.16,.54):
            candidates={best}
            axes=(0,) if horiz or best[1] in channels else (1,)
            for ax in axes:
                for sign in (-2,-1,1,2):
                    q=list(best);q[ax]+=sign*delta;v=legal(q)
                    if v is not None:candidates.add(v)
            best=min(candidates,key=measure)
        cost,wire,imb=measure(best)
        if not math.isfinite(cost):raise ValueError('no reachable channel merge')
        stats['merges'].append(dict(children=[c1,c2],q=best,cross_street=horiz,wire_um=wire,imbalance_ps=imb))
        return best,imb,wire-md(c1,c2)
    D.merge_point_delay=merge
    return stats

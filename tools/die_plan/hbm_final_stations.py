"""Opt-in final-pin station regeneration after all hub pin spreading and W/E chaining.
Regenerate on the fixed core rectangles. Preserve the old minimum register count; explicitly price added cycles.
A failed path retains its original data and makes the result FAIL. This tool never authorizes P&R or changes pins.
"""
import argparse,copy,json
from pathlib import Path
import hub_repack as HR


def hops(s):
    pts=[s['from_um']]+s.get('regs_um',[])+[s['to_um']]
    return [sum(abs(a-b) for a,b in zip(x,y)) for x,y in zip(pts,pts[1:])]


def preserve_count(raster,a,b,regs,n_old,ring_max=40):
    """HR.route_station only TRIES to keep n_old (place_regs stops when the longest gap has no free lattice sample
    left), so keep the priced register count explicitly: each missing register goes on the nearest free, unused
    4.32-um lattice site to the midpoint of the longest remaining hop and is inserted in that hop (static schedule
    unchanged, no cycle silently dropped). Returns the padded list, or None when no free site exists (fail closed)."""
    regs=[list(r) for r in regs]
    G=HR.G
    while len(regs)<n_old:
        pts=[list(a)]+regs+[list(b)]
        gi=max(range(len(pts)-1),key=lambda k:sum(abs(x-y) for x,y in zip(pts[k],pts[k+1])))
        mx,my=[(p+q)/2 for p,q in zip(pts[gi],pts[gi+1])]
        used={(round(r[0],3),round(r[1],3)) for r in regs}
        site=None
        for ring in range(ring_max+1):
            cand=[(dx,dy) for dx in range(-ring,ring+1) for dy in range(-ring,ring+1) if max(abs(dx),abs(dy))==ring]
            cand.sort(key=lambda d:abs(d[0])+abs(d[1]))
            for dx,dy in cand:
                x,y=round(round(mx/G+dx)*G,3),round(round(my/G+dy)*G,3)
                if raster.free(x,y) and (x,y) not in used:
                    site=[x,y];break
            if site:break
        if site is None:return None
        regs.insert(gi,site)
    return regs


def regenerate(t,reach=405.0,pad_ring=40):
    if not 0 < reach <= 405.0:raise ValueError('reach must respect the <=405um rule')
    out=copy.deepcopy(t);W,H=out['outline_um']
    raster=HR.Raster(W,H,[HR._core_rect(h) for h in out.get('hard_cores',[])])
    rows=[];fail=[]
    for i,s in enumerate(out.get('internal_stations',[])):
        old=len(s.get('regs_um',[]))
        routed=HR.route_station(raster,s['from_um'],s['to_um'],old,reach)
        if routed is None:
            fail.append(i);rows.append(dict(station=i,conn=s.get('conn'),verdict='FAIL',reason='no legal final-pin station path'))
            continue
        regs=[list(p) for p in routed['regs']]
        padded=preserve_count(raster,s['from_um'],s['to_um'],regs,old,pad_ring)
        if padded is None:
            fail.append(i);rows.append(dict(station=i,conn=s.get('conn'),verdict='FAIL',reason='no free site to keep the priced register count',old_cycles=old,routed_cycles=len(regs)))
            continue
        s['regs_um']=padded
        extra=len(s['regs_um'])-old
        assert extra>=0,'route_station dropped a priced register'
        rows.append(dict(station=i,conn=s.get('conn'),verdict='PASS',old_cycles=old,new_cycles=len(s['regs_um']),added_cycles=extra,
                         preserved_cycles=len(s['regs_um'])-len(regs),max_hop_um=max(hops(s),default=0),kind=routed['kind']))
        if rows[-1]['max_hop_um']>reach+1e-6:
            rows[-1].update(verdict='FAIL',reason='final reach exceeds rule');fail.append(i)
    report=dict(schema='opentallas.hbm_final_stations.v1',verdict='FAIL' if fail else 'PASS',reach_um=reach,
        scope='model-only final-pin station geometry; native RTL/compiler latency and route/clock/PG gates remain required',
        failed=fail,stations=len(rows),added_cycles=sum(r.get('added_cycles',0) for r in rows),
        max_hop_um=max((max(hops(s),default=0) for s in out.get('internal_stations',[])),default=0),rows=rows)
    return out,report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('type_json');p.add_argument('--out',required=True);p.add_argument('--reach',type=float,default=405.0);p.add_argument('--pad-ring',type=int,default=40,help='lattice rings searched for a kept register site');a=p.parse_args()
    out=Path(a.out)
    if out.exists():raise SystemExit('refusing to overwrite an existing result directory')
    t=json.loads(Path(a.type_json).read_text());new,report=regenerate(t,a.reach,a.pad_ring);out.mkdir(parents=True)
    (out/'candidate_type.json').write_text(json.dumps(new,indent=1)+'\n');(out/'report.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=1));return report['verdict']!='PASS'
if __name__=='__main__':raise SystemExit(main())

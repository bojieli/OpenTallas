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


def regenerate(t,reach=405.0):
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
        s['regs_um']=[list(p) for p in routed['regs']]
        extra=len(s['regs_um'])-old
        assert extra>=0,'route_station dropped a priced register'
        rows.append(dict(station=i,conn=s.get('conn'),verdict='PASS',old_cycles=old,new_cycles=len(s['regs_um']),added_cycles=extra,max_hop_um=max(hops(s),default=0),kind=routed['kind']))
        if rows[-1]['max_hop_um']>reach+1e-6:
            rows[-1].update(verdict='FAIL',reason='final reach exceeds rule');fail.append(i)
    report=dict(schema='opentallas.hbm_final_stations.v1',verdict='FAIL' if fail else 'PASS',reach_um=reach,
        scope='model-only final-pin station geometry; native RTL/compiler latency and route/clock/PG gates remain required',
        failed=fail,stations=len(rows),added_cycles=sum(r.get('added_cycles',0) for r in rows),
        max_hop_um=max((max(hops(s),default=0) for s in out.get('internal_stations',[])),default=0),rows=rows)
    return out,report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('type_json');p.add_argument('--out',required=True);p.add_argument('--reach',type=float,default=405.0);a=p.parse_args()
    out=Path(a.out)
    if out.exists():raise SystemExit('refusing to overwrite an existing result directory')
    t=json.loads(Path(a.type_json).read_text());new,report=regenerate(t,a.reach);out.mkdir(parents=True)
    (out/'candidate_type.json').write_text(json.dumps(new,indent=1)+'\n');(out/'report.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=1));return report['verdict']!='PASS'
if __name__=='__main__':raise SystemExit(main())

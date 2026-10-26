"""Materialize a bounded density-derived clock table, then check actual controls.

Fixed clock endpoints remove clock/control coordinate feedback. The normal
native clock, load, distance and halo obligations remain in force.
"""
import argparse
import copy
import json
from pathlib import Path
import sys


def share_unchanged_grids(old,new,changed,RT):
    # A local tap grid reads only its type, clock/layer/budget context and
    # instance/port geometry. START/reset flags never determine a clock grid.
    for name in ('layers','layer_budget','budgets','clock','parts','ports'):
        if getattr(old,name)!=getattr(new,name):
            raise ValueError('clock context changed: '+name)
    count=0
    for tn in old.types:
        if tn in changed or old.types[tn]!=new.types[tn]:
            continue
        cached=RT._TAPS.get((id(old),tn))
        if cached is not None and cached[0] is old:
            RT._TAPS[(id(new),tn)]=(new,list(cached[1]));count+=1
    return count


def wave_delta(before,after):
    rows={}
    for name,a in after['parts'].items():
        b=before['parts'][name]
        cores={k:dict(before=b.get('core_release',{}).get(k),after=v)
               for k,v in a.get('core_release',{}).items() if b.get('core_release',{}).get(k)!=v}
        if b['release']!=a['release'] or b['parent']!=a['parent'] or cores:
            rows[name]=dict(type=a['type'],before=b['release'],after=a['release'],delta=a['release']-b['release'],
                           parent_before=b['parent'],parent_after=a['parent'],core_release_changes=cores)
    pins={n:dict(before={k:before['types'][n][k] for k in ('in_um','outs')},after={k:t[k] for k in ('in_um','outs')})
          for n,t in after['types'].items() if any(before['types'][n][k]!=t[k] for k in ('in_um','outs'))}
    return dict(parts_compared=len(after['parts']),unchanged_parts=len(after['parts'])-len(rows),
                max_release_before=before['max_release'],max_release_after=after['max_release'],
                partition_changes=rows,reset_pin_changes=pins,unreachable=after['unreachable'],long_hops=after['long_hops'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('baseline',type=Path);ap.add_argument('geometry',type=Path)
    ap.add_argument('geometry_report',type=Path);ap.add_argument('out',type=Path)
    ap.add_argument('--tools',type=Path,default=Path(__file__).resolve().parents[3]/'tools/die_plan')
    ap.add_argument('--plan-context',type=Path,default=Path(__file__).resolve().parent/'die_plan.json')
    args=ap.parse_args();sys.path.insert(0,str(args.tools));sys.path.insert(0,str(Path(__file__).resolve().parent))
    import schema as S,reset_tree as RT,taps,gen as G
    import delta_station_controls_1713 as D
    original=json.loads(args.baseline.read_text());geometry=json.loads(args.geometry.read_text())
    report=json.loads(args.geometry_report.read_text());names=report['types']
    if report['failures']:raise ValueError('geometry failures must be fixed first')
    args.out.mkdir(parents=True,exist_ok=True)
    baseline=S.Plan(original,path=args.plan_context)
    print('BASELINE whole-die reset contract',flush=True);before=RT.wf_plan(baseline)
    (args.out/'baseline_wavefront.json').write_text(json.dumps(before,indent=1)+'\n')
    seed=copy.deepcopy(geometry);seed.setdefault('reset',{})['start']='broadcast'
    pseed=S.Plan(seed,path=args.plan_context)
    report['shared_baseline_grids']=share_unchanged_grids(baseline,pseed,names,RT)
    print('SEED actual RESET+START sites on data-density taps',flush=True)
    inventories={n:D.census(RT.for_type(pseed,n)) for n in names}
    for n,(sites,_) in inventories.items():seed['partition_types'][n]['clock']['sink_sites_um']=sites
    density=S.Plan(seed,path=args.plan_context)
    tables={n:taps.density_taps(density,n) for n in names}
    fixed=copy.deepcopy(geometry)
    for n,table in tables.items():
        ck=fixed['partition_types'][n]['clock']
        ck['taps']=[p for p in ck.get('taps',[]) if p.get('kind')=='core']+[
            dict(name=port,xy=[x,y],kind='leaf',note='materialized bounded density; actual control coverage checked')
            for port,x,y,_,_ in table]
        ck['tap_mode']='explicit';ck['sink_sites_um']=inventories[n][0]
    (args.out/'fixed_seed.json').write_text(json.dumps(fixed,indent=1)+'\n')
    report['control_seed']={n:dict(sites=len(s),flops=sum(p[2] for p in s),roles=r) for n,(s,r) in inventories.items()}
    for mode in ('reset','start'):
        raw=copy.deepcopy(fixed)
        if mode=='start':raw.setdefault('reset',{})['start']='broadcast'
        p=S.Plan(raw,path=args.plan_context);share_unchanged_grids(baseline,p,names,RT)
        print(mode.upper()+' fixed-table actual controller census',flush=True)
        trees={n:RT.for_type(p,n) for n in names}
        actual={n:D.census(t) for n,t in trees.items()}
        for n,(sites,_) in actual.items():raw['partition_types'][n]['clock']['sink_sites_um']=sites
        (args.out/(mode+'_actual_unchecked.json')).write_text(json.dumps(raw,indent=1)+'\n')
        (args.out/(mode+'_control_sites.json')).write_text(json.dumps(actual,indent=1)+'\n')
        # The tables are immutable; verify every actual weighted control/FT sink
        # before reusing topology caches, which depend on endpoint geometry only.
        coverage={n:taps.explicit_taps(p,n) for n in names}
        for n,table in coverage.items():
            if [(a,b,c) for a,b,c,_,_ in table]!=[(a,b,c) for a,b,c,_,_ in tables[n]]:
                raise ValueError('explicit endpoint geometry changed: '+n)
        wave=RT.wf_plan(p)
        report['whole_die_'+mode+'_delta']=wave_delta(before,wave)
        report[mode+'_controls']={n:dict(sites=len(s),flops=sum(v[2] for v in s),roles=r,
                                        release_clocks=RT.release_clocks(trees[n]),fixed_endpoint_geometry=True)
                                 for n,(s,r) in actual.items()}
        report[mode+'_coverage']={n:dict(taps=len(v),max_load=max(t[3] for t in v),max_distance_um=max(t[4] for t in v),empty=0)
                                 for n,v in coverage.items()}
        G.write_latency(raw,args.out/(mode+'_latency'),inplace_path=args.out/(mode+'_die_plan.json'))
        (args.out/(mode+'_wavefront.json')).write_text(json.dumps(wave,indent=1)+'\n')
        print(mode.upper()+' actual sink load/distance/halo PASS',flush=True)
    report['route_authorized']=False
    report['scope']='explicit clock source candidate; actual CTS/GRT/native TT/FF, START parent/bind/calendar and pricing acceptance still required'
    (args.out/'fixed_clock_report.json').write_text(json.dumps(report,indent=1)+'\n')
    print('FIXED_CLOCK_SOURCE_COMPLETE',flush=True)


if __name__=='__main__':main()

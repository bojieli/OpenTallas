#!/usr/bin/env python3
"""Compose disjoint completed station repairs without summing latency deltas."""
import argparse, copy, hashlib, json, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'/'die_plan'))
import schema as S

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base',type=Path,required=True)
    ap.add_argument('--repair',type=Path,action='append',required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists():raise SystemExit('output must be new')
    p=json.loads((a.base/'die_plan.json').read_text()); before=S.Plan(copy.deepcopy(p)); used=set()
    report={'release_ready':False,'clock_pending':True,'physical_proto_pending':True,'repairs':[]}
    for src in a.repair:
        r=json.loads((src/'repair_report.json').read_text())
        if r['internal_unroutable'] or r['ft_repair'].get('type_failures') or r['ft_repair'].get('unfixed'):
            raise ValueError(f'{src}: repair did not pass')
        q=json.loads((src/'die_plan.json').read_text())
        for field in ('die','partitions','ports','lanes'):
            if q.get(field)!=p.get(field):raise ValueError(f'{src}: incompatible global {field}')
        overlap=used.intersection(r['types'])
        if overlap:raise ValueError(f'overlapping type repairs {overlap}')
        for tn in r['types']:
            if q['partition_types'][tn]['outline_um']!=p['partition_types'][tn]['outline_um']:
                raise ValueError(f'{src}: incompatible outline {tn}')
            target=p['partition_types'][tn]; repaired=q['partition_types'][tn]
            # A repair may predate the canonical interface publisher. Transfer
            # station geometry only; keep current pins and core OBS contracts.
            target['internal_stations']=repaired.get('internal_stations',[])
            slots={s['name']:s for s in target.get('ft_slots',[])}
            for sl in repaired.get('ft_slots',[]):
                if sl['name'] not in slots:raise ValueError(f'{tn}: unknown repaired slot')
                for key in ('stations','regs_um','bit_site_cell_um','bit_sites_um'):
                    if key in sl:slots[sl['name']][key]=sl[key]
                    else:slots[sl['name']].pop(key,None)
        used.update(r['types'])
        report['repairs'].append({'source':str(src),'sha256':hashlib.sha256((src/'die_plan.json').read_bytes()).hexdigest(),'types':r['types'],'ft_checked':r['ft_repair']['checked'],'ft_added':len(r['ft_repair']['added'])})
    after=S.Plan(p)
    unresolved=[pid for pid,pr in after.ports.items() if any(k not in pr for k in ('face','window_um','layers'))]
    if unresolved:raise ValueError(f'unresolved canonical ports: {unresolved}')
    p['latency']['lanes']={lid:after.lane_latency(lid) for lid in after.lanes}
    report['lane_cycle_delta_from_base']={lid:p['latency']['lanes'][lid]['cycles']-before.lane_latency(lid)['cycles'] for lid in after.lanes if p['latency']['lanes'][lid]['cycles']!=before.lane_latency(lid)['cycles']}
    report['internal_type_max']={tn:max([len(s['regs_um']) for s in p['partition_types'][tn].get('internal_stations',[])]+[0]) for tn in sorted(used)}
    shutil.copytree(a.base,a.out)
    # Repair is plan-only. Sidecars must be byte-identical; never hide a changed master.
    for src in a.repair:
        for pin in src.glob('cores/**/*'):
            if pin.is_file():
                target=a.out/pin.relative_to(src)
                if target.exists() and pin.read_bytes()!=target.read_bytes():raise ValueError(f'changed sidecar {pin}')
                if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(pin,target)
    (a.out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n')
    (a.out/'composition_report.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps(report))
if __name__=='__main__':main()

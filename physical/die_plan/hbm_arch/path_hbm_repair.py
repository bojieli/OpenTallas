#!/usr/bin/env python3
"""Rebuild HBM candidate station/boot geometry without changing its windows.

This consumes a new plan candidate; original failure evidence is never modified.
The selected types permit disjoint SU and band repairs to run concurrently.
"""
import argparse,copy,importlib,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'tools'/'die_plan'),str(HERE)]
import schema as S


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--src',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--helper',type=Path,required=True);ap.add_argument('--types',required=True);a=ap.parse_args()
    if a.out.exists():raise SystemExit('output must be new')
    sys.path.insert(0,str(a.helper.resolve()));B=importlib.import_module('b2o');BN=importlib.import_module('b2n');HBS=importlib.import_module('hbm_bit_stations')
    p=json.loads((a.src/'die_plan.json').read_text());old=copy.deepcopy(p);types=a.types.split(',');shutil.copytree(a.src,a.out)
    report={'not_release_ready':True,'types':types,'unproven_face_budgets':{},'clock_pending':True};log=[]
    for tn,t in p['partition_types'].items():
        if isinstance(t.get('face_pins_per_um'),dict):report['unproven_face_budgets'][tn]=t.pop('face_pins_per_um')
    print('REBUILD_INTERNAL',','.join(types),flush=True)
    report['internal_unroutable']=B.internal_stations(p,a.out,types,log)
    print('REBUILD_ACTUAL_FT',flush=True)
    try:report['ft_repair']=HBS.repair(p,log=lambda m:print(m,flush=True),only_types=types)
    except HBS.RepairFailure as e:report['ft_repair']=e.report
    print('REBUILD_RESET',flush=True);BN.reset_wavefront(p,log)
    before=S.Plan(old,a.src/'die_plan.json');after=S.Plan(p,a.out/'die_plan.json');p['latency']['lanes']={lid:after.lane_latency(lid) for lid in after.lanes}
    report['lane_cycle_delta']={lid:p['latency']['lanes'][lid]['cycles']-before.lane_latency(lid)['cycles'] for lid in after.lanes if p['latency']['lanes'][lid]['cycles']!=before.lane_latency(lid)['cycles']}
    report['internal_type_max']={tn:{'before':max([len(s['regs_um']) for s in old['partition_types'][tn].get('internal_stations',[])]+[0]),'after':max([len(s['regs_um']) for s in p['partition_types'][tn].get('internal_stations',[])]+[0])} for tn in types}
    report['log']=log
    (a.out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n');(a.out/'repair_report.json').write_text(json.dumps(report,indent=1,default=str)+'\n');print('REPAIR_COMPLETE',json.dumps({'internal_unroutable':report['internal_unroutable'],'ft_failures':report['ft_repair'].get('type_failures'),'lane_delta':report['lane_cycle_delta']}),flush=True)

if __name__=='__main__':main()

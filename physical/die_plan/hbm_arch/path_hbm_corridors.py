#!/usr/bin/env python3
"""Re-place HBM bank hard cores outside die-owned FT bands.

The source plan remains immutable. Refuse any unsatisfied core-free band; do
not shrink cores, erase obstructions, change pins, or change the clock period.
Use --repair-helper for the lane's matching b2o station generator.
"""
import argparse
import copy
import importlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / 'tools' / 'die_plan'), str(HERE)]
import cores_b2 as CB


def overlap(a, b):
    return a[0] < b[0]+b[2]-1e-6 and b[0] < a[0]+a[2]-1e-6 and a[1] < b[1]+b[3]-1e-6 and b[1] < a[1]+a[3]-1e-6


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--src',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--types',default='q_b001,q_b011')
    ap.add_argument('--repair-helper',type=Path)
    a=ap.parse_args()
    if a.out.exists(): raise SystemExit('output must be new')
    p=json.loads((a.src/'die_plan.json').read_text())
    report={'source':str(a.src),'types':{},'lane_cycle_delta':{},'not_release_ready':True}
    changed=[]
    # Legacy DIE-FT plans stored per-face 12/um overrides before the current
    # scalar + measured-G2 contract. Preserve them as evidence; evaluate the
    # candidate under the default budget until real probe receipts exist.
    report['unproven_face_budgets']={}
    for tn,t in p['partition_types'].items():
        if isinstance(t.get('face_pins_per_um'),dict):
            report['unproven_face_budgets'][tn]=t.pop('face_pins_per_um')
    for tn in a.types.split(','):
        t=p['partition_types'][tn]; w,h=t['outline_um']; cs=t.get('hard_cores',[])
        obs=[(0,b['span_um'][0]-8.64,w,b['span_um'][1]-b['span_um'][0]+17.28) for b in t.get('die_ft_bands',[]) if b['dir']=='EW']
        before=sum(overlap((*c['origin_um'],*c['outline_um']),r) for c in cs for r in obs)
        attrs={c['inst']:[(1,tuple(c['origin_um'][i]+c['outline_um'][i]/2 for i in [0,1]))] for c in cs}
        pos=CB.place_flow([(c['inst'],*c['outline_um']) for c in cs],w,h,attrs,obst=obs,passes=2,step=8.64)
        if pos is None: raise SystemExit(f'{tn}: no core-free placement')
        moves=[]; contents={c['inst']:c for c in t.get('contents',[])}
        for c in cs:
            old=list(c['origin_um']); new=list(pos[c['inst']]); c['origin_um']=new
            if old!=new:moves.append({'inst':c['inst'],'from':old,'to':new})
            cc=contents.get(c['inst'])
            if cc and 'origin_um' in cc:cc['origin_um']=new
            for tap in t.get('clock',{}).get('taps',[]):
                if tap['name']==c['inst']:
                    tap['xy']=[round(tap['xy'][i]+new[i]-old[i],4) for i in [0,1]]
        assert not any(overlap((*c['origin_um'],*c['outline_um']),r) for c in cs for r in obs)
        report['types'][tn]={'prior_core_band_intersections':before,'moves':moves,'after_core_band_intersections':0}
        changed.append(tn)
    # The spt/spu FT lane is a wide northbound transfer with a 222-um lateral jog.
    # Give its jog an explicitly empty horizontal strip, rather than using M7
    # against its preferred direction over the core field.
    for tn, bands in {
      'q_spt0':[('NS',[380.16,1071.36],['M5','M7']),('EW',[302.4,457.92],['M4','M6'])],
      'q_spu0':[('NS',[380.16,1071.36],['M5','M7']),('EW',[302.4,457.92],['M4','M6'])],
    }.items():
        t=p['partition_types'][tn];w,h=t['outline_um'];out=[]
        cs=t.get('hard_cores',[])
        obs=[(0,sp[0],w,sp[1]-sp[0]) if dr=='EW' else (sp[0],0,sp[1]-sp[0],h) for dr,sp,ls in bands]
        if any(overlap((*c['origin_um'],*c['outline_um']),r) for c in cs for r in obs):
            pos=CB.place_flow([(c['inst'],*c['outline_um']) for c in cs],w,h,
                {c['inst']:[(1,tuple(c['origin_um'][i]+c['outline_um'][i]/2 for i in [0,1]))] for c in cs},obst=obs,passes=1,step=8.64)
            if pos is None:raise SystemExit(f'{tn}: band relocation infeasible')
            for c in cs:
                old=list(c['origin_um']);new=list(pos[c['inst']]);c['origin_um']=new
                for ct in t.get('contents',[]):
                    if ct['inst']==c['inst'] and 'origin_um' in ct:ct['origin_um']=new
                for tap in t.get('clock',{}).get('taps',[]):
                    if tap['name']==c['inst']:tap['xy']=[round(tap['xy'][i]+new[i]-old[i],4) for i in [0,1]]
            changed.append(tn)
        for direction,span,layers in bands:
            r=(0,span[0],w,span[1]-span[0]) if direction=='EW' else (span[0],0,span[1]-span[0],h)
            if any(overlap((*c['origin_um'],*c['outline_um']),r) for c in t.get('hard_cores',[])):
                raise SystemExit(f'{tn}: new band touches core')
            out.append({'dir':direction,'span_um':span,'layers':layers,'die_share':1.0,'note':'HBM corridor delta: core-free lane capacity, no obstruction removal'})
        t['die_ft_bands']=out
        report['types'][tn]={'bands':out,'core_intersections':0}
    shutil.copytree(a.src,a.out)
    before={s['conn']:len(s['regs_um']) for tn in changed for s in p['partition_types'][tn].get('internal_stations',[])}
    if a.repair_helper:
        sys.path.insert(0,str(a.repair_helper.resolve()))
        B=importlib.import_module('b2o');log=[]
        failures=B.internal_stations(p,a.out,changed,log)
        report['station_rebuild']={'log':log,'failures':failures}
        after={s['conn']:len(s['regs_um']) for tn in changed for s in p['partition_types'][tn].get('internal_stations',[])}
        report['internal_cycle_delta']={k:after[k]-before.get(k,0) for k in after if after[k]!=before.get(k,0)}
    else:report['station_rebuild']='NOT RUN; stale station geometry blocks adoption'
    (a.out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n')
    (a.out/'corridor_report.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps(report,indent=1))

if __name__=='__main__':main()

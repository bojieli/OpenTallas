#!/usr/bin/env python3
"""Generate the zero-cycle compact BK-g hard-core candidate for the one S81 B2 plan event.

No source RTL changes. New plan/pin/LEF outputs are separate from the historical views.
Measured k26b: 28303 cells,6012 flops,fill12.45%,empty61.96%,r2r368.23um.
Two SRAMs originally only0.024um apart vertically; candidate gap17.256um.
"""
import argparse
import copy
import importlib.util
import hashlib
import json
import math
from pathlib import Path

MODULE = 'dsdv_bk_g'
SIZE = (159.84, 164.16)
GRID = {'M3': ('x', .009, .036, .072), 'M4': ('y', .012, .048, .096),
        'M5': ('x', .012, .048, .096)}
RECT = {'M3': (.018, .038), 'M4': (.084, .024), 'M5': (.024, .084)}


def compact(plan, s81, out):
    hits = [c for t in plan['partition_types'].values() for c in t.get('hard_cores', [])
            if c.get('module') == MODULE]
    if not hits:
        raise ValueError('no BK-g hard core in the supplied plan')
    first = hits[0]
    old = tuple(first['outline_um'])
    if old != (216.0, 172.8):
        raise ValueError(f'unexpected BK-g outline {old}; do not compact an evolved core')
    if any(tuple(c['outline_um']) != old or c['pins_file'] != first['pins_file'] for c in hits):
        raise ValueError('BK-g instances do not share one pin/outline contract')
    pj = json.loads((s81 / first['pins_file']).read_text())
    pins = copy.deepcopy(pj['pins'])
    oldw, oldh = old
    w, h = SIZE
    groups = {}
    for p in pins:
        face = min([(p['x'], 'W'), (oldw-p['x'], 'E'), (p['y'], 'S'), (oldh-p['y'], 'N')])[1]
        groups.setdefault((face, p['layer']), []).append(p)
    checks = []
    for (face, layer), ps in groups.items():
        axis, offset, pitch, spacing = GRID[layer]
        if axis != ('x' if face in 'NS' else 'y'):
            raise ValueError(f'{layer} direction disagrees with {face} face')
        length = w if axis == 'x' else h
        oldlength = oldw if axis == 'x' else oldh
        lo, hi = 4.32, length-4.32
        # Every second track, matching the approved legacy core pin lattice capacity.
        sites = [offset+k*spacing for k in range(math.ceil((lo-offset)/spacing),
                                                 math.floor((hi-offset)/spacing)+1)]
        if len(sites) < len(ps):
            raise ValueError(f'{face}/{layer}: {len(ps)} pins exceed {len(sites)} sites')
        ps.sort(key=lambda p: (p[axis], p['name']))
        # Monotonic assignment preserves bus ordering and reserves a unique physical site per bit.
        previous = -1
        for i,p in enumerate(ps):
            target = (max(lo,min(hi,p[axis]/oldlength*length)) if face == 'W'
                      else lo + i * (hi-lo) / max(1,len(ps)-1))
            want = round((target-sites[0])/spacing)
            idx = max(previous+1,min(want,len(sites)-(len(ps)-i)))
            p[axis] = round(sites[idx],6)
            pw,ph = RECT[layer]
            p['y' if axis=='x' else 'x'] = round({'N':h-ph/2,'S':ph/2,'E':w-pw/2,'W':pw/2}[face],6)
            previous=idx
        checks.append({'face':face,'layer':layer,'pins':len(ps),'sites':len(sites)})
    # Directions are read from the original view; a missing signal remains an error.
    repo=s81.parents[2]
    spec=importlib.util.spec_from_file_location('legacy',s81/'cores/legacy/gen_core_kit_legacy.py')
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    dirs=legacy.lef_dirs(repo/first['lef'])
    unknown=[p['name'] for p in pins if p['name'] not in dirs]
    if unknown:raise ValueError(f'missing directions {unknown[:4]}')
    rel=Path('cores/compact_bkg_1026');dest=out/rel;dest.mkdir(parents=True,exist_ok=True)
    pinrel=rel/f'{MODULE}.json';lefrel=rel/f'{MODULE}.lef'
    pj['pins']=pins;pj['lef']=str((s81/lefrel).relative_to(repo));pj['source']='compact BK-g candidate; preserves all port names, face ordering and RTL latency; fresh planned PG, same pin layers; not adopted'
    pj['pinhash']=hashlib.sha256(json.dumps(pins,sort_keys=True).encode()).hexdigest()[:12]
    (out/pinrel).write_text(json.dumps(pj,indent=1)+'\n')
    lines=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',f'MACRO {MODULE}',' CLASS BLOCK ;',' ORIGIN 0 0 ;',f' SIZE {w} BY {h} ;',' SYMMETRY X Y ;']
    for p in pins:
        pw,ph=RECT[p['layer']];x,y=p['x'],p['y']
        lines += [f" PIN {p['name']}",f"  DIRECTION {dirs[p['name']]} ;",'  USE SIGNAL ;','  PORT',f"   LAYER {p['layer']} ;",f'   RECT {x-pw/2:.6f} {y-ph/2:.6f} {x+pw/2:.6f} {y+ph/2:.6f} ;','  END',f" END {p['name']}"]
    # Fresh planned PG rectangles from the unchanged legacy PDN recipe. These
    # are a candidate interface only; actual post-PDN pins must replace them
    # before parent adoption. No old LEF is cropped or presented as measured.
    for supply,use,delta in [('VDD','POWER',0),('VSS','GROUND',.192)]:
        lines += [f' PIN {supply}','  DIRECTION INOUT ;',f'  USE {use} ;','  PORT','   LAYER M5 ;']
        for k in range(100):
            x=4.32+2.064+delta+4.32*k
            if x+.06>w-4.32:break
            lines += [f'   RECT {x-.06:.6f} 4.320000 {x+.06:.6f} {h-4.32:.6f} ;']
        lines += ['  END',f' END {supply}']
    lines += [' OBS']
    for L in ['M1','M2','M3','M4','M5']:lines += [f'  LAYER {L} ;',f'  RECT 0.5 0.5 {w-.5} {h-.5} ;']
    lines += [' END',f'END {MODULE}','END LIBRARY']
    (out/lefrel).write_text('\n'.join(lines)+'\n')
    for c in hits:
        c.update(outline_um=list(SIZE),pins_file=str(pinrel),lef=str((s81/lefrel).relative_to(repo)),obs_max='M5')
    (out/'die_plan.json').write_text(json.dumps(plan,indent=1)+'\n')
    recipes=json.loads((s81/'cores/legacy/recipes.json').read_text())
    recipes[MODULE]['macro_sites']={'ot_sram_1r1w_128x256_m1_r2c2':[[32.4,32.4,'R0'],[32.4,90.72,'R0']]}
    recipes[MODULE]['pin_layers_from_plan']=True
    # Port names and directions are unchanged; use the source LEF directions.
    # Coordinator system Yosys predates inline integer loop declarations.
    recipes[MODULE]['rtl_dirs']=False
    (out/'recipes.json').write_text(json.dumps(recipes,indent=1)+'\n')
    report={'module':MODULE,'pins':len(pins),'core_entries':len(hits),'old_outline_um':old,'new_outline_um':SIZE,
            'max_possible_r2r_manhattan_um':sum(SIZE),'data_cycles_added':0,'rtl':'UNCHANGED',
            'site_capacity':checks,'status':'CANDIDATE; requires B2 G0/G0C, parent image review and actual placement'}
    (out/'bkg_compact_report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True,type=Path);ap.add_argument('--s81',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    print(json.dumps(compact(json.loads(a.plan.read_text()),a.s81,a.out)))

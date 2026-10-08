#!/usr/bin/env python3
"""Prepare one immutable explicit-chain ECO; no RTL, clock or timing relaxation."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
BASE=Path('physical/s81_pq_return_delay')


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def tcl_atom(s):
    if any(c in s for c in '{}\n\r'):raise ValueError('Unsupported Tcl name')
    return '{'+s+'}'


def prepare(regions,out,verify_runtime=True):
    if regions != 16:
        raise ValueError('R128 requires the fresh expanded-footprint ODB and its own timing/topology inventory before a delay-chain ECO')
    planpath=ROOT/BASE/f'r{regions}/plan_retained_wire.json';plan=json.loads(planpath.read_text())
    if plan['status']!='READY_FOR_PHYSICAL_CANDIDATE' or plan['unsupported']:
        raise ValueError('Unresolved endpoint plan is not admitted')
    if out.exists():raise FileExistsError('Preserve prior attempt: '+str(out))
    inputs=json.loads((ROOT/BASE/'runtime_inputs.json').read_text())
    runtime=inputs[str(regions)]
    db=next(x for x in runtime if x['path'].endswith('.odb'))
    if db['sha256']!=plan['original_odb_sha256']:raise ValueError('Timing/topology ODB mismatch')
    for p,h in plan['inputs'].items():
        if sha(ROOT/p)!=h:raise ValueError('Plan source input changed: '+p)
    if verify_runtime:
        for r in runtime:
            p=Path(r['path'])
            if p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise ValueError('Runtime input differs: '+str(p))
    post=ROOT/BASE/'signoff.sdc'
    if sha(post)!=runtime[-1]['sha256']:raise ValueError('Signoff constraints differ from original')
    out.mkdir(parents=True)
    lines=['set pq_delay_plan {']
    for row in plan['selected']:
        inst,pin=row['odb_endpoint'].rsplit('/',1);d=row['original_driver']
        lines.append('  {'+' '.join(tcl_atom(s) for s in (inst,pin,d['instance'],d['pin'],row['original_net']))+' '+str(row['cells'])+'}')
    lines+=['}'];(out/'plan.tcl').write_text('\n'.join(lines)+'\n')
    source=(ROOT/BASE/'frozen/hold_eco.tcl').read_text()
    prefix=source.split('# ---- setup protection data',1)[0]
    snap=source.split('# ---- snapshot, repair, legalise',1)[1].split('if {[llength [dict get $win fixable]]}',1)[0]
    tail=source.split('# ---- re-route: every signal wire stripped',1)[1]
    insert='''
source /p/plan.tcl
source /src/physical/s81_pq_return_delay/insert.tcl
set n0 [llength [get_cells *]]
pq_delay_apply
detailed_placement
check_placement -verbose
pq_delay_check 1
puts "PQ_DELAY_EXPLICIT_INSERTION_DONE"
'''
    text=prefix+snap+insert+'\n# ---- re-route: every signal wire stripped'+tail
    text=text.replace('puts "OT_ECO done"','pq_delay_check 1\nputs "PQ_DELAY_ROUTE_DONE"')
    commands='\n'.join(l for l in text.splitlines() if not l.lstrip().startswith('#'))
    if 'repair_timing -hold' in commands or 'repair_timing -setup' in commands:raise ValueError('Unexpected automatic timing mutation')
    (out/'explicit_eco.tcl').write_text(text)
    shutil.copyfile(planpath,out/'plan.json')
    rec=dict(status='PREPARED_RUNTIME_VERIFIED' if verify_runtime else 'PREPARED_RUNTIME_NOT_VERIFIED',
        region=regions,plan_sha256=sha(planpath),runtime=runtime,image_id=inputs['image_id'],
        input_base=str(Path(db['path']).parent),physical_closed=False,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/BASE/'insert.tcl',ROOT/BASE/'frozen/hold_eco.tcl',ROOT/BASE/'frozen/hold_eco_corner.tcl',ROOT/BASE/'frozen/hold_eco_window.tcl',post]},
        generated_hashes={p.name:sha(p) for p in out.iterdir() if p.is_file()})
    (out/'preparation.json').write_text(json.dumps(rec,indent=2)+'\n')
    return rec


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--regions',type=int,choices=(16,128),required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    r=prepare(a.regions,a.out,not a.prepare_only);print(json.dumps(dict(status=r['status'],source_odb_sha256=next(x['sha256'] for x in r['runtime'] if x['path'].endswith('.odb')))))
if __name__=='__main__':main()

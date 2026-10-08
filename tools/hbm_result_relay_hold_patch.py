#!/usr/bin/env python3
"""Literal 384-buffer relay candidate; original route/constraints stay immutable.

Prepare emits the sized model and hash-bound mutation recipe before any OpenROAD
mutation. Run uses three separate processes: physical patch, fresh SS, fresh FF.
No synthesis, repair_timing fallback, relaxed constraints or automatic adoption.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
from w18.corner_sta import script as corner_script

ROOT=Path(__file__).resolve().parents[1]
MASTER='DFFASRHQNx1_ASAP7_75t_R'
BUFFER='BUFx2_ASAP7_75t_R'
FILES=('6_final.odb','6_final.sdc','6_final.spef')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def endpoints():
    return [f'u_stage.g_registered.payload[{i}]$_DFF_PN0_/{pin}' for i in range(64) for pin in ('D','RESETN')]

def make_plan(base,orientation,baseline=None):
    if orientation not in ('ew','ns'):raise ValueError('Bad orientation')
    if baseline is None:
        baseline=json.loads((ROOT/f'results/physical/hbm_result_relay64_screen_20261007/{orientation}/1_corner_sta.json').read_text())
    hashes={name:sha(base/name) for name in FILES}
    for corner in ('setup_ss','hold_ff'):
        for name,key in [('6_final.odb','odb_sha256'),('6_final.sdc','sdc_sha256'),('6_final.spef','spef_sha256')]:
            if hashes[name]!=baseline[corner][key]:raise ValueError('Input differs from committed baseline '+name)
    return dict(schema='opentallas.hbm.result_relay_hold_patch.v1',status='MODELED_NOT_MEASURED_NOT_ADOPTED',
        top=f'hfd_result_relay64_{orientation}',cycles_added=0,flipflops_added=0,boundary_pins=130,
        inserted_cells=384,inserted_nets=384,area_added_um2=384*.0729,
        added_area_at_55pct_um2=384*.0729/.55,slot_um=[20,20],
        estimated_added_ff_delay_ps=36,delay_estimate_scope='3x approximately12ps baseline BUFx2; fresh measurement required',
        original_sha256=hashes,baseline_setup_ss_ps=baseline['setup_ss']['worst_slack_ps'],baseline_hold_ff_ps=baseline['hold_ff']['worst_slack_ps'],
        patches=[dict(endpoint=e,expected_master=MASTER,cells=[BUFFER]*3) for e in endpoints()],
        gates=['Full128 terminal inventory and literal noninverting topology',
               'Original833.333ps clock,60/25ps uncertainties and IO SDC byte-identical',
               'FreshSS>=15ps,FF>=15ps including reset recovery/removal,DRC0',
               '20x20 physical fit, original RTL proof and actual die-interface binding'])

def validate(plan):
    if plan.get('schema')!='opentallas.hbm.result_relay_hold_patch.v1':raise ValueError('Bad schema')
    if plan.get('top') not in ('hfd_result_relay64_ew','hfd_result_relay64_ns'):raise ValueError('Bad top')
    for k,v in dict(cycles_added=0,flipflops_added=0,boundary_pins=130,inserted_cells=384,inserted_nets=384,slot_um=[20,20]).items():
        if plan.get(k)!=v:raise ValueError('Model mismatch: '+k)
    if not math.isclose(plan.get('area_added_um2',-1),27.9936,abs_tol=1e-9):raise ValueError('Wrong area')
    rows=plan.get('patches',[])
    if len(rows)!=128 or {r['endpoint'] for r in rows}!=set(endpoints()):raise ValueError('Must bind exactly64D+64RESETN')
    if any(r['expected_master']!=MASTER or r['cells']!=[BUFFER]*3 for r in rows):raise ValueError('Wrong cell topology')
    if set(plan['original_sha256'])!=set(FILES) or any(not re.fullmatch('[0-9a-f]{64}',h) for h in plan['original_sha256'].values()):raise ValueError('Missing source hashes')

def prepare(base,out,plan):
    validate(plan)
    if out.exists():raise ValueError('Immutable output exists')
    for path in (base,out):
        if not re.fullmatch(r'[A-Za-z0-9_./-]+',str(path)):raise ValueError('Unsafe Tcl path')
    if base.resolve()==out.resolve() or base.resolve() in out.resolve().parents:raise ValueError('Output must be outside original route')
    for name in FILES:
        if sha(base/name)!=plan['original_sha256'][name]:raise ValueError('Original hash mismatch: '+name)
    out.mkdir(parents=True)
    shutil.copy2(base/'6_final.sdc',out/'6_final.sdc')
    # This receipt exists before the first process that can mutate the database.
    plan['helper_sha256']={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'physical/hbm_result_relay_hold_20261007/patch.tcl',ROOT/'tools/w18/corner_sta.py']}
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    prefix=corner_script('ss',str(base),[]).split('puts "OT_CORNER')[0]
    actions='set expected_top {'+plan['top']+'}\nset patches {\n'+'\n'.join(' {'+r['endpoint']+'} {'+r['expected_master']+'} {'+' '.join(r['cells'])+'}' for r in plan['patches'])+'\n}\n'
    body=(ROOT/'physical/hbm_result_relay_hold_20261007/patch.tcl').read_text()
    (out/'patch.tcl').write_text(prefix+'\nset patch_out {'+str(out)+'}\n'+actions+body)
    for corner,check in [('ss','max'),('ff','min')]:
        source=corner_script(corner,str(out),[]).rsplit('exit',1)[0]
        targets='set expected_targets {\n'+'\n'.join(' {'+e+'}' for e in endpoints())+'\n}\n'
        targets+='''foreach endpoint $expected_targets {
 set hits {}
 foreach p [get_pins -hierarchical *] {
  if {[get_full_name $p] eq $endpoint} {lappend hits $p}
 }
 if {[llength $hits] != 1} {error "Missing or ambiguous endpoint $endpoint"}
 puts "HBM_TARGET endpoint=$endpoint slack=[get_property [lindex $hits 0] slack_CHECK]"
}
'''.replace('CHECK',check)
        (out/f'sta_{corner}.tcl').write_text(source+targets+'exit\n')
    return out

def parse_timing(text):
    rows=re.findall(r'^HBM_TARGET endpoint=(\S+) slack=(\S+)$',text,re.M)
    if len(rows)!=128 or set(x[0] for x in rows)!=set(endpoints()):raise ValueError('Missing/duplicate endpoint timing')
    values={name:float(value) for name,value in rows}
    match=re.search(r'^OT_WS (\S+)$',text,re.M)
    if not match or '[ERROR' in text:raise ValueError('Missing/failed corner timing')
    worst=float(match[1])*1e12
    if not all(math.isfinite(v) for v in [worst,*values.values()]):raise ValueError('Nonfinite endpoint timing')
    return dict(worst_slack_ps=worst,target_slack_ps=values)

def run(out,binary):
    receipts=[]
    plan=json.loads((out/'plan.json').read_text());validate(plan)
    for stage in ('patch','sta_ss','sta_ff'):
        log=out/(stage+'.log')
        with log.open('x') as stream:
            rc=subprocess.run([binary,'-no_init','-exit',str(out/(stage+'.tcl'))],stdout=stream,stderr=subprocess.STDOUT).returncode
        receipts.append(dict(stage=stage,rc=rc,log_sha256=sha(log)))
        (out/'execution.json').write_text(json.dumps(receipts,indent=2)+'\n')
        if rc:raise RuntimeError('Failed '+stage)
    if sha(out/'6_final.sdc')!=plan['original_sha256']['6_final.sdc']:raise RuntimeError('Constraints changed')
    text=(out/'patch.log').read_text()
    if '[ERROR' in text or text.count('HBM_RELAY_PATCH endpoint=')!=384 or 'HBM_RELAY_PATCH_WRITTEN cells_added=384' not in text:raise RuntimeError('Missing mutation topology receipt')
    timing={c:parse_timing((out/f'sta_{c}.log').read_text()) for c in ('ss','ff')}
    drc=(out/'drc.rpt').read_text();count=0 if not drc.strip() else len(re.findall('violation type:',drc,re.I)) or None
    passed=count==0 and all(r['worst_slack_ps']>=15 and min(r['target_slack_ps'].values())>=15 for r in timing.values())
    result=dict(status='MEASURED_CANDIDATE_NOT_ADOPTED',timing=timing,drc_count=count,screen_gates_pass=passed,
        outputs={n:sha(out/n) for n in (*FILES,'6_final.v')},stages=receipts,
        scope='primitive screen; actual die clock/IO and protection binding still required')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--orientation',choices=['ew','ns'],required=True);ap.add_argument('--run',action='store_true')
    ap.add_argument('--openroad',default='openroad');a=ap.parse_args()
    prepare(a.base,a.out,make_plan(a.base,a.orientation))
    if a.run:run(a.out,a.openroad)

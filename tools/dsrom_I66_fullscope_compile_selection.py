#!/usr/bin/env python3
"""Select current core and passive fullscope top; never invoke a compiler/run.

Preserves the frozen producer and legacy compilation order. This is a hashed
source selection, not elaboration, program enrollment, or provider admission.
"""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PRODUCER='results/uarch/dsrom_I66_fullscope_native_hooks_20261003'
OUT=ROOT/'results/uarch/dsrom_I66_fullscope_compile_selection_20261003'

def sha(data):return hashlib.sha256(data).hexdigest()

def select(root=ROOT):
    plan_path=root/PRODUCER/'run_source_plan.json'
    plan=json.loads(plan_path.read_text())
    sources=plan['baseline_source_candidates']
    for row in sources:
        if sha((root/row['path']).read_bytes())!=row['sha256']:
            raise ValueError('legacy source changed: '+row['path'])
    if len(plan['actual_selected_core_mismatch'])!=1:
        raise ValueError('expected one concrete legacy core replacement')
    old=plan['actual_selected_core_mismatch'][0]['path']
    current=plan['selected_core_required']
    original='rtl/test/v41_runtime/ot_v41_rt_die.sv'
    top=PRODUCER+'/ot_v41_rt_die_i66_fullscope.sv'
    substitutions={old:current,original:top}
    order=plan['die_compile_order']
    for p in substitutions:
        if order.count(p)!=1 or sum(r['path']==p for r in sources)!=1:
            raise ValueError('ambiguous or missing source replacement: '+p)
    selected=[]
    for row in sources:
        path=substitutions.get(row['path'],row['path'])
        selected.append(dict(path=path,sha256=sha((root/path).read_bytes())))
    paths={r['path'] for r in selected}
    if len(paths)!=len(selected) or old in paths or original in paths:
        raise ValueError('duplicate or unselected source remains')
    if sha((root/current).read_bytes())!=plan['selected_core_sha256']:
        raise ValueError('current selected core identity changed')
    return dict(status='CURRENT_CORE_AND_PASSIVE_TOP_SOURCE_SELECTION_READY_NOT_COMPILED',
        producer_commit='139ecf3db',producer_plan_sha256=sha(plan_path.read_bytes()),
        emitter_schema='opentallas.PHW10.native-fullscope.raw.v1',
        emitter_and_elaboration_owner='Maxwell per latest explicit user assignment',
        downstream_lifetime_F_owner='Nash/requester',
        selected_sources=selected,source_census_count=len(selected),
        selected_die_compile_order=[substitutions.get(p,p) for p in order],
        substitutions=substitutions,top='ot_v41_rt_die_i66_fullscope',
        required_parameters=dict(I66_OBSERVE=1,ROM_PHW=10,ROM_FBW=1632,ROM_R=128,SUN=256),
        compiled_binary=None,actual_journal=None,trace_handle=None,
        complete_run_source_closure=False,elaboration_pass=False,jobs_launched=0,
        qualified_F=None,actual_fullcontext_max_live_versions=None,
        missing=['reviewed native driver/include/define/top parameter enrollment',
                 'complete current r0..3 program and separate field images enrollment',
                 'compiled hierarchy/ABI/source closure and actual binary identity',
                 'selected all384 stage dispatcher/full169 owner/captured CDC credit/packet retirement/qualified idle source implementation'],
        baseline_can_measure='Native acceptance, native idle, postNBA VM publication, SU reads/R+2 and source address version lifetime after current enrollment.',
        baseline_cannot_measure='Unimplemented candidate positive credit, packet debt, bank generation, or qualified F.',
        hardware_admission=False,fulltoken=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.write_text(json.dumps(select(),sort_keys=True,indent=2)+'\n')

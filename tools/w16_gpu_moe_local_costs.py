#!/usr/bin/env python3
"""Local MoE bank/staging scenario; upstream producer residence remains unpriced."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import w16_gpu_hc_vector_costs as C
import w19_gpu_elementwise_calendar as E

ROOT=C.ROOT
OUT='results/uarch/w16_gpu_moe_local_costs_20261001'
PROOF='results/quality/w19_moe_opcode_proof_20261001/proof.json'
CALENDAR='results/quality/w16_w19_composed_schedule_20261001/moe_sum_calendar.json'


def layout():
    # Separate full64-lane padded arrays; never alias a live expert slot.
    return dict(regions=[dict(name=f'expert{e}',base=e*128,bytes=128) for e in range(7)]
        +[dict(name='output',base=896,bytes=128),dict(name='control',base=1024,bytes=4096)],
        end_bytes=5120,capacity_bytes=65536,active_SM_per_rank=1,
        inactive_SM_budget_retained=31,producer_location='UNBOUND')


def build(commit=None):
    commit=commit or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    hc,_,g,S=C.build(C.R.read(C.OUT+'/cost_r1.json')['cost_evidence_commit'])
    proof=C.R.read(PROOF);calendar=C.R.read(CALENDAR)
    C.R.require(proof['verdict']=='PASS' and proof['calendar_sha256']==C.R.sha(CALENDAR),'MoE proof/calendar mismatch')
    C.R.require(calendar['recipe']==E.moe_recipe(E.provider()),'MoE recipe drift')
    C.R.require(proof['row_distribution']=={'53_rows':64,'54_rows':32},'TP96 rows changed')
    p=C.inputs()['profile'];kernel,trace=C.replay(calendar['recipe'],2,p)
    # All64 lanes executed, padded slots staged explicitly. Output only53/54
    # source-owned rows are exported. Fullword RMW touches private padded words.
    # A single32B fabric ingress/egress port serializes all seven arrays.
    to_serial=lambda n: math.ceil(n*p['serial_hz']/p['fabric_hz'])
    staged=7*128
    stage=to_serial(math.ceil(staged/p['NoC_bytes_cycle']))+p['CDC_cycles']+p['shared_latency']
    result=to_serial(math.ceil(54*2/p['NoC_bytes_cycle']))+p['shared_latency']+p['CDC_cycles']
    barrier=p['barrier_latency']+p['shared_latency']
    phases=dict(operand_stage=stage,gpu_simt_kernel=kernel['conditional_cycles'],
                result_stage=result,local_drain_barrier=barrier)
    own='tools/w16_gpu_moe_local_costs.py';evidence=dict(commit=commit,path=own,sha256=C.R.sha(own))
    costs={}
    for n in g['nodes']:
        op=g['operations'][n['source_operation_index']]
        if op.get('fn')!='moe_sum' or n['phase'] not in phases:continue
        costs[n['id']]=dict(cycles=phases[n['phase']],clock_hz=p['serial_hz'],resource_units=1,
            evidence=evidence,finite_waits_included=True,exact_gpu_lowering_bound=True,
            progress_deadline_validated=False,target_GPU_exactness=False,
            waits_are_scenario_allowances=True,
            scope='Local assumed-ready ingress/shared/egress only; source queues and downstream service unpriced.')
    C.R.require(len(costs)==160,'MoE phase mapping changed')
    paths=[own,'tools/w19_composed_schedule_r2.py','tools/w19_gpu_elementwise_calendar.py',
        'tools/w16_gpu_hc_vector_costs.py','tools/w16_gpu_hc_dot_schedule.py',
        C.INPUTS,C.HC_COST,C.OUT+'/cost_r1.json',PROOF,CALENDAR]
    return dict(schema='opentallas.w16.MoE-local-scenario.v1',cost_evidence_commit=commit,
        graph_sha256=g['graph_sha256'],scope='GPU_SIMT_FULL_TOKEN_MODEL',
        resource_capacities=dict(staging=32,simt=32,barrier=1),node_costs=costs,
        phase_cycles=phases,kernel=kernel,shared_layout=layout(),
        endpoint_bytes=dict(staged_padded_input=staged,source_input_max=54*7*2,
                            result_max=54*2,padded_output=128),
        bank_policy='Seven packed BF16 loads each serialize2; half extraction priced. Even/odd fullword RMW stores, no byte-enable credit.',
        transport_scope='One32B local fabric port, positive CDC/shared/barrier latencies assumed. Arrays staged serially after upstream arrival; upstream reads, landing contention, producer residence and output acceptance deadline remain unbound.',
        numerical_scope='Existing CPU proof validates ordered sevenFADDs and BF16 rounding. Modified packed-store calendar has software ordering witness only; production lane masks and GPU instructions remain unqualified.',
        progress_deadline_validated=False,validated_progress_bound=False,
        bound_admission='REFUSED_NO_SOURCE_DESTINATION_PROGRESS_DEADLINES',
        scenario_costs_only=True,hardware_adopted=False,physical_admission=False,
        full_token_cycles=None,headline_rate=None,
        unpriced_phases=['operand_read_credit_wait'],
        conditional_local_us_40=sum(phases.values())*40/p['serial_hz']*1e6,
        pins={path:C.R.sha(path) for path in paths}),trace,g,S,hc


def check(record):
    for path,pin in record['pins'].items():C.R.require(C.R.sha(path)==pin,'pin drift '+path)
    raw=subprocess.check_output(['git','show',record['cost_evidence_commit']+':tools/w16_gpu_moe_local_costs.py'],cwd=ROOT)
    C.R.require(hashlib.sha256(raw).hexdigest()==record['pins']['tools/w16_gpu_moe_local_costs.py'],'committed source drift')
    C.R.require(build(record['cost_evidence_commit'])[0]==record,'MoE local replay drift')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);m=ap.add_mutually_exclusive_group(required=True)
    m.add_argument('--out',type=Path);m.add_argument('--check',type=Path);a=ap.parse_args()
    if a.check:check(json.loads(a.check.read_text()))
    else:
        r,trace,g,S,hc=build()
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print('PASS160 local MoE scenario phases; upstream residence/read and progress bounds unpriced')

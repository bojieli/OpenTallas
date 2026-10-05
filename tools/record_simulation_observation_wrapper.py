#!/usr/bin/env python3
"""Record source-bound fake-harness controls; never invokes a full RTL build."""
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
import prepare_simulation_observation_wrapper as prep
from simulation_observation_api import State, encode, observe

EVIDENCE='results/rtl/simulation_observation_wrapper_4e383_20261002'

def packet(cycle=0, **values):
    for prefix in ['window_']+[f'ckv{i}_' for i in range(4)]:
        if values.get(prefix+'req_take'): values.setdefault(prefix+'req_ready',1)
    return encode(dict(epoch=1,rank=0,cycle=cycle,**values))

def controls():
    selection,_=observe(State(),packet(ckv_available=1,ckv_select_accept=1))
    replay,_=observe(selection,packet(1,ckv_available=1,ckv_job_accept=1,ckv_job_gen=19))
    fetch,_=observe(replay,packet(2,ckv_available=1,ckv_fetch_accept=1))
    outstanding,_=observe(fetch,packet(3,ckv_available=1,ckv0_req_take=1,ckv0_req_offer=1))
    refill,_=observe(State(),packet(window_prefetch_accept=1))
    cases=[
        ('wrong_generation',replay,packet(2,ckv_available=1,ckv_stream_take=1,ckv_job_gen=20),'job gen19 -> beat gen20'),
        ('early_retire',outstanding,packet(4,ckv_available=1,ckv_fetch_done=1),'fetch done with accepted request still outstanding'),
        ('repeated_step',replay,packet(1,ckv_available=1,ckv_job_accept=1,ckv_job_gen=19),'host repeats same sampled rising edge'),
        ('offer_as_accept',refill,packet(1,window_req_offer=1,window_req_ready=0,window_req_take=1),'take=offer replaces take=offer&&ready'),
        ('replace_selection',replay,packet(2,ckv_available=1,ckv_select_accept=1),'selection accepted during old replay lifetime')]
    records=[]
    for name,state,bad,mutation in cases:
        before=repr(state)
        try: observe(state,bad)
        except ValueError as exc:
            assert repr(state)==before
            records.append(dict(name=name,mutated_packet_decimal=str(bad),input_state=before,mutation=mutation,verdict='EXPECTED_REJECTION_BEFORE_MUTATION',diagnostic=str(exc)))
        else: raise AssertionError('negative control survived: '+name)
    return records


def record(repo):
    repo=Path(repo); directory=repo/EVIDENCE
    prior=json.loads((directory/'hook_authority.json').read_text())
    for path,sha in prior['source_sha256'].items():
        data=subprocess.check_output(['git','show',prep.SOURCE+':'+path],cwd=repo)
        assert hashlib.sha256(data).hexdigest()==sha
    copy=(repo/prep.COPY).read_text()
    assert prep.inverse(copy)==prep.original(repo)
    plan=json.loads((directory/'source_plan.json').read_text())
    plan['preflight'].update(simulation_packet_bits=prep.BITS,observer_register_bits=prep.BITS+65,packed_bytes_per_rank=(prep.BITS+7)//8,four_rank_bytes_per_sample=4*((prep.BITS+7)//8))
    plan['model_preflight_scope']='Observer host/simulation state only; no engine/primitives or synthesized block introduced; unified hardware model unchanged. No FPGA/ASIC area, boundary routing, fanout or token latency credit.'
    plan['preflight']['api_ledger_limits']={'window_native_serial_requests_per_active_stack':1,'ckv_native_slots_available':64,'ckv_native_sectors_per_slot':9,'ckv_request_keys_max_derived':576,'ckv_stack_in_identity':True,'caution':'576 counts source slot/sector allocation, not proven outstanding transport bound. Python object overhead unmeasured; no retention of payloads or unbounded cycle trace required.'}
    plan['future_compile_prerequisites']=['Parent go/no-go and measured host headroom within stated caps.','Prove exact hierarchy elaboration and pre/post-edge cycle agreement using future generated class; not established by fake harness.','CKV mode requires existing die transport and producer bindings supplied by a reviewed test wrapper configuration; current default remains CKV_SELECTED0.','Actual native DMA issued/got/poison and reset/selection drain fences needed before any reply causal_certificate may be admitted.']
    (directory/'source_plan_final.json').write_text(json.dumps(plan,indent=2)+'\n')
    results=dict(status='FAKE_HARNESS_ONLY_NO_HIERARCHY_ELABORATION',python=sys.version,platform=platform.platform(),source_commit=prep.SOURCE,negative_controls=controls(),tests='python -m pytest -q tests/test_simulation_observation_wrapper.py',product_liveness='BOUND_MISSING',deadlines_admitted=0,full_build_run=False,live_getter_selected=False,engine_edits=False)
    (directory/'validation.json').write_text(json.dumps(results,indent=2)+'\n')
    paths=[prep.COPY,'tools/prepare_simulation_observation_wrapper.py','tools/simulation_observation_api.py','tools/record_simulation_observation_wrapper.py','tests/test_simulation_observation_wrapper.py']
    paths += [str(p.relative_to(repo)) for p in sorted(directory.iterdir()) if p.name!='artifact_sha256.json']
    hashes={path:hashlib.sha256((repo/path).read_bytes()).hexdigest() for path in paths}
    (directory/'artifact_sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    return results

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--repo',default='.');args=ap.parse_args()
    print(json.dumps(record(args.repo),indent=2))

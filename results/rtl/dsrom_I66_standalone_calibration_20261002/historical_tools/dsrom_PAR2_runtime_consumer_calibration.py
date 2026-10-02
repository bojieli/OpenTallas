#!/usr/bin/env python3
"""Additive I66 completion model: source NBA transitions, original FAIL immutable."""
import collections,json,shutil
from pathlib import Path
import dsrom_PAR2_runtime_consumer_observer as O
M=O.M
ROOT=O.ROOT
B=ROOT/'rtl/test/dsrom_PAR2_runtime_consumer_calibration'
OUT=ROOT/'results/rtl/dsrom_PAR2_runtime_consumer_calibration_20261002'
PRIOR=O.OUT/'preparation_r1'

def completion_edges(root_events, rows, upstream_idle):
    """Sample old debt/state, commit new debt/state after each source edge."""
    returns=collections.Counter(x['edge'] for x in root_events)
    debt=rows;spine_idle=False;adapter_idle=False;trace=[]
    for edge in range(max(returns)+10):
        old_debt=debt;old_spine=spine_idle;old_adapter=adapter_idle
        if old_spine and not old_adapter:adapter_idle=True
        if old_debt==0 and edge>=upstream_idle:spine_idle=True
        debt-=returns[edge]
        if debt<0:raise ValueError('excess returns')
        if edge>=min(returns):trace.append(dict(edge=edge,rows_left_pre=old_debt,returns=returns[edge],rows_left_post=debt,spine_idle_pre=old_spine,adapter_idle_pre=old_adapter))
        if old_adapter:return next(x['edge'] for x in trace if x['spine_idle_pre']),edge,trace
    raise ValueError('retirement absent')

def observe_completion(samples):
    accepted=False;busy=False
    for edge,phase_accept,spine_idle in samples:
        accepted|=phase_accept
        busy|=accepted and not spine_idle
        if accepted and busy and spine_idle:return edge
    return None

def source_contract():
    spine=(O.B/'pinned/rtl/v41die/ot_v41_spine_w17w10.sv').read_text()
    adapter=(O.B/'pinned/rtl/v41die/ot_v41_rom_adapt.sv').read_text()
    assert "else rows_left <= rows_left - 19'($countones(r_v));" in spine
    assert "S_RUN: if (rows_left == 19'd0 && !sm_run && !ld_run) begin" in spine
    assert "st <= S_IDLE; phase_cycles <= cyc;" in spine
    assert "S_WAIT: if (!s_go && s_idle) st <= S_IDLE;" in adapter
    assert 'assign idle = st == S_IDLE && s_idle;' in adapter
    return {p:M.sha(O.B/'pinned'/p) for p in ['rtl/v41die/ot_v41_spine_w17w10.sv','rtl/v41die/ot_v41_rom_adapt.sv']}

def prepare(out):
    source=source_contract();shutil.copytree(PRIOR,out)
    model=json.loads((out/'prediction.json').read_text())
    roots=[json.loads(l) for l in (out/'root_prediction.jsonl').read_text().splitlines()]
    upstream=[json.loads(l) for l in (out/'upstream_prediction.jsonl').read_text().splitlines()]
    # Last native streamer advance commits sm_run=0; loader is already off.
    # This conservative source-idle bound precedes every root return.
    upstream_idle=max(x['edge'] for x in upstream)+1
    si,ai,trace=completion_edges(roots,model['prediction_counts']['root_rows'],upstream_idle)
    model['schema']='opentallas.dsrom.PAR2.current-native-consumer-calibration.v2'
    model['absolute_edges'].update(spine_idle_preedge=si,adapter_retire_preedge=ai)
    model['completion_source_contract']=dict(source_sha256=source,upstream_idle_bound=upstream_idle,rule='S_RUN tests old rows_left; adapter S_WAIT tests old s_idle; preedge observations follow committed NBA state',observer_rule='phase accepted AND spine busy observed before subsequent idle')
    model['prior_prediction_sha256']=M.sha(PRIOR/'prediction.json')
    model['new_host_sha256']=M.sha(B/'host.cpp')
    model['hardware_changes']=False
    (out/'prediction.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
    (out/'retirement_prediction.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in trace))
    return model

def expected(preparation):
    old=O.expected(preparation)
    model=json.loads((Path(preparation)/'prediction.json').read_text())
    return [x for x in old if x[0] not in ('spine_idle','phase_retire')]+[('spine_idle',model['absolute_edges']['spine_idle_preedge'],-1,-1),('phase_retire',model['absolute_edges']['adapter_retire_preedge'],-1,-1)]

def compare(preparation,events):
    # Existing comparator uses its expected() lookup; no parser/identity waiver.
    prior=O.expected
    wanted=expected(preparation)
    try:
        O.expected=lambda _:wanted
        return O.compare(preparation,events)
    finally:O.expected=prior

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--prepare',type=Path,required=True)
    print(json.dumps(prepare(p.parse_args().prepare)['absolute_edges'],sort_keys=True))

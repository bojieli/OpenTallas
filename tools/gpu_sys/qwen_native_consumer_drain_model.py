"""Prospective finite native consumer/drain bridge in the unified SM model.

No operator arithmetic and no supplied latency is promoted to SS/FF evidence.
"""
import gzip
import hashlib
import json
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[2]
SOURCE='results/uarch/h3_complete_native_calendar_20261002/inputs/Qwen_native.json.gz'
COHORTS=('stage','payload_request','payload_return','metadata','RF_commonACK',
         'consumer','request_CDC','reverse_CDC')


def source_join(root=ROOT):
    raw=(Path(root)/SOURCE).read_bytes()
    p=json.loads(gzip.decompress(raw))
    rows=[]
    for o in p['operations']:
        if o['opcode'] not in ('SCORES','PV'):continue
        src=p['source_program']['instructions'][o['pc']]
        import re
        m=re.match(r'L(\d+)\.d([01])\.',src['inputs'][1])
        if not m:raise ValueError('actual KV source operand')
        layer,rank=map(int,m.groups());stage=int(o['opcode']=='PV')
        if o['pc']!=48*layer+13+16*rank+2*stage:raise ValueError('literal native PC map')
        if o['recipe'][-1].get('op')!='CONSUMER_DONE' or o['recipe'][-1].get('stage')!=o['opcode']:
            raise ValueError('source terminal consumer point')
        rows.append(dict(pc=o['pc'],layer=layer,rank=rank,stage=stage,
                         input_version=o['reads'][1],output_version=o['writes'][0],
                         events=src['event_ids']))
    if len(rows)!=144 or len({(r['layer'],r['rank'],r['stage']) for r in rows})!=144:
        raise ValueError('all36layers/two ranks/SCORES+PV')
    return dict(path=SOURCE,sha256=hashlib.sha256(raw).hexdigest(),operators=rows)


def unified_constant(name):
    # Read literal constants from the actual unified model without importing its
    # unrelated graph elaborators. Refuse computed/missing values.
    source=(ROOT/'tools/uarch_model.py').read_text()
    for node in ast.parse(source).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('missing unified model constant '+name)


def model():
    # Existing KV controller retains the 72 reader rows and SCORE-before-PV masks.
    # One serial native full-operator context per rank, not another reader table.
    native_bits=64+64+11+5+1+64+20+1
    raw_bits=native_bits+3+64+20+8+8+1+1
    words=(raw_bits+63)//64
    comparator_bits=2*native_bits+8*(64+20)
    mux_bits=raw_bits*2
    gates=words*1536+comparator_bits*5+mux_bits*4+1024
    body=words*72*unified_constant('DFF_UM2')+gates*.0648
    return dict(schema='qwen-native-consumer-drain-r1',source=source_join(),
        replicas_per_rank=1,ranks=2,SMs_per_rank=32,existing_reader_table_reused=True,
        native_context_bits=native_bits,raw_bits=raw_bits,protected_words=words,
        protected_FF_bits=words*72,new_payload_bytes=0,new_SRAM_macros=0,MACs_per_cycle=0,
        port_bytes_per_cycle=0,compute_and_communication='identity/control only; no arithmetic/payload port',
        boundaries_bits=dict(native_accept=native_bits,native_completion=native_bits,
            native_reverse=native_bits,KV_consumer=84+3,drain_request=84+8,
            cohort_request=8*(84+1),cohort_response=8*(84+2),drain_done=84+8),
        ports=dict(native_context_write=1,native_completion_match=1,native_reverse_match=1,
                   drain_context_write=1,cohort_response_match_parallel=8,cohort_status_write_parallel=8),
        mux_demux=dict(state_mux_bits=mux_bits,comparison_bits=comparator_bits,
            drain_identity_fanout=8,shared_state_write_router='single composed next-state six coded words'),
        NAND_equivalent_allowance_ASSUMED=gates,cell_mm2_ASSUMED=body/1e6,
        footprint_mm2_50pct_ASSUMED=2*body/1e6,
        both_ranks_mm2_50pct_ASSUMED=4*body/1e6,
        tracks=dict(new_control_signal_bits=sum((native_bits*3,87,92,680,688,92)),
            channel_capacity=None,route_fit=False,
            placement='one controller-local bridge per rank; eight actual endpoint taps retained until drain release'),
        clock=dict(domain='same streaming clock as actual lifecycle controller',prospective_period_ns=1/1.2,
            setup_uncertainty_ps=unified_constant('UNCERTAINTY_PS'),hold_uncertainty_ps=25,SSFF=False,
            CDC='no new CDC inserted; request/reverse CDC cohorts supplied by actual existing CDC endpoints'),
        latency=dict(native_accept_to_context_edges=1,completion_capture_edges=1,
            reverse_capture_edges=1,consumer_handshake_edges=1,
            drain_request_edges=1,endpoint_response_capture_edges=1,drain_done_edges=1,
            consumer_after_later_completion_reverse_min_edges=1,
            drain_after_last_actual_endpoint_min_edges=1,
            eligibility_and_endpoint_wait='actual backpressure; no time-based completion or finite bound invented',
            paid_calendar_event_keys=['native-context-accept','native-output-capture','native-reverse-capture',
                'KV-consumer-handshake','KV-drain-request','eight-endpoint-request-response','KV-drain-done'],
            single_user_added_edges_no_contention=4+3,
            per_token_native_pairs=144,per_token_reader_drains=72,
            bridge_serial_control_edges_upper_when_all_eligible=144*4+72*3,
            same_edges_ns_ASSUMED=(144*4+72*3)/1.2,
            whole_token=None,physical_rate_qualified=False),
        source_binding='actual opPC.issue/result_visible/credit_return, not a primitive or partial PC40 fragment; real reader lease tuple',
        admission='functional source component only; enclosing actual endpoint and full calendar joins remain required')

if __name__=='__main__':print(json.dumps(model(),sort_keys=True,indent=2))

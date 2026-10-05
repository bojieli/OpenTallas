#!/usr/bin/env python3
"""Finite expert dispatch costs; consumes Ram geometry, never searches geometry."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import w17_integer_expert_residency as R
ROOT=R.ROOT
GEOMETRY='results/quality/w16_w17_geometry_search_20261001/search.json'
OUT='results/uarch/w16_expert_dispatch_costs_20261001'
FIELDS=('registered_route_ticks_per_hop','forward_CDC_ticks','reverse_CDC_ticks','consumer_remainder_ticks','source_arbitration_ticks','return_visibility_ticks')


def calculate(candidate,service):
    d=candidate['dispatch_sensitivity']
    if (d['replicas'],d['proposed_bits_per_replica_source_cycle'],d['request_bits_per_rank'],d['return_bits_per_rank'])!=(4,256,81920,20480):
        raise ValueError('actual rank-link payload/width mapping drift')
    known=candidate['per_expert_cfg_plus_stream_partial_cycles']*40*6+d['source_order_six_expert_worst_linear_dispatch_serialization_cycles']
    result=dict(known_conditional_partial_fabric_cycles=known,known_conditional_partial_ns=str(Fraction(known*5,6)),
        scope='Config/stream issue plus serialization components only; no complete operator bound.',
        packet_buffer_data_bits_per_rank_hop=dict(request=81920,return_packet=20480),
        simultaneous_TP4_request_plus_return_buffer_bytes_per_hop=51200,
        missing_inputs=[],complete_dispatch_bound_ticks=None,validated_progress_bound=False,physical_admission=False,engine_RTL_build_ready=False,headline_rate=None)
    for f in FIELDS:
        x=service.get(f)
        if type(x) is not int or x<0 or (x==0 and service.get('zero_proved',{}).get(f) is not True):result['missing_inputs'].append(f)
    for f in ('request_queue_data_bits_per_rank_hop','return_queue_data_bits_per_rank_hop'):
        if type(service.get(f)) is not int:result['missing_inputs'].append(f)
    if result['missing_inputs']:
        result['status']='BLOCKED_FINITE_OPERATOR_INPUTS';return result
    if service['request_queue_data_bits_per_rank_hop']<81920 or service['return_queue_data_bits_per_rank_hop']<20480:
        raise ValueError('wholepacket capacity insufficient')
    if service.get('request_and_return_share_only_one_credit') is not False:raise ValueError('held request credit blocks return packet; deadlock')
    trace=[];time=0
    for layer in candidate['layer_dispatch_distances']:
        hops=layer['maximum_distance_from_first_owner']+d['dedicated_hub_to_first_expert_extra_hop']
        for selected in range(6):
            start=time+service['source_arbitration_ticks']
            arrival=start+hops*(320*3+service['registered_route_ticks_per_hop'])+service['forward_CDC_ticks']
            consumer=arrival+candidate['per_expert_cfg_plus_stream_partial_cycles']*3+service['consumer_remainder_ticks']
            done=consumer+hops*(80*3+service['registered_route_ticks_per_hop'])+service['reverse_CDC_ticks']+service['return_visibility_ticks']
            # Four rank packets and four links:320cycles/rank, not80cycles/rank.
            credit=R.price_hop(81920*4,256,4,hops,service['registered_route_ticks_per_hop'],service['forward_CDC_ticks'],consumer-start,done-consumer)
            if credit['packet_credit_release_tick']+start!=done:raise ValueError('credit timeline drift')
            trace.append(dict(layer=layer['layer'],selected_index=selected,hops=hops,request_start_tick=start,
                request_arrival_tick=arrival,consumer_done_tick=consumer,response_visible_and_request_credit_release_tick=done))
            time=done
    result.update(status='CONDITIONAL_FINITE_DISPATCH_NOT_QUALIFIED',complete_dispatch_bound_ticks=time,
        conditional_dispatch_ns=str(Fraction(time*5,18)),trace=trace,
        source_destination_progress_qualified=service.get('source_destination_progress_qualified') is True,
        missing_physical_caps=['allocated link/queue metadata and SRAM area','actual route tracks/PHY','complete consumer/RF/bank service','SS/FF clocks wake/drain','whole nonexpert/collective/KV program'])
    return result


def build(service,commit=None):
    commit=commit or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    g=json.loads((ROOT/GEOMETRY).read_text());candidate=next(c for c in g['candidates'] if c['q_pairs']==1024)
    for p in g['source_pins'].values():
        raw=subprocess.check_output(['git','show',p['commit']+':'+p['path']],cwd=ROOT)
        if hashlib.sha256(raw).hexdigest()!=p['sha256']:raise ValueError('geometry source pin drift')
    paths=[GEOMETRY,'tools/w17_integer_expert_residency.py','tools/w16_expert_dispatch_costs.py']
    return dict(schema='opentallas.w16.expert-dispatch-cost.v1',evidence_commit=commit,
        source_pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        geometry_owner='Ram 01a0f697-9c82-7572-8900-dd7b15d59ebf',q_pairs=1024,
        expert_only_stages=candidate['expert_only_physical_stages'],product_stage_count=None,service_inputs=service,
        dispatch=calculate(candidate,service),CPUwalltime_used=False,engine_RTL_build_ready=False,physical_admission=False,full_token_cycles=None)


def check(r):
    for p,h in r['source_pins'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('source drift '+p)
    raw=subprocess.check_output(['git','show',r['evidence_commit']+':tools/w16_expert_dispatch_costs.py'],cwd=ROOT)
    if hashlib.sha256(raw).hexdigest()!=r['source_pins']['tools/w16_expert_dispatch_costs.py']:raise ValueError('committed source drift')
    if build(r['service_inputs'],r['evidence_commit'])!=r:raise ValueError('finite dispatch replay drift')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);m=ap.add_mutually_exclusive_group(required=True)
    m.add_argument('--service',type=Path);m.add_argument('--check',type=Path);ap.add_argument('--out',type=Path);a=ap.parse_args()
    if a.check:r=json.loads(a.check.read_text());check(r)
    else:
        if a.out is None:ap.error('--service requires --out')
        r=build(json.loads(a.service.read_text()));a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(r['dispatch']['status'])

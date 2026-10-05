#!/usr/bin/env python3
"""Two distinct lower bounds: source topology, and fixed recorded lease work."""
import argparse
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/qwen_rom_kv_stall_attribution_20261002'

def build():
    trace=OUT/'model-r3.json';m=json.loads(trace.read_text())
    original=ROOT/'results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json'
    old=json.loads(original.read_text());budget=F(1,3000);extra=F(str(old['calendar']['extra_nonlayer_compute_s']))
    def integer_work(value):
        if int(value)!=value:raise ValueError('expected integral service lease ps')
        return F(int(value))
    group_work=sum(max(integer_work(v) for v in r['diagnostic']['measured_group_lease_work_ps'].values()) for r in m['rows'])
    global_work=sum(sum(integer_work(v) for v in r['diagnostic']['measured_group_lease_work_ps'].values()) for r in m['rows'])
    group_floor=group_work/16/10**12+extra;global_floor=global_work/128/10**12+extra
    group_min=math.ceil(group_work/10**12/(budget-extra));global_min=math.ceil(global_work/10**12/(budget-extra))
    if group_min!=17 or global_min!=129:raise ValueError('frozen minimal credit requirement changed')
    # Optimistic source port/causal relaxation. Two-stage windows, sequential
    #layers, retained cold21, allocator3, request10/link39, provider25/raw3,
    #owner12/response39; no erase of retained service latency.
    first_data=F(139000) # ps, including3 arbiter edges; phase rounding relaxed.
    first_complete_cohort=first_data+16000 #16 DATA slots/stack for initial K cohort.
    period=F(2500,3);rest=F(7671900,3);prefix=F(1127500,3)
    fillcounts=old['dimensioning']['successor_fill_counts_per_layer']
    t=F(0);compute=F(0);windows=[F(0)]*2;boundrows=[]
    for layer in range(36):
        begin=max(t,windows[layer%2]);prefix_end=compute+prefix
        #Cohort barrier retained: all16 sectors arrive before its first fill.
        fill=begin+first_complete_cohort+4*period+max(fillcounts)*period+period
        owner_count=max(max(st) for st in m['rows'][layer]['diagnostic']['owner_group_slots_per_stack'])
        t=max(begin+first_data+owner_count*1000,fill+F(39*2500,3)+1000)
        compute=max(fill,prefix_end)+rest;windows[layer%2]=max(t,compute)
        boundrows.append(dict(layer=layer,begin_ps=float(begin),fill_lower_ps=float(fill),grant_lower_ps=float(t),compute_lower_ps=float(compute)))
    topology_floor=(max(t,compute)/10**12)+extra
    wall={};pc={}
    for row in m['rows']:
        for k,v in row['diagnostic']['allocator_exclusive_wait_ps'].items():wall[k]=wall.get(k,0)+v
        for k,v in row['diagnostic']['PC_overlapping_wait_edges'].items():pc[k]=pc.get(k,0)+v
    credit_wall=sum(v for k,v in wall.items() if 'credit' in k)
    # Standalone lower bounds overlap; recorded maintenance count cannot be
    #inserted into the general topology recurrence as a universal minimum.
    return dict(schema='qrom-same-topology-and-fixed-lease-bounds.v1',trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
        frozen_calendar_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),target_s=float(budget),
        source_port_bounds=m['lower_bounds'],optimistic_same_topology_causal_floor_s=float(topology_floor),
        topology_causal_lower_rows=boundrows,
        topology_scope='Source ports/cold21/lookup12/links/whole-cohort first-fill fence/two windows/36 sequential layers retained. Relaxed bank/refresh/deadline/producer constraints only weaken this lower bound; it does not prove8/4/7 feasible.',
        fixed_lease=dict(group16_full_token_floor_s=float(group_floor),global128_full_token_floor_s=float(global_floor),
            maximum_group_work_sum_ps=int(group_work),global_lease_work_sum_ps=int(global_work),
            minimum_uniform_group_credits=group_min,minimum_global_credits=global_min,
            group17_floor_if_lifetimes_unchanged_s=float(group_work/17/10**12+extra),
            scope='Little law / area under occupancy: sum(cohort retirement-allocation)<=credits*span. Apply independently to each group/layer, sum sequentiallayer spans, add known nonlayer cost once. Fixed recorded lifetimes, not universal lower bound under another ordering or earlier per-beat retirement.',
            necessary_change='Current16/group and128global cannot sustain the recorded lease work within333.333us. Change credit circulation: increase finite capacity or reduce source-valid lease holds; no additional fill/column/owner port is implied.'),
        wait_attribution=dict(allocator_interval_start_signatures_ps=wall,credit_blocked_wall_s=credit_wall/1e12,
            request_only_wall_s=wall.get('request_allocator_II1',0)/1e12,final_drain_wall_s=wall.get('final_drain_no_unissued_heads',0)/1e12,
            signature_scope='Mixed labels describe interval-start blockers; request_II1 may expire before a credit wait ends. Credit state persists until the next retirement event. Signature durations partition allocator wall time; do not add mixed categories twice.',
            overlapping_PC_wait_edges=pc,PC_scope='Sum over4stacks/128PCs/columns; not token critical-path duration. Older reserved work separated from actual5-edge feedback; refresh debt may propagate into older-work waits.'),
        ONE_next_target=dict(change='Regular credit-window sizing17/group; prove end-to-end service with finite spill rather than add transport lanes.',
            group_credits=17,regular_total_cohort_capacity=136,global_necessary_bound=129,
            pending_entries_per_PC=68,existing_pending_return_RAM_entries=64,additional_FF_spill_entries_per_PC=4,
            words_per_group_lane_pool=85,group_lane_pools=56,total_assembly_words=4760,
            source_context_RAM_entries_per_PC=128,needed_context_records_per_PC_at_most=17,
            no_context_macro_replication=True,return_groups_per_stack=8,column_paths_per_stack=4,global_fill_lanes=7,
            write_slots_per_PC=4,lookup_edges=12,source_tag_namespace_copied=False,
            proof='17cohorts/group*<=4sectors/PC/cohort=68 combined pending. 17*<=5words/group/lane=85 slots. Source context128 records/PC can hold17 burst contexts; context records are not per-sector pending slots. Eight identical17-cohort banks require136 physical header slots;129 is only the pooled fixed-work minimum.',
            qualification='Necessary fixed-work sizing only. Larger windows change queueing and refresh, so17 is not a fit prediction.68 spill/protection/1R1W selection/collectors/route/CDC and source-active tag/update/ACK must be fully priced and replayed before any build.'),
        PHY_qualified=False,actual_production_policy_bound=False,hardware=False,adopted_rate=None,
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--result',type=Path,required=True);a=ap.parse_args()
    with a.result.open('x') as f:json.dump(build(),f,indent=2);f.write('\n')

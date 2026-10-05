#!/usr/bin/env python3
"""Compose the ONE Ampere-joined replay and scoped credit/traffic bounds."""
import argparse
import copy
import hashlib
import json
import math
from fractions import Fraction as F
from uarch_model_qwen_kv_beat_retirement import ROOT,OUT,A,P

def build():
    path=OUT/'model-r2.json';m=copy.deepcopy(json.loads(path.read_text()));b=m['bounds']
    read=F(str(b['optimistic_perbeat_causal_quarantine_s']))
    write=read-F(7*P,3)/10**12 # writes have no destination-word fill dependency
    groupwork=F(0)
    for layer in range(36):
        weighted=[]
        for g in range(8):
            c=A.GroupCursor(layer,g);w=F(0)
            while c.head is not None:
                w+=write if c.head[0] in ('KW','VW') else read;c.advance()
            weighted.append(w)
        groupwork+=max(weighted)
    b['optimistic_read_causal_quarantine_s']=float(read)
    b['optimistic_write_causal_quarantine_s']=float(write)
    b['causal_group_credit_scope']='Read and LEN1 write minima separately weighted through actual source group cursors. Bank/cold/refresh/arbitration relaxed. Every live tag still quarantines until consumed ACKs and reader drain. Necessary occupancy floor only, not capacity sufficiency.'
    port=b['source_port_lower_bounds'];extra=F(3164*2500,3)/10**12
    for rate,t in b['targets'].items():
        budget=F(1,int(rate))-extra;t['causal_group_credit_lower']=math.ceil(groupwork/budget)
        t['fill_lane_necessary_ideal_only']=t.pop('fill_lane_necessary')
        t['fill_port_scope']='Equivalent throughput relative to the unchanged modulo7 partition.6 at3k is ideal-only; the existing complete composition requires7.13/18 at historical rates are necessary capacity equivalents, not a selected new partition.'
        t['minimum_fill_traffic_pressure_avoided_fraction']=max(0,1-float(budget)/port['fill_demand_port_s'])
        t['minimum_owner_receipt_pressure_avoided_fraction']=max(0,1-float(budget)/port['owner_DATA_plus_GRANT_port_s'])
        t['minimum_column_payload_pressure_avoided_fraction']=max(0,1-float(budget)/port['column_payload_only_port_s'])
        t['traffic_avoidance_scope']='Necessary only with unchanged ports and known nonlayer cost. Source policy must avoid actual transfers/receipts, not hide them in compute. Existing8191 tail/Vforward savings already included; no additional resident/reuse traffic credit presumed.'
    old=json.loads((ROOT/'results/uarch/qwen_rom_kv_stall_attribution_20261002/bound-contract-r1.json').read_text())
    rows=m['calendar']['rows'];lease=sum(sum(r['group_lease_work_ps'].values()) for r in rows)
    m['causal_attribution']=dict(optimistic_read_hold_ns=float(read*1e9),optimistic_write_hold_ns=float(write*1e9),
        observed_mean_full_cohort_lease_ns=lease/(36*2084)/1000,
        old_recorded_global_cohort_lease_work_ps=old['fixed_lease']['global_lease_work_sum_ps'],new_recorded_global_cohort_lease_work_ps=lease,
        raw_hold_to_final_grant_removed_ps=sum(r['removed_raw_wait_to_final_grant_ps'] for r in rows),
        reverse_dispatch_queue_wait_ps=sum(r['queued_reverse_wait_ps'] for r in rows),
        counters_scope='Sums over many overlapping beats/cohorts/groups; not additive single-token delays. Raw credits release on accepted captured copies. Cohort/tag credit still requires every matching ACK and reader drain. The optimistic source minima cannot be subtracted from observed wall time as independent costs.',
        new_lifetimes_scope='Perword dispatch changes command/refresh ordering. Recorded new lease bounds only; no promise17wouldfit and no capacity tuning.',
        copy_reader_scope='Calendar retains one capture edge, four registered selectors plus Ampere predicate, masked write and visibility fence. Local copy reader is drained by visibility; tile-window reader ownership remains through priced compute/two-window reuse. Actual observed reader/journal binding missing.',
        actual_producer_release_reuse_bound=False)
    m['schema']='qrom-one-Ampere-joined-causal-composition.v1'
    m['status']='REJECT_MODEL_GAIN_LT1PERCENT_AND_3K_FAIL_PHYSICAL_PRODUCTION_OPEN'
    m['completed_replay_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    m['causal_journal_sha256']=hashlib.sha256((OUT/'causal-journal-r2.jsonl.gz').read_bytes()).hexdigest()
    m['historical_source']={'path':'results/uarch/qwen_rom_kv_beat_retirement_20261003/inputs/historical-model.md','lines':[706,707],
        'explanation':'8460 analytical SS row includes KV_PREP/droop/preramp;6222 adds old RTLbody1.0923 and991cycle allreduces. These historical8K rows are not the current finite physical coldKV-service admission. Current3338layer/71AR source composition replaces existing KV/HBM debit once.'}
    m['implementation_composition_sha256']=hashlib.sha256(__import__('pathlib').Path(__file__).read_bytes()).hexdigest()
    return m

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--result',type=__import__('pathlib').Path,required=True);a=p.parse_args()
    with a.result.open('x') as f:json.dump(build(),f,indent=2);f.write('\n')

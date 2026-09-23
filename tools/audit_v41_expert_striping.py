#!/usr/bin/env python3
"""Static unbatched expert striping tradeoff; partial service, not token forecast."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def service(shards, local_TB_s=4.5, link_GB_s=400, one_way_us=.5,
            multicast=False, expert_bytes=18800640, hidden=5120,
            selected=6, layers=40):
    if shards < 1 or 2304 % shards or min(local_TB_s,link_GB_s) <= 0 or one_way_us < 0:
        raise ValueError('Invalid shard geometry or service')
    # Six experts on disjoint shard sets: best placement. Gate/up partition by
    # intermediate rows, down by matching K. The down result needs reduction.
    active=selected*shards
    reads=layers*expert_bytes/(shards*local_TB_s*1e6)
    dispatch=hidden*2*(1 if multicast else active)
    returns=hidden*4*active
    serial=layers*(dispatch+returns)/(link_GB_s*1000)
    fixed=layers*2*one_way_us
    return {'shards_per_expert':shards,'active_chips_for_six_disjoint_experts':active,
            'local_delivered_TB_s_per_chip':local_TB_s,
            'source_multicast':multicast,
            'dispatch_bytes_per_layer':dispatch,'fp32_partial_return_bytes_per_layer':returns,
            'expert_weight_read_us':reads,'endpoint_serialization_us':serial,
            'fixed_fabric_us':fixed,
            'nonoverlapped_read_plus_fabric_us':reads+serial+fixed,
            'optimistic_read_fabric_overlap_floor_us':max(reads,serial+fixed)}


def main():
    names=['configs/models/candidates/deepseek-v4.1-flash.json',
           'compiler/models/deepseek-v4.1-flash/inference_config.json',
           'tools/audit_v41_expert_striping.py']
    m,c=[json.loads((ROOT/n).read_text()) for n in names[:2]]
    assert (c['dim'],c['moe_inter_dim'],c['n_activated_experts'],c['n_layers'])==(5120,2304,6,40)
    eb=m['routed_weight_bytes']//m['num_experts']//m['num_layers']
    cases=[]
    for bw in (4.5,18,72):
        for multicast in (False,True):
            rows=[service(s,bw,multicast=multicast,expert_bytes=eb) for s in (1,2,4,8,16)]
            cases.append({'local_service_sensitivity_TB_s':bw,'source_multicast':multicast,
                          'rows':rows,'minimum_partial_service_shards':min(rows,key=lambda r:r['nonoverlapped_read_plus_fabric_us'])['shards_per_expert']})
    out={'schema':'opentallas.v41-expert-striping.v1',
         'status':'conditional_partial_service_tradeoff_not_physical_system_selection',
         'cases':cases,
         'fixed_inputs':{'delivered_endpoint_GB_s_per_direction':400,'one_way_fixed_us':.5},
         'limits':[
             'Per-expert intermediate-axis striping keeps gate/up nonlinear products local; down K partition creates a partial-result reduction.',
             'Six selected experts use disjoint shard sets. Concentrated/shared-chip routes can increase read time and contention; no replication or placement capacity is proven.',
             'Returns are FP32 for all rows including one shard for a controlled format comparison; BF16 one-shard expert output could reduce bytes separately.',
             'Native partial arithmetic, activation quantization, routing-weight placement, rounding and merge association require qualification. No semantic equivalence is assumed.',
             'Nonoverlapped number prices only weight reads plus dispatch/return. Compute and reduction arithmetic, scale work, dense paths, KV and control are omitted.',
             'Max(read,fabric) is an optimistic overlap floor; it is not a constructed overlap schedule.',
             '18 and 72 TB/s are sensitivity values, not qualified ROM rates; 4.5 TB/s is the existing assumed HBM delivered rate.',
             'Multicast removes source duplication but not leaf bytes or the growing partial returns. No in-network reduction is credited.',
             'Endpoint model serializes source fanout and merge ingress, with no other traffic or packet overhead. Distributed collectives can differ.',
             'Sharding optimizes a partial service component only; its optimum is not a chosen complete system configuration.'],
         'input_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}}
    (ROOT/'results/architecture/v41_expert_striping.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    for c in cases:
        print(c['local_service_sensitivity_TB_s'],c['source_multicast'],[(r['shards_per_expert'],round(r['nonoverlapped_read_plus_fabric_us'],3)) for r in c['rows']])


if __name__=='__main__':main()

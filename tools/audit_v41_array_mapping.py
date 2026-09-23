#!/usr/bin/env python3
"""Explicit stage/island ROM capacity map and route concentration bounds."""
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def mapping(chips, shards, layers_per_stage, rom_payload, layer_dense, expert_bytes,
            experts=384, selected=6, local_TB_s=4.5):
    layers=len(layer_dense)
    if layers % layers_per_stage or 2304 % shards:
        raise ValueError('Whole layers and native intermediate partitions required')
    stages=layers//layers_per_stage
    islands_per_stage=chips//(stages*shards)
    if islands_per_stage < 1 or islands_per_stage > experts:
        return None
    max_experts=math.ceil(experts/islands_per_stage)
    # Balanced expert-ID islands; each expert striped over every chip in its
    # island. The same island partition owns each layer in its stage.
    stage_peak=[]
    for start in range(0,layers,layers_per_stage):
        dense=sum(layer_dense[start:start+layers_per_stage])
        stage_peak.append(math.ceil(layers_per_stage*max_experts*expert_bytes/shards)
                          + math.ceil(dense/(islands_per_stage*shards)))
    best=math.ceil(selected/min(islands_per_stage,selected))
    worst=min(selected,max_experts)
    return {'chips':chips,'shards_per_island':shards,'layers_per_stage':layers_per_stage,
            'stages':stages,'expert_islands_per_stage':islands_per_stage,
            'used_backbone_chips':stages*islands_per_stage*shards,
            'max_experts_per_layer_per_island':max_experts,
            'max_backbone_bytes_per_chip':max(stage_peak),
            'rom_payload_per_chip':rom_payload,'backbone_capacity_fits':max(stage_peak)<=rom_payload,
            'best_route_experts_per_hot_island':best,'worst_route_experts_per_hot_island':worst,
            'expert_read_us_best_route':layers*best*expert_bytes/(shards*local_TB_s*1e6),
            'expert_read_us_worst_route':layers*worst*expert_bytes/(shards*local_TB_s*1e6),
            'six_disjoint_selected_islands_possible':islands_per_stage>=selected}


def main():
    names=['configs/models/candidates/deepseek-v4.1-flash.json',
           'configs/models/candidates/deepseek-v4.1-flash-engram_hbm.json',
           'configs/architecture/rom_hbm_review_v3.json','tools/audit_v41_array_mapping.py']
    m,h,c=[json.loads((ROOT/n).read_text()) for n in names[:3]]
    eb=m['routed_weight_bytes']//m['num_layers']//m['num_experts']
    rows=[]
    for chips,area in [(80,500),(120,400)]:
        payload=math.floor(area*c['rom_bytes_per_mm2_assumed']*(1-c['rom_reserved_fraction']))
        for shards in (1,2,4,8,16):
            for depth in (1,2,4,8,20,40):
                r=mapping(chips,shards,depth,payload,m['layer_dense_weight_bytes'],eb)
                if r is not None:
                    r['rom_area_per_chip_mm2']=area
                    r['total_hybrid_inventory_fits_aggregate_capacity']=chips*payload>=h['checkpoint_bytes']
                    rows.append(r)
    out={'schema':'opentallas.v41-array-mapping.v1','status':'byte_mapping_and_service_sensitivity_not_physical_feasibility',
         'rows':rows,'local_TB_s_sensitivity':4.5,
         'limits':['4.5TB/s prices the same map with the existing HBM assumption; it is not a ROM macro rate. All times scale inversely with local service.',
                   'Within each stage, expert IDs are balanced over islands, each expert striped over island chips. Every stage layer uses that partition.',
                   'Dense bytes are ideally divisible among stage chips. Shape constraints, replicas, alignment and executable operator placement may increase the peak.',
                   'Aggregate hybrid capacity includes head/draft/resident inventory; per-chip placement of those remaining objects is not proven.',
                   'Backbone capacity fit does not establish compute/SRAM/PHY area, macro ports, power or package feasibility.',
                   'Routing extremes are analytic, not probabilities. Six disjoint islands possible does not guarantee a route selects six islands.',
                   'More layers per stage can improve single-token active-chip reach but shares compute across those layers and changes concurrent pipeline throughput.',
                   'No fabric, compute, cache hits, KV or other service included in expert read numbers; no whole-token speed claim.'],
         'input_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}}
    (ROOT/'results/architecture/v41_array_mapping.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    for r in rows:
        if r['chips']==80 and r['shards_per_island']==4:
            print(json.dumps(r))


if __name__=='__main__':main()

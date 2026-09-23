#!/usr/bin/env python3
"""Capacity-constrained local-layer placements and expert service ceilings."""
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def expert_read_floor(chips, expert_bytes=18800640, selected=6, experts=384,
                      layers=40, delivered_bytes_s=4.5e12):
    if not 1 <= chips <= experts or delivered_bytes_s <= 0:
        raise ValueError('Invalid placement or service')
    # Each expert wholly on one chip; balanced expert-ID partition, no replicas.
    best=math.ceil(selected/min(chips,selected))
    worst=min(selected,math.ceil(experts/chips))
    return {'chips_owning_layer':chips,'best_max_selected_experts_on_one_chip':best,
            'worst_max_selected_experts_on_one_chip':worst,
            'expert_only_read_floor_us_best_route':layers*best*expert_bytes/delivered_bytes_s*1e6,
            'expert_only_read_floor_us_concentrated_route':layers*worst*expert_bytes/delivered_bytes_s*1e6}


def layer_placement(dense_bytes, experts, expert_bytes, payload):
    for chips in range(1,experts+1):
        # Dense inventory evenly divisible in this screen; no replicas. Whole
        # experts do not split. Largest owner determines the fit.
        peak=math.ceil(experts/chips)*expert_bytes+math.ceil(dense_bytes/chips)
        if peak <= payload:
            return {'chips':chips,'max_occupied_bytes_per_chip':peak,
                    'layer_bytes':dense_bytes+experts*expert_bytes,
                    'layer_reserved_payload_bytes':chips*payload}
    raise ValueError('No whole-expert placement fits')


def main():
    names=['configs/models/candidates/deepseek-v4.1-flash.json',
           'configs/models/candidates/deepseek-v4.1-flash-engram_hbm.json',
           'configs/architecture/rom_hbm_review_v3.json',
           'tools/audit_v41_layer_local_arrays.py']
    m,h,c=[json.loads((ROOT/n).read_text()) for n in names[:3]]
    e=m['num_experts']; eb=m['routed_weight_bytes']//m['num_layers']//e
    placements=[]
    for rom_area in (300,400,500):
        payload=math.floor(rom_area*c['rom_bytes_per_mm2_assumed']*(1-c['rom_reserved_fraction']))
        rows=[layer_placement(d,e,eb,payload) for d in m['layer_dense_weight_bytes']]
        occupied=sum(r['layer_bytes'] for r in rows)
        chips=sum(r['chips'] for r in rows)
        spare=chips*payload-occupied
        other=h['checkpoint_bytes']-occupied
        extra=math.ceil(max(0,other-spare)/payload)
        placements.append({'rom_area_per_815mm2_chip':rom_area,'payload_per_chip':payload,
                           'chips_per_layer':[r['chips'] for r in rows],
                           'layer_dedicated_chips':chips,
                           'remaining_hybrid_inventory_bytes':other,
                           'layer_chip_spare_payload_bytes':spare,
                           'additional_chips_if_other_inventory_perfectly_packed':extra,
                           'total_chips_capacity_screen':chips+extra,
                           'total_die_area_mm2':(chips+extra)*815,
                           'non_rom_area_per_chip_before_other_overheads_mm2':815-rom_area})
    out={'schema':'opentallas.v41-layer-local-arrays.v1',
         'status':'capacity_placement_screen_and_conditional_expert_read_ceiling',
         'placements':placements,
         'hbm_whole_expert_placement_sweep':[expert_read_floor(n,eb) for n in (1,2,3,6,8,16,32,64,84,384)],
         'service_scaling':'Multiply reported HBM times by 4.5e12 / actual per-chip delivered bytes/s for the same unstriped uncached placement. ROM service cannot be inferred from HBM bandwidth.',
         'limits':['Layer-dedicated means each chip owns backbone tensors of one layer; other retained inventory may occupy spare bytes without service proof.',
                   'Dense bytes are evenly partitionable in this capacity screen; operator grouping, bank alignment, replication and topology may require more chips.',
                   'ROM areas leave a fixed remainder, not a proof that compute/SRAM/PHY/power fit. No chip count is selected.',
                   'Engram remains external with its capacity, service, links and energy separately charged.',
                   'HBM expert bounds are local bandwidth bounds with all chips in a layer reading concurrently, no cache, no inter-token reuse, no expert tensor sharding, and sequential layers.',
                   'Dense and attention work, numerical recurrence, communication and control are omitted, so reciprocal read floors are only conditional speed ceilings.',
                   'Tensor striping or replicas can reduce hot-chip load but change capacity, traffic and numerical reduction requirements. Routing cannot be changed for load balancing without model qualification.',
                   'These are feasible byte assignments under the stated packing assumptions, not physically qualified machines.'],
         'input_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}}
    (ROOT/'results/architecture/v41_layer_local_arrays.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    for r in placements: print(r['rom_area_per_815mm2_chip'],r['layer_dedicated_chips'],r['total_chips_capacity_screen'],r['total_die_area_mm2'],sorted(set(r['chips_per_layer'])))
    for r in out['hbm_whole_expert_placement_sweep']:print(r)


if __name__=='__main__':main()

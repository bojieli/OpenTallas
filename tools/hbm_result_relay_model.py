#!/usr/bin/env python3
"""Size the fixed-stream HBM result relay before stage RTL or physical builds."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATHS='results/uarch/hbm_result_relay_stage_20261007/result_paths.json'

def hbm_result_relay_stage_model():
    p=json.loads((ROOT/PATHS).read_text());rows=p['result_leaves']
    if len(rows)!=32 or any('latency_cycles' not in r for r in rows):
        raise ValueError('complete32leafpath model required')
    if p['optimistic_cut_capacity']['overflow_cuts']:
        raise ValueError('result-only optimistic corridor capacity failed')
    for r in rows:
        if sorted(i for g in r['groups'] for i in g['bit_indices'])!=list(range(270)):
            raise ValueError('result identity map is incomplete')
    depth=max(r['latency_cycles']for r in rows)
    slices=sum(len(r['groups'])for r in rows)
    replicas=slices*depth
    return dict(schema='opentallas.hbm_result_relay_stage_model.v1',default_off=True,selected=False,
        target='DeepSeek HBM actual32SM result leaves; not a Qwen or full-die adoption',
        source_path_model=PATHS,flow='unconditional fixed stream; no ready, credits or receive queues',
        logical_payload='rv1+rrow12+rdata256+fault1 in unchanged packed bit order',
        MACs_per_cycle=0,compute_intensity=0,memory_port_bytes_per_cycle=0,
        boundary_bits_per_cycle_per_leaf=270,total_leaf_bits_per_cycle=32*270,
        payload_bytes_per_cycle_per_leaf=270/8,
        physical_hardened_slice_bits=64,slices_per_die_per_stage=slices,
        station_replica_count=replicas,balanced_latency_cycles=depth,
        period_ps=1000000/1200,transport_latency_ps_per_traversal=depth*1000000/1200,
        token_traversal_count=None,token_latency_ps=None,
        useful_payload_register_bits=32*270*depth,
        physical_register_bits=64*replicas,padding_register_bits=replicas*64-32*270*depth,
        padding_routing='unused hardmacro inputs tied locally; no extra payload tracks across die',
        mux_inputs_per_bit=0,demux_outputs_per_bit=0,clock_fanout_per_slice=64,reset_fanout_per_slice=64,
        physical_pin_count=130,planned_macro_shapes=['EW d/q on opposing M4 faces','NS d/q on opposing M5 faces'],
        assumed_slot_width_um=20,assumed_slot_height_um=20,slot_area_um2=400,
        total_reserved_station_slot_area_um2=replicas*400,
        reserved_endpoint_slot_area_um2=p['endpoint_area_um2'],
        standard_cell_area_um2=None,area_utilization_target=.55,maximum_cell_area_for_slot_um2=220,
        routed_slot_fit='OPEN:20x20is reservation, not measured hardened size',
        required_payload_tracks_per_slice=max(len(g['bit_indices'])for r in rows for g in r['groups']),
        capacity_scope='zero overflow for result-only optimistic3layer cuts; othertraffic, PDN and clock remain unbound',
        context_clock='streaming833.333ps,SS60pssetup/FF25pshold; regionalarrival, load, slew andIO budgets pending',
        primitive_screening='a route under provisional IO is screening only, even ifSS/FF>=15ps andDRC0',
        energy_pJ_per_traversal=None,
        required_gates=['actual64bitEW/NS stageRTL and exact measured dimensions/pins match physicalreservation',
          'all270bits andall six spatial slices preserve identities/reset/latency; miswire/skew/fault-drop negatives',
          'intermediate and balancing hardmacro locations legalized with clock/reset,PDN andothertraffic',
          'source-pinned routed SS>=15ps/FF>=15ps,DRC0 under actualclock/interfacebudgets',
          'full logicalgather andcontrol joins preserve originalclock/order; compose actualtoken traversalcounts andenergy'])

if __name__=='__main__':print(json.dumps(hbm_result_relay_stage_model(),indent=2))

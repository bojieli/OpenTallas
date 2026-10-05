#!/usr/bin/env python3
"""Add source row-spine/collector wire costs to the ONE completed17 replay."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from uarch_model_qwen_kv_credit17 import ROOT,OUT

def build():
    path=OUT/'model-r2.json';base=json.loads(path.read_text());out=copy.deepcopy(base)
    context_path=ROOT/'results/uarch/qwen_rom_parent_context_service_20261002/model-r7.json'
    context=json.loads(context_path.read_text());wire=context['wire']
    policy_path=ROOT/'results/uarch/qwen_rom_current_reset_construction_20261002/inputs/model.json'
    policy=json.loads(policy_path.read_text())['corridor']
    w=wire['grid_w_um']/64;h=wire['grid_h_um']/24;lanes=[]
    for lane in range(7):
        horizontal=sum(max(t%64 for t in range(r*64,(r+1)*64) if t%7==lane)*w for r in range(24))
        lanes.append((23*h+horizontal)*1048)
    collector_um=base['cells']['clock_reset_collector_increment']*32
    cap_per_um=wire['nominal_cap_fF']/wire['total_allocated_um']
    fill_total=sum(lanes)
    out['schema']='qrom-composed-one17-credit-successor.v1'
    out['status']='FAIL_FINITE_3K_AND_1PERCENT_SCREEN_PHYSICAL_PRODUCTION_OPEN'
    out['completed_calendar_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    out['routing_cost']=dict(grid_columns=64,grid_rows=24,grid_w_um=wire['grid_w_um'],grid_h_um=wire['grid_h_um'],
        source_policy_corridor_um=policy['width_um'],source_policy_layer_capacity=policy['capacity_by_layer'],
        source_signal_capacity_tracks=sum(policy['capacity_by_layer'].values()),required_fill_control_tracks=7973,
        fill_control_track_deficit=7973-sum(policy['capacity_by_layer'].values()),
        seven_fill_wire_um_by_lane=lanes,seven_fill_total_wire_um=fill_total,
        existing_seven_fill_wire_recharged_as_credit_delta=False,
        added_clock_reset_collector_wire_um=collector_um,collector_segment_um=32,
        collector_segment_scope='Inherited local32um collector allocation recipe, not routed SS/FF wire proof.',
        nominal_signal_cap_fF_per_um=cap_per_um,nominal_signal_resistance_ohm_per_um=wire['nominal_resistance_ohm_per_um'],
        seven_fill_nominal_cap_fF=fill_total*cap_per_um,added_collector_nominal_cap_fF=collector_um*cap_per_um,
        fill_mesh_source='Inherited row-spine/modulo7 tile partition. Exactly1536 destinations; no additional lane.',
        local_spill_RAM_join_bits_per_PC=base['cuts']['local_RAM_spill_select_bundle_bits_per_PC'],
        local_assembly_read_bits_per_pool=base['cuts']['local_85word_pool_read_bundle_bits'],
        protected_status_boundary_bits=base['cuts']['global_boundary_reserved_bits'],
        root_to_actual_shoreline_group_PC_pool_lengths_um=None,local_spill_and_pool_pin_routes_um=None,
        loaded_wire_buffer_hold_via_PG_area_mm2=None,actual_clock_reset_CDC_delay_s=None,
        nominal_RC_is_extracted=False,separate_legal_channels_allocated=False,
        uniform_widening_selected=False,
        route_cost_scope='Known wire volume/capacity/nominalRC allocation and collector cells priced. Loaded route/CTS/reset/CDC/hold/PG/OBS costs require Ampere named placement/channel receipt; unknowns are not zero and block full admission. Metal length/capacitance is not added as die area.')
    out['admission']['blockers'].append('Known shared-corridor deficit6613tracks; separate legal channel/PHY/loaded route costs missing')
    out['source_join_inputs_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (context_path,policy_path)}
    out['implementation_sha256']['tools/qwen_rom_kv_credit17_compose.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--result',type=Path,required=True);a=ap.parse_args()
    with a.result.open('x') as f:json.dump(build(),f,indent=2);f.write('\n')

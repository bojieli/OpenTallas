#!/usr/bin/env python3
"""Conditional synchronous branch/drain reservation; no physical reuse credit."""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
from tools.w10_engram_192_power import read,typed_inputs,block

def build(c,prior,power,clock,area):
    s=c['control_storage'];g=c['synchronous_branch'];rows=[]
    extra=sum(s['per_home_roles'].values());nand=g['nodes_per_home']*g['conditional_gate_recipe_per_branch']['NAND2_equivalent']
    if extra!=s['per_home_total'] or extra*s['homes']!=s['added_register_bits']:raise ValueError('role inventory mismatch')
    if nand*s['homes']!=g['conditional_branch_NAND2_equivalent_total']:raise ValueError('gate mismatch')
    if prior['aggregate_FF_bits']!=s['prior_all_E32_FF_preserved']:raise ValueError('prior source mismatch')
    cs=power['conservative_coefficients'];hz=D('1.2e9');cv=hz*D('.77')**2*D('1e-15')
    gate={'NAND2_cells_per_home':nand,'leakage_upper_W':str(nand*D(cs['nand']['leakage_W'])),
      'data_internal_full_activity_upper_W':str(nand*D(cs['nand']['internal_cycle_fJ'])*hz*D('1e-15')),
      'data_input_pin_full_activity_upper_W':str(nand*D(cs['nand']['input_cap_fF'])*cv),
      'output_load_ceiling_W':str(nand*D(cs['nand']['output_load_ceiling_fF'])*cv),
      'area_at_fixed50pct_mm2':str(nand*D(area['palette']['nand']['area_um2'])/D('.5e6'))}
    for r in prior['homes']:
        h=r['source_state'];p=block(h['total_storage_FF_bits']+extra,h['preserved_response_MUX2_bits']+h['request_demux_AND2_bits']//2,h['actual_macros'],power,clock,area)
        static=D(p['ungated_clock_W'])+D(p['all_state_leakage_upper_W'])+D(gate['leakage_upper_W'])
        rows.append({'home_id':h['home_id'],'prior_FF_bits':h['total_storage_FF_bits'],'added_FF_roles':s['per_home_roles'],'priced_FF_feedback_prior_cones':p,'additional_branch_gates':gate,'clock_plus_all_leak_W':str(static),'margin_before_data_hub_PHY_W':str(D('474.56')-static)})
    total=sum(r['priced_FF_feedback_prior_cones']['FF_bits'] for r in rows)
    if total!=s['conditional_total_register_bits']:raise ValueError('total mismatch')
    return {'schema':'w10_engram_sync_branch_drain_typed_v1','homes':rows,'conditional_total_FF_bits':total,'added_FF_bits':s['added_register_bits'],'additional_branch_NAND2_cells':g['conditional_branch_NAND2_equivalent_total'],
      'all192_ungated_clock_W':str(sum(D(r['priced_FF_feedback_prior_cones']['ungated_clock_W']) for r in rows)),
      'all192_leakage_upper_W':str(sum(D(r['priced_FF_feedback_prior_cones']['all_state_leakage_upper_W'])+D(gate['leakage_upper_W']) for r in rows)),
      'conditional_branch_data_scope':'Both input pins/all arc compatible full activity upper and output maxcap ceiling. Not selected token data or actual load/power; disabled cones never zeroed.',
      'clock_scope':c['clock_binding'],'missing_actual_bindings':c['missing_actual_bindings'],
      'reservation_is_minimum':False,'complete_inventory':False,'actual_power_qualified':False,'physical_admission':False,'selected_data_qualified':False,'historical_power_subtraction_W':0,'root_stop_credit':0,
      'prior_depth2_reservation_superseded_as_actual_measurement':False,'whole_token_latency_cycles':None,
      'verdict':'CONDITIONAL_SYNC_BRANCH_DRAIN_TYPED_RESERVATION_WITH_UNBOUND_ENDPOINT_RESET_CDC_GATE_ACTIVITY_FIT'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--libs',default='/home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1');p.add_argument('--output',required=True);a=p.parse_args()
    c,cp=read('5b8c456a34965043ae9c6656725ca0565a5ce905','results/quality/w16_engram_rom_constructive_home_20261001/sync_branch_drain_inventory.json')
    prior,pp=read('e3a1a53db','results/uarch/w10_engram_epoch32_power_r1/budget.json')
    power,clock,area,pins,sources=typed_inputs(Path(a.libs));x=build(c,prior,power,clock,area)
    x['source_pins']={'branch_drain':cp,'prior_E32':pp,**pins};x['typed_HQN_library_sha256']=sources
    Path(a.output).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()

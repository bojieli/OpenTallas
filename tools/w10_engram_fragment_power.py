#!/usr/bin/env python3
"""Conditional serialized inventory: all endpoint clocks, no selected-path credit."""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
from tools.w10_engram_192_power import read, typed_inputs, block

def build(c,power,clock,area):
    if len(c['homes'])!=192:raise ValueError('incomplete homes')
    rows=[]
    for h in c['homes']:
        if h['held_feedback_MUX2_bits']!=h['total_storage_FF_bits']:raise ValueError('feedback omitted')
        if h['new_fragment_reassembly_and_control_FF_bits']!=c['response_hop_endpoint_count_per_home']*c['new_state_per_response_hop_bits']:raise ValueError('selected-path inventory is forbidden')
        if h['total_storage_FF_bits']!=h['preserved_prior_FF_bits']+h['new_fragment_reassembly_and_control_FF_bits']:raise ValueError('old state removed')
        demux=h['request_demux_AND2_bits']
        if demux%2:raise ValueError('noninteger AND conversion')
        p=block(h['total_storage_FF_bits'],h['preserved_response_MUX2_bits']+demux//2,h['actual_macros'],power,clock,area)
        static=D(p['ungated_clock_W'])+D(p['all_state_leakage_upper_W'])
        rows.append({'home_id':h['home_id'],'actual_macros':h['actual_macros'],'prior_FF_bits':h['preserved_prior_FF_bits'],'new_FF_bits':h['new_fragment_reassembly_and_control_FF_bits'],'priced_reservation':p,'clock_plus_leak_W':str(static),'margin_before_data_hub_PHY_W':str(D('474.56')-static)})
    ff=sum(h['priced_reservation']['FF_bits'] for h in rows)
    if ff!=c['aggregate_total_storage_FF_bits']:raise ValueError('aggregate mismatch')
    return {'schema':'w10_engram_fragment_ungated_reservation_v1','homes':rows,'aggregate_FF_bits':ff,'aggregate_new_FF_bits':sum(h['new_FF_bits'] for h in rows),'actual_macros':sum(h['actual_macros'] for h in rows),'all192_ungated_clock_W':str(sum(D(h['priced_reservation']['ungated_clock_W']) for h in rows)),'all192_leakage_upper_W':str(sum(D(h['priced_reservation']['all_state_leakage_upper_W']) for h in rows)),
      'inventory_scope':'ca5a consumed-once correction, 318 new FF at every physical endpoint; provisional epoch8/tag24 only, not full32 identity or actual lowering.',
      'clock_rule':'All macro and old/new FF clocks continuously1.2GHz. Conditional integer CTS and wire guard retained. No CE/rootstop/selected-path clock credit.',
      'candidate_tracks':c['packet']['total_cut_tracks'],'candidate_margin_tracks':c['packet']['margin_tracks'],'max_conditional_row_cycles':c['timing']['max_local_row_cycles'],
      'source_software_words':c['software_gate']['roundtrip_words'],'source_software_mutants':c['software_gate']['negative_mutant_rejections'],
      'selected_data_energy_qualified':False,'actual_power_qualified':False,'physical_admission':False,'root_stop_credit':0,'historical_power_subtraction_W':0,
      'missing':['full32 generation/image identity and setup/distribution state','actual ACK wire protocol and drained reuse','new fragment/control selected data and disabled pin event lowering','allport escape/CTS/PG/PHY/CRC/site fit/contextualSSFF/IR','whole-token composed schedule and actual signalRC'],
      'verdict':'PROVISIONAL_FINITE_ALL_ENDPOINT_RESERVATION_NO_PHYSICAL_ADMISSION_NO_MINIMUM_POWER_CLAIM'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--libs',default='/home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1');p.add_argument('--output',required=True);a=p.parse_args()
    c,cp=read('ca5a444d0934833f2e9f16096cb368fadab16aee','results/quality/w16_engram_rom_constructive_home_20261001/two_fragment_contract_consumed_once.json')
    power,clock,area,pins,sources=typed_inputs(Path(a.libs));x=build(c,power,clock,area)
    x['source_pins']={'fragment_contract':cp,**pins};x['typed_HQN_library_sha256']=sources
    Path(a.output).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()

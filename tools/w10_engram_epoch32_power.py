#!/usr/bin/env python3
"""FullE32 candidate typed reservation, preserving all prior inventory."""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
from tools.w10_engram_192_power import read,typed_inputs,block

def build(c,power,clock,area):
    s=c['state_inventory'];rows=[]
    if len(s['homes'])!=192:raise ValueError('incomplete home inventory')
    for h in s['homes']:
        if h['request_setup_FF_bits']!=s['all_physical_hop_endpoints_per_home']*s['new_request_state_bits_per_hop']:raise ValueError('missing request setup')
        if h['response_E32_reassembly_FF_bits']!=s['all_physical_hop_endpoints_per_home']*s['new_response_state_bits_per_hop']:raise ValueError('missing response state')
        state=sum(h[k] for k in ('preserved_prior_FF_bits','request_setup_FF_bits','response_E32_reassembly_FF_bits','new_home_image_session_FF_bits','new_root_rowlease_FF_bits'))
        if state!=h['total_storage_FF_bits'] or state!=h['feedback_MUX2_bits']:raise ValueError('state/feedback mismatch')
        demux=h['request_demux_AND2_bits']
        if demux%2:raise ValueError('AND conversion mismatch')
        p=block(state,h['preserved_response_MUX2_bits']+demux//2,h['actual_macros'],power,clock,area)
        static=D(p['ungated_clock_W'])+D(p['all_state_leakage_upper_W'])
        rows.append({'home_id':h['home_id'],'source_state':h,'priced_reservation':p,'clock_plus_leak_W':str(static),'margin_before_data_control_hub_PHY_W':str(D('474.56')-static)})
    if sum(r['priced_reservation']['FF_bits'] for r in rows)!=s['aggregate_FF_bits']:raise ValueError('aggregate mismatch')
    if sum(r['source_state']['actual_macros'] for r in rows)!=1500067:raise ValueError('macro inventory mismatch')
    return {'schema':'w10_engram_epoch32_typed_reservation_v1','homes':rows,'aggregate_FF_bits':s['aggregate_FF_bits'],'all192_ungated_clock_W':str(sum(D(r['priced_reservation']['ungated_clock_W']) for r in rows)),'all192_leakage_upper_W':str(sum(D(r['priced_reservation']['all_state_leakage_upper_W']) for r in rows)),
      'actual_macros':1500067,'historical_power_subtraction_W':0,'root_stop_credit':0,'macro_CE_clock_credit_W':0,
      'all_old_FF_retained':s['all_old_FF_retained'],'image_session_row_state_FF_bits':s['all_image_session_row_state_FF_bits'],
      'fullE32_setup_and_fourphase_ACK_actual_provider':False,'selected_data_energy_qualified':False,'actual_power_qualified':False,'physical_admission':False,
      'clock_rule':s['clocks'],'whole_token_latency_cycles':None,'whole_token_average_power_W':None,
      'source_software_gate':c['gate'],'source_candidate_tracks':c['response']['cut_tracks'],
      'missing':c['admission_blockers']+['Selected serialized data and disabled NAND/MUX raw pin events; startup/reset/globaldrain activity','Actual RC/enable fanout and package/IR; allport escape/PG/CTS/site fit; contextualSSFF'],
      'verdict':'FINITE_TYPED_FULL_E32_STORAGE_RESERVATION_NOT_COMPLETE_POWER_OR_PHYSICAL_ADMISSION_NOT_ACTUAL_MINIMUM'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--libs',default='/home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1');p.add_argument('--output',required=True);a=p.parse_args()
    c,cp=read('9ef36f6542cc91b1a48ff274101372d063c580ef','results/quality/w16_engram_rom_constructive_home_20261001/epoch32_fragment_contract.json')
    power,clock,area,pins,sources=typed_inputs(Path(a.libs));x=build(c,power,clock,area)
    x['source_pins']={'epoch32_contract':cp,**pins};x['typed_HQN_library_sha256']=sources
    Path(a.output).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()

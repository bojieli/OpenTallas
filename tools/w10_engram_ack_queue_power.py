#!/usr/bin/env python3
"""Provisional ACK queues: recompute full typed inventory, never transfer margin."""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
from tools.w10_engram_192_power import read,typed_inputs,block

def build(c,prior,power,clock,area):
    s=c['proposed_capture_storage'];rows=[]
    extra=s['depth']*(s['entry_tag_bits']+s['entry_level_bits'])+s['queue_pointer_occupancy_bits']
    if extra!=s['extra_FF_per_hop']:raise ValueError('ACK recipe mismatch')
    if prior['aggregate_FF_bits']!=s['prior_FF_total']:raise ValueError('stale prior state')
    if len(prior['homes'])!=s['homes']:raise ValueError('missing homes')
    new=s['paired_hops_per_home']*extra
    for r in prior['homes']:
        h=r['source_state'];ff=h['total_storage_FF_bits']+new
        p=block(ff,h['preserved_response_MUX2_bits']+h['request_demux_AND2_bits']//2,h['actual_macros'],power,clock,area)
        static=D(p['ungated_clock_W'])+D(p['all_state_leakage_upper_W'])
        rows.append({'home_id':h['home_id'],'prior_FF_bits':h['total_storage_FF_bits'],'ACK_queue_extra_FF_bits':new,'priced_reservation':p,'clock_plus_leak_W':str(static),'margin_before_other_costs_W':str(D('474.56')-static)})
    total=sum(r['priced_reservation']['FF_bits'] for r in rows)
    if total!=s['new_provisional_FF_total'] or new*len(rows)!=s['extra_FF_total']:raise ValueError('aggregate mismatch')
    return {'schema':'w10_engram_ack_queue_typed_reservation_v1','homes':rows,'aggregate_provisional_FF_bits':total,'aggregate_ACK_extra_FF_bits':s['extra_FF_total'],'all192_ungated_clock_W':str(sum(D(r['priced_reservation']['ungated_clock_W']) for r in rows)),'all192_leakage_upper_W':str(sum(D(r['priced_reservation']['all_state_leakage_upper_W']) for r in rows)),
      'historical_power_subtraction_W':0,'root_stop_credit':0,'macro_CE_clock_credit_W':0,'physical_admission':False,'actual_power_qualified':False,'complete_state_inventory':False,'actual_ACK_transport_provider':False,
      'exclusions':s['exclusions'],'source_software_gate':c['gate'],'whole_token_latency_cycles':None,'whole_token_average_power_W':None,
      'verdict':'PROVISIONAL_ACK_QUEUE_STORAGE_RESERVATION_WITH_INCOMPLETE_ENDPOINT_CDC_RESET_GATE_DATA_PHY_IR_TIMING_BUDGET_NOT_MINIMUM_POWER'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--libs',default='/home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1');p.add_argument('--output',required=True);a=p.parse_args()
    c,cp=read('ddc93f3789ef2b3b7d1313a5512797334a3a3f3f','results/quality/w16_engram_rom_constructive_home_20261001/epoch32_ACK_source_receipts.json')
    prior,pp=read('e3a1a53db','results/uarch/w10_engram_epoch32_power_r1/budget.json')
    power,clock,area,pins,sources=typed_inputs(Path(a.libs));x=build(c,prior,power,clock,area)
    x['source_pins']={'ACK_contract':cp,'prior_E32':pp,**pins};x['typed_HQN_library_sha256']=sources
    Path(a.output).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()

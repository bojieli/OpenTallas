#!/usr/bin/env python3
"""Conditional warm selected-path demand; clocks remain fully ungated."""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
from tools.w10_engram_192_power import typed_inputs, block, read

def budget(contract,power,clock,area):
    b=contract['finite_runtime_transition_bounds_per_lookup'];n=13;nodes=8191
    request=b['request_register_payload_and_valid_bit_transitions_upper']
    response=b['response_register_bit_transitions_upper']
    copies=b['request_selected_path_register_copies_upper']
    if copies!=b['response_selected_path_register_copies_upper']:raise ValueError('asymmetric source path')
    ff_events=copies*(request+response)+b['macro_and_tag_capture_bit_transitions_upper']+b['one_packet_slot_write_bit_transitions_upper']+b['root_control_upper_accepted_bit_write_events']
    # Nine accepted writes (eight beats plus valid-clear) per plane. At
    # most two enable transitions per accepted write, including stalls.
    enable_events=copies*(51+288)*18+298*18+2*b['one_packet_slot_write_bit_transitions_upper']+2*b['root_control_upper_accepted_bit_write_events']
    # A four-NAND feedback mux has <=3 raw NAND input events per data
    # transition, <=6 per enable transition. Count each propagating input
    # separately; the output may glitch even when its logical value holds.
    feedback_pin_events=3*ff_events+6*enable_events
    demux_enable_events=2*n*51*18
    demux_pin_events=3*(b['both_child_request_demux_raw_input_bit_transitions_upper']+demux_enable_events)
    selected_mux_pin_events=3*b['selected_response_MUX_raw_input_bit_transitions_upper']+6*n*288*2
    disabled_feedback_D_events=b['inactive_request_sibling_raw_input_bit_transitions_upper']
    # Holding Q does not isolate the disabled NAND/MUX D pin. Charge
    # this separately even where candidate demux masking may suppress it.
    nand_events=feedback_pin_events+demux_pin_events+selected_mux_pin_events+disabled_feedback_D_events
    ff_D_raw_events=ff_events+2*enable_events
    cs=power['conservative_coefficients'];v2=D('.77')**2;fJ=D('1e-15')
    ffE=max(D(clock['compatible_event_proof'][c]['storage']['event_cycle_fJ']['D']) for c in ('SS','TT','FF'))
    ffC=max(D(power['corner_coefficients'][c]['storage']['pins']['D']['cap_fF']) for c in ('SS','TT','FF'))
    # Full both-pin rise+fall cycle energy per single raw pin transition
    # intentionally overbounds all actual NAND states and event polarity.
    nandE=D(cs['nand']['internal_cycle_fJ']);nandC=D(cs['nand']['input_cap_fF'])
    internal=(ff_D_raw_events*ffE+nand_events*nandE)*fJ
    pin=(ff_D_raw_events*ffC+nand_events*nandC+b['macro_addr_pin_transitions_upper']*D('.6837')+b['macro_CE_transitions_upper']*D('.6837'))*v2*fJ
    output=(ff_events*D(cs['storage']['output_load_ceiling_fF'])+nand_events*D(cs['nand']['output_load_ceiling_fF'])+b['macro_output_bit_transitions_upper']*D('46.08'))*v2*fJ
    control=block(2*nodes,0,0,power,clock,area)
    control_data=sum(D(control[k]) for k in ('data_internal_upper_W','data_input_pin_upper_W','unresolved_output_load_ceiling_W'))
    # The node state is already in every home clock inventory. Price only
    # its data here; do not add a duplicate clock tree or subtract TT power.
    rows=[]
    for h in contract['homes']:
        p=block(h['total_storage_FF_bits'],h['response_MUX2_bits']+h['request_demux_AND2_bits']//2,h['actual_macros'],power,clock,area)
        rows.append({'home_id':h['home_id'],'actual_macros':h['actual_macros'],'FF_bits':h['total_storage_FF_bits'],
                     'ungated_clock_W':p['ungated_clock_W'],'leakage_upper_W':p['all_state_leakage_upper_W']})
    return {'schema':'w10_engram_conditional_selected_data_v1','repacked_home_clock_inventory':rows,
      'aggregate_FF_bits':sum(h['FF_bits'] for h in rows),
      'all192_ungated_clock_W':str(sum(D(h['ungated_clock_W']) for h in rows)),
      'per_lookup_event_counts':{'registered_state_bit_transitions_upper':ff_events,'enable_bit_transitions_upper':enable_events,
        'disabled_sibling_demux_included':True,
        'both_child_demux_raw_input_events':b['both_child_request_demux_raw_input_bit_transitions_upper'],
        'feedback_NAND_raw_input_events':feedback_pin_events,
        'demux_NAND_raw_input_events':demux_pin_events,
        'selected_response_MUX_NAND_raw_input_events':selected_mux_pin_events,
        'disabled_feedback_MUX_D_raw_input_events':disabled_feedback_D_events,'NAND_raw_input_events_upper':nand_events,'FF_D_raw_events_including_mux_hazards_upper':ff_D_raw_events},
      'per_lookup_data_energy_allocation_J':{'internal':str(internal),'input_pin':str(pin),
        'all_output_load_ceiling':str(output),'total_including_ceiling':str(internal+pin+output)},
      'all48_lookup_event_energy_allocation_J':str(48*(internal+pin+output)),
      'per_home_control_state_full_activity_data_upper_W':str(control_data),
      'control_state_clock_counted_once':True,'all_macro_clock_internal_energy_retained':True,
      'unpriced':['enable-mask driver fanout/local buffers','descriptor/ready qualification and reset/epoch distribution','actual pin/wire/glitch/peakIR','PHY/CRC/reassembly and twofragment route repair'],
      'conditional_scope':'Warm initialized held-mask candidate only. Source c8 states no actual tree/provider. Node control data fullactivity1 charged separately, not zero. Unknown ACK time still incurs full clocks and control demand; no token-rate or averaging credit.',
      'existing_route_gate':'FAIL_341_TRACKS_EXCEEDS_321; source is eight fullwidth responses, NOT sixteen serialized fragments.',
      'serialized_256_model_data_qualified':False,'physical_data_provider_proven':False,'physical_admission':False,
      'whole_token_average_power_W':None,'root_stop_credit':0,
      'verdict':'CONDITIONAL_MODEL_EVENT_ALLOCATION_WITH_OPEN_FANOUT_RESET_ROUTE_GATES'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--libs',default='/home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1');p.add_argument('--output',required=True);a=p.parse_args()
    contract,cp=read('c8ea5395d','results/quality/w16_engram_rom_constructive_home_20261001/repacked_192_enable_mask_contract.json')
    power,clock,area,pins,sources=typed_inputs(Path(a.libs));x=budget(contract,power,clock,area)
    x['source_pins']={'mask_contract':cp,**pins};x['typed_HQN_library_sha256']=sources
    Path(a.output).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()

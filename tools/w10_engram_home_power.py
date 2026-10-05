#!/usr/bin/env python3
"""Finite ungated Engram home power join, before accepting any area screen."""
import argparse
import copy
import re
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
from tools.w10_crom_control_reservation import block, read
from tools.w10_q_power_envelope import coefficients
from tools.w10_liberty_event_energy import events

def build(candidate,inventory,power,clock,area):
    variant=candidate['variants']['planning_75Mbit']
    treeFF=variant['base_tree_FF_bits_per_home']+variant['extra_wire_FF_bits_per_home']
    hold={h['home_id']:h for h in inventory['homes']}
    mux=variant['response_mux2_bit_equivalents_per_home']
    demux=variant['request_demux_gate_bit_equivalents_per_home']
    if len(candidate['homes'])!=96 or sum(h['actual_macros'] for h in candidate['homes'])!=1500067:raise ValueError('incomplete home inventory')
    rows=[]
    for h in candidate['homes']:
        i=hold[h['home_id']];capture=i['macro_and_tag_capture_FF_bits']
        if capture!=h['actual_macros']*298:raise ValueError('macro/tag capture mismatch')
        # Two NAND2 per request AND2, four per response/feedback MUX2:
        # a finite Boolean construction, not measured mapped cells.
        priced=block(i['total_storage_FF_bits'],mux+demux//2,h['actual_macros'],power,clock,area)
        if demux%2:raise ValueError('AND2 conversion requires integral model')
        if priced['total_NAND2_cells'] != i['feedback_and_select_NAND2_if_four_per_MUX2']+i['request_demux_NAND2_if_two_per_AND2']:raise ValueError('held-state NAND inventory mismatch')
        clk=D(priced['ungated_clock_W']);leak=D(priced['all_state_leakage_upper_W'])
        rows.append({'home_id':h['home_id'],'source_layer':h['layer'],'source_column':h['column'],
          'macros':h['actual_macros'],'tree_wire_FF_bits':treeFF,'macro_tag_capture_FF_bits':capture,
          'request_demux_gate_bit_equivalents':demux,'response_MUX2_bits':mux,
          'ungated_priced_reservation':priced,
          'static_clock_leak_W':str(clk+leak),
          'margin_after_ungated_clock_leak_W':str(D('474.56')-clk-leak),
          'conditional_data_pin_internal_clock_leak_W':str(clk+leak+D(priced['data_internal_upper_W'])+D(priced['data_input_pin_upper_W'])),
          'clock_or_data_physical_minimum_claim':False,'physical_admission':False})
    total={k:str(sum(D(r['ungated_priced_reservation'][k]) for r in rows)) for k in
           ('ungated_clock_W','all_state_leakage_upper_W','data_internal_upper_W','data_input_pin_upper_W','unresolved_output_load_ceiling_W')}
    return {'schema':'w10_engram_ungated_home_power_v1','homes':rows,'all96_component_totals_W':total,
      'actual_macro_count':1500067,'all_tree_wire_FF_bits':treeFF*96,
      'all_macro_tag_capture_FF_bits':sum(i['macro_and_tag_capture_FF_bits'] for i in inventory['homes']),
      'all_storage_FF_bits':sum(i['total_storage_FF_bits'] for i in inventory['homes']),
      'storage_cell_type':'DFFHQNx1_ASAP7_75t_R',
      'storage_clock_reset_scope':'PlainHQN typed CLK/D/leak, no ASRHQN substitution. Reset/valid lowering not qualified; additional reset implementation remains unpriced/noadmission.',
      'macro_leakage_component_W':str(1500067*D(power['conservative_coefficients']['macro']['leakage_W'])),
      'frequency_Hz':'1200000000','clock_rule':'All96 home clocks, all declared FFs and all macros ungated;24active homes does not reduce clock cost.',
      'data_rule':'Worstactivity1 construction internal/pin allocation and separate all-output ceiling. No inactive/enable/macro-CE credit; actual source activity and signal wire are not qualified.',
      'CTS_rule':'FFfanout32,macrofanout3,parentfanout4,14stages,500um wire/buffer,guard2; source-model hypothesis, not extractedCTS or measured phase.',
      'source_grid_area_screen_is_not_power_admission':True,
      'retained_hub_placement_fit':False,
      'retained_hub_failure_pin':{'commit':'9511b6b978d9aaf3028625cb0d58fddc818667d8','path':'results/quality/w16_engram_rom_constructive_home_20261001/retained_hub_screen.json'},
      'hub_removal_credit':0,
      'standalone_table_home_floorplan_qualified':False,
      'physical_admission':False,'actual_power_qualified':False,'root_stop_credit':0,
      'missing':['localcapture/outputload and contextual SSFF','exact wake/hold/credit and real source data activation','source-bound signal-wire and full clock spatial capacity',
                 'unpriced PHY/collector/CRC/framing/arbitration and root-to-PHY extra pipeline','package/IR and complete token schedule'],
      'verdict':'CONDITIONAL_UNGATED_CLOCK_AND_DATA_ALLOCATION_NO_ADMISSION_NOT_PHYSICAL_MINIMUM'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--candidate-commit',required=True);p.add_argument('--libs',default='/home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1');p.add_argument('--output',required=True);a=p.parse_args()
    if a.candidate_commit: candidate,cp=read(a.candidate_commit,a.candidate)
    else:
        raw=Path(a.candidate).read_bytes();candidate=json.loads(raw);cp={'path':a.candidate,'commit':None,'sha256':hashlib.sha256(raw).hexdigest(),'immutable_commit_bound':False}
    power,pp=read('e79394b1c','results/uarch/w10_q_power_envelope_r1/power.json')
    clock,kp=read('fea811df4','results/uarch/w10_q_existing_icg_r1/clock.json')
    area,ap=read('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json')
    inventory,ip=read(a.candidate_commit,'results/quality/w16_engram_rom_constructive_home_20261001/clock_hold_inventory.json')
    if inventory['candidate_sha256'] != cp['sha256']:raise ValueError('candidate/inventory pin mismatch')
    power=copy.deepcopy(power);clock=copy.deepcopy(clock);area=copy.deepcopy(area);typed_sources={}
    source_records,srp=read('fea811df4','results/uarch/w10_q_existing_icg_r1/HQN_sources.json')
    for corner in ('SS','TT','FF'):
        path=Path(a.libs)/('HQN_'+corner+'.cells.lib');raw=path.read_bytes();text=raw.decode()
        if hashlib.sha256(raw).hexdigest()!=source_records[path.name]['selected_sha256']:raise ValueError('HQN source hash mismatch')
        power['corner_coefficients'][corner]['storage']=coefficients(text,'DFFHQNx1_ASAP7_75t_R',D('1e-12'))
        clock['compatible_event_proof'][corner]['storage']=events(text,'DFFHQNx1_ASAP7_75t_R')
        typed_sources[str(path)]=hashlib.sha256(raw).hexdigest()
    leakage,lp=read('fea811df4','results/uarch/w10_q_existing_icg_r1/leakage_palette.json')
    power['conservative_coefficients']['storage']['leakage_W']=leakage['per_cell_all_state_leakage_upper_W']['DFFHQNx1_ASAP7_75t_R']
    power['conservative_coefficients']['storage']['output_load_ceiling_fF']=str(max(D(power['corner_coefficients'][c]['storage']['pins']['QN']['max_cap_fF']) for c in ('SS','TT','FF')))
    lefpath='results/uarch/w10_baseline_wake/local_fit_r1/selected_cell_lef.txt'
    import subprocess
    lefraw=subprocess.check_output(['git','show','cfa564f3f:'+lefpath]);lef=lefraw.decode();selected=lef.split('MACRO DFFHQNx1_ASAP7_75t_R')[1].split('END DFFHQNx1_ASAP7_75t_R')[0]
    width,height=re.search(r'SIZE ([0-9.]+) BY ([0-9.]+)',selected).groups()
    area['palette']['storage']={'cell':'DFFHQNx1_ASAP7_75t_R','area_um2':str(D(width)*D(height))}
    x=build(candidate,inventory,power,clock,area);x['typed_HQN_library_sha256']=typed_sources;x['typed_HQN_area_um2']=area['palette']['storage']['area_um2'];x['source_pins']={'candidate':cp,'power':pp,'clock':kp,'area':ap,
      'clock_hold_inventory':ip,'typed_library_source_records':srp,'typed_leakage':lp,'typed_LEF':{'commit':'cfa564f3f','path':lefpath,'sha256':hashlib.sha256(lefraw).hexdigest()},
      'pricing_tool':{'commit':'ebef36895','path':'tools/w10_crom_control_reservation.py'}}
    Path(a.output).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()

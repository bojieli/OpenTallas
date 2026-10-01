#!/usr/bin/env python3
"""Exact192-home integer power join; no half-of96 shortcut or idle credit."""
import argparse
import copy
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
from tools.w10_engram_home_power import block, read, coefficients, events

def typed_inputs(libs):
    prior,prior_pin=read('b2aa960a6','results/uarch/w10_engram_home_power_r1/budget.json')
    power,pp=read('e79394b1c','results/uarch/w10_q_power_envelope_r1/power.json')
    clock,kp=read('fea811df4','results/uarch/w10_q_existing_icg_r1/clock.json')
    area,ap=read('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json')
    power=copy.deepcopy(power);clock=copy.deepcopy(clock);area=copy.deepcopy(area)
    sources={}
    for corner in ('SS','TT','FF'):
        path=libs/('HQN_'+corner+'.cells.lib');raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        if digest!=prior['typed_HQN_library_sha256'][str(path)]:raise ValueError('HQN source changed')
        power['corner_coefficients'][corner]['storage']=coefficients(raw.decode(),'DFFHQNx1_ASAP7_75t_R',D('1e-12'))
        clock['compatible_event_proof'][corner]['storage']=events(raw.decode(),'DFFHQNx1_ASAP7_75t_R')
        sources[str(path)]=digest
    leakage,lp=read('fea811df4','results/uarch/w10_q_existing_icg_r1/leakage_palette.json')
    power['conservative_coefficients']['storage']['leakage_W']=leakage['per_cell_all_state_leakage_upper_W']['DFFHQNx1_ASAP7_75t_R']
    power['conservative_coefficients']['storage']['output_load_ceiling_fF']=str(max(D(power['corner_coefficients'][c]['storage']['pins']['QN']['max_cap_fF']) for c in ('SS','TT','FF')))
    area['palette']['storage']={'cell':'DFFHQNx1_ASAP7_75t_R','area_um2':prior['typed_HQN_area_um2']}
    return power,clock,area,{'typed96_source':prior_pin,'power':pp,'clock':kp,'area':ap,'typed_leakage':lp},sources

def build(candidate,power,clock,area):
    homes=candidate['homes']
    if len(homes)!=192 or sum(h['actual_macros'] for h in homes)!=1500067:raise ValueError('incomplete192 inventory')
    if sum(h['total_storage_FF_bits'] for h in homes)!=candidate['all_storage_FF_bits']:raise ValueError('FF aggregate mismatch')
    rows=[]
    for h in homes:
        if h['held_state_feedback_MUX2_bits']!=h['total_storage_FF_bits']:raise ValueError('missing held feedback')
        demux=h['request_demux_AND2_bits']
        if demux%2:raise ValueError('nonintegral AND2 conversion')
        p=block(h['total_storage_FF_bits'],h['response_MUX2_bits']+demux//2,h['actual_macros'],power,clock,area)
        static=D(p['ungated_clock_W'])+D(p['all_state_leakage_upper_W'])
        logicArea=D(p['conditional_cell_plus_macro_area_mm2'])-h['actual_macros']*D('7881.3648')/D('1e6')
        rows.append({'home_id':h['home_id'],'source_column_ordinal':h['column_ordinal'],'macros':h['actual_macros'],
          'tree_wire_FF_bits':h['tree_wire_FF_bits'],'macro_tag_capture_FF_bits':h['macro_tag_capture_FF_bits'],
          'response_MUX2_bits':h['response_MUX2_bits'],'request_demux_AND2_bits':demux,
          'priced_reservation':p,'clock_plus_leak_W':str(static),
          'margin_before_data_PHY_hub_W':str(D('474.56')-static),
          'planning_grid_plus_library_cell_reservation_mm2':str(D(str(candidate['grid_area_mm2']))+logicArea),
          'physical_admission':False})
    totals={k:str(sum(D(r['priced_reservation'][k]) for r in rows)) for k in
            ('ungated_clock_W','all_state_leakage_upper_W','data_internal_upper_W','data_input_pin_upper_W','unresolved_output_load_ceiling_W')}
    return {'schema':'w10_engram192_ungated_power_v1','homes':rows,'all192_component_totals_W':totals,
      'all_storage_FF_bits':candidate['all_storage_FF_bits'],'actual_macros':1500067,
      'storage_cell_type':'DFFHQNx1_ASAP7_75t_R','storage_area_um2':area['palette']['storage']['area_um2'],
      'clock_rule':'All192 home macro and FF clocks1.2GHz ungated; recompute integer CTS perhome. No idle/gating credit, no divide96 totals.',
      'source_grid_size_um':candidate['grid_size_um'],'source_grid_origin_um':candidate['grid_origin_um'],
      'retained_hub_rectangle_grid_screen_only':True,'all_other_obstacles_CTS_PG_PHY_cleared':False,
      'hub_removal_credit':0,'root_stop_credit':0,'physical_admission':False,'actual_power_qualified':False,
      'no_physical_power_minimum_claim':True,
      'remaining':['macro escape/placement and all retained obstacles','feedback/clock/IO/control placement','actual selected request/data/held-state waveforms and signalRC',
                   'reset lowering/CRC/framing/sharedports/PHY/root-toPHY pipeline','package/IR/contextualSSFF and complete token latency'],
      'verdict':'FINITE_TYPED192_CONSTRUCTION_RESERVATION_NOT_FULL_ADMISSION'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--libs',default='/home/ubuntu/w10-w18-recovery/baseline_wake/q_power_envelope_r1');p.add_argument('--output',required=True);a=p.parse_args()
    candidate,cp=read('65eb60a9d','results/quality/w16_engram_rom_constructive_home_20261001/sensitivity_192_homes.json')
    power,clock,area,pins,sources=typed_inputs(Path(a.libs));x=build(candidate,power,clock,area)
    x['source_pins']={'candidate192':cp,**pins};x['typed_HQN_library_sha256']=sources
    Path(a.output).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()

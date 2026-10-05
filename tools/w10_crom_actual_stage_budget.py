#!/usr/bin/env python3
"""Typed actual stage-catalog dimensions and finite calendar join; no admission."""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
from tools.w10_crom_control_reservation import read,block

def build(candidates,comparison,base,control,local,power,clock,area):
    page_mux=control['control_catalog_tag_reservation']['explicit_MUX2_bits'];route=local['registered_route_fast_cycles_each_direction'];out=[]
    if route!=11:raise ValueError('unexpected route')
    for case in comparison['cases']:
        banks=case['readonly_banks'];c=candidates[str(banks)]
        if banks==45:
            cat=c['regular_catalog'];catalog=cat['existing4096x274_catalog_macros'];landing=c['nominal_service_ports']['capture_coefficients']
            if not c['nominal_service_ports']['same_bank_conflict_structure_preserved']:raise ValueError('45port conflict mismatch')
        else:
            e=c['regular_element'];catalog=e['regular_request_catalog_banks']+e['regular_fill_catalog_banks'];landing=e['landing_capacity_coefficients']
            if e['readonly_banks_per_home']!=banks or e['total_macros_per_home']!=banks+catalog:raise ValueError('bank source mismatch')
            if c['exact_address_route']['logical_coefficient_reads']!=549760:raise ValueError('read coverage mismatch')
        mux=base['MUX2_bits_by_purpose']['gamma_band_select']+16*(landing-1)*32+page_mux
        for credit in (2,4,128):
            roles={'retained_staging':base['total_storage_bits'],'retained_tag_epoch_state':control['tag_state_FF_bits_additional_to_operands'],'catalog_raw_capture':catalog*274,'TX_packets':credit*672,'RX_packets':credit*672,'payload_route':route*1024,'forward_control':route*64,'reverse_control_plusACKserial':(route+1)*64,'credit_state':2*credit+2*max(1,(credit-1).bit_length())}
            p=block(sum(roles.values()),mux,banks+catalog,power,clock,area)
            deficit=D('11.956')+D(p['conditional_cell_plus_macro_area_mm2'])-D(local['current_SU_region_area_mm2'])
            out.append({'parameter_banks':banks,'catalog_banks':catalog,'macro_count':banks+catalog,'credits':credit,'landing_words':landing,'landing_selector_MUX2_bits':16*(landing-1)*32,'FF_by_role':roles,'fresh_declared_reservation':p,'exclusive_SU_slot_area_deficit_mm2':str(deficit),'fit_verdict':'FAIL_CHOSEN_RETAINED_STAGING_RESERVATION' if deficit>0 else 'AREA_SCREEN_ONLY','finite_coefficient_only_calendar_us':case['finite_credit_fill_us'][str(credit)],'effective_fulltoken_latency_qualified':False,'physical_admission':False})
    return {'schema':'w10_crom_actual_stage_budget_v1','source_compiler_model_address_roundtrip_bound':True,'cases':out,'retained_page_select_MUX2_allocation':page_mux,'page_select_scope':'Conservative old3288 allocation retained; actual new decoder/arbitration/selection/reset/fanout lowering missing. This does not assert these cells are instantiated.',
      'macro_depth':4096,'small1024x72_variant_adopted':False,'small_macro_power_transfer_credit':0,
      'storage_only_three_bank_service_credit':0,'gamma_three_bank_read_floor_before_conflicts_cycles':569,
      'fastest_enumerated_coefficient_only_banks':comparison['fastest_enumerated_coefficient_only_candidate'],
      'clock_scope':'Full fresh integer CTS and all macro/FF clocks ungated; no old power subtraction or clock gate credit. Characterized coefficients retained with declared guarded wire/load hypothesis only.',
      'L1_complete_image_valid':False,'actual_physical_catalog_published':False,'complete_current_control_and_CDC_inventory':False,'actual_PC_absolute_deadlines_bound':False,'physical_admission':False,'actual_power_qualified':False,'whole_point_power_W':None,'whole_point_power_margin_W':None,'whole_token_latency_cycles':None,
      'missing':['L1invalid20480words/source and actualencodedconsumerbases','actual compiled immutable physicalcatalog/identity/validity decoder/reset','concretehome replicas/currentplacement+allobstacles, signalclockPG/IR/SSFF','current completecontrol/CDC/phase/read-select/consumerdeadlines'],
      'verdict':'SOURCE_STAGE_CATALOG_AND_CALENDAR_PRICED_ALL_CHOSEN_SU_SLOT_RESERVATIONS_FAIL_NO_ADMISSION_NOT_MINIMUM'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();pins={};records={};candidates={};prefix='results/quality/w16_engram_initializer_20261001/'
    for b in (6,9,16,45):
        path=prefix+('stage_local45_rows.json' if b==45 else 'stage_local'+str(b)+'.json');candidates[str(b)],pins[str(b)]=read('3977c33920751cbd40db970ae3d87a7046e0d658',path)
    specs={'comparison':('3977c3392',prefix+'stage_local_comparison.json'),'base':('cda48d1f7','results/uarch/w10_crom_staging_correction_r1/budget.json'),'control':('ebef36895','results/uarch/w10_crom_control_reservation_r1/budget.json'),'local':('47b715428','results/quality/w16_w17_crom_finite_prefetch_20261001/local_home.json'),'power':('e79394b1c','results/uarch/w10_q_power_envelope_r1/power.json'),'clock':('fea811df4','results/uarch/w10_q_existing_icg_r1/clock.json'),'area':('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json')}
    for k,(commit,path) in specs.items():records[k],pins[k]=read(commit,path)
    for c in records['comparison']['cases']:
        if 'sha256' in c and pins[str(c['readonly_banks'])]['sha256']!=c['sha256']:raise ValueError('catalog comparison join mismatch')
    x=build(candidates=candidates,**records);x['source_pins']=pins;x['characterized_library_inputs']=records['power']['sources'];Path(a.output).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Frozen CROM declared local inventory, phase allocations and fail-closed fit."""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
from tools.w10_crom_control_reservation import read,block

def build(frozen,local,base,controls,calendar,power,clock,area):
    f=frozen['finite_service'];layout=frozen['layout'];route=local['registered_route_fast_cycles_each_direction']
    ports=f['selected_FP32_outputs_per_fast_cycle']
    if ports!=16 or route!=11:raise ValueError('unexpected frozen service/route source')
    floors={'all_words':(layout['logical_words']+ports-1)//ports,'gamma_all':(f['gamma_words']+ports-1)//ports,'single_gamma_home':(f['gamma_home_words']+ports-1)//ports}
    if floors!={'all_words':34360,'gamma_all':25920,'single_gamma_home':320}:raise ValueError('service floor mismatch')
    cc=calendar['compiler_control_storage'];rows=[]
    mux=sum(v for k,v in base['MUX2_bits_by_purpose'].items() if k!='storage_write_enable')+cc['page_select_mux_bits']
    ffbase=base['total_storage_bits']+cc['tag_valid_and_epoch_state_FF_bits']+cc['mandatory_raw_capture_FF_bits']
    macros=f['macro_read_ports']+cc['total4096x274_macros']
    for credit in (2,4,128):
        roles={'two_operand_gamma_capture_landing':base['total_storage_bits'],'tag_valid_epoch':cc['tag_valid_and_epoch_state_FF_bits'],'catalog_raw_capture':cc['mandatory_raw_capture_FF_bits'],'TX_fullpacket':credit*672,'RX_fullpacket':credit*672,'payload_route':route*1024,'forward_control_route':route*64,'reverse_control_route_and_ACK_serialization':(route+1)*64,'credit_valid_return':credit*2+2*max(1,(credit-1).bit_length())}
        p=block(sum(roles.values()),mux,macros,power,clock,area)
        phases=[]
        clk=D(p['ungated_clock_W']);leak=D(p['all_state_leakage_upper_W'])
        data=sum(D(p[k]) for k in ('data_internal_upper_W','data_input_pin_upper_W'))
        wire=D(p['unresolved_output_load_ceiling_W'])
        for name,cycles in floors.items():
            seconds=D(cycles)/D('1.2e9')
            phases.append({'phase':name,'service_floor_fast_cycles':cycles,'minimum_service_interval_seconds':str(seconds),'clock_exposure_allocation_J_at_floor':str(clk*seconds),'leakage_allocation_J_at_floor':str(leak*seconds),'full_activity_data_internal_pin_allocation_J_at_floor':str(data*seconds),'separate_output_load_ceiling_allocation_J_at_floor':str(wire*seconds),'scope':'Declared inventory alpha1 envelope over service floor ONLY; not elapsed execution energy or actual data trace. Stalls/CDC/setup/drain extend exposure; no averaging or inactive-cone credit.'})
        rows.append({'credits':credit,'storage_FF_by_role':roles,'total_FF_bits':sum(roles.values()),'explicit_select_MUX2_bits':mux,'macro_count_including_catalog':macros,'recomputed_declared_reservation':p,'phase_allocations':phases,'actual_provider':False})
    return {'schema':'w10_frozen_crom_local_phase_budget_v1','source_logical_words':layout['logical_words'],'source_padded_words':layout['padded_words'],'source_invalid_hole':layout['invalid_source_hole'],'selected_FP32_ports_per_fast_cycle':ports,'phase_service_floors_fast_cycles':floors,
      'local_route_cycles_each_direction':route,'rows':rows,'local_fit':{'macro_cell_area_only_not_placement':True,'retained_SU_region_area_mm2':local['current_SU_region_area_mm2'],'placement_verdict':local['placement_verdict'],'existing_SU_occupied_area_credit_mm2':0,'actual_macro_and_SU_coordinates_bound':False,'exclusive_route_tracks_required':1152,'track_recipe':'1024payload +64forward +64reverse distinct control; no optional initializer3008-track corridor reuse','actual_track_capacity':None,'actual_route_fit':False},
      'phase_composition':{'actual_resident_home_count_and_intervals':None,'actual_data_trace':None,'full_engram_sync_control_complete':False,'full_E32_identity_setup_and_drain_complete':False,'actual_1p2_to_0p9_CDC':None,'mandatory_macro_CLK_energy_retained':True,'adaptive_clock_gate_credit':0,'root_stop_credit':0,'historical_power_subtraction_W':0,'whole_point_power_W':None,'whole_point_power_margin_W':None},
      'image_valid':False,'consumer_operand_bases_encoded':False,'catalog_reencoded_for_frozen_padded_layout':False,'catalog_scope':'bc1 historical catalog structure dimensions only; current padded bank/base/validity lowering not qualified.','complete_phase_budget':False,'physical_admission':False,'actual_power_qualified':False,'whole_token_latency_cycles':None,'headline_rate':None,
      'missing':['L1 words508800..529279 and complete immutable image publication/consumer encoded bases','actual localhome/replica/placement and nonoverlap with retained SU','descriptor decoders/arbiters/enables/fanout/reset/CRC/image-valid-state and actualCDC','whole resident phase simultaneity, payload/disabledMUX raw pin trace, source load/RC','complete synchronousbranch localidle predicates/endpointcompare/serializer and drain bindings','fullallport CTS/PG/contextualSSFF/packageIR'],
      'verdict':'FINITE_DECLARED_LOCAL_CROM_PHASE_ALLOCATION_SOURCE_IMAGE_AND_FULL_CONTROL_FIT_GATE_FAIL_NO_ADMISSION'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();records={};pins={}
    inputs={'frozen':('64a04715c','results/quality/w16_engram_initializer_20261001/frozen_closure.json'),'local':('47b715428','results/quality/w16_w17_crom_finite_prefetch_20261001/local_home.json'),'base':('cda48d1f7','results/uarch/w10_crom_staging_correction_r1/budget.json'),'controls':('ebef36895','results/uarch/w10_crom_control_reservation_r1/budget.json'),'calendar':('bc1ec8b8f','results/quality/w16_w17_crom_finite_prefetch_20261001/calendar.json'),'power':('e79394b1c','results/uarch/w10_q_power_envelope_r1/power.json'),'clock':('fea811df4','results/uarch/w10_q_existing_icg_r1/clock.json'),'area':('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json')}
    for k,(commit,path) in inputs.items():records[k],pins[k]=read(commit,path)
    x=build(**records);x['source_pins']=pins
    Path(a.output).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()

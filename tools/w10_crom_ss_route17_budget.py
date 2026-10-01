#!/usr/bin/env python3
"""Additive SS reach correction; prior11-route receipts remain immutable."""
import argparse
from decimal import Decimal as D,ROUND_CEILING
import hashlib
import json
from pathlib import Path
import re
import subprocess
from tools.w10_crom_control_reservation import read,block
from tools.w10_crom_small_macro_budget import price,macro_profile

def route_basis(local,model):
    reach=D(re.search(r'^WIRE_REACH_SS_UM\s*=\s*([0-9.]+)',model,re.M)[1])
    distance=D(local['local_manhattan_envelope_um'])
    stages=int((distance/reach).to_integral_value(rounding=ROUND_CEILING))
    if reach!=D(504) or distance!=D('8159.616') or stages!=17:raise ValueError('SS route source changed')
    return {'source_reach_SS_um':str(reach),'source_envelope_um':str(distance),'forward_fast_stages':stages,'reverse_fast_stages':stages,'reverse_ACK_serialization_fast_cycles':1,'scope':'Conditional scalar SS reach basis from541; NOT actual1152bitCROM bus route or CDC timing proof.'}

def revised_roles(roles,route):
    x=dict(roles);x['payload_route']=route*1024;x['forward_control']=route*64;x['reverse_control_plusACKserial']=(route+1)*64
    if sum(x.values())-sum(roles.values())!=6*1152:raise ValueError('expected old11 ->new17 delta mismatch')
    return x

def build(old,before_small,local,model,power,clock,area,small,big):
    basis=route_basis(local,model);route=basis['forward_fast_stages'];cases=[];small_cases=[]
    for r in old['cases']:
        roles=revised_roles(r['FF_by_role'],route);macro_count=r['parameter_banks']+r['catalog_banks']
        mux=r['landing_selector_MUX2_bits']+262144+old['retained_page_select_MUX2_allocation']
        p=block(sum(roles.values()),mux,macro_count,power,clock,area)
        deficit=D('11.956')+D(p['conditional_cell_plus_macro_area_mm2'])-D(local['current_SU_region_area_mm2'])
        cases.append({'parameter_banks':r['parameter_banks'],'catalog_banks':r['catalog_banks'],'credits':r['credits'],'FF_by_role':roles,'extra_pipeline_FF_vs11':6912,'fresh_declared_reservation':p,'exclusive_SU_slot_area_deficit_mm2':str(deficit),'route17_finite_calendar_us':None,'old11_calendar_not_current':True,'physical_admission':False})
    for r in before_small['rows']:
        roles=revised_roles(r['FF_by_role'],route);p=price(sum(roles.values()),262144+68608+old['retained_page_select_MUX2_allocation'],[(135,small),(4,big)],power,clock,area)
        deficit=D('11.956')+D(p['conditional_cell_plus_macro_area_mm2'])-D(local['current_SU_region_area_mm2'])
        small_cases.append({'parameter_small_macros':135,'catalog_large_macros':4,'credits':r['credits'],'FF_by_role':roles,'extra_pipeline_FF_vs11':6912,'fresh_mixed_reservation':p,'exclusive_SU_slot_area_deficit_mm2':str(deficit),'route17_finite_calendar_us':None,'old11_calendar_not_current':True,'explicit_depth_alternative_adopted':False,'physical_admission':False})
    return {'schema':'w10_crom_ss_route17_typed_correction_v1','route_basis':basis,'cases':cases,'small_macro_alternative_cases':small_cases,'forward_control_bits_per_stage':64,'reverse_control_bits_per_stage':64,'payload_bits_per_stage':1024,'route_pipeline_FF_sum':17*1024+17*64+18*64,'route_pipeline_extra_FF_vs11':6912,
      'actual_bus_width_tracks':1152,'actual_1152bit_bus_routing_reach_proven':False,'actual_128bit_CDC_binding':False,'actual_128bit_CDC_extra_state_bits':None,'CDC_implementation_area_power_timing_qualified':False,
      'old11_records_preserved':True,'old11_calendar_transfer_credit':0,'historical_power_subtraction_W':0,'adaptive_clock_gate_credit':0,'root_stop_credit':0,'physical_admission':False,'complete_inventory':False,'actual_power_qualified':False,'whole_point_power_W':None,'whole_point_power_margin_W':None,'whole_token_latency_cycles':None,
      'missing':['Ram sourcebound17bothway bankwave/credit calendar and actualPC absolute release/deadlines','actual1152bus routing/loads+128wideCDC registered storage/reset/drain/control','L1completeimage/catalogpublication/encodedbases','newconstructor localSU/wholegeometry and allretainedobstacles/CTS/PG/fanout/hold/capture/IR/contextualSSFF'],
      'verdict':'SS17_REACH_PIPELINE_CORRECTION_ALL_TYPED_RESERVATIONS_REPRICED_NO_11_CALENDAR_OR_FIT_ADMISSION'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();r={};pins={}
    specs={'old':('4276c2587','results/uarch/w10_crom_actual_stage_budget_r1/budget.json'),'before_small':('f05904253','results/uarch/w10_crom_small_macro_budget_r1/budget.json'),'local':('47b715428','results/quality/w16_w17_crom_finite_prefetch_20261001/local_home.json'),'power':('e79394b1c','results/uarch/w10_q_power_envelope_r1/power.json'),'clock':('fea811df4','results/uarch/w10_q_existing_icg_r1/clock.json'),'area':('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json')}
    for k,(c,path) in specs.items():r[k],pins[k]=read(c,path)
    raw=subprocess.check_output(['git','show','541a1d2f:tools/uarch_model.py']);pins['SS_route_model']={'commit':'541a1d2f','path':'tools/uarch_model.py','sha256':hashlib.sha256(raw).hexdigest()}
    x=build(**r,model=raw.decode(),small=macro_profile('ot_rom_1024x72_m8'),big=macro_profile('ot_rom_4096x274_m8'));x['source_pins']=pins;x['macro_library_source_pins']=r['before_small']['small_macro_profile']['source_pins'];x['standard_cell_library_inputs']=r['power']['sources'];Path(a.output).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()

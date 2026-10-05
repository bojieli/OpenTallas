#!/usr/bin/env python3
"""Own-Liberty mixed ROM depth alternative, never historical power transfer."""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import re
import subprocess
from tools.w10_crom_control_reservation import read
from tools.w10_q_power_envelope import coefficients,serial

def macro_profile(name):
    pins={};cs={};prefix='physical/asap7_memory_macros/'+name+'/'
    for corner in ('SS','TT','FF'):
        path=prefix+name+'_'+corner.lower()+'.lib';raw=subprocess.check_output(['git','show','d2c28c279:'+path])
        pins[corner]={'commit':'d2c28c279','path':path,'sha256':hashlib.sha256(raw).hexdigest()}
        text=raw.decode();cs[corner]=coefficients(text,name,D('1e-9'))
        if len(re.findall(r'\binternal_power\s*\(',text))!=1 or 'when :' in text:raise ValueError('macro energy no longer unconditional CLK-only')
    path=prefix+name+'.lef';raw=subprocess.check_output(['git','show','d2c28c279:'+path]);w,h=map(D,re.search(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',raw.decode()).groups());pins['LEF']={'commit':'d2c28c279','path':path,'sha256':hashlib.sha256(raw).hexdigest()}
    return {'name':name,'corner_coefficients':serial(cs),'area_um2':str(w*h),'CLK_cap_fF':str(max(c['pins']['clk']['cap_fF'] for c in cs.values())),'CLK_internal_cycle_fJ':str(max(c['internal_cycle_fJ'] for c in cs.values())),'leakage_W':str(max(c['leakage_W'] for c in cs.values())),'data_input_cap_fF':str(max(sum(p['cap_fF'] for n,p in c['pins'].items() if p['direction']=='input' and n!='clk') for c in cs.values())),'physical_output_load_ceiling_fF':str(max(sum(p['max_cap_fF'] for p in c['pins'].values() if p['direction']=='output') for c in cs.values())),'source_pins':pins}

def price(ff,mux,groups,power,clock,area):
    macros=sum(n for n,_ in groups);nand=4*(ff+mux);levels=[(ff+31)//32+sum((n+2)//3 for n,_ in groups)]
    while levels[-1]>1:levels.append((levels[-1]+3)//4)
    if len(levels)>14:raise ValueError('tree hypothesis depth exceeded')
    buffers=sum(levels)+14-len(levels);cs=power['conservative_coefficients'];hz=D('1.2e9');v2=D('.77')**2;cv=hz*v2*D('1e-15')
    fc=max(D(power['corner_coefficients'][c]['storage']['pins']['CLK']['cap_fF']) for c in ('SS','TT','FF'))
    fd=max(D(power['corner_coefficients'][c]['storage']['pins']['D']['cap_fF']) for c in ('SS','TT','FF'))
    ce=max(D(clock['compatible_event_proof'][c]['storage']['event_cycle_fJ']['CLK']) for c in ('SS','TT','FF'))
    de=max(D(clock['compatible_event_proof'][c]['storage']['event_cycle_fJ']['D']) for c in ('SS','TT','FF'))
    clockW=(ff*fc+buffers*(D(cs['buffer']['input_cap_fF'])+500*D('.145426')*2)+sum(n*D(m['CLK_cap_fF']) for n,m in groups))*cv
    clockW+=(ff*ce+buffers*D(cs['buffer']['internal_cycle_fJ'])+sum(n*D(m['CLK_internal_cycle_fJ']) for n,m in groups))*hz*D('1e-15')
    dataW=(ff*de+nand*D(cs['nand']['internal_cycle_fJ']))*hz*D('1e-15')
    pinW=(ff*fd+nand*D(cs['nand']['input_cap_fF'])+sum(n*D(m['data_input_cap_fF']) for n,m in groups))*cv
    outputW=(ff*D(cs['storage']['output_load_ceiling_fF'])+nand*D(cs['nand']['output_load_ceiling_fF'])+sum(n*D(m['physical_output_load_ceiling_fF']) for n,m in groups))*cv
    leak=ff*D(cs['storage']['leakage_W'])+nand*D(cs['nand']['leakage_W'])+buffers*D(cs['buffer']['leakage_W'])+sum(n*D(m['leakage_W']) for n,m in groups)
    std=ff*D(area['palette']['storage']['area_um2'])+nand*D(area['palette']['nand']['area_um2'])+buffers*D(area['palette']['buffer']['area_um2'])
    ma=sum(n*D(m['area_um2']) for n,m in groups)/D('1e6')
    return {'FF_bits':ff,'NAND2_cells':nand,'macro_clock_endpoints':macros,'clock_buffers':buffers,'ungated_clock_W':str(clockW),'all_state_leakage_upper_W':str(leak),'data_internal_full_activity_upper_W':str(dataW),'data_input_pin_full_activity_upper_W':str(pinW),'separate_output_load_ceiling_W':str(outputW),'macro_area_mm2':str(ma),'conditional_cell_plus_macro_area_mm2':str(std/D('.5e6')+ma)}

def build(source,base,control,local,power,clock,area,small,big):
    choice=next(c for c in source['available_choices'] if c['name']=='three_existing1024x72_per_bank')
    if choice['coefficient_macros']!=135 or source['max_regular_rows_per_bank']!=250:raise ValueError('source alternative changed')
    catalog=source['regular_catalog']['existing4096x274_catalog_macros'];route=local['registered_route_fast_cycles_each_direction'];rows=[]
    mux=base['MUX2_bits_by_purpose']['gamma_band_select']+16*(135-1)*32+control['control_catalog_tag_reservation']['explicit_MUX2_bits']
    for c in (2,4,128):
        roles={'retained_staging':base['total_storage_bits'],'retained_tags':control['tag_state_FF_bits_additional_to_operands'],'catalog_raw_capture':catalog*274,'TX_packets':c*672,'RX_packets':c*672,'payload_route':route*1024,'forward_control':route*64,'reverse_control_plusACKserial':(route+1)*64,'credit_state':2*c+2*max(1,(c-1).bit_length())}
        p=price(sum(roles.values()),mux,[(135,small),(catalog,big)],power,clock,area)
        deficit=D('11.956')+D(p['conditional_cell_plus_macro_area_mm2'])-D(local['current_SU_region_area_mm2'])
        rows.append({'credits':c,'FF_by_role':roles,'fresh_mixed_macro_reservation':p,'exclusive_SU_slot_area_deficit_mm2':str(deficit),'fit_verdict':'FAIL_CHOSEN_RETAINED_STAGING_RESERVATION' if deficit>0 else 'AREA_SCREEN_NOT_PHYSICAL_FIT','physical_admission':False})
    return {'schema':'w10_crom_135_small_macro_typed_alternative_v1','rows':rows,'small_macro_profile':small,'catalog_macro_profile':big,'parameter_macros':135,'catalog_macros':catalog,'extra_macro_clock_endpoints_vs45':90,'useful_bits_per_small_macro':64,'physical_bits_per_small_macro':72,'padding_output_pin_loads_charged':True,'bank_clock_fanout':3,'capture_scope':'135physical parameter reply streams, all72bits clock/output-load priced. Original475402staging remains; new endpoint adapters/address/CE/select/fanout/hold/reset not measured or fully typed.',
      'clock_policy':'1.2GHz ungated; own SS/TT/FF macro CLK energy/pins, generic declared integer fanout/guard2. Macro CE provides no CLKpower credit.',
      'baseline4096_depth_rule_preserved':False,'explicit_depth_alternative_adopted':False,'same45bank_conflict_mapping_model':source['nominal_service_ports']['same_bank_conflict_structure_preserved'],'SS_macro_clkq_ps_source':choice['SS_clkq_ps'],'SS_contextual_capture_qualified':False,
      'historical_power_subtraction_W':0,'root_stop_credit':0,'adaptive_clock_gate_credit':0,'physical_admission':False,'actual_power_qualified':False,'complete_inventory':False,'whole_point_power_W':None,'whole_point_power_margin_W':None,'whole_token_latency_cycles':None,
      'missing':['L1invalid and actualnewcatalog/sourcevalue publication','135macro port/capture/address/CE/clock/sharedfanout routing and timing','allendpoint adapter/control/CDC/reset/hold/site/PG/IR bounds','actualhome replicas/PCdeadlines/phase RC/load/current'],'verdict':'EXPLICIT_135_MACRO_DEPTH_ALTERNATIVE_FRESH_TYPED_DECLARED_RESERVATION_NO_ADOPTION_NOT_MINIMUM'}
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();r={};pins={}
    specs={'source':('3977c3392','results/quality/w16_engram_initializer_20261001/stage_local45_rows.json'),'base':('cda48d1f7','results/uarch/w10_crom_staging_correction_r1/budget.json'),'control':('ebef36895','results/uarch/w10_crom_control_reservation_r1/budget.json'),'local':('47b715428','results/quality/w16_w17_crom_finite_prefetch_20261001/local_home.json'),'power':('e79394b1c','results/uarch/w10_q_power_envelope_r1/power.json'),'clock':('fea811df4','results/uarch/w10_q_existing_icg_r1/clock.json'),'area':('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json')}
    for k,(commit,path) in specs.items():r[k],pins[k]=read(commit,path)
    x=build(**r,small=macro_profile('ot_rom_1024x72_m8'),big=macro_profile('ot_rom_4096x274_m8'));x['source_pins']=pins;x['standard_cell_library_inputs']=r['power']['sources'];Path(a.output).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()

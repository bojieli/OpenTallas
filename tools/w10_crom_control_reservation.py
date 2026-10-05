#!/usr/bin/env python3
"""Charge source-pinned CROM tag/catalog and finite credit/route state separately."""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import subprocess

def read(commit,path):
    raw=subprocess.check_output(['git','show',commit+':'+path])
    return json.loads(raw),{'commit':commit,'path':path,'sha256':hashlib.sha256(raw).hexdigest()}

def block(ff,mux,macros,power,clock,area):
    if min(ff,mux,macros)<0:raise ValueError('negative state count')
    nand=4*(ff+mux)
    levels=[(ff+31)//32+(macros+2)//3]
    while levels[-1]>1:levels.append((levels[-1]+3)//4)
    if len(levels)>14:raise ValueError('clock depth hypothesis exceeded')
    buffers=sum(levels)+14-len(levels)
    cs=power['conservative_coefficients'];hz=D('1.2e9');cv=hz*D('.77')**2*D('1e-15')
    corners=('SS','TT','FF')
    fc=max(D(power['corner_coefficients'][c]['storage']['pins']['CLK']['cap_fF']) for c in corners)
    fd=max(D(power['corner_coefficients'][c]['storage']['pins']['D']['cap_fF']) for c in corners)
    mc=max(D(power['corner_coefficients'][c]['macro']['pins']['clk']['cap_fF']) for c in corners)
    md=max(sum(D(v['cap_fF']) for k,v in power['corner_coefficients'][c]['macro']['pins'].items()
               if v['direction']=='input' and k!='clk') for c in corners)
    ce=max(D(clock['compatible_event_proof'][c]['storage']['event_cycle_fJ']['CLK']) for c in corners)
    de=max(D(clock['compatible_event_proof'][c]['storage']['event_cycle_fJ']['D']) for c in corners)
    clockW=(ff*fc+macros*mc+buffers*(D(cs['buffer']['input_cap_fF'])+500*D('.145426')*2))*cv
    clockW+=(ff*ce+macros*D(cs['macro']['internal_cycle_fJ'])+buffers*D(cs['buffer']['internal_cycle_fJ']))*hz*D('1e-15')
    dataW=(ff*de+nand*D(cs['nand']['internal_cycle_fJ']))*hz*D('1e-15')
    pinW=(ff*fd+nand*D(cs['nand']['input_cap_fF'])+macros*md)*cv
    wireW=(ff*D(cs['storage']['output_load_ceiling_fF'])+nand*D(cs['nand']['output_load_ceiling_fF'])+macros*D(cs['macro']['output_load_ceiling_fF']))*cv
    leakW=ff*D(cs['storage']['leakage_W'])+nand*D(cs['nand']['leakage_W'])+macros*D(cs['macro']['leakage_W'])+buffers*D(cs['buffer']['leakage_W'])
    cells=ff*D(area['palette']['storage']['area_um2'])+nand*D(area['palette']['nand']['area_um2'])+buffers*D(area['palette']['buffer']['area_um2'])
    return {'FF_bits':ff,'explicit_MUX2_bits':mux,'write_enable_NAND2_cells_included':4*ff,
      'total_NAND2_cells':nand,'macros':macros,'additional_clock_buffers':buffers,
      'conditional_cell_plus_macro_area_mm2':str(cells/D('.5')/D('1e6')+macros*D('7881.3648')/D('1e6')),
      'ungated_clock_W':str(clockW),'all_state_leakage_upper_W':str(leakW),
      'data_internal_upper_W':str(dataW),'data_input_pin_upper_W':str(pinW),
      'unresolved_output_load_ceiling_W':str(wireW),
      'clock_leak_data_pin_subtotal_W':str(clockW+leakW+dataW+pinW)}

def build(control,base,power,clock,area):
    cc=control['compiler_control_storage']
    tags=cc['tag_valid_and_epoch_state_FF_bits'];captures=cc['mandatory_raw_capture_FF_bits']
    if not isinstance(tags,int) or tags<=0:raise ValueError('missing positive tag/state inventory')
    catalog=block(tags+captures,cc['page_select_mux_bits'],cc['total4096x274_macros'],power,clock,area)
    scenarios=[]
    for s in control['finite_packet_credit_area_screens']:
        counts={k:s[k] for k in ('TX_fullpacket_bits','RX_landing_fullpacket_bits','route_pipeline_bits','credit_valid_and_return_state_bits')}
        if s['credits'] not in (2,4,128) or any(not isinstance(n,int) or n<0 for n in counts.values()):raise ValueError('invalid credit state inventory')
        reservation=block(sum(counts.values()),0,0,power,clock,area)
        totalFF=base['total_storage_bits']+catalog['FF_bits']+reservation['FF_bits']
        combinedClock=D(base['ungated_clock_W'])+D(catalog['ungated_clock_W'])+D(reservation['ungated_clock_W'])
        combinedArea=D(base['conditional_cell_plus_macro_area_mm2'])+D(catalog['conditional_cell_plus_macro_area_mm2'])+D(reservation['conditional_cell_plus_macro_area_mm2'])
        scenarios.append({'credits':s['credits'],'state_bits_by_purpose':counts,'credit_route_reservation':reservation,
          'buffer_plus_catalog_plus_credit_route_FF_bits':totalFF,'conditional_combined_area_mm2':str(combinedArea),
          'combined_ungated_clock_W':str(combinedClock),'whole_CROM_budget_ready':False})
    if sorted(s['credits'] for s in scenarios)!=[2,4,128]:raise ValueError('missing or duplicate credit scenarios')
    return {'schema':'w10_crom_tag_credit_route_reservation_v1','operand_bits_only':131072,
      'base_buffer_FF_bits':base['total_storage_bits'],
      'tag_state_FF_bits_additional_to_operands':tags,'control_raw_capture_FF_bits':captures,
      'control_catalog_tag_reservation':catalog,'credit_scenarios':scenarios,
      'historical_per_lane_20bit_address_allocation':{'bits':2*1024*20,'actual_implementation_qualified':False,
        'scope':'Not contained in131072operand bits. Source compiler uses static request/fill catalog and separate tag/state; no free address-state elimination claim.'},
      'control_scope':'Ram immutable encoded-demand candidate inventory, not measured RTL or instantiated provider. Tags/capture/macros/page mux and credit/route state are extra to operands.',
      'clock_rule':'Additional independently budgeted14-stage CTS trees, all ungated, worstdataactivity1. No sharing/reuse/clock-stop subtraction.',
      'physical_admission':False,'actual_provider_instantiated':False,'complete_power_qualified':False,
      'unpriced_controls':['descriptor decoder/arbiter logic','registered page/selector timing and fanout repair','source image/decompressor','actual CDC and receiver credit acceptance'],
      'root_stop_credit':0,'verdict':'ADDITIVE_NONZERO_CONTROL_RESERVATION_NO_ADMISSION'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--control-commit',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    control,cp=read(a.control_commit,'results/quality/w16_w17_crom_finite_prefetch_20261001/calendar.json')
    base,bp=read('cda48d1f7','results/uarch/w10_crom_staging_correction_r1/budget.json')
    power,pp=read('e79394b1c','results/uarch/w10_q_power_envelope_r1/power.json')
    clock,kp=read('fea811df4','results/uarch/w10_q_existing_icg_r1/clock.json')
    area,ap=read('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json')
    x=build(control,base,power,clock,area);x['source_pins']={'control_calendar':cp,'operand_buffer':bp,'power':pp,'clock':kp,'area':ap}
    Path(a.output).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Additive two-operand staging correction; prior CROM receipt stays immutable."""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import subprocess

def read(commit, path):
    raw=subprocess.check_output(['git','show',commit+':'+path])
    return json.loads(raw),{'commit':commit,'path':path,'sha256':hashlib.sha256(raw).hexdigest()}

def corrected(old, power, clock, area):
    x=json.loads(json.dumps(old))
    old_emit=x['storage_bits_by_purpose'].pop('two_emit_slots_payload_plus_address')
    emit=2*1024*32*2
    extra_ff=emit-old_emit
    x['storage_bits_by_purpose']['two_operands_FP32_two_emit_slots']=emit
    x['total_storage_bits']+=extra_ff
    x['MUX2_bits_by_purpose']['storage_write_enable']+=extra_ff
    extra_nand=4*extra_ff
    x['NAND2_construction_cells']+=extra_nand
    levels=[(x['total_storage_bits']+31)//32+(45+2)//3]
    while levels[-1]>1:levels.append((levels[-1]+3)//4)
    if len(levels)>14:raise ValueError('clock stage bound exceeded')
    buffers=sum(levels)+14-len(levels)
    extra_buf=buffers-x['conditional_clock_buffers']
    x['conditional_clock_buffers']=buffers
    x['clock_tree_levels_before_padding']=levels
    cs=power['conservative_coefficients'];hz=D('1.2e9');cv=hz*D('.77')**2*D('1e-15')
    ffC=max(D(power['corner_coefficients'][c]['storage']['pins']['CLK']['cap_fF']) for c in ('SS','TT','FF'))
    ffD=max(D(power['corner_coefficients'][c]['storage']['pins']['D']['cap_fF']) for c in ('SS','TT','FF'))
    clkE=max(D(clock['compatible_event_proof'][c]['storage']['event_cycle_fJ']['CLK']) for c in ('SS','TT','FF'))
    dataE=max(D(clock['compatible_event_proof'][c]['storage']['event_cycle_fJ']['D']) for c in ('SS','TT','FF'))
    delta_clock=(extra_ff*ffC+extra_buf*(D(cs['buffer']['input_cap_fF'])+500*D('.145426')*2))*cv
    delta_clock+=(extra_ff*clkE+extra_buf*D(cs['buffer']['internal_cycle_fJ']))*hz*D('1e-15')
    delta_leak=extra_ff*D(cs['storage']['leakage_W'])+extra_nand*D(cs['nand']['leakage_W'])+extra_buf*D(cs['buffer']['leakage_W'])
    delta_int=(extra_ff*dataE+extra_nand*D(cs['nand']['internal_cycle_fJ']))*hz*D('1e-15')
    delta_pin=(extra_ff*ffD+extra_nand*D(cs['nand']['input_cap_fF']))*cv
    delta_wire=(extra_ff*D(cs['storage']['output_load_ceiling_fF'])+extra_nand*D(cs['nand']['output_load_ceiling_fF']))*cv
    deltas={'ungated_clock_W':delta_clock,'all_state_leakage_upper_W':delta_leak,
            'selected_data_internal_upper_W':delta_int,'data_pin_upper_W':delta_pin,
            'unresolved_all_output_load_ceiling_W':delta_wire}
    for k,v in deltas.items():x[k]=str(D(x[k])+v)
    delta_area=(extra_ff*D(area['palette']['storage']['area_um2'])+extra_nand*D(area['palette']['nand']['area_um2'])+extra_buf*D(area['palette']['buffer']['area_um2']))/D('.5')/D('1e6')
    for k in ('conditional_50pct_standard_area_mm2','conditional_cell_plus_macro_area_mm2'):x[k]=str(D(x[k])+delta_area)
    subtotal=sum(D(x[k]) for k in ('ungated_clock_W','all_state_leakage_upper_W','selected_data_internal_upper_W','data_pin_upper_W'))
    x['priced_clock_leak_data_pin_subtotal_W']=str(subtotal)
    x['priced_all_output_ceiling_subtotal_W']=str(subtotal+D(x['unresolved_all_output_load_ceiling_W']))
    x['schema']='w10_crom_two_operand_staging_correction_v1'
    x['staging_correction']={'old_emit_bits':old_emit,'correct_emit_bits':emit,'extra_FF_bits':extra_ff,
        'extra_NAND2_write_enable_cells':extra_nand,'extra_clock_buffers':extra_buf,
        'delta_standard_area_mm2':str(delta_area),'delta_components_W':{k:str(v) for k,v in deltas.items()},
        'reason':'Two CROM axes per emit require two FP32 operands times1024lanes times2slots, not payload-plus-address staging.'}
    x['owner_model_specification']='Ram corrected handoff:two operands*1024*32*2slots=131072emit bits; no CAM; sixteen static selected indices into135landing and16bitlane mask.'
    x['credit_route_clock_reservation']={'scope':'Separate source-bound queue/route/control state required; no free clock or power credit.',
        'credit_scenarios':[2,4,128],'actual_state_bits':None,'clock_W':None,'whole_CROM_budget_ready':False}
    x['actual_encoded_burst_model_source_pin']=None
    x['latency_source_join']='Ram encoded burst model must bind selector/fill/finite credits and route. SixteenFP32outputs/fast,672bit packets against1024link are candidate capacities only.'
    return x

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    old,op=read('cb50c5850','results/uarch/w10_crom_buffer_budget_r1/budget.json')
    power,pp=read('e79394b1c','results/uarch/w10_q_power_envelope_r1/power.json')
    clock,cp=read('fea811df4','results/uarch/w10_q_existing_icg_r1/clock.json')
    area,ap=read('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json')
    x=corrected(old,power,clock,area);x['correction_source_pins']={'original_receipt':op,'power':pp,'clock':cp,'area':ap}
    Path(a.output).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()

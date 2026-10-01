#!/usr/bin/env python3
"""Conditional FF-backed CROM buffers priced before RTL; no provider adoption."""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import subprocess

def source(commit, path):
    raw = subprocess.check_output(['git', 'show', commit + ':' + path])
    return json.loads(raw), {'commit': commit, 'path': path, 'sha256': hashlib.sha256(raw).hexdigest()}

def build(power, clock, construction):
    bits = {'two_gamma_families': 2*5*1024*32, 'two_emit_slots_payload_plus_address': 2*1024*(32+20),
            'bank_word_landing': 135*32, 'raw_macro_capture': 45*274}
    storage = sum(bits.values())
    muxes = {'sixteen_bank_select_outputs': 16*(135-1)*32, 'gamma_band_select': 2*1024*4*32,
             'storage_write_enable': storage}
    # A 2:1 mux is three NAND2 plus a tied-input NAND2 for select inverse.
    # No free write enable, signal-wire, or clock gate is assumed.
    nand = 4*sum(muxes.values())
    leaf_buffers = (storage+31)//32 + (45+2)//3
    levels = [leaf_buffers]
    while levels[-1] > 1:
        levels.append((levels[-1]+3)//4)
    if len(levels) > 14:
        raise ValueError('construction exceeds declared fourteen clock stages')
    buffers = sum(levels) + 14-len(levels)
    cs = power['conservative_coefficients']
    stcap = max(D(power['corner_coefficients'][c]['storage']['pins']['CLK']['cap_fF']) for c in ('SS','TT','FF'))
    macrocap = max(D(power['corner_coefficients'][c]['macro']['pins']['clk']['cap_fF']) for c in ('SS','TT','FF'))
    datapincap = max(D(power['corner_coefficients'][c]['storage']['pins']['D']['cap_fF']) for c in ('SS','TT','FF'))
    macropins = max(sum(D(v['cap_fF']) for k,v in power['corner_coefficients'][c]['macro']['pins'].items()
                       if v['direction']=='input' and k!='clk') for c in ('SS','TT','FF'))
    ffclk = max(D(clock['compatible_event_proof'][c]['storage']['event_cycle_fJ']['CLK']) for c in ('SS','TT','FF'))
    ffdata = max(D(clock['compatible_event_proof'][c]['storage']['event_cycle_fJ']['D']) for c in ('SS','TT','FF'))
    hz = D('1.2e9'); v = D('.77'); cv = hz*v*v*D('1e-15')
    wireclock = buffers*500*D('.145426')*2
    capclock = storage*stcap+45*macrocap+buffers*D(cs['buffer']['input_cap_fF'])
    intclock = storage*ffclk+45*D(cs['macro']['internal_cycle_fJ'])+buffers*D(cs['buffer']['internal_cycle_fJ'])
    clockW = (capclock+wireclock)*cv+intclock*hz*D('1e-15')
    dataE = storage*ffdata+nand*D(cs['nand']['internal_cycle_fJ'])
    datapins = storage*datapincap+nand*D(cs['nand']['input_cap_fF'])+45*macropins
    # The all-output ceiling is intentionally not a measured route load.
    outputceiling = storage*D(cs['storage']['output_load_ceiling_fF'])+nand*D(cs['nand']['output_load_ceiling_fF'])+45*D(cs['macro']['output_load_ceiling_fF'])
    leak = storage*D(cs['storage']['leakage_W'])+nand*D(cs['nand']['leakage_W'])+45*D(cs['macro']['leakage_W'])+buffers*D(cs['buffer']['leakage_W'])
    area = storage*D(construction['palette']['storage']['area_um2'])+nand*D(construction['palette']['nand']['area_um2'])+buffers*D(construction['palette']['buffer']['area_um2'])
    pinW = datapins*cv; intW = dataE*hz*D('1e-15'); wireW = outputceiling*cv
    return {'schema':'w10_crom_finite_buffer_reservation_v1', 'storage_bits_by_purpose':bits,'total_storage_bits':storage,
      'MUX2_bits_by_purpose':muxes,'NAND2_construction_cells':nand,'conditional_clock_buffers':buffers,
      'clock_tree_levels_before_padding':levels,'clock_depth_hypothesis':14,
      'conditional_50pct_standard_area_mm2':str(area/D('.5')/D('1e6')),
      'macro_area_mm2':str(45*D('7881.3648')/D('1e6')),
      'conditional_cell_plus_macro_area_mm2':str(area/D('.5')/D('1e6')+45*D('7881.3648')/D('1e6')),
      'frequency_Hz':str(hz),'characterized_voltage_ceiling_V':str(v),
      'ungated_clock_W':str(clockW),'all_state_leakage_upper_W':str(leak),
      'selected_data_internal_upper_W':str(intW),'data_pin_upper_W':str(pinW),
      'unresolved_all_output_load_ceiling_W':str(wireW),
      'priced_clock_leak_data_pin_subtotal_W':str(clockW+leak+intW+pinW),
      'priced_all_output_ceiling_subtotal_W':str(clockW+leak+intW+pinW+wireW),
      'macro_read_ports':45,'macro_read_bits_per_port':274,'landing_word_bits':32,
      'output_select_ports':16,'selected_payload_bits_per_fast_cycle':512,
      'emit_slots':2,'gamma_refill_bits_per_single_5120word_home':5120*32,
      'distinct_cold_gamma_homes_per_rank':81,'cold_gamma_payload_bits_per_rank':81*5120*32,
      'gamma_all_layer_reuse_credit':0,'root_stop_credit':0,'physical_admission':False,
      'actual_provider_instantiated':False,'complete_CROM_budget_qualified':False,
      'latency_source_join':'Bank selectors/fill queues/finite credits and wake/reset/drain must be priced by Ram; no parallel-read or cache latency gain is granted here.',
      'construction_scope':'FF-backed two gamma families and finite emit/landing/raw-capture buffers specified by Ram. Mux and write-enable data allocations at worst activity1. Subtotal excludes unbound control, select fanout repairs and extracted wire/glitch.',
      'remaining':['exact selector/fill/credit control and decoder cost','select high fanout driver capacity and local tracks',
                   'registered selector stages and latency','complete slot footprint/CTS/PG/SSFF/IR','full source phase/reset/glitch/RC'],
      'verdict':'FINITE_CONSTRUCTION_RESERVATION_NOT_ACTUAL_THERMAL_MINIMUM_NO_ADMISSION'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    power,ps=source('e79394b1c','results/uarch/w10_q_power_envelope_r1/power.json')
    clock,cs=source('fea811df4','results/uarch/w10_q_existing_icg_r1/clock.json')
    construction,ss=source('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json')
    _,gs=source('3fdbeb823','results/uarch/w11_crom_gamma_interleave_20261001/verification.json')
    _,rs=source('9345c1fc0','results/quality/w16_w17_whole_dsrom_candidate_20261001/candidate.json')
    x=build(power,clock,construction);x['source_pins']={'power':ps,'clock':cs,'cell_palette':ss,'gamma_protocol':gs,'CROM_provider_preflight':rs}
    x['owner_model_specification']='Ram direct handoff:327680 gamma bits/HUB,106496 emit bits,4320landing,12330rawcapture;68608bank+262144gammaMUX2bits;81coldhomes/rank.'
    Path(a.output).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()

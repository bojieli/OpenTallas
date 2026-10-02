#!/usr/bin/env python3
"""Explicit additive full-tile sizing reservation; synthesis admission only."""
import argparse,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROM='ot_rom_4096x266_m8'
KV='ot_sram_1r1w_128x256_m1_r2c2'

def price(width=96.768, clock_tracks=64, reset_tracks=64, smin=6):
    if smin != 6: raise ValueError('Current wrapper SMIN6; SMIN7 inventory cannot transfer')
    capacity={l:math.floor(math.floor(width/(pitch/1000)+1e-8)*0.5) for l,pitch in [('M6',64),('M8',80)]}
    required=1048+clock_tracks+reset_tracks
    if sum(capacity.values()) < required: raise ValueError('Undersized fill/clock/reset corridor')
    macros=[]; hashes={}
    for name,count in [(ROM,10),(KV,2)]:
        p=ROOT/'physical/asap7_memory_macros'/name/(name+'.lef');b=p.read_bytes();text=b.decode()
        w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text).groups());hashes[str(p.relative_to(ROOT))]=hashlib.sha256(b).hexdigest()
        macros.append(dict(name=name,count=count,w_um=w,h_um=h,area_um2=w*h*count,
                           PG_pins_present=all('PIN '+pin in text for pin in ('VDD','VSS')),
                           OBS_layers=re.findall(r'LAYER\s+(M\d+)\s*;',text.split('OBS',1)[1])))
    # Width widening is local to this additive candidate; baseline60 stays intact.
    slot_w=2*macros[0]['w_um']+4*4.32+width
    slot_h=1360.8
    macro_area=sum(m['area_um2'] for m in macros)
    halo_reservation=10000
    logic_capacity=(slot_w*slot_h-width*slot_h-macro_area-halo_reservation)*0.5
    cell_ceiling=125000
    if logic_capacity<cell_ceiling: raise ValueError('Conservative complete-cell reservation does not fit')
    return dict(schema='QWEN_FULLTILE_SLOT_SIZING_SUCCESSOR_V1',selection='explicit opt-in; baseline model unchanged',
      owners=dict(reset_model='Ampere6dd340d3e',persistent_KV='Russell22ec26bd2',source_context='Euclid'),
      target=dict(SMIN=6,CODE_BANKS=5,KV_NH=2,KV_VB=131072,MEM_EXTRA=1,ACC_LAT=7,TREE_LAT=7,MUL_LAT=6,FAST_ISSUE=1,KV_PREP=3,arithmetic_extra=55),
      corridor=dict(width_um=width,baseline_width_um=60,signal_share=0.5,capacity_by_layer=capacity,fill_tracks=1048,
        clock_reserved_tracks=clock_tracks,reset_reserved_tracks=reset_tracks,remaining_tracks=sum(capacity.values())-required,
        PDN_vias_OBS_reserved_fraction=0.5,actual_PDN_blockage_receipt=None,
        reservation_is_not_measured_routed_capacity=True,clock_reset_reservation_must_be_validated_downstream=True),
      slot=dict(w_um=slot_w,h_um=slot_h,area_um2=slot_w*slot_h,logic_utilization=0.5,
        macro_halo_reservation_um2=halo_reservation,available_cell_area_um2=logic_capacity,complete_cell_area_ceiling_um2=cell_ceiling,
        source_clock_bit_budget_ceiling=200000,source_async_reset_bit_budget_ceiling=100000,
        cell_budget_includes_RF_arithmetic_capture_control_reset_distribution=True,
        incremental_width_area_um2=(width-60)*slot_h,incremental_width_area_mm2_per_1536tile_die=(width-60)*slot_h*1536/1e6,
        array_area_mm2_per_1536tile_die=slot_w*slot_h*1536/1e6,die_other_services_remaining_mm2=815-slot_w*slot_h*1536/1e6,
        complete_die_and_persistent_service_fit_proven=False),
      macros=macros,source_hashes=hashes,
      boundary=dict(fill_bits_per_cycle=1048,fill_payload_bytes_per_cycle=64,MACs_per_cycle=64,replicas_per_die=1536,
        new_data_muxes=0,new_data_demuxes=0,new_rtl_cycles=0,transport_wire_delay_cycles=None,
        latency_credit=False,steady_latency_reference='Pinned +55/MEM_EXTRA1; no changed RTL/program/rounding. Wider-slot delay awaits actual contextual measurement.'),
      historical_SMIN7_counts_transferred=False,
      admission=dict(current_source_synthesis_map=True,engine_RTL=False,tile_PR=False,contextual_SSFF=False,hardware_adoption=False),
      map_acceptance=['ExactSMIN6 complete hierarchy10ROM2KV actual producer/RF/issue/capture','Current source proc widths under explicit200000clock/100000reset budgets','Complete mapped cell area <=125000um2; otherwise retainFAIL, no area-fit claim','Report actual FF/buffer survival and SS/FF pin classes; CTS/arrivals/PDN downstream'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);a=p.parse_args();s=json.dumps(price(),indent=2)+'\n'
    if a.out:
        if a.out.exists():raise SystemExit('refuse overwrite')
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(s)
    else: print(s,end='')

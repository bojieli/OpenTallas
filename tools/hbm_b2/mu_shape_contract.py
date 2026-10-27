#!/usr/bin/env python3
"""Opt-in HBM SU/MU FUSED sizing diagnostic; never a timing or release gate.

The current native FUSED source is a fixed 32-lane, eight-FP32-word design.
This catches a half-sized floorplan being compared against its full-shape
cycle measurements. It also reports the memory-port obligation when two
lanes share one bank; it does not assume that logical VM ports supply it.
"""
import argparse
import json
import math


def evaluate(lanes=16, nm=20, vector_words=5120, vm_banks=16,
             lane_width_um=345.6, lane_height_um=518.4,
             external_tree_nodes=0, hub_instances=0):
    if min(lanes, nm, vector_words, vm_banks) <= 0:
        raise ValueError('shape dimensions must be positive')
    native_lanes, words_per_sector, xslots, store_rows = 32, 8, 4, 128
    covered = lanes * words_per_sector * nm
    errors = []
    if lanes != native_lanes:
        errors.append('native top instantiates 32 lanes and a 32-chunk golden tree; provided lane count differs')
    if covered != vector_words:
        errors.append(f'provided lanes cover {covered} FP32 coordinates, requested vector has {vector_words}')
    if nm > 31:
        errors.append('native top rejects NM > 31; widening its counters requires a new implementation')
    if xslots * nm > store_rows:
        errors.append(f'KX*NM={xslots*nm} exceeds the native 128-row x-store')
    if external_tree_nodes < 28:
        errors.append('distributed implementation requires 28 external reduction nodes in addition to the hub')
    if hub_instances < 1:
        errors.append('distributed FUSED controller/scalar store/hub is absent from the sizing inventory')
    return dict(
        diagnostic='HBM native FUSED shape, not a release gate',
        shape_consistent=not errors, errors=errors,
        vector_words=vector_words, provided_lanes=lanes,
        covered_words=covered, coverage_fraction=covered/vector_words,
        nm=nm, x_store_rows=xslots*nm, native_x_store_rows=store_rows,
        native_fixed_lanes=native_lanes,
        vm_banks=vm_banks,
        max_lanes_per_bank=math.ceil(lanes/vm_banks),
        simultaneous_lane_read_demand=lanes,
        simultaneous_lane_write_demand=lanes,
        bank_calendar_status='NEEDS_NATIVE_MAPPING_AND_SLOT_CHECK',
        bank_calendar_note='32 lanes over 16 VM banks require two real lane calendars per bank; a port-name count is insufficient',
        provided_lane_outline_mm2=lanes*lane_width_um*lane_height_um/1e6,
        native32_lane_outline_mm2=native_lanes*lane_width_um*lane_height_um/1e6,
        missing_lane_outline_mm2=max(0,native_lanes-lanes)*lane_width_um*lane_height_um/1e6,
        provided_external_tree_nodes=external_tree_nodes, required_external_tree_nodes=28,
        provided_hubs=hub_instances,
        external_tree_outline_mm2=28*172.8**2/1e6,
        hub_outline_mm2=345.6**2/1e6,
        latency_status='81/103 row-II measurements require the full native shape and a compatible memory calendar',
        nm40_alternative='16 lanes * 8 words * 40 sectors cover 5120, but NM40 violates both the native NM31 bound and KX4*NM<=128',
    )


def vm_tradeoffs():
    """Capacity and service floors for the three compared physical inventories.

    Source: native q0 bank body reserves exactly one read and one write per
    bank/cycle. Existing hnx VM is 32 banks with A0/A1, C and B (four macros).
    Claude's seven-macro shape is an inferred new four-data-array controller.
    """
    cases=[]
    for name,banks,data_rows,macros,height,qualified_source in (
        ('current_B2_SU',16,1024,3,313.2,True),
        ('claude_grown16_proxy',16,4096,7,561.6,False),
        ('native_grown32',32,2048,4,403.92,True)):
        cases.append(dict(name=name,banks=banks,regular_words=banks*data_rows*8,
            macros=banks*macros,bank_outline_mm2=banks*270*height/1e6,
            full_5120_word_fused_read_floor=dict(pre=math.ceil(32*80/banks),post=math.ceil(32*100/banks)),
            existing_RTL_shape=qualified_source,
            memory_timing_and_combined_calendar_qualified=False))
    return dict(cases=cases,
        native32_extra_outline_vs_proxy_mm2=cases[2]['bank_outline_mm2']-cases[1]['bank_outline_mm2'],
        native32_extra_macros_vs_proxy=cases[2]['macros']-cases[1]['macros'],
        native32_extra_macro_area_vs_proxy_mm2=16*12317/1e6,
        inference='Two logical lanes on a 1R bank cannot sustain the native measured 81/103 row II: read floors are 160/200. Native32 has 80/100 floors, necessary but not sufficient.',
        shared_SU_blocker='Current B2 PRE/POST SFU lowering and PRE norm/gain producer join remain unqualified; dedicated FUSED is not exclusively a MU semantic requirement.',
        performance_scope='Old 16-SM CMTP rates cannot be transplanted to the current 8-SM B2 plan.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lanes',type=int,default=16)
    ap.add_argument('--nm',type=int,default=20)
    ap.add_argument('--vector-words',type=int,default=5120)
    ap.add_argument('--vm-banks',type=int,default=16)
    ap.add_argument('--external-tree-nodes',type=int,default=0)
    ap.add_argument('--hubs',type=int,default=0)
    ap.add_argument('--out')
    a=ap.parse_args()
    r=evaluate(a.lanes,a.nm,a.vector_words,a.vm_banks,
               external_tree_nodes=a.external_tree_nodes,hub_instances=a.hubs)
    r['vm_inventory_comparison']=vm_tradeoffs()
    s=json.dumps(r,indent=2)+'\n'
    if a.out:
        from pathlib import Path
        Path(a.out).write_text(s)
    print(s,end='')


if __name__=='__main__':
    main()

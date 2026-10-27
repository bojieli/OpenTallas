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
    s=json.dumps(r,indent=2)+'\n'
    if a.out:
        from pathlib import Path
        Path(a.out).write_text(s)
    print(s,end='')


if __name__=='__main__':
    main()

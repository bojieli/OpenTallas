#!/usr/bin/env python3
"""Explicit pipeline/floorplan budget for staged native SVG composition.

Stage A is the actual two-SRAM landing boundary, not full SVG hardening.
Stage B is a proposed regional pair/rotate return tree, not an implemented view.
"""
from __future__ import annotations
import json
import math


def model():
    landing_slots = [dict(pair=p, banks=[p,p+4], origin_um=[(p%2)*224.64,(p//2)*362.88],
                         outline_um=[224.64,362.88]) for p in range(4)]
    return dict(schema='opentallas.hbm-svg-regional-proposal.v1',
        opt_in_default=False,
        source_qualification='SRAM core FIFO and production landing exact+mutant proven; native boundary component Verilator5.050 exact+admission/prefetch mutants proven; whole-SVG native composition not yet proven',
        arithmetic_macs_per_cycle=0, replicas_per_SM=8, replicas_per_die=128,
        mutable_macros_per_SM=dict(landing256x256=8,response8x285_dualclock=8,
            cache128x256=5,programme1024x256=2,descriptor128x256=2,total=25),
        native_boundary=dict(input_ring_bits_per_bank=1140,
            incoming_sector_bits=285,outgoing_read_bits=256,
            write_rate_sectors_per_HBM_edge=1,
            proved_sustained_windows='12 windows,16sectors/16HBMedges each, at pins and core',
            added_ingress_HBM_edges=2,reserve_stream_edges=1,
            completion_consumer_stream_edges=1,read_result_stream_edges=2,
            overflow_HBM_edges=1,fault_stream_edges=1),
        stage_A_soft_parent_composition=dict(
            HBM_to_stream_ratio=1024/833.333,
            conservative_prefetch_added_stream_edges=math.ceil(2*1024/833.333)+1+1+2,
            selected_prefetch_margin_stream_edges=8,
            optional_KR_bridge_HBM_edges=1,
            with_KR_bridge_prefetch_edges=math.ceil(3*1024/833.333)+1+1+2,
            metadata_delay_stream_edges=2,
            cache_open_delay_stream_edges=2,
            cache_open_contract='Delay the complete OPEN envelope by the same2edges as drain sector data/labels; cache enforces fixed sector pulses from OPEN and cannot accept a gap.',
            metadata_fields=['valid','mask4','ordinal11','bank2','epoch16','last','read_mux_ordinal11'],
            protocol='Keep fixed GO and SM programme words unchanged. Delay actual landing data with metadata2edges; reserve is naturally1edge later inside the native bank and HBM response2edges later. Compiler first/fetch/ids residency margins add8edges; measure production smoke before accepting.',
            physical_scope='The aggregate still has unregistered/millimetre parent paths. This integration cannot establish physical closure.'),
        stage_B_regional_proposal=dict(
            repeatable_element='one native landing bank with actual FIFO+landing SRAMs, two local clock roots',
            paired_regions=landing_slots,
            parent_outline_um=[449.28,725.76],
            pair_select='For bankpair{j,j+4}, select the bank needed by outputlane(j-ordinal)%4; one2:1 source-local stage perpair',
            rotate='Four selected pairs undergo a registered cyclic4way rotation into four256bitsectors; static ordinal lowbits control fixed butterfly stages',
            pair_select_edges=2,ring_transport_edges=2,cache_pin_rotate_edges=3,
            local_landing_edges=2,
            proposed_additional_return_edges=7,
            selected_total_prefetch_margin_stream_edges=15,
            metadata_delay_stream_edges=7,
            source_bound_proof="ot_hbm_svg_return_regional,1632 groups,min=max7edges,threeoccupiedresets,II1; select/rotate/epoch mutants all fail",
            clocks='Separate stream roots for four pairregions and cachehub. Actual4slot fixed-latency landed crossings, no ready path across SM programme boundary. Halfcycle forwarded relay if placed reach exceeds405um.',
            region_to_center_manhattan_um=224.64/2+362.88/2,
            boundary_bits_per_region_edge=256,
            fanout_rule='Register and KEEP per32bit select copies; no select drives all256loads; validate mapped copies',
            storage_rule='Do not implement5edge285bit delaychains as flops. Use explicit4slot ring/SRAM landing and priced clocked stages.',
            qualification='PROPOSAL: area/slots, actual child clocks/reach, ring implementation, source exactness/mutants, productionbudget, CTS/route and parentnativeaudit all open'),
        price=dict(added_FIFO_macro_area_mm2_per_SM=8*4192.036416/1e6,
            added_FIFO_macro_area_mm2_per_16SM_die=128*4192.036416/1e6,
            removed_runtime_FIFO_flops_per_SM=8*2280,
            added_native_ingress_flops_per_SM=8*1140,
            net_flop_change_excluding_controls_per_SM=8*(1140-2280),
            bandwidth='Current physicalservice52B/edge finding remains. TheoreticalII1 landing capacity cannot be claimed as99B/edge service throughput.'),
        status='REGIONAL COMPOSITION MODEL BEFORE RTL; production native OPEN retry still pending; all release masters stay byte-identical')


if __name__ == '__main__':
    print(json.dumps(model(),indent=1))

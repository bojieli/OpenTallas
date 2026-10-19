#!/usr/bin/env python3
"""HBM-SMB-KITS: analytical sizing BEFORE macro-FIFO / native landing RTL.

One repeatable element is one ordinal-mod-8 landing bank. Proposals are not
physical qualification or throughput credit. The mutable payload is real SRAM.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def model():
    macro = dict(name='ot_sram_1r1w2c_8x285_m1', words=8, bits=285,
                 ports='1r1w2c', width_um=96.984, height_um=43.224,
                 area_um2=4192.036416, clk_to_q_ss_ps=322.199973,
                 source='mem_compiler.sram_gen SramSpec(8,285,mux1,1r1w2c); aligned-v2 outline')
    landing = dict(name='ot_sram_1r1w_256x256_m2_r2c2', width_um=172.824,
                   height_um=41.064, area_um2=7096.844736,
                   source='physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2')
    return dict(schema='opentallas.hbm-svg-landing-macro-proposal.v1',
        opt_in_default=False, production_shape=dict(SMs=16, banks_per_SM=8, LBANKS=4,
            sectors_per_block=272, sector_bytes=32, response_bits=285, fifo_depth=8),
        arithmetic_macs_per_cycle=0, actual_mutable_macros_per_element=[macro, landing],
        fifo_storage_bits=2280, landing_storage_bits=65536,
        fifo_macro_added_area_um2_per_SM=8*macro['area_um2'],
        fifo_macro_added_area_mm2_per_die=16*8*macro['area_um2']/1e6,
        memory_ports=dict(fifo_write_bits_per_HBM_edge=285,
                         fifo_read_bits_per_stream_edge=285,
                         landing_write_bits_per_stream_edge=256,
                         landing_read_bits_per_stream_edge=256),
        boundary_budget=dict(response_sectors_per_HBM_edge_per_bank=1,
            nominal_four_PC_sector_rate_per_HBM_edge=4,
            average_sector_rate_per_bank_per_HBM_edge=.5,
            streaming_bytes_per_edge_per_SM=99, peak_FIFO_payload_bytes_per_stream_edge_per_SM=256,
            payload_sector_util_at_price=99/256,
            channel_tracks_for_285_bits_at_048um_pitch=285,
            equivalent_single_layer_channel_width_um=285*.048,
            two_layer_pin_band_um_at_6pins_per_um=285/6),
        control_fanout=dict(binary_read_pointer_bits=3, gray_pointer_bits=4,
            macro_address_loads_per_pointer_bit=1,
            pointer_wide_mux_removed=True,
            max_critical_external_loads_target=32,
            verification='mapped kept-copy and native fanout lint required'),
        proposed_floorplan=dict(outline_um=[224.64,181.44], aspect=224.64/181.44,
            macro_origins_um=[[43.2,43.2],[43.2,129.6]],
            ordering=['landing','fifo'],
            full_width_cell_band_y_um=[84.264,129.6],
            macro_only_fill=(macro['area_um2']+landing['area_um2'])/(224.64*181.44),
            notes='generous lattice/channel envelope; mapped cell area and full-face pin fit decide final outline; no closure claim'),
        latency=dict(fifo_core_proposal_added_cycles=0,
            fifo_core_rule='continuously read look-ahead head (rd_bin+pop); current head is captured before pop, next head immediately after pop; empty visibility waits two synchronized pointer stages',
            fifo_core_qualification='UNPROVEN until old-vs-new asynchronous clock component bench, reset/wrap/stall cases and mutants',
            fallback='registered-write+RSEL2 MEMM: +1HBM write publication and +1stream read/capture, paid before local ready',
            hard_boundary_added_cycles='OPEN: per-domain pin and landed-region stages must be committed with compiler GO/reserve/fetch changes; no rate credit'),
        clock=dict(HBM_period_ps=1024,stream_period_ps=833.333,
            native_roots_per_element=2, crossing='Gray-pointer FIFO, no credit protocol change',
            reach_limit_um=405, pin_flop_spread_limit_ps=80,
            native_capture_budget_ss_ps=833.333-60-macro['clk_to_q_ss_ps']),
        qualification='MODEL ONLY. Real macro generation, causal FIFO bench/mutants, production landing exactness and 99B/edge budget, hierarchical boundary pipeline/clock model, CTS then SS/FF route all open')


if __name__ == '__main__':
    print(json.dumps(model(), indent=1))

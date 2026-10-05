#!/usr/bin/env python3
"""Selected STREAM4 inline source cut and separate model, not a replacement leaf.

Extracts the original decoded-landing/arbitration/FILL_LAT pipe verbatim. It
also enumerates the actual four-stack sector mapping to find each tile's real
PC/half aperture. No new arithmetic, pipeline, ACK, physical macro or RTL
admission is supplied by this source extraction.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = "rtl/hdc/kv/ot_qwen_rt_kv_stream4_service.sv"
TOP = "rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_stream4.sv"
TILE = "rtl/hdc/ot_qwen_rom_tile_w12.sv"
MACRO = "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
HOST = "tools/runtime/qwen_baseline_ar_stream4/qwen_rom_rt_w12_stream4_fulltoken.cpp"


def section(text: str, start: str, end: str) -> str:
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError("source cut anchors must be unique")
    i, j = text.index(start), text.index(end)
    if j <= i:
        raise ValueError("source cut anchors reversed")
    return text[i:j]


def tile_apertures() -> list[list[tuple[int, int]]]:
    """All source layer sectors; exact l2port + b_tile expressions, NSTK4 only."""
    ports = [set() for _ in range(1536)]
    for sector in range(131072):
        pc = (sector & 3) * 32 + (((sector >> 15) & 1) << 4) + ((sector >> 2) & 15)
        word = sector * 2
        if word < 131072:
            t, d = (word >> 7) & 511, word & 127
            ports[(t % 48) * 32 + d // 4].add((pc, 0))
        else:
            w = word - 131072
            pos, q = (w >> 3) & 8191, w & 7
            ports[q * 128 + (pos % 512) // 4].add((pc, 0))
            ports[(q + 1) * 128 + (pos % 512) // 4].add((pc, 1))
    return [sorted(p) for p in ports]


def fixed_clock_edges(*, accepted_edge=0, fill_lat=8, same_clock=True) -> dict:
    """NBA source edge chain, conditional on every real tile clock edge occurring."""
    if fill_lat != 8:
        raise ValueError("this extraction binds selected FILL_LAT8")
    if not same_clock:
        raise ValueError("gated/other-domain consumption requires actual clock/consume provider")
    return dict(accepted_q0_edge=accepted_edge,
                q7_edge=accepted_edge+7,
                service_kvw_output_edge=accepted_edge+8,
                tile_input_capture_edge=accepted_edge+9,
                macro_masked_write_edge=accepted_edge+10,
                original_inflight_clear_edge=accepted_edge+11,
                source_simulation_only=True, physical_completion=False)


def model(root: Path = ROOT) -> dict:
    service = (root/SERVICE).read_text()
    if "ot_qwen_kv_land_merge #" in service:
        raise ValueError("selected inline service unexpectedly substituted landing leaf")
    assert "parameter integer FILL_LAT = 8" in service
    assert "wire pipe_empty = (inflight == 0) && (e_v == 0);" in service
    assert "assign kv_write_drained = (idl || posted_wb_in) ? 1'b1" in service
    aps = tile_apertures()
    sw, npc, nt, fill = 64, 128, 1536, 8
    ne = sw + 2*npc
    entry = 1+11+7+512+512
    return dict(schema="opentallas.qwen.selected_inline_landing.v1",
        source_pins={n:hashlib.sha256((root/n).read_bytes()).hexdigest()
                     for n in (SERVICE,TOP,TILE,MACRO,HOST)},
        selected=dict(G=6144,TG=4,SW=sw,NSTK=4,NPC=npc,NT=nt,FILL_LAT=fill,
                      selected_top_args_verified=False),
        physical_cut=dict(tile_replicas=nt, maximum_PC_half_sources=12,
            aperture_histogram={str(k):v for k,v in sorted(Counter(map(len,aps)).items())},
            token_source_inputs_per_tile_conservative=sw,
            token_source_inputs_reduced_by_unproven_layout=False,
            arithmetic_MACs_per_cycle=0,
            SRAM_write_ports_per_tile=2, SRAM_data_bits_per_port=256,
            SRAM_mask_bits_per_port=256, SRAM_address_bits_per_port=7,
            maximum_payload_bytes_per_tile_edge=64,
            payload_plus_mask_plus_address_enable_bits_per_tile=1032,
            additional_pipeline_edges=0, substitution_selected=False),
        existing_storage=dict(dense_network_entries=ne, entry_bits=entry,
            dense_network_register_bits=fill*ne*entry,
            original_inflight_bits=fill+3,
            half_done_bits=2*npc, original_round_robin_bits=7,
            per_tile_registered_service_output_bits=1032,
            per_tile_input_capture_bits=1032,
            added_state_bits=0, removed_state_credit_bits=0,
            charging="existing dense network is counted once; per-tile aperture is not extra replicated storage"),
        arbitration=dict(token_priority=True, rotating_PC_order=True,
            same_local_word_required=True, earlier_valid_quarter_blocks_later=True,
            both_V_halves_required_before_pop=True, original_bad_drop_pop_retained=True,
            full_original_SW_inputs_retained=True),
        acceptance=dict(accepted="e_v sampled into q_v[0] at service rising edge",
            service_output="old q_v[7] produces registered kvw_ce/address/data/mask",
            tile_capture="real tile rising edge samples kvw_* into kvw_*_q",
            SRAM_retire="real SRAM posedge w_ce_in and matching held address/data/mask",
            pipe_empty="original inflight==0 && e_v==0",
            writeback_drain="original tok_pending/tok_in/w_valid predicate, or explicit posted/ideal bypass",
            writeback_drain_is_SRAM_retirement=False,
            physical_provider_ACK_added=False,
            edge_chain=fixed_clock_edges()),
        prebuild_price=dict(added_latency_cycles=0,
            source_service_FF_floor_um2=(fill*ne*entry+fill+3+2*npc+7)*0.2916,
            service_output_FF_floor_um2_all_tiles=nt*1032*0.2916,
            tile_input_capture_FF_floor_um2_all_tiles=nt*1032*0.2916,
            added_area_credit_um2=0, removed_leaf_area_credit_um2=0,
            mux_demux_fanout_loaded_area_um2=None, local_routing_tracks_available=None,
            SRAM_pins_loads_slot=None, loaded_clock_reset_hold_area_um2=None,
            period_ps=833, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
            composed_existing_accepted_to_write_same_clock_edges=10,
            physical_consume_clock_mapping=None, added_token_latency_cycles=0,
            parent_slot_fit=False, physical_build_admitted=False),
        model_registration_owner="Maxwell",
        gate_status="SOURCE_EXTRACTION_ONLY", SSFF_closed=False, adopted=False)


def extract(out: Path, root: Path = ROOT):
    out.mkdir(parents=True, exist_ok=False)
    text = (root/SERVICE).read_text()
    cuts = {
        "token_decode.svh": section(text,"    // ---- token (stream-unit) writes:","    // ---- landed beats:"),
        "beat_decode.svh": section(text,"    // ---- landed beats:","    // ---- arbitration:"),
        "arbitration.svh": section(text,"    // ---- arbitration:","    // ---- network pipe"),
        "network.svh": section(text,"    // ---- network pipe","    // ---- write-back selection:"),
    }
    for name, cut in cuts.items():
        (out/name).write_text(cut)
    (out/"tile_apertures.json").write_text(json.dumps(tile_apertures(),separators=(",",":"))+"\n")
    (out/"model.json").write_text(json.dumps(model(root),indent=2)+"\n")
    (out/"manifest.json").write_text(json.dumps(
        {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},indent=2)+"\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", type=Path)
    args = ap.parse_args()
    if args.extract:
        extract(args.extract)
    else:
        print(json.dumps(model(),indent=2))

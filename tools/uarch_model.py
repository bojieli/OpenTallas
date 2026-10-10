#!/usr/bin/env python3
"""Microarchitecture analytical model: re-price the architecture DAG from elements, replicas, mappings,
ports, networks and wires (docs/MICROARCH_MODEL.md, AGENTS.md rule 1).

    python3 tools/uarch_model.py [--ctx 1048576] [--out results/uarch/v41_rom.json]

WHY.  tools/arch_budget_v41.py prices every node of the token DAG from die-level widths (spec.weight_macs,
spec.rom_bytes, ...): a matvec reads ROM at the WHOLE DIE's aggregate rate, activations and results cost
nothing to move, and wire delay is a separate lump (arch_lanes_v41.wire_mutation).  Composed hardware does not
work that way.  A matrix is read only as fast as the macros that hold it; its activation vector comes out of
the vector memory through a finite read port and a broadcast tree whose depth is set by the floorplan; its
results go back through a finite return network and VM write port; a stream-unit op runs at the lane count
actually built; and the index scan runs at the reader's measured sector rate.  This module keeps the
architecture's DAG, its workload and its dependency structure, and replaces each node's issue and depth with
those microarchitectural terms.  The same node therefore has an architecture price and a microarchitecture
price, and every gap between them is attributed to one named parameter.

A DESIGN is a dict of named parameters (PRESETS below): the as-built RTL (measured elements), the
architecture spec realised naively (the spec's widths but real mappings, ports and wires), and proposals.
Every constant cites its source; ASSUMED marks a number that has no measurement yet.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import hashlib
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))



def hbm_smh_result_valid_model(columns=8, row_bits=12):
    """Size the optional south-front result qualification before RTL changes."""
    if columns < 1 or row_bits < 1:
        raise ValueError("positive shape required")
    return dict(schema="opentallas.smh-result-valid.v1", opt_in_default=False,
        master="ot_hbm_accel_smh_front_s", columns=columns,
        macs_per_cycle=0, memory_bytes_per_cycle=0,
        existing_result_bits_per_cycle=columns*(34+row_bits),
        added_boundary_bits_per_cycle=0, added_data_registers=0,
        qualification_and_gates=columns,
        reduction_gate_upper_bound=4*columns, replicas=1,
        mux_demux_cost=0, control_fanout_max=2,
        local_routing_tracks_upper_bound=3*columns,
        floorplan_slot_fit="existing south-front result landing; <=5*columns small gates, physical route required",
        added_cycles=0, token_latency_added_ns=0.0,
        correctness="fault only with own-column valid; row retires only with all columns valid; any partial valid vector raises fault",
        physical_gate="refresh full NC8 front_s timing/DRC with RESULT_VALID=1; unchanged BE/tile closures do not qualify it")


def hbm_visibility_fence_pin_return_model():
    """Default-off output registers with registered accepted-beat credit return."""
    from tools.hbm_fence_pin_return_model import model
    return model()


def hbm_collective_port2_tiles_model():
    """Pair two independently hardened protected halves without seam traffic."""
    from tools.hbm_coll_port2_tiles_model import model
    return model()


def qwen_result_slot_conveyor_model(ns=8, db=64, rs=42, crb=16):
    """Full-shape structural successor; price before RTL, no adoption credit."""
    assert ns == 8 and db == 64 and crb >= ns
    latency = 2*ns + 5
    slot_w, slot_h = 259.2, 324.0
    boundary = 1+3+6 + 1+1+1+20+16+512
    ff = 64*38 + 3*557 + 2*551 + 8*38 + 38 + 2*10 + 32
    return dict(schema='opentallas.qwen_result_slot_conveyor.v1',
        adopted=False, default_off=True, models=['Qwen3-8B ROM'],
        MACs_per_cycle=0, compute_intensity_MACs_per_byte=0,
        replicas=dict(bands=6,slots_per_band=ns,total_slot_macros=6*ns),
        memory=dict(bytes_per_write_cycle=64,bytes_per_read_cycle=64,
                    macro='ot_sram_1r1w_64x512_m1_r2c2',depth=db),
        boundary=dict(request_bits_per_cycle=10,response_bits_per_cycle=551,
                      producer_bits_per_slot=557,credit_bits_per_cycle=1),
        routing=dict(estimated_tracks=boundary,available_tracks=int(2*slot_h/.064*.70),
                     pin_layers=['M4','M6','M5','M7']),
        replicas_cost=dict(global_data_mux_inputs=0,local_response_mux_inputs=2,
                            metadata_read_mux_levels=[8,8],control_fanout='local pin seat per slot'),
        area=dict(slot_um=[slot_w,slot_h],slot_area_um2=slot_w*slot_h,
                  macro_area_um2=171.288*77.760,estimated_FF=ff,
                  FF_area_proxy_um2=ff*DFF_UM2,controller_slot_um=[216,216],
                  band_area_um2=ns*slot_w*slot_h+216*216,physical_fit=False),
        latency=dict(request_to_response_cycles=latency,burst_issue_cycles=ns,
                     worst_full_burst_response_cycles=latency+ns-1,
                     ingress_to_request_cycles=3,ingress_to_first_slot0_output_cycles=latency+3,
                     ingress_to_first_slot7_or_empty_output_cycles=latency+10,
                     baseline_first_beat_cycles=5,added_first_beat_cycles_min=latency+3-5,
                     added_first_beat_cycles_max=latency+10-5,
                     token_cost='+19..26 first-beat edges according to first used slot; sparse slots still consume issue tokens; measured landed token bench required',
                     stall_budget_edges=rs,store_headroom_bursts=5,
                     ready_threshold=db-rs-5),
        capacity=dict(credits=crb,reserve_per_request=1,disabled_slot_refund=True,
                      measured_full_burst_span_cycles=4311/359,
                      measured_empty_burst_span_cycles=4139/359,
                      measured_profile_bursts=360,
                      profile_scope='saturated element, immediate consumer credit, full shape actual SRAM model; not token rate'),
        exact_gate='full NS8 DB64 RS42 CRB16 ordered burst scoreboard, stalls, wrap, pause, reset, true mutants')


def hbm_svc_dma_wide_admission_model(**kwargs):
    """Actual four-stack HBM bandwidth/window/corridor/SRAM admission sizing."""
    from hbm_svc_dma_wide_model import wide_model
    return wide_model(**kwargs)

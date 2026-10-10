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

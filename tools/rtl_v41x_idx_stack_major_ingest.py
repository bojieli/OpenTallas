#!/usr/bin/env python3
"""Bounded stack-major index ingest gate; no chip-rate inference."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "rtl/hdc/v41x/ot_hdc_v41x_idx_stack_major_ingest.sv",
    "rtl/test/tb_hdc_v41x_idx_stack_major_ingest.sv",
    "tools/rtl_v41x_idx_stack_major_ingest.py",
)


def score_key(bits: int) -> int:
    if bits & 0x7FFF == 0:  # -0 and +0 are equal
        bits = 0
    return (~bits & 0xFFFF) if bits & 0x8000 else (bits ^ 0x8000)


def global_index(stack: int, local: int) -> int:
    return 64 * (local >> 4) + 16 * stack + (local & 15)


def check_topk(n: int, k: int) -> dict:
    # Finite positive/negative BF16 values and frequent equal-score ties.
    bits = [((i * 173 + (i >> 5) * 11) % 1536) +
            (0xB900 if i & 1 else 0x3900) for i in range(n)]
    for i in range(0, n, 97):
        bits[i] = 0x8000 if (i // 97) & 1 else 0
    def ordered(indices):
        return sorted(indices, key=lambda i: (-score_key(bits[i]), i))[:k]
    global_winners = ordered(range(n))
    local_winners = []
    for stack in range(4):
        local_winners.extend(ordered(
            global_index(stack, j) for j in range((n + 63) // 64 * 16)
            if global_index(stack, j) < n
        ))
    merged_winners = ordered(local_winners)
    assert merged_winners == global_winners
    return {"nkeys": n, "k": k, "local_survivor_bound": 4 * k,
            "winner_digest": hashlib.sha256(
                ",".join(map(str, global_winners)).encode()).hexdigest()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "results/rtl/v41_idx_stack_major_ingest.json")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "tb"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_stack_major_ingest",
                        "-o", str(exe), str(ROOT / SOURCES[0]), str(ROOT / SOURCES[1])], check=True)
        sim = subprocess.run(["vvp", str(exe)], check=True, capture_output=True, text=True)
    m = re.fullmatch(r"PASS stack-major ingest beats=(\d+) keys=(\d+)\n", sim.stdout)
    assert m, sim.stdout
    ys = subprocess.run(["yosys", "-Q", "-T", "-p",
                         f"read_verilog -sv {ROOT / SOURCES[0]}; "
                         "hierarchy -top ot_hdc_v41x_idx_stack_major_ingest; "
                         "synth -top ot_hdc_v41x_idx_stack_major_ingest; stat"],
                        check=True, capture_output=True, text=True)
    cell_matches = re.findall(r"Number of cells:\s+(\d+)", ys.stdout)
    flop_matches = re.findall(r"\$_DFF_PN0_\s+(\d+)", ys.stdout)
    assert cell_matches and flop_matches
    rows = [check_topk(1040, 512), check_topk(262144, 512)]
    record = {
        "scope": "standalone bounded 16-key ingress and mathematical local-topK-union proof; no score RTL, selector merge, HBM integration or routed rate",
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
        "rtl_gate": {"beats": int(m[1]), "keys": int(m[2]), "atomic_four_lane_handshake": True,
                     "local_rank_to_global_index": True, "tested_nkeys": [1040, 262144]},
        "generic_synthesis": {"yosys_cells": int(cell_matches[-1]),
                              "yosys_reset_flops": int(flop_matches[-1]),
                              "scope": "ingress control only; excludes score arithmetic, selector, HBM, and physical routing"},
        "topk_proof": rows,
        "design": {"keys_per_beat": 16, "score_lanes": 4, "keys_per_lane": 4,
                   "score_order": "stack local-rank ascending; global index reconstructed as 64*(j>>4)+16*s+(j&15)",
                   "selector_plan": "four independent local top-512 selectors, then exact global top-512 from at most 2048 survivors, tie by lower global index; emit selected indices ascending",
                   "bounded_score_index_storage_bits": 4 * 512 * (16 + 30),
                   "raw_key_buffer_bits": 0},
        "limits": ["score tile throughput not measured", "cross-stack survivor selector not implemented",
                   "HBM same-controller rate and physical timing not measured"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()

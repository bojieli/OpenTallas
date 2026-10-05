#!/usr/bin/env python3
"""Source-pinned full-geometry pipelined index score slice gate."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    "rtl/hdc/v41x/ot_hdc_v41x_idx_score_quarter.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_score_slice.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv",
    "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/hdc/ot_hdc_delay.sv",
    "rtl/test/tb_hdc_v41x_idx_score_slice.sv",
    "tools/rtl_v41x_idx_score_slice.py",
]
PAT = re.compile(r"PASS score slice sent=(\d+) got=(\d+) first_output_cycle=(\d+) total_cycles=(\d+) input_stalls=(\d+)\n")


def run(nk: int, stalled: bool, out: Path) -> dict:
    exe = out / f"tb{nk}"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_score_slice",
                    f"-Ptb_hdc_v41x_idx_score_slice.NK={nk}", "-o", str(exe),
                    *[str(ROOT / p) for p in SOURCES if p.endswith(".sv")]], check=True)
    sim = subprocess.run(["vvp", str(exe), *([] if stalled else ["+NOSTALL"])],
                         check=True, capture_output=True, text=True)
    m = PAT.fullmatch(sim.stdout)
    assert m, sim.stdout
    sent, got, first, total, stalls = map(int, m.groups())
    assert sent == got == 128
    return {"nk": nk, "stalled": stalled, "beats": got, "keys": got * nk,
            "first_output_cycle": first, "total_cycles": total,
            "input_stalls": stalls, "steady_state_ii": 1 if not stalled and stalls == 0 else None}


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        rows = [run(1, True, tmp), run(4, False, tmp)]
        subprocess.run(["iverilog", "-g2012", "-s", "ot_hdc_v41x_idx_score_quarter",
                        "-Pot_hdc_v41x_idx_score_quarter.NK=1", "-o", str(tmp / "quarter1"),
                        *[str(ROOT / p) for p in SOURCES if p.endswith(".sv")]], check=True)
    earlier = json.loads((ROOT / "results/rtl/hdc_v41x_idx_campaign.json").read_text())
    arithmetic = SOURCES[2:6]
    assert all(earlier["sources"][p] == hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
               for p in arithmetic)
    nk = 4
    q4dot_per_slice = nk * 32 * 4
    logical_macs_per_slice = q4dot_per_slice * 32
    record = {
        "schema": "opentallas.v41-idx-score-slice.v1",
        "status": "standalone_exact_simple_vectors_and_backpressure",
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
        "upstream_arithmetic_gate": {"record": "results/rtl/hdc_v41x_idx_campaign.json",
                                     "shipped_16384_key_back_to_back_errors": earlier["shipped"]["back_to_back"]["errors"],
                                     "source_hashes_match": True},
        "rtl_cases": rows,
        "quarter_elaboration": {"slices": 4, "nk_per_slice": 1, "iverilog": "pass"},
        "numerics": "32 heads x 128 E2M1 FP4 dims, four 32-element scaled blocks/head; sequential block adds, BF16 ReLU-weight terms, chunk-8 head sums and fixed pairwise chunk tree; dense code-2/zero vectors, mask, refusal and backpressure",
        "resource_contract": {
            "nk_per_slice": nk, "q4dot_instances_per_slice": q4dot_per_slice,
            "logical_fp4_macs_per_cycle_per_slice": logical_macs_per_slice,
            "query_register_bits_per_slice": 32 * (4 * (128 + 8) + 16),
            "key_input_bits_per_cycle_per_slice": nk * 4 * 136,
            "slices_for_32_keys_per_cycle": 8,
            "slices_for_64_keys_per_cycle": 16,
            "logical_macs_at_32_keys_per_cycle": 8 * logical_macs_per_slice,
            "logical_macs_at_64_keys_per_cycle": 16 * logical_macs_per_slice,
            "scan_compute_floor_cycles_at_262144_keys_32kpc": 262144 // 32,
            "scan_compute_floor_cycles_at_262144_keys_64kpc": 262144 // 64},
        "reader_comparison": {"four_stack_exact_262144_key_cycles": 9278,
                              "record": "reader owner source-pinned campaign pending publication",
                              "interpretation": "32-score/cycle slice assembly could match this reader's mean 28.25 keys/cycle; 64-score/cycle assembly is needed only if reader bandwidth rises toward model target"},
        "limits": ["NK=4 simple-vector wrapper gate; broader real-vector arithmetic exactness inherited from source-matched engine campaign",
                   "four-quarter score assembly and selector connection not yet built",
                   "reader+score+selector same-controller gate and physical route not measured"]}
    target = ROOT / "results/rtl/v41_idx_score_slice.json"
    target.write_text(json.dumps(record, indent=2) + "\n")
    print(target)


if __name__ == "__main__":
    main()

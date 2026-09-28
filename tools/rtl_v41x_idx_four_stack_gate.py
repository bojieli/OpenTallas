#!/usr/bin/env python3
"""Source-pinned four-stack, sixteen-range, timed-HBM exact read gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / p for p in (
    "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_range.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_range_pc_arb.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_quarter_ranges.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_quarter_collect.sv",
    "rtl/test/tb_hdc_v41x_idx_four_stack_gate.sv",
)]
OUT = ROOT / "results/rtl/hdc_v41x_idx_four_stack_gate.json"
PAT = re.compile(
    r"V41X_FOUR_STACK_PASS n=(\d+) quantum=(\d+) checked=(\d+) "
    r"sectors=(\d+) cycles=(\d+) stalled=(\d+) request_stalls=(\d+) output_stalls=(\d+)"
)


def rank(x: int, stack: int) -> int:
    full, rem = divmod(x, 64)
    return 16 * full + max(0, min(16, rem - 16 * stack))


def expected_sectors(n: int) -> int:
    qs = 8 * (n // 32)
    total = 0
    for stack in range(4):
        for quarter in range(4):
            first = rank(quarter * qs, stack)
            last = rank(n if quarter == 3 else (quarter + 1) * qs, stack)
            if last > first:
                total += 2 * (last - first) + (last + 7) // 8 - first // 8
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="also run exact N262144 scan")
    parser.add_argument("--quantum", type=int, default=1)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    rows = []
    with tempfile.TemporaryDirectory(prefix="v41-four-stack-") as td:
        for n in (65, 1040, 262_144) if args.full else (65, 1040):
            binary = Path(td) / f"n{n}.vvp"
            subprocess.run([
                "iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_four_stack_gate",
                f"-Ptb_hdc_v41x_idx_four_stack_gate.NKEYS={n}",
                f"-Ptb_hdc_v41x_idx_four_stack_gate.QUANTUM={args.quantum}",
                "-o", str(binary), *map(str, SOURCES),
            ], check=True, cwd=ROOT)
            started = time.perf_counter()
            run = subprocess.run(["vvp", str(binary)], capture_output=True, text=True,
                                 timeout=7200 if args.full else 300, cwd=ROOT)
            wall_seconds = round(time.perf_counter() - started, 3)
            if run.returncode:
                raise RuntimeError(f"N{n} failed:\n{run.stdout}\n{run.stderr}")
            match = PAT.search(run.stdout)
            if not match:
                raise RuntimeError(f"N{n} missing pass marker:\n{run.stdout}")
            keys, quantum, checked, sectors, cycles, stalled, req_stalls, out_stalls = map(int, match.groups())
            assert (keys, quantum, checked, sectors) == (n, args.quantum, n, expected_sectors(n))
            rows.append({
                "keys": keys, "quantum": quantum, "checked": checked,
                "sectors": sectors, "cycles": cycles,
                "simulation_wall_seconds": wall_seconds,
                "sector_per_cycle": round(sectors / cycles, 6),
                "collector_empty_cycles": stalled,
                "request_stall_cycles": req_stalls,
                "response_stall_cycles": out_stalls,
            })
            print(run.stdout.strip(), flush=True)
    script = Path(__file__).resolve()
    rec = {
        "schema": "opentallas.hdc-v41x-idx-four-stack-gate.v1",
        "status": "pass",
        "source_baseline": "6e2b7ae38fe3019e38d2574ffad9df89538bd08a",
        "collector_source_commits": ["a1843d61", "c00a0141"],
        "configuration": {
            "stacks": 4, "quarter_contexts_per_stack": 4,
            "physical_pseudo_channels_per_stack": 32,
            "streamer_WB": 32, "streamer_GA": 24,
            "hbm_QD": 64, "hbm_RQD": 32, "hbm_REFPB": 3,
            "physical_TAGW": 16, "quantum": args.quantum,
            "collector_output_keys_per_beat": 64,
        },
        "cases": rows,
        "coverage": "All collector output keys, valid masks, final markers and ref bits checked against independently generated timed-HBM sector pattern; sector count checked independently from 16 stack-local range endpoints.",
        "limitations": "Behavioral HBM and partitioned per-context ROB; no physical timing, power, array token or model throughput claim. Full 262144-key result is present only when run with --full.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [*SOURCES, script]},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2) + "\n")


if __name__ == "__main__":
    main()

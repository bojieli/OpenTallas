#!/usr/bin/env python3
"""Timed HBM queue/window sensitivity for the V4.1 sharded range reader."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import rtl_v41x_idx_range_pc_arb as baseline

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/hdc_v41x_idx_range_pc_queue.json"
CASES = ((262144, 32, 24, 128, 128, 16),
         (262144, 32, 24, 128, 128, 32))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41-range-queue-") as d:
        with ThreadPoolExecutor(max_workers=2) as pool:
            cases = list(pool.map(lambda c: baseline.run_case(Path(d), *c), CASES))
    assert all(r["stack_keys"] == 65536 and r["sectors"] == 139264 for r in cases)
    script = Path(__file__).resolve()
    inputs = [*baseline.SOURCES, Path(baseline.__file__), script]
    record = {
        "schema": "opentallas.hdc-v41x-idx-range-pc-queue.v1",
        "status": "exact",
        "tools": {
            "iverilog": subprocess.run(["iverilog", "-V"], capture_output=True,
                                      text=True, check=True).stdout.splitlines()[0],
            "vvp": subprocess.run(["vvp", "-V"], capture_output=True,
                                 text=True, check=True).stderr.splitlines()[0],
        },
        "cases": cases,
        "baseline_record": "results/rtl/hdc_v41x_idx_range_pc_arb.json",
        "one_stack_adopted_effective_cap_sectors_per_cycle": 25.875,
        "coverage": "The Q128/WB32/GA24 range reader reads every wanted key and sector exactly on one timed 32-PC HBM stack. QD128 with RW16 and RW32 is compared against the pinned QD64/RW16 baseline; each option is a distinct controller-capacity configuration.",
        "limitation": "Controller queue capacity and FR-FCFS search window are simulation parameters, not yet synthesized or routed at these sizes. No four-stack/collector result or adopted model rate follows from this record.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in inputs},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2) + "\n")
    for row in cases:
        print(f"PASS QD={row['hbm_queue_depth_sectors_per_pc']} RW={row['hbm_frfcfs_window']} "
              f"{row['sectors']}/{row['cycles']}={row['sectors_per_cycle']} sectors/cycle")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Cross-check the exact four-stack timed gate in Verilator, then run full scan."""
from __future__ import annotations

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
    "rtl/test/tb_hdc_v41x_idx_four_stack_verilator.sv",
)]
CPP = ROOT / "rtl/test/hdc_v41x_idx_four_stack_verilator.cpp"
OUT = ROOT / "results/rtl/hdc_v41x_idx_four_stack_verilator.json"
PAT = re.compile(r"V41X_FOUR_STACK_PASS n=(\d+) quantum=(\d+) checked=(\d+) sectors=(\d+) cycles=(\d+) stalled=(\d+) request_stalls=(\d+) output_stalls=(\d+)")


def rank(x: int, s: int) -> int:
    full, rem = divmod(x, 64)
    return 16 * full + max(0, min(16, rem - 16 * s))


def sectors(n: int) -> int:
    qs = 8 * (n // 32)
    result = 0
    for s in range(4):
        for q in range(4):
            lo = rank(q * qs, s)
            hi = rank(n if q == 3 else (q + 1) * qs, s)
            if hi > lo:
                result += 2 * (hi - lo) + (hi + 7) // 8 - lo // 8
    return result


def main() -> None:
    rows = []
    with tempfile.TemporaryDirectory(prefix="v41-four-vlt-") as td:
        for n in (65, 1040, 262_144):
            obj = Path(td) / f"obj{n}"
            cmd = ["verilator", "--cc", "--exe", "--build", "-j", "4",
                   "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNOPTFLAT",
                   "--top-module", "tb_hdc_v41x_idx_four_stack_verilator",
                   f"-GNKEYS={n}", "-GQUANTUM=64", "--Mdir", str(obj),
                   *map(str, SOURCES), str(CPP)]
            started = time.perf_counter()
            build = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT,
                                   timeout=3600)
            if build.returncode:
                raise RuntimeError(f"Verilator build N{n} failed:\n{build.stdout[-4000:]}\n{build.stderr[-4000:]}")
            build_wall = round(time.perf_counter() - started, 3)
            binary = obj / "Vtb_hdc_v41x_idx_four_stack_verilator"
            started = time.perf_counter()
            run = subprocess.run([str(binary)], capture_output=True, text=True,
                                 cwd=ROOT, timeout=7200)
            if run.returncode:
                raise RuntimeError(f"Verilator N{n} failed:\n{run.stdout[-4000:]}\n{run.stderr[-4000:]}")
            sim_wall = round(time.perf_counter() - started, 3)
            m = PAT.search(run.stdout)
            if not m:
                raise RuntimeError(f"Verilator N{n} missing pass marker:\n{run.stdout[-4000:]}")
            keys, quantum, checked, got_sectors, cycles, stalled, req_stalls, out_stalls = map(int, m.groups())
            assert (keys, quantum, checked, got_sectors) == (n, 64, n, sectors(n))
            if n in (65, 1040):
                assert cycles == {65: 82, 1040: 149}[n], (n, cycles)
            row = {"keys": n, "checked": checked, "sectors": got_sectors,
                   "cycles": cycles, "sector_per_cycle": round(got_sectors / cycles, 6),
                   "collector_empty_cycles": stalled, "request_stall_cycles": req_stalls,
                   "response_stall_cycles": out_stalls,
                   "build_wall_seconds": build_wall, "simulation_wall_seconds": sim_wall}
            rows.append(row)
            print(run.stdout.strip(), flush=True)
    script = Path(__file__).resolve()
    rec = {
        "schema": "opentallas.hdc-v41x-idx-four-stack-verilator.v1",
        "status": "pass", "source_baseline": "6e2b7ae38fe3019e38d2574ffad9df89538bd08a",
        "simulator": "Verilator", "configuration": {"stacks": 4, "contexts_per_stack": 4,
            "WB": 32, "GA": 24, "quantum": 64, "hbm_QD": 64, "hbm_RQD": 32, "hbm_REFPB": 3},
        "cases": rows,
        "coverage": "Same six RTL modules and exact key/mask/last/reference-bit testbench checks as Icarus gate; external C++ clock/reset/command driver; short-case cycle equality required before full run.",
        "limitation": "Behavioral timed HBM; no physical or model throughput claim.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [*SOURCES, CPP, script]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Stream pinned full-scan four-stack progress and collect per-stack counters."""
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
    "rtl/test/tb_hdc_v41x_idx_four_stack_diag.sv",
)]
OUT = ROOT / "results/rtl/hdc_v41x_idx_four_stack_q64_diag.json"


def rank(x: int, s: int) -> int:
    full, rem = divmod(x, 64)
    return 16 * full + max(0, min(16, rem - 16 * s))


def expected_stack_sectors(n: int, s: int) -> int:
    qs = 8 * (n // 32)
    total = 0
    for q in range(4):
        first = rank(q * qs, s)
        last = rank(n if q == 3 else (q + 1) * qs, s)
        if last > first:
            total += 2 * (last - first) + (last + 7) // 8 - first // 8
    return total


def main() -> None:
    n = 262_144
    with tempfile.TemporaryDirectory(prefix="v41-four-diag-") as td:
        binary = Path(td) / "full.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_four_stack_diag",
                        f"-Ptb_hdc_v41x_idx_four_stack_diag.NKEYS={n}",
                        "-Ptb_hdc_v41x_idx_four_stack_diag.QUANTUM=64",
                        "-o", str(binary), *map(str, SOURCES)], check=True, cwd=ROOT)
        started = time.perf_counter()
        process = subprocess.Popen(["vvp", str(binary)], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, cwd=ROOT)
        assert process.stdout is not None
        lines = []
        for line in process.stdout:
            line = line.rstrip()
            print(line, flush=True)
            lines.append(line)
        rc = process.wait()
        wall = round(time.perf_counter() - started, 3)
        if rc:
            raise RuntimeError(f"full diag failed rc={rc}: " + "\n".join(lines[-20:]))
    whole = re.search(r"V41X_FOUR_STACK_PASS n=(\d+) quantum=(\d+) checked=(\d+) sectors=(\d+) cycles=(\d+) stalled=(\d+) request_stalls=(\d+) output_stalls=(\d+)", "\n".join(lines))
    stacks = [tuple(map(int, m.groups())) for m in re.finditer(
        r"V41X_DIAG_STACK stack=(\d+) sectors=(\d+) grants=(\d+)", "\n".join(lines))]
    stall = re.search(r"V41X_DIAG_STALL stream=(\d+) collector=(\d+) request=(\d+) response=(\d+) output_beats=(\d+)", "\n".join(lines))
    if not whole or not stall or len(stacks) != 4:
        raise RuntimeError("missing full diagnostic marker")
    wn, quantum, checked, sectors, cycles, collector_empty, req_stalls, rsp_stalls = map(int, whole.groups())
    assert (wn, quantum, checked) == (n, 64, n)
    assert [s for _, s, _ in stacks] == [expected_stack_sectors(n, i) for i in range(4)]
    assert sectors == sum(s for _, s, _ in stacks)
    stream_stall, collector_stall, req_stall, rsp_stall, output_beats = map(int, stall.groups())
    assert (collector_stall, req_stall, rsp_stall, output_beats) == (collector_empty, req_stalls, rsp_stalls, 4096)
    script = Path(__file__).resolve()
    rec = {
        "schema": "opentallas.hdc-v41x-idx-four-stack-q64-diag.v1",
        "status": "pass", "source_baseline": "6e2b7ae38fe3019e38d2574ffad9df89538bd08a",
        "nkeys": n, "checked_keys": checked, "sectors": sectors, "cycles": cycles,
        "simulation_wall_seconds": wall, "sectors_per_cycle": round(sectors / cycles, 6),
        "per_stack": [{"stack": i, "sectors": s, "pc_request_grants": g} for i, s, g in stacks],
        "collector_output_beats": output_beats, "stream_stall_cycles": stream_stall,
        "collector_empty_cycles": collector_stall, "request_stall_cycles": req_stall,
        "response_stall_cycles": rsp_stall,
        "progress": [line for line in lines if line.startswith("V41X_DIAG_PROGRESS")],
        "limitations": "Behavioral timed HBM, partitioned per-context ROB; no physical or model throughput claim.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [*SOURCES, script]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")


if __name__ == "__main__":
    main()

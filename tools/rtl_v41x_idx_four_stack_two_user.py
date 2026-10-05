#!/usr/bin/env python3
"""Exact four-stack two-user base-address separation gate."""
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
    "rtl/test/tb_hdc_v41x_idx_four_stack_two_user.sv",
)]
OUT = ROOT / "results/rtl/hdc_v41x_idx_four_stack_two_user.json"
PAT = re.compile(r"V41X_TWO_USER_PASS user=(\d+) base_sector=(\d+) n=(\d+) checked=(\d+) sectors=(\d+) cycles=(\d+)")


def rank(x: int, stack: int) -> int:
    full, rem = divmod(x, 64)
    return 16 * full + max(0, min(16, rem - 16 * stack))


def sectors(n: int) -> int:
    qs = 8 * (n // 32)
    total = 0
    for s in range(4):
        for q in range(4):
            first = rank(q * qs, s)
            last = rank(n if q == 3 else (q + 1) * qs, s)
            if last > first:
                total += 2 * (last - first) + (last + 7) // 8 - first // 8
    return total


def main() -> None:
    rows = []
    with tempfile.TemporaryDirectory(prefix="v41-two-user-") as tmp:
        for n in (65, 1040):
            binary = Path(tmp) / f"n{n}.vvp"
            subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_four_stack_two_user",
                            f"-Ptb_hdc_v41x_idx_four_stack_two_user.NKEYS={n}",
                            "-o", str(binary), *map(str, SOURCES)], check=True, cwd=ROOT)
            started = time.perf_counter()
            run = subprocess.run(["vvp", str(binary)], capture_output=True, text=True,
                                 timeout=600, cwd=ROOT)
            if run.returncode:
                raise RuntimeError(f"N{n} failed:\n{run.stdout}\n{run.stderr}")
            parsed = [tuple(map(int, m.groups())) for m in PAT.finditer(run.stdout)]
            expected = [(u, 2176 * u, n, n, sectors(n)) for u in (0, 1)]
            assert [r[:5] for r in parsed] == expected, (parsed, expected, run.stdout)
            assert "ot_hdc_v41x_idx_hbm: request on port" not in run.stdout, run.stdout
            rows.append({"keys_per_user": n, "users": [
                {"user": r[0], "base_sector": r[1], "checked": r[3], "sectors": r[4], "cycles": r[5]}
                for r in parsed], "simulation_wall_seconds": round(time.perf_counter() - started, 3)})
            print(run.stdout.strip(), flush=True)
    script = Path(__file__).resolve()
    record = {
        "schema": "opentallas.hdc-v41x-idx-four-stack-two-user.v1",
        "status": "pass", "arbiter_source_commit": "6e2b7ae38fe3019e38d2574ffad9df89538bd08a",
        "configuration": {"stacks": 4, "contexts_per_stack": 4, "WB": 32, "GA": 24,
                          "quantum": 1, "hbm_QD": 64, "hbm_RQD": 32, "hbm_REFPB": 3,
                          "base_sectors": [0, 2176]},
        "cases": rows,
        "coverage": "Two sequential users in one live timed-HBM simulation, no reset between users. Every output key, valid mask, last marker, and reference bit exact against distinct address-derived images; every accepted burst maps to its physical pseudo-channel; independent sector totals per user.",
        "limitation": "Behavioral HBM, two users run sequentially, short scans only; no physical timing or model throughput claim.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [*SOURCES, script]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()

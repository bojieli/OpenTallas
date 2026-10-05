#!/usr/bin/env python3
"""Check 16 compact index quarter ranges against an independent rank map."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_quarter_ranges.sv"
TB = ROOT / "rtl/test/tb_hdc_v41x_idx_quarter_ranges.sv"
OUT = ROOT / "results/rtl/hdc_v41x_idx_quarter_ranges.json"
LENGTHS = [*range(1, 129), 255, 256, 263, 1023, 1024, 1031, 1040,
           262_144, 1_000_000, 1_048_576]


def rank(x: int, stack: int) -> int:
    full, rem = divmod(x, 64)
    return 16 * full + max(0, min(16, rem - 16 * stack))


def global_from_local(local: int, stack: int) -> int:
    return 64 * (local // 16) + 16 * stack + local % 16


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41-quarter-ranges-") as t:
        tmp = Path(t)
        binary, vectors = tmp / "sim.vvp", tmp / "vectors.txt"
        vectors.write_text("".join(f"{n}\n" for n in LENGTHS))
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_quarter_ranges",
                        "-o", str(binary), str(RTL), str(TB)], check=True, cwd=ROOT)
        run = subprocess.run(["vvp", str(binary), f"+vectors={vectors}"],
                             check=True, capture_output=True, text=True, timeout=120, cwd=ROOT)
    lines = [tuple(map(int, line.split()[1:])) for line in run.stdout.splitlines()
             if line.startswith("R ")]
    assert len(lines) == len(LENGTHS) * 16
    for n in LENGTHS:
        rows = lines[LENGTHS.index(n) * 16:(LENGTHS.index(n) + 1) * 16]
        qs = 8 * (n // 32)
        for stack in range(4):
            prev = None
            for quarter in range(4):
                row = rows[4 * stack + quarter]
                first_global = quarter * qs
                last_global = n if quarter == 3 else first_global + qs
                first, last = rank(first_global, stack), rank(last_global, stack)
                want = (n, 4 * stack + quarter, first, last - first,
                        1088 + 17 * (first // 1024), first % 1024)
                assert row == want, (row, want)
                if prev is not None:
                    assert first == prev
                prev = last
                if n <= 128:
                    got = {global_from_local(i, stack) for i in range(first, last)}
                    expected = {i for i in range(first_global, last_global)
                                if (i // 16) % 4 == stack}
                    assert got == expected, (n, stack, quarter)
            assert prev == rank(n, stack)
    script = Path(__file__).resolve()
    rec = {
        "schema": "opentallas.hdc-v41x-idx-quarter-ranges.v1", "status": "pass",
        "scan_lengths": len(LENGTHS), "contexts_checked": len(lines),
        "largest_scan_keys": max(LENGTHS),
        "coverage": "Sixteen (stack,quarter) contiguous local-key ranges, exact base-block/skip, per-stack adjacency, exhaustive 1..128 key ownership and sampled 1M geometry; includes Qs mod16=8 and 1024-key boundary.",
        "limitation": "Geometry only. No multi-context HBM arbiter, skip/shift collector, four-stack throughput, token gate or physical closure.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in (RTL, TB, script)},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(f"PASS {len(lines)} context vectors across {len(LENGTHS)} scan lengths")


if __name__ == "__main__":
    main()

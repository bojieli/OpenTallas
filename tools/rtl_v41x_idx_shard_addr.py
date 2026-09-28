#!/usr/bin/env python3
"""Exhaustive small-shape and sampled 1M address gate for sharded index reads."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_addr.sv"
TB = ROOT / "rtl/test/tb_hdc_v41x_idx_shard_addr.sv"
OUT = ROOT / "results/rtl/hdc_v41x_idx_shard_addr.json"
LENGTHS = (1, 7, 8, 9, 15, 16, 17, 31, 32, 39, 40, 63, 64, 65,
           127, 128, 1023, 1024, 1031, 1040, 2048, 1_000_000, 1_048_576)


def expected(n: int, beat: int, quarter: int, lane: int, base: int) -> tuple[int, ...]:
    qs = 8 * (n // 32)
    length = n - 3 * qs if quarter == 3 else qs
    off = 16 * beat + lane
    global_key = quarter * qs + off
    stack = (global_key // 16) % 4
    local = (global_key // 64) * 16 + global_key % 16
    superblock, within = divmod(local, 1024)
    first = base + 2176 * superblock
    return (int(off < length), global_key, stack, local,
            first + within // 8, within % 8, first + 128 + 2 * within)


def main() -> None:
    vectors: list[tuple[int, int, int, int, int]] = []
    complete: dict[int, set[int]] = {}
    for n in LENGTHS:
        qs = 8 * (n // 32)
        beats = (n - 3 * qs + 15) // 16
        choices = (range(beats) if n <= 2048 else sorted({0, 1, beats // 2, beats - 2, beats - 1}))
        if n <= 2048:
            complete[n] = set()
        for beat in choices:
            for quarter in range(4):
                for lane in range(16):
                    vectors.append((n, beat, quarter, lane, 4096))
    with tempfile.TemporaryDirectory(prefix="v41-shard-addr-") as tmp:
        binary = Path(tmp) / "sim.vvp"
        inp = Path(tmp) / "vectors.txt"
        inp.write_text("".join(" ".join(map(str, row)) + "\n" for row in vectors))
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_shard_addr",
                        "-o", str(binary), str(SRC), str(TB)], check=True, cwd=ROOT)
        run = subprocess.run(["vvp", str(binary), f"+vectors={inp}"], capture_output=True,
                             text=True, check=True, timeout=120)
    rows = [line for line in run.stdout.splitlines() if line.startswith("A ")]
    assert len(rows) == len(vectors), (len(rows), len(vectors), run.stderr)
    scale_seen: dict[int, set[tuple[int, int]]] = {n: set() for n in complete}
    code_seen: dict[int, set[tuple[int, int]]] = {n: set() for n in complete}
    for vector, line in zip(vectors, rows):
        values = tuple(map(int, line.split()[1:]))
        assert values[:4] == vector[:4], (vector, values)
        want = expected(*vector)
        assert values[4:] == want, (vector, values[4:], want)
        n, _, _, _, _ = vector
        if n in complete and want[0]:
            assert want[1] not in complete[n], (n, want[1])
            complete[n].add(want[1])
            scale_seen[n].add((want[2], want[4]))
            assert (want[2], want[6]) not in code_seen[n]
            code_seen[n].add((want[2], want[6]))
            code_seen[n].add((want[2], want[6] + 1))
    for n, found in complete.items():
        assert found == set(range(n)), n
        assert len(scale_seen[n]) == (n + 7) // 8, (n, len(scale_seen[n]))
        assert len(code_seen[n]) == 2 * n, (n, len(code_seen[n]))
    rec = {
        "schema": "opentallas.hdc-v41x-idx-shard-address.v1", "status": "pass",
        "vectors_checked": len(vectors), "complete_scans": len(complete),
        "largest_sampled_scan_keys": max(LENGTHS),
        "layout": "16-key stripes, four stacks, 68 B/key compact per-stack superblocks",
        "coverage": "Quarter-order permutation, 8-key offset crossings, 1024-key local superblock boundaries, exact sector uniqueness and 1M samples",
        "limitation": "Address planner only: HBM request scheduling, response collection and full token exactness remain unverified.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in (SRC, TB, Path(__file__).resolve())},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(f"PASS {len(vectors)} address vectors, {len(complete)} complete scans")


if __name__ == "__main__":
    main()

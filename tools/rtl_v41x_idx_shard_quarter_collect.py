#!/usr/bin/env python3
"""Exact sampled-stream gate for the four-stack quarter collector."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / p for p in (
    "rtl/hdc/v41x/ot_hdc_v41x_idx_shard_quarter_collect.sv",
    "rtl/test/tb_hdc_v41x_idx_shard_quarter_collect.sv",
)]
OUT = ROOT / "results/rtl/hdc_v41x_idx_shard_quarter_collect.json"
LENGTHS = (1, 7, 8, 16, 31, 32, 64, 96, 160, 1000, 1032, 2048, 2080, 5000)
PAT = re.compile(r"^PASS n=(\d+) beats=(\d+) cycles=(\d+)$", re.MULTILINE)
FAST = re.compile(r"^FAST_PASS n=(\d+) beats=(\d+) cycles=(\d+) max_gap=(\d+)$", re.MULTILINE)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="v41-quarter-collect-") as t:
        binary = Path(t) / "sim.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_shard_quarter_collect",
                        "-o", str(binary), *map(str, SOURCES)], check=True, cwd=ROOT)
        run = subprocess.run(["vvp", str(binary)], check=True, capture_output=True,
                             text=True, timeout=180, cwd=ROOT)
        fast_run = subprocess.run(["vvp", str(binary), "+fast"], check=True,
                                  capture_output=True, text=True, timeout=180, cwd=ROOT)
    assert "PASS quarter collector campaign" in run.stdout, run.stdout
    rows = [{"keys": int(n), "output_beats": int(beats), "cycles": int(cycles)}
            for n, beats, cycles in PAT.findall(run.stdout)]
    assert tuple(row["keys"] for row in rows) == LENGTHS, run.stdout
    for row in rows:
        n = row["keys"]
        qs = 8 * (n // 32)
        assert row["output_beats"] == (n - 3 * qs + 15) // 16, row
    match = FAST.search(fast_run.stdout)
    assert match and "PASS quarter collector campaign" in fast_run.stdout, fast_run.stdout
    fast_n, fast_beats, fast_cycles, max_gap = map(int, match.groups())
    assert (fast_n, fast_beats, max_gap) == (5000, 79, 2)
    script = Path(__file__).resolve()
    rec = {
        "schema": "opentallas.hdc-v41x-idx-shard-quarter-collect.v1",
        "status": "pass",
        "cases": rows,
        "total_output_beats_checked": sum(row["output_beats"] for row in rows),
        "continuous_input": {"keys": fast_n, "output_beats": fast_beats,
                             "cycles_including_prefix": fast_cycles,
                             "maximum_output_gap_cycles": max_gap},
        "coverage": "Four-stack 16-stream sampled HBM-like keys with independent stream delays and random output backpressure; exact 64-key kv/last/key/ref/padding, stable stalled output, leading placeholders, Qs mod16=8, 1024-key boundaries and repeated commands. Continuous-input, always-ready mode proves no more than two cycles between output beats after the first of a 5000-key scan.",
        "limitation": "Sampled stream input only; timed HBM and per-PC four-context arbiter are gated separately. No four-stack bandwidth or physical closure claim.",
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in [*SOURCES, script]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(f"PASS {len(rows)} lengths, {rec['total_output_beats_checked']} exact output beats")


if __name__ == "__main__":
    main()

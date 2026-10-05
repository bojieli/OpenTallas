#!/usr/bin/env python3
"""Exact HBM-sector WINDOW-only attention source and replay gate."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/v41x_window_attn_source.json"
SOURCES = (
    "rtl/chip/ot_chip_v41x_window_attn_source.sv",
    "rtl/chip/ot_chip_v41x_window_refill_schedule.sv",
    "rtl/chip/ot_chip_v41x_window_kv_prefetch.sv",
    "rtl/chip/ot_chip_v41x_window_stage4.sv",
    "rtl/chip/ot_chip_v41x_window_row_codec.sv",
    "rtl/chip/ot_chip_v41x_attn_row_merge.sv",
    "rtl/chip/ot_chip_v41x_attn_desc_lifecycle.sv",
    "rtl/test/tb_chip_v41x_window_attn_source.sv",
    "tools/rtl_v41x_window_attn_source_gate.py",
)
PATTERN = re.compile(
    r"WINDOW_ATTN_SOURCE_PASS jobs=(\d+) rows=(\d+) sectors=(\d+) "
    r"beats=(\d+) full=(\d+) backpressure=(\d+) stale_fault=(\d+) "
    r"refill0=(\d+) refill1=(\d+)"
)


def source_hashes():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES}


def run(output: Path = OUT):
    with tempfile.TemporaryDirectory(prefix="v41_window_attn_source_") as tmp:
        binary = Path(tmp) / "source.vvp"
        build = subprocess.run(
            ["iverilog", "-g2012", "-s", "tb_chip_v41x_window_attn_source",
             "-o", str(binary), *(str(ROOT / p) for p in SOURCES if p.endswith(".sv"))],
            capture_output=True, text=True, check=True)
        assert not build.stderr, build.stderr
        sim = subprocess.run(["vvp", str(binary)], capture_output=True,
                             text=True, check=True)
        match = PATTERN.search(sim.stdout)
        assert match, sim.stdout
        values = list(map(int, match.groups()))
        assert values == [2, 256, 4352, 64, 1, 3, 1, 4608, 4608], values
        lint = subprocess.run(
            ["verilator", "--lint-only", "-Wno-fatal", "-Wno-TIMESCALEMOD",
             "--top-module", "ot_chip_v41x_window_attn_source",
             *(str(ROOT / p) for p in SOURCES if p.endswith(".sv") and "/test/" not in p)],
            capture_output=True, text=True, check=True)
        assert lint.returncode == 0
    result = {
        "schema": "v41x_window_attn_source/1",
        "status": "pass",
        "scope": "WINDOW-only 128-row packed FP8 HBM refill, generation-tagged lifecycle stage/issue/drain, and two 32-beat replays with backpressure; ideal one-cycle single-client HBM response, no selected CKV, no full token or routed rate",
        "window_start": 126,
        "rows_per_job": 128,
        "jobs": values[0],
        "hbm_sector_requests": values[2],
        "accepted_packed_beats": values[3],
        "refill_cycles_per_job": values[7:9],
        "beat_backpressure_cycles": values[5],
        "stale_cross_user_fault": bool(values[6]),
        "hbm_model": "one-cycle sector response, always-ready selected stack, no pooled-index/RoPE/CKV contention",
        "sources": source_hashes(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

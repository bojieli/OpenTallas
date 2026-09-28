#!/usr/bin/env python3
"""Focused source-pinned packed V4.1 window KV write/fetch gate."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "rtl/chip/ot_chip_v41x_window_kv_prefetch.sv",
    "rtl/chip/ot_chip_v41x_window_row_codec.sv",
    "rtl/test/tb_chip_v41x_window_kv_prefetch.sv",
    "tools/rtl_chip_v41x_window_kv_prefetch.py",
)
OUTPUT = ROOT / "results/rtl/chip_v41x_window_kv_prefetch.json"


def sources():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES}


def run(output: Path = OUTPUT):
    with tempfile.TemporaryDirectory(prefix="v41_window_kv_prefetch_") as temp:
        binary = Path(temp) / "tb.vvp"
        build = subprocess.run(
            ["iverilog", "-g2012", "-s", "tb_chip_v41x_window_kv_prefetch",
             "-o", str(binary), *(str(ROOT / p) for p in SOURCES[:3])],
            capture_output=True, text=True, check=True,
        )
        sim = subprocess.run(["vvp", str(binary)], capture_output=True,
                             text=True, check=True)
    lines = sim.stdout.splitlines()
    assert "PASS" in lines and "FAIL" not in lines and "TIMEOUT" not in lines, sim.stdout
    assert not build.stderr, build.stderr
    stat = next(line for line in lines if line.startswith("WINDOW_KV "))
    fields = dict(part.split("=", 1) for part in stat.split()[1:])
    values = {key: int(value) for key, value in fields.items()}
    assert values == {
        "rows": 2, "blocks": 32, "reads": 34, "writes": 64,
        "stale_fault": 1, "errors": 0,
    }, values
    result = {
        "status": "pass",
        "scope": "window-only packed HBM row DMA; serialized functional path, no mixed compressed-KV token or rate claim",
        "profile": "opentallas.deepseek_v41.window_fp8_e4m3_s32_e8m0.row.v1",
        "window_slots": 128,
        "bytes_per_row": 528,
        "hbm_pitch_bytes": 544,
        "sectors_per_row": 17,
        "checks": values,
        "sources": sources(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

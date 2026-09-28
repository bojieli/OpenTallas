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
    "rtl/chip/ot_chip_v41x_kv_reqmux.sv",
    "rtl/test/tb_chip_v41x_kv_reqmux.sv",
    "rtl/chip/ot_chip_v41x_hbm_karb.sv",
    "rtl/test/tb_chip_v41x_hbm_karb_wide.sv",
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
        mux_bin = Path(temp) / "mux.vvp"
        subprocess.run(
            ["iverilog", "-g2012", "-s", "tb_chip_v41x_kv_reqmux", "-o", str(mux_bin),
             str(ROOT / SOURCES[4]), str(ROOT / SOURCES[5])],
            capture_output=True, text=True, check=True,
        )
        mux_sim = subprocess.run(["vvp", str(mux_bin)], capture_output=True,
                                 text=True, check=True)
        wide_bin = Path(temp) / "wide.vvp"
        subprocess.run(
            ["iverilog", "-g2012", "-s", "tb_chip_v41x_hbm_karb_wide", "-o", str(wide_bin),
             str(ROOT / SOURCES[6]), str(ROOT / SOURCES[7])],
            capture_output=True, text=True, check=True,
        )
        wide_sim = subprocess.run(["vvp", str(wide_bin)], capture_output=True,
                                  text=True, check=True)
    lines = sim.stdout.splitlines()
    assert "PASS" in lines and "FAIL" not in lines and "TIMEOUT" not in lines, sim.stdout
    assert not build.stderr, build.stderr
    assert "KV_REQMUX bad=0\nPASS" in mux_sim.stdout, mux_sim.stdout
    assert "KARB30 cases=2 bad=0\nPASS" in wide_sim.stdout, wide_sim.stdout
    stat = next(line for line in lines if line.startswith("WINDOW_KV "))
    fields = dict(part.split("=", 1) for part in stat.split()[1:])
    values = {key: int(value) for key, value in fields.items()}
    assert values["stalls"] > 0
    assert {key: value for key, value in values.items() if key != "stalls"} == {
        "rows": 5, "blocks": 64, "reads": 85, "writes": 128,
        "stale_fault": 1, "region_fault": 1, "context_fault": 1, "errors": 0,
    }, values
    result = {
        "status": "pass",
        "scope": "window-only packed HBM row DMA; serialized functional path, no mixed compressed-KV token or rate claim",
        "profile": "opentallas.deepseek_v41.window_fp8_e4m3_s32_e8m0.row.v1",
        "window_slots": 128,
        "user_slices": 2,
        "preloaded_rows": 1,
        "bytes_per_row": 528,
        "hbm_pitch_bytes": 544,
        "sectors_per_row": 17,
        "checks": values,
        "request_mux": {"status": "pass", "bad": 0,
                        "cases": ["same-stack priority", "different-stack parallel grants",
                                  "tagged response demux", "CKV write suppression"]},
        "arbiter_30bit": {"status": "pass", "cases": 2, "bad": 0,
                          "addresses": [0x20000001, 0x3FFFFFFE]},
        "sources": sources(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

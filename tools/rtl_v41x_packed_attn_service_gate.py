#!/usr/bin/env python3
"""Source-pinned refill barrier simulation and local packed-attention lint gate."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/v41x_packed_attn_service.json"
SOURCES = (
    "rtl/chip/ot_chip_v41x_packed_attn_service.sv",
    "rtl/chip/ot_chip_v41x_window_refill_schedule.sv",
    "rtl/test/tb_chip_v41x_window_refill_schedule.sv",
    "rtl/chip/ot_chip_v41x_window_kv_prefetch.sv",
    "rtl/chip/ot_chip_v41x_window_stage4.sv",
    "rtl/chip/ot_chip_v41x_window_row_codec.sv",
    "rtl/chip/ot_chip_v41x_attn_row_merge.sv",
    "rtl/test/ot_hdc_v41x_attn_service_lint_stub.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_attn.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv",
    "rtl/hdc/ot_hdc_fastfp.sv",
    "tools/rtl_v41x_packed_attn_service_gate.py",
)


def source_hashes():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES}


def run(output: Path = OUT):
    with tempfile.TemporaryDirectory(prefix="v41_packed_attn_service_") as tmp:
        sim = Path(tmp) / "schedule.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_chip_v41x_window_refill_schedule",
                        "-o", str(sim), str(ROOT / SOURCES[1]), str(ROOT / SOURCES[2])],
                       check=True, capture_output=True, text=True)
        gate = subprocess.run(["vvp", str(sim)], check=True, capture_output=True, text=True)
        assert "WINDOW_REFILL_SCHEDULE_PASS jobs=3 rows=6 users=2 wrap=1" in gate.stdout
        lint_sources = [p for p in SOURCES if p.endswith(".sv") and
                        ("/test/" not in p or p.endswith("service_lint_stub.sv")) and
                        not p.startswith("rtl/hdc/")]
        lint = subprocess.run(
            ["verilator", "--lint-only", "-Wno-fatal", "-Wno-TIMESCALEMOD",
             "-DV41X_ATTN_SERVICE_LINT_STUB",
             "--top-module", "ot_chip_v41x_packed_attn_service",
             *(str(ROOT / p) for p in lint_sources)],
            check=False, capture_output=True, text=True)
        assert lint.returncode == 0, lint.stderr
    row_dma = json.loads((ROOT / "results/rtl/chip_v41x_window_kv_prefetch.json").read_text())
    merger = json.loads((ROOT / "results/rtl/v41x_attn_row_merge.json").read_text())
    assert row_dma["status"] == merger["status"] == "pass"
    assert row_dma["sources"][SOURCES[3]] == source_hashes()[SOURCES[3]]
    assert merger["sources"][SOURCES[6]] == source_hashes()[SOURCES[6]]
    record = {
        "schema": "v41x_packed_attn_service/1", "status": "pass",
        "scope": "registered local WINDOW refill barrier and co-located WINDOW/merger boundary lint with interface-only attention-engine stub; separate window HBM and merger exact gates; no composed token or sustained HBM rate claim",
        "scheduler": {"jobs": 3, "window_rows": 6, "users": 2,
                      "boundary_positions": [126, 127, 128, 129, 254, 1048575]},
        "window": {"payload_bytes_per_row": 528, "hbm_pitch_bytes_per_row": 544,
                   "sectors_per_row": 17, "stage_rows": 128,
                   "stage_payload_bytes": 67584, "hbm_pitch_bytes_per_user": 69632,
                   "serialized_sector_requests_per_four_row_beat": 68},
        "dependencies": {"window_dma": "results/rtl/chip_v41x_window_kv_prefetch.json",
                         "row_merger": "results/rtl/v41x_attn_row_merge.json"},
        "sources": source_hashes(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

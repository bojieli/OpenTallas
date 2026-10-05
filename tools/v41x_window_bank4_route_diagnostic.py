"""Summarize source-pinned four-bank SRAM route failures without timing claims."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from tools.v41x_window_bank4_physical_preflight import BASE, ROOT

SOURCES = (
    "rtl/chip/ot_chip_v41x_window_bank4_phy.sv",
    "physical/v41x_window_bank4_macro_place.tcl",
    "physical/v41x_window_bank4_hold_repair.tcl",
    "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.lef",
    "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_tt.lib",
    "tools/run_abi3_physical.py",
    "tools/v41x_window_bank4_route_diagnostic.py",
)
ARTIFACTS = (
    "physical_remote.json", "cts_failure.log", "cts_metrics.json",
    "physical_hold100.json", "hold100_cts.json", "hold100_grt.json",
    "hold100_drt.json", "hold100_drt.log.gz",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> dict:
    baseline = json.loads((BASE / "physical_remote.json").read_text())
    variant = json.loads((BASE / "physical_hold100.json").read_text())
    cts = json.loads((BASE / "hold100_cts.json").read_text())
    grt = json.loads((BASE / "hold100_grt.json").read_text())
    baseline_log = (BASE / "cts_failure.log").read_text()
    detail_log = gzip.open(BASE / "hold100_drt.log.gz", "rt").read()
    assert baseline["status"] == "error" and not baseline["flow_completed"]
    assert variant["status"] == "error" and not variant["flow_completed"]
    assert "RSZ-0060" in baseline_log and "Inserted 2656 hold buffers" in baseline_log
    assert "PRE_CTS=physical/v41x_window_bank4_hold_repair.tcl" in variant["runner"]["argv"]
    assert "DRT-0255" in detail_log
    assert "Error: detail_route.tcl, 83 DRT-0255" in detail_log
    source_hash = digest(ROOT / SOURCES[0])
    for run_record in (baseline, variant):
        source = next(x for x in run_record["design"]["sources"] if x["path"] == SOURCES[0])
        assert source["sha256"] == source_hash
    return {
        "schema": "v41x_window_bank4_route_diagnostic/1",
        "status": "detail_route_failed_after_expanded_hold_repair",
        "scope": "four parallel SRAM sector slices, one of 17 slices per WINDOW bank; not the full packed stage or die",
        "baseline": {
            "status": "cts_failed",
            "error_code": "RSZ-0060",
            "inserted_hold_buffers": 2656,
            "flow_completed": False,
        },
        "expanded_hold_repair": {
            "max_buffer_percent": 100,
            "cts_hold_buffers": cts["cts__design__instance__count__hold_buffer"],
            "cts_stdcell_area_um2": cts["cts__design__instance__area__stdcell"],
            "cts_macro_area_um2": cts["cts__design__instance__area__macros"],
            "cts_setup_ws_ps": cts["cts__timing__setup__ws"],
            "cts_hold_ws_ps": cts["cts__timing__hold__ws"],
            "global_route_setup_ws_ps_estimated": grt["globalroute__timing__setup__ws"],
            "global_route_hold_ws_ps_estimated": grt["globalroute__timing__hold__ws"],
            "detail_route_error_code": "DRT-0255",
            "detail_route_maze_failures": detail_log.count("[ERROR DRT-0255]"),
            "flow_completed": False,
        },
        "routed_timing_claim": False,
        "routed_drc_claim": False,
        "power_claim": False,
        "sources": {p: digest(ROOT / p) for p in SOURCES},
        "artifacts": {p: digest(BASE / p) for p in ARTIFACTS},
    }


def main() -> None:
    path = BASE / "route_diagnostic.json"
    path.write_text(json.dumps(run(), indent=2, sort_keys=True) + "\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()

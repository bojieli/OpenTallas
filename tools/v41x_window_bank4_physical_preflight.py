"""Record the bounded four-bank SRAM slice placement/route attempt."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/physical_abi3/asap7/chip/v41x_window_bank4_phy"
INPUTS = (
    "rtl/chip/ot_chip_v41x_window_bank4_phy.sv",
    "physical/v41x_window_bank4_macro_place.tcl",
    "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.lef",
    "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_tt.lib",
    "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_bb.v",
    "tools/run_abi3_physical.py",
    "tools/v41x_window_bank4_physical_preflight.py",
)
STAGE_FILES = (
    "macro_place.log", "macro_place.json", "pdn.json",
    "global_place_first.json", "pin_place.json", "global_place_timeout.log",
)


def hashes(paths: tuple[str, ...], base: Path) -> dict[str, str]:
    return {p: hashlib.sha256((base / p).read_bytes()).hexdigest() for p in paths}


def build_record() -> dict:
    stages = {p: json.loads((BASE / p).read_text()) for p in STAGE_FILES if p.endswith(".json")}
    place_log = (BASE / "macro_place.log").read_text()
    timeout_log = (BASE / "global_place_timeout.log").read_text()
    macros = re.search(r"Number of macros: (\d+)", place_log)
    macro_area = re.search(r"Area of macros: ([\d.]+)", place_log)
    iterations = [int(x) for x in re.findall(r"^\s+(\d+)\s+\|\s+0\.\d+\s+\|", timeout_log, re.M)]
    assert macros and int(macros.group(1)) == 4
    assert macro_area and abs(float(macro_area.group(1)) - 28366.85) < 0.1
    assert stages["macro_place.json"]["flow__errors__count"] == 0
    assert stages["pdn.json"]["flow__errors__count"] == 0
    assert stages["pin_place.json"]["flow__errors__count"] == 0
    assert stages["pin_place.json"]["floorplan__design__io"] == 413
    assert iterations and max(iterations) == 390
    return {
        "schema": "v41x_window_bank4_physical_preflight/1",
        "status": "timed_out_during_global_placement",
        "flow_completed": False,
        "routed_timing_claim": False,
        "routed_drc_claim": False,
        "power_claim": False,
        "scope": "four parallel 256-bit SRAM sector slices with registered local digest; one of 17 slices per bank, not the full packed-window stage or die",
        "run": {
            "tool": "tools/run_abi3_physical.py",
            "view": "asap7",
            "clock_period_ns": 0.92,
            "die_area_um": [0, 0, 420, 270],
            "core_area_um": [2, 2, 418, 268],
            "timeout_seconds": 1500,
            "timeout_exit_code": 124,
            "macro_orientation": "R0",
            "macro_count": 4,
            "macro_area_um2": float(macro_area.group(1)),
            "completed": ["synthesis", "macro_placement", "power_grid", "first_global_placement", "pin_placement"],
            "interrupted": "timing_driven_global_placement",
            "last_logged_iteration": max(iterations),
        },
        "full_stage_macro_mapping": {
            "packed_bits": 4 * 32 * 4224,
            "macro_count_at_256bit_slices": 4 * 17,
            "provisioned_macro_bits": 4 * 17 * 256 * 256,
            "macro_area_um2_at_this_profile": round(4 * 17 * 172.8 * 41.04, 3),
            "note": "capacity/area mapping only; 68-macro stage was not placed or routed",
        },
        "sources": hashes(INPUTS, ROOT),
        "stage_logs": hashes(STAGE_FILES, BASE),
    }


def main() -> None:
    output = BASE / "preflight.json"
    output.write_text(json.dumps(build_record(), indent=2, sort_keys=True) + "\n")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()

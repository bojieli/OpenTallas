"""Fast source-pinned interface lint for the V4.1 packed-window die boundary.

The adopted full core and behavioral HBM make an unrestricted die lint very
large.  This gate keeps their *exact port headers* while blackboxing their
internals.  It checks both reduced and full die wiring; it is not a token,
memory, synthesis, or timing verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from tools import rtl_chip_v41x_die_smoke as die


ROOT = Path(__file__).resolve().parents[1]
CHIP = ROOT / "rtl/chip"
ROM = ROOT / "rtl/rom"
SOURCES = [
    CHIP / f"{n}.sv" for n in (
        "ot_chip_v41x_die", "ot_chip_v41x_tile", "ot_chip_v41x_hbm3e_phy",
        "ot_chip_v41x_window_row_codec", "ot_chip_v41x_window_kv_prefetch",
        "ot_chip_v41x_window_block_guard",
        "ot_chip_v41x_kv_reqmux", "ot_chip_v41x_kv_prefetch",
        "ot_chip_v41x_hbm_karb", "ot_chip_v41x_coll_dma",
    )
] + [ROM / f"{n}.sv" for n in (
    "ot_rom_pkg_ctrl_x", "ot_rom_fabric_router", "ot_rom_oneshot_px",
)] + [ROOT / "rtl/hdc/ot_hdc_fastfp.sv"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> dict:
    results = {}
    with tempfile.TemporaryDirectory(prefix="v41_packed_die_boundary_") as name:
        scratch = Path(name)
        for stem in ("ot_chip_v41x_tile", "ot_chip_v41x_hbm3e_phy"):
            die.blackbox_stub(CHIP / f"{stem}.sv", scratch / f"{stem}.sv")
        rtl = [scratch / "ot_chip_v41x_tile.sv", scratch / "ot_chip_v41x_hbm3e_phy.sv"]
        rtl += [p for p in SOURCES if p.name not in {
            "ot_chip_v41x_tile.sv", "ot_chip_v41x_hbm3e_phy.sv"}]
        for full in (0, 1):
            cmd = [
                die.VERILATOR, "--lint-only", *die.LINT_FLAGS,
                "-Wno-PINMISSING", "-Wno-UNDRIVEN",
                "--top-module", "ot_chip_v41x_die", f"-GFULL_SHAPE={full}",
                "-GK_MEM=524288", *map(str, rtl),
            ]
            result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                                    timeout=90, check=False)
            results["full" if full else "reduced"] = {
                "returncode": result.returncode,
                "diagnostics": [line.replace(str(ROOT) + "/", "")
                                for line in result.stderr.splitlines() if line.startswith("%")],
            }
    return {
        "claim": "die port/header elaboration with exact tile and HBM PHY headers; no token or P&R claim",
        "verilator": die.tool_version(die.VERILATOR),
        "sources_sha256": {str(p.relative_to(ROOT)): sha(p) for p in SOURCES + [Path(__file__)]},
        "modes": results,
        "pass": all(item["returncode"] == 0 for item in results.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results/rtl/chip_v41x_packed_die_boundary.json")
    args = parser.parse_args()
    record = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"packed die boundary: {'PASS' if record['pass'] else 'FAIL'}; {args.output}")
    if not record["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

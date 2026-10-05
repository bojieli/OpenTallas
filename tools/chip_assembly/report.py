#!/usr/bin/env python3
"""Summaries of the hierarchical implementation and the full-die scaling.

Reads the records under results/physical_abi3/asap7/chip/ (blocks/, tiles/,
dies/, budgets/) and writes results/physical_abi3/asap7/chip/summary.json:

* per block: timing against its budget, area, utilisation, wirelength;
* per tile and die: closure, area, clock tree, wirelength;
* the budget tables' status counts;
* the full-die floorplan: how many measured tiles the 815 mm2 reticle holds
  beside its PHYs and links, and the wire, area and clock-distribution
  scaling from the reduced die's measured numbers.

    python3 tools/chip_assembly/report.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chip_assembly import floorplans as fp, orfs  # noqa: E402

RESULTS = orfs.ROOT / "results/physical_abi3/asap7/chip"
RETICLE_W_MM, RETICLE_H_MM = 26.0, 31.35            # 815.1 mm2 (HC1-class envelope)
# Full-die edge budgets (docs/ARCHITECTURE_ATLAS.html die budget for V4.1:
# PHY 50 mm2 for five HBM3E stacks, links 65.2 mm2).
HBM_STACK_PHY_MM2 = 10.0
FULL_DIE = {
    "qwen_rom": {"hbm_stacks": 2, "ucie_modules": 0, "serdes_slices": 8, "tiles_needed": 256,
                 "basis": "Qwen3-8B on one reticle: 256 64-lane tiles (16,384 lanes); KV in two "
                          "HBM3E stacks beside the die; board SerDes for the host and scale-out"},
    "hbm": {"hbm_stacks": 5, "ucie_modules": 0, "serdes_slices": 8, "tiles_needed": 256,
            "basis": "HBM comparator: the same 256 tiles with weights and KV streamed from five "
                     "HBM3E stacks"},
    "v41_rom": {"hbm_stacks": 5, "ucie_modules": 12, "serdes_slices": 16, "tiles_needed": None,
                "basis": "DeepSeek-V4.1 universal die: five HBM3E stacks, UCIe to the other three "
                         "dies of the package, board SerDes for the package ring"},
}


def load(path: Path) -> dict[str, Any] | None:
    return orfs.read_json(path)


def block_summary() -> dict[str, Any]:
    out = {}
    for f in sorted((RESULTS / "blocks").glob("*.json")):
        r = load(f)
        m = r["metrics"]
        out[r["block"]] = {
            "closed_against_budget": r["closed_against_budget"],
            "setup_wns_ps": m.get("setup_wns_ps"), "hold_wns_ps": m.get("hold_wns_ps"),
            "setup_violations": m.get("setup_violations"),
            "drv": {k: m.get(k) for k in ("max_slew_violations", "max_cap_violations",
                                          "max_fanout_violations")},
            "drc_errors": m.get("drc_errors"),
            "die_um": r["die_um"], "stdcell_area_um2": m.get("stdcell_area_um2"),
            "utilization": m.get("utilization"), "wirelength_um": m.get("wirelength_um"),
            "fmax_mhz": (m.get("fmax_hz") or 0) / 1e6 or None,
            "record": f"results/physical_abi3/asap7/chip/blocks/{f.name}",
        }
    return out


def budget_summary() -> dict[str, Any]:
    out = {}
    for f in sorted((RESULTS / "budgets").glob("*.json")):
        b = load(f)
        counts: dict[str, int] = {}
        for blk in b["blocks"].values():
            for r in blk["ports"].values():
                counts[r["status"]] = counts.get(r["status"], 0) + 1
        out[b["name"]] = {"port_buses": counts, "violations": len(b["violations"]),
                          "table": f"results/physical_abi3/asap7/chip/budgets/{f.name}"}
    return out


def full_die(arch: str, tile_w_mm: float, tile_h_mm: float) -> dict[str, Any]:
    """How many tiles the reticle holds with this architecture's edge budget.

    PHYs and links sit on the die edges (their shoreline is the constraint);
    tiles fill the interior on the reduced die's pitch (tile + 20 um gap).
    """
    cfg = FULL_DIE[arch]
    gap = fp.GAP_UM / 1000.0
    strip = fp.PHY_STRIP_UM / 1000.0
    side = fp.SERDES_W_UM / 1000.0
    cols = math.floor((RETICLE_W_MM - 2 * side - 2 * gap) / (tile_w_mm + gap))
    rows = math.floor((RETICLE_H_MM - 2 * strip - 2 * gap) / (tile_h_mm + gap))
    tiles = cols * rows
    phy_mm2 = cfg["hbm_stacks"] * HBM_STACK_PHY_MM2
    return {
        "reticle_mm": [RETICLE_W_MM, RETICLE_H_MM],
        "tile_mm": [round(tile_w_mm, 4), round(tile_h_mm, 4)],
        "columns": cols, "rows": rows, "tiles": tiles,
        "tiles_needed": cfg["tiles_needed"],
        "tile_area_mm2": round(tiles * tile_w_mm * tile_h_mm, 1),
        "edge_strips_mm2": round(RETICLE_W_MM * RETICLE_H_MM - (cols * (tile_w_mm + gap)) *
                                 (rows * (tile_h_mm + gap)), 1),
        "hbm_phy_mm2": phy_mm2,
        "basis": cfg["basis"],
    }


def main() -> int:
    summary: dict[str, Any] = {
        "schema": "opentallas-chip-summary-v1",
        "clock_period_ns": fp.CLOCK_PERIOD_NS,
        "wire_model": fp.wire_delay_model(),
        "blocks": block_summary(),
        "budgets": budget_summary(),
        "tiles": {}, "dies": {}, "full_die": {},
    }
    for f in sorted((RESULTS / "tiles").glob("*.json")):
        summary["tiles"][f.stem] = load(f)
    for f in sorted((RESULTS / "dies").glob("*.json")):
        summary["dies"][f.stem] = load(f)
    for arch in ("qwen_rom", "hbm"):
        t = fp.hdc_tile(arch)
        summary["full_die"][arch] = full_die(arch, t.width_um / 1000, t.height_um / 1000)
    out = RESULTS / "summary.json"
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

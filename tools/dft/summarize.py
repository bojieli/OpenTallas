#!/usr/bin/env python3
"""Collect the DFT evidence into results/dft/summary.json.

Per block it reads, when present:
  results/dft/<block>/atpg.json                      (tools/dft/run_atpg.py)
  results/dft/<block>/equivalence.json               (tools/dft/check_scan_equivalence.py)
  results/physical_abi3/asap7/dft/<block>/noscan/physical.json
  results/physical_abi3/asap7/dft/<block>/scan/physical.json
and reports coverage, pattern counts and the scan overheads the paired routes
measure (same RTL, same 0.9 ns target, --false-path-io, --slew-margin-percent 20;
the only difference is --dft scan).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATPG = ROOT / "results/dft"
PHYS = ROOT / "results/physical_abi3/asap7/dft"

ARCH = {
    # block -> architectures it serves
    "stream": ["hbm_comparator", "qwen3_8b_rom"],
    "matvec": ["hbm_comparator", "qwen3_8b_rom"],
    "kv_stream": ["hbm_comparator"],
    "sinkhorn": ["v41_rom_array"],
    "pkg_ctrl": ["v41_rom_array"],
    "fabric_router": ["v41_rom_array"],
    "pkg_link": ["v41_rom_array"],
    "argmax_reduce": ["v41_rom_array"],
    "mcast_node": ["v41_rom_array"],
    "moe_dispatch": ["v41_rom_array"],
    "expert_port": ["v41_rom_array"],
    "tap": ["hbm_comparator", "qwen3_8b_rom", "v41_rom_array"],
}


def _load(path: Path):
    return json.loads(path.read_text()) if path.is_file() else None


def _phys(rec):
    if not rec or "place_and_route" not in rec:
        return None
    m = rec["place_and_route"]["metrics"]
    out = {
        "status": rec["status"],
        "fmax_mhz": round(float(m["fmax_hz"]) / 1e6, 2) if m.get("fmax_hz") else None,
        "design_area_um2": m.get("design_area_um2"),
        "core_area_um2": m.get("core_area_um2"),
        "instance_count": m.get("instance_count") or m.get("cell_count"),
        "routed_wirelength_um": m.get("routed_wirelength_um"),
        "setup_wns_ns": m.get("setup_wns_ns"),
        "drc_errors": m.get("drc_errors"),
    }
    dft = rec["place_and_route"].get("dft")
    if dft:
        out["scan"] = {k: dft[k] for k in ("flops", "chain_count", "chain_length_max", "scan_cells",
                                           "scan_mux_cells", "lockup_latches", "cell_area_added_fraction")}
    return out


def _ratio(a, b):
    try:
        return round(float(a) / float(b) - 1.0, 6)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def main() -> int:
    blocks = sorted({p.name for p in ATPG.iterdir() if p.is_dir()} | ({p.name for p in PHYS.iterdir() if p.is_dir()} if PHYS.is_dir() else set()))
    rows = {}
    for b in blocks:
        atpg = _load(ATPG / b / "atpg.json")
        eq = _load(ATPG / b / "equivalence.json")
        ns = _phys(_load(PHYS / b / "noscan/physical.json"))
        sc = _phys(_load(PHYS / b / "scan/physical.json"))
        row = {"architectures": ARCH.get(b, [])}
        if atpg:
            row["atpg"] = {
                "top": atpg["top"],
                "scan_cells": atpg["scan"]["scan_cells"],
                "chains": atpg["scan"]["chains"],
                "max_chain_length": atpg["scan"]["max_chain_length"],
                "faults": atpg["faults_total"],
                "classes": atpg["classes"],
                "fault_coverage": atpg["fault_coverage"],
                "test_coverage": atpg["test_coverage"],
                "capture_patterns": atpg["patterns"]["capture"],
                "tester_cycles": atpg["patterns"]["tester_cycles"],
                "gate_level": {k: atpg["gate_level"][k] for k in (
                    "good_machine_patterns", "good_machine_mismatches", "capture_faults_injected",
                    "capture_faults_confirmed", "chain_faults_injected", "chain_faults_confirmed")}
                if atpg.get("gate_level") else None,
            }
        if eq:
            row["scan_off_equivalence"] = {k: eq[k] for k in ("proven", "equiv_cells", "unproven_cells")}
        if ns or sc:
            row["route"] = {"noscan": ns, "scan": sc}
            if ns and sc:
                row["route"]["overhead"] = {
                    "design_area": _ratio(sc["design_area_um2"], ns["design_area_um2"]),
                    "routed_wirelength": _ratio(sc["routed_wirelength_um"], ns["routed_wirelength_um"]),
                    "fmax": _ratio(sc["fmax_mhz"], ns["fmax_mhz"]),
                    "instances": _ratio(sc["instance_count"], ns["instance_count"]),
                }
        rows[b] = row
    out = {
        "schema": "opentallas.dft.summary.v1",
        "route_settings": "asap7, 0.9 ns target, --false-path-io, --slew-margin-percent 20, --stages pnr; "
                          "scan adds --dft scan --scan-max-length 1024",
        "blocks": rows,
    }
    (ATPG / "summary.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    for b, r in rows.items():
        a = r.get("atpg") or {}
        o = (r.get("route") or {}).get("overhead") or {}
        print(f"{b:14s} FC={a.get('fault_coverage')} TC={a.get('test_coverage')} pat={a.get('capture_patterns')} "
              f"area={o.get('design_area')} wl={o.get('routed_wirelength')} fmax={o.get('fmax')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

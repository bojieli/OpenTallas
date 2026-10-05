#!/usr/bin/env python3
"""Summarise a W2 ROM/MAC neighborhood route (run_abi3_physical record + generate_abstract views).

    python3 tools/v41_w2_romac_record.py qe

Reads results/physical_abi3/asap7/chip/v41_w2_rommac/<case>_romac_physical.json and the views that
jobs/w2b_route.sh copied beside it (<tag>_views/: LEF, Liberty, abstract.log, reports), copies the
abstracts to results/physical_abi3/asap7/chip/abstracts/<top>/ and writes <case>_romac_summary.json
with closure numbers, the acceptance verdict, and every abstract's sha256.  It never rewrites the route
record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "results/physical_abi3/asap7/chip/v41_w2_rommac"
TOPS = {"qe": "ot_chip_v41x_qe_romac", "me": "ot_chip_v41x_me_romac"}


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("case", choices=sorted(TOPS))
    ap.add_argument("--tag", default=None)
    a = ap.parse_args()
    top = TOPS[a.case]
    tag = a.tag or f"w2b_{a.case}_romac"
    rec_path = DIR / f"{a.case}_romac_physical.json"
    rec = json.loads(rec_path.read_text())
    m = (rec.get("place_and_route") or {}).get("metrics", {})
    views = DIR / f"{tag}_views"
    abstracts = {}
    dest = ROOT / "results/physical_abi3/asap7/chip/abstracts" / top
    for name in (f"{top}.lef", f"{top}_typ.lib"):
        src = views / name
        if src.is_file():
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest / name)
            abstracts[name] = {"path": str((dest / name).relative_to(ROOT)), "sha256": digest(src),
                               "bytes": src.stat().st_size}
    keys = ("setup_wns_ns", "setup_tns_ns", "setup_violations", "hold_wns_ns", "hold_tns_ns", "hold_violations",
            "drc_errors", "antenna_violating_nets", "max_slew_violations", "max_cap_violations",
            "max_fanout_violations", "fmax_hz", "die_area_um2", "core_area_um2", "macro_area_um2", "macro_count",
            "standard_cell_area_um2", "standard_cell_count", "sequential_cell_count", "utilization_fraction",
            "routed_wirelength_um", "vias", "power_total_w")
    summary = {
        "schema": "opentallas.v41_w2.romac_route_summary.v1",
        "case": a.case, "top": top, "route_record": str(rec_path.relative_to(ROOT)),
        "route_record_sha256": digest(rec_path),
        "clock_period_ns": 0.92, "clock_uncertainty_ns": 0.06, "hold_margin_ns": 0.02,
        "status": (rec.get("acceptance") or {}).get("status"),
        "reason": (rec.get("acceptance") or {}).get("reason"),
        "error": rec.get("error"),
        "closure": {k: m.get(k) for k in keys},
        "abstracts": abstracts,
        "abstract_generated": bool(abstracts),
        "sources": rec.get("design", {}).get("sources"),
        "claim_scope": ("One routed V4.1 ROM/MAC neighborhood at ASAP7 TT with extracted parasitics, its "
                        "ORFS generate_abstract LEF and Liberty for die assembly. Boundary I/O budgets are the "
                        "conventional 20% of period; no die composition, MCMM signoff or token rate."),
    }
    out = DIR / f"{a.case}_romac_summary.json"
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: summary[k] for k in ("status", "reason", "closure", "abstracts")}, indent=1))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Package a routed V4.1 one-PC request slice for geometry-only hierarchy.

The LEF must be extracted from the exact routed ODB named in the physical
record.  Its pin geometry is measured.  The Liberty file deliberately has no
timing arcs: a later composition can test placement and interconnect routing,
but cannot claim end-to-end Fmax from this macro view.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.chip_assembly import macros as mc  # noqa: E402

NAME = "ot_chip_v41x_hbm_karb_pc_local"
RECORD = ROOT / "results/asap7_physical/v41x_die_karb_pc_local_budget_slew50_m9/physical.json"
OUT = ROOT / "physical/asap7_v41x_karb_pc_budget" / NAME


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spec() -> mc.MacroSpec:
    pins = [mc.Pin("rst_n", "input", timed=False)]
    for prefix in ("b", "k"):
        pins += [
            mc.Pin(f"{prefix}_v", "input", timed=False),
            mc.Pin(f"{prefix}_rdy", "output", timed=False),
            mc.Pin(f"{prefix}_addr", "input", 28, timed=False),
            mc.Pin(f"{prefix}_len", "input", 4, timed=False),
            mc.Pin(f"{prefix}_tag", "input", 16, timed=False),
            mc.Pin(f"{prefix}_we", "input", timed=False),
            mc.Pin(f"{prefix}_wdata", "input", 256, timed=False),
            mc.Pin(f"{prefix}_wstrb", "input", 32, timed=False),
            mc.Pin(f"{prefix}_wr_done", "output", timed=False),
        ]
    pins += [
        mc.Pin("h_v", "output", timed=False),
        mc.Pin("h_rdy", "input", timed=False),
        mc.Pin("h_addr", "output", 28, timed=False),
        mc.Pin("h_len", "output", 4, timed=False),
        mc.Pin("h_tag", "output", 17, timed=False),
        mc.Pin("h_we", "output", timed=False),
        mc.Pin("h_wdata", "output", 256, timed=False),
        mc.Pin("h_wstrb", "output", 32, timed=False),
        mc.Pin("h_wr_done", "input", timed=False),
        mc.Pin("k_grants", "output", 32, timed=False),
        mc.Pin("b_grants", "output", 32, timed=False),
        mc.Pin("contended", "output", 32, timed=False),
    ]
    return mc.MacroSpec(NAME, 375.0, 17.01, pins, kind="routed_pc_request",
                        basis="measured routed LEF; geometry-only hierarchical abstract")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--routed-lef", type=Path, required=True)
    ap.add_argument("--record", type=Path, default=RECORD)
    ap.add_argument("--output-dir", type=Path, default=OUT)
    a = ap.parse_args()
    record = json.loads(a.record.read_text())
    if record["status"] != "pass" or record["design"]["top"] != NAME:
        raise SystemExit("source physical record is not a passing local-child route")
    odb = record["place_and_route"]["artifacts"]["6_final.odb"]
    if not odb["sha256"]:
        raise SystemExit("record lacks the routed ODB hash")
    s = spec()
    lef = a.routed_lef.read_text()
    if f"MACRO {NAME}\n" not in lef or "SIZE 375 BY 17.01 ;" not in lef:
        raise SystemExit("routed LEF has the wrong macro name or size")
    actual = set(re.findall(r"^  PIN (\S+)$", lef, re.M))
    expected = {"clk", "VDD", "VSS"} | {bit for pin in s.pins for bit in pin.bits()}
    if actual != expected:
        raise SystemExit(f"routed LEF port mismatch: missing={sorted(expected-actual)[:8]}, "
                         f"extra={sorted(actual-expected)[:8]}")
    a.output_dir.mkdir(parents=True, exist_ok=True)
    lef_out = a.output_dir / f"{NAME}.lef"
    if a.routed_lef.resolve() != lef_out.resolve():
        shutil.copyfile(a.routed_lef, lef_out)
    lib_out = a.output_dir / f"{NAME}_tt.lib"
    lib_out.write_text(mc.liberty_text(s))
    stub_out = a.output_dir / f"{NAME}_bb.v"
    stub_out.write_text(mc.verilog_stub(s))
    manifest = {
        "schema_version": 1,
        "purpose": "geometry-only routed one-PC macro for composed placement/routing; no timing arcs",
        "source_record": str(a.record.resolve().relative_to(ROOT)),
        "source_commit": record["git"]["commit"],
        "source_routed_odb_sha256": odb["sha256"],
        "macro_size_um": [s.width_um, s.height_um],
        "signal_pin_count": len(expected) - 2,
        "files_sha256": {p.name: sha256(p) for p in (lef_out, lib_out, stub_out)},
        "timing_limit": "Liberty intentionally has no arcs. Do not use composition STA as chip Fmax.",
    }
    (a.output_dir / f"{NAME}.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "pass", "macro": NAME, "pins": len(actual), "output": str(a.output_dir)}))


if __name__ == "__main__":
    main()

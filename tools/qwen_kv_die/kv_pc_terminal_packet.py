#!/usr/bin/env python3
"""Summarize copied immutable terminal gate evidence; no EDA or source changes."""
import hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2] / "results/arch/kv_pc_terminal_1019"
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
    summary = {"schema": "kv.pc_terminal_collection.v1", "release_qualified": False, "complete_uncapped_source_census": None, "fixed_face_ff_ownership": None, "tiles": {}}
    for name in ("pc", "pc_h"):
        p = ROOT / name
        gate = json.loads((p / "gate_result.json").read_text())
        tb = json.loads((p / "textbook.json").read_text())
        dump = json.loads((p / "gate_dump.json").read_text())
        log = (p / "gate.log").read_text()
        w, h = dump["die"][2:]
        faces = {s: [] for s in "NSEW"}
        clocks = {}
        for pin, net, kind, direction, rects in dump["bterms"]:
            layer, rect = rects[0]
            x1, y1, x2, y2 = rect
            x, y = (x1+x2)/2, (y1+y2)/2
            side = min(((abs(y-h), "N"), (abs(y), "S"), (abs(x-w), "E"), (abs(x), "W")))[1]
            faces[side].append(pin)
            if pin in ("ck", "hck"):
                clocks[pin] = {"center_um": [x, y], "side": side, "rect": rect, "layer": layer}
        setup, hold = re.search(r"setup WNS ([-+\deE.]+) hold WNS ([-+\deE.]+)", log).groups()
        binding = gate["source_binding"]
        summary["tiles"][name] = {
            "verdict": gate["verdict"], "generated": gate["generated"],
            "source_start_commit": binding["start_commit"], "source_identity": binding["identity"],
            "source_manifest_sha256": binding["manifest_sha256"], "source_archive_sha256": binding["archive_sha256"],
            "source_tree": binding["remote_run"] + "/src", "remote_run": binding["remote_run"],
            "clock": gate["clock"], "reset_landing": gate["reset_landing"], "trial_route": gate["trial_route"],
            "textbook_metrics": tb["metrics"], "cells": tb["cells"], "flops": tb["flops"],
            "diagnostic_tt_placement_setup_ps": float(setup)*1e12, "diagnostic_tt_placement_hold_ps": float(hold)*1e12,
            "ff_signoff_setup_hold": None, "native_launch_capture_qualified": False,
            "outline_um": [w,h], "aspect_ratio": max(w,h)/min(w,h), "macros": len(dump["macros"]),
            "face_pin_counts": {s:len(v) for s,v in faces.items()},
            "face_average_density_per_um": {s:len(v)/(w if s in "NS" else h) for s,v in faces.items()},
            "clock_pin_geometry": clocks,
            "complete_uncapped_transparent_logical_pin_census": None,
            "fixed_face_ff_ownership": None,
            "historical_physical_json_warning": "physical.json was emitted at initial floorplan stop before final gate CTS/GRT; its not_met timings are preserved and are not final signoff",
        }
    (ROOT / "summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    paths = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (ROOT/"SHA256SUMS").write_text("".join(sha(p)+"  "+str(p.relative_to(ROOT))+"\n" for p in paths))
if __name__ == "__main__":
    run()

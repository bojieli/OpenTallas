#!/usr/bin/env python3
"""Fail-closed master checks for the opt-in macro alignment launch path.

The pinned aligned launcher stays unchanged. Without --macro-track-gate its
original pass-through behavior is retained. This checks abstract completeness,
not the complete placed-instance census, routing, or timing qualification.
"""
from pathlib import Path
import re
import sys

import run_abi3_physical_aligned as base

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_GATE = base.gate


def gate(driver_args):
    refusals, required, seen = [], [], set()
    for spec in base._values(driver_args, "--macro-view"):
        name, separator, directory = spec.partition("=")
        if not separator or not name or not directory:
            refusals.append(f"invalid macro-view specification: {spec}")
            continue
        if name in seen:
            refusals.append(f"duplicate requested master: {name}")
        seen.add(name)
        path = Path(directory)
        path = (path if path.is_absolute() else ROOT / path) / (name + ".lef")
        entry = {"requested_master": name, "lef": str(path)}
        required.append(entry)
        try:
            text = path.read_text()
            entry["lef_sha256"] = base.sha(path)
            matches = [m for m in base.cmta.parse_lef(text) if m["name"] == name]
            if len(matches) != 1:
                raise ValueError(f"expected exactly one requested master, found {len(matches)}")
            master = matches[0]
            if master["class"] != "BLOCK" or min(master["W"], master["H"]) <= 0:
                raise ValueError("positive-size CLASS BLOCK required")
            clean = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
            if not re.search(r"^\s*END\s+" + re.escape(name) + r"\s*;?\s*$", clean, re.M):
                raise ValueError("requested master has no closing END")
            signals = [p for p in master["pins"] if p["use"] not in ("POWER", "GROUND")]
            if not signals:
                raise ValueError("signal pins required; empty outline is not a qualified abstract")
            names = [p["name"] for p in signals]
            if len(names) != len(set(names)):
                raise ValueError("duplicate signal pin")
            for pin in signals:
                if not pin["rects"]:
                    raise ValueError(f"signal pin {pin['name']} has no rectangles")
                for layer, rect in pin["rects"]:
                    if layer not in base.cmta.ASAP7_LAYERS:
                        raise ValueError(f"signal pin {pin['name']} uses unchecked layer {layer}")
                    x0, y0, x1, y1 = rect
                    if not (0 <= x0 < x1 <= master["W"] and 0 <= y0 < y1 <= master["H"]):
                        raise ValueError(f"signal pin {pin['name']} rectangle outside positive master geometry")
            entry["signal_pins_checked"] = len(signals)
        except (OSError, ValueError, IndexError, TypeError) as exc:
            refusals.append(f"{name}: {exc}")
    if refusals:
        return list(driver_args), {
            "schema": "opentallas.macro_track_gate.guarded.v1", "verdict": "REFUSED",
            "required_masters": required, "macros": [], "hooks": [],
            "refusals": refusals, "warnings": [],
        }
    forwarded, record = ORIGINAL_GATE(driver_args)
    record["required_master_guard"] = {
        "tool": "tools/run_abi3_physical_aligned_guarded.py",
        "sha256": base.sha(Path(__file__)), "masters": required,
        "complete_placed_instance_census": False,
    }
    return forwarded, record


def main(argv=None):
    previous = base.gate
    try:
        base.gate = gate
        return base.main(argv)
    finally:
        base.gate = previous


if __name__ == "__main__":
    sys.exit(main())

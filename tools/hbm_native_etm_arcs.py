#!/usr/bin/env python3
"""Inventory actual exported pin arcs against the immutable native contract.

Reports table extrema; it does not turn intrinsic characterization into a
die-context verdict. Reuses the repository's generated-Liberty group reader.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from chip_assembly.etm import _groups, _NUM


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pins(text, master):
    library = next(g for g in _groups(text) if g[0] == "library")
    body = text[library[2]:library[3]]
    cell = next(g for g in _groups(body) if g[0] == "cell" and g[1] == master)
    body = body[cell[2]:cell[3]]
    unit = re.search(r'time_unit\s*:\s*"1(ps|ns)"', text)
    if not unit:
        raise ValueError("exported Liberty must declare 1ps or 1ns time units")
    scale = {"ps": 1, "ns": 1000}[unit[1]]
    entries = {}

    def visit(group_body):
        for kind, name, b0, b1 in _groups(group_body):
            pb = group_body[b0:b1]
            if kind == "bus":
                visit(pb)
            elif kind == "pin":
                direction = re.search(r'direction\s*:\s*(\w+)', pb)
                arcs = []
                for ak, _, a0, a1 in _groups(pb):
                    if ak != "timing":
                        continue
                    ab = pb[a0:a1]
                    typ = re.search(r'timing_type\s*:\s*"?(\w+)', ab)
                    rel = re.search(r'related_pin\s*:\s*"([^"]+)"', ab)
                    arc = dict(type=typ[1] if typ else "combinational",
                               related_pin=rel[1] if rel else None, tables={})
                    for tk, _, t0, t1 in _groups(ab):
                        if tk not in ("cell_rise", "cell_fall", "rise_constraint", "fall_constraint"):
                            continue
                        values = re.search(r'values\s*\((.*?)\)\s*;', ab[t0:t1], re.S)
                        if values:
                            vals = [float(v)*scale for v in _NUM.findall(values[1])]
                            if vals:
                                arc["tables"][tk] = dict(min_ps=min(vals), max_ps=max(vals))
                    arcs.append(arc)
                if name in entries:
                    raise ValueError(f"duplicate Liberty pin {name}")
                entries[name] = dict(direction=direction[1] if direction else None, arcs=arcs)
    visit(body)
    return entries


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ports", type=Path, required=True)
    ap.add_argument("--view", type=Path, required=True)
    ap.add_argument("--interface-sdc", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    contract = json.loads(a.ports.read_text())
    expected = {pin[0]: (port, data["direction"]) for port, data in contract["ports"].items() for pin in data["pins"]}
    rec = dict(schema="opentallas.native_etm_arc_inventory.v1", scope="intrinsic PATHFINDING, not R25I die qualification",
               master=contract["master"], native_pin_count=len(expected), native_ports_sha256=digest(a.ports),
               interface_sdc_sha256=digest(a.interface_sdc), corners={})
    for corner in ("tt", "ss", "ff"):
        path = a.view / f'{contract["master"]}_{corner}.lib'
        actual = pins(path.read_text(), contract["master"])
        missing = sorted(set(expected)-set(actual))
        unexpected = sorted(set(actual)-set(expected))
        wrong_direction = sorted(p for p in expected.keys() & actual.keys() if actual[p]["direction"] != expected[p][1])
        grouped = {port: {} for port in contract["ports"]}
        for pin, (port, _) in expected.items():
            grouped[port][pin] = actual.get(pin)
        rec["corners"][corner] = dict(liberty_sha256=digest(path), pin_count=len(actual), missing=missing,
            unexpected=unexpected, wrong_direction=wrong_direction, per_port_pins=grouped,
            pins_without_arcs=sorted(p for p in expected.keys() & actual.keys() if not actual[p]["arcs"]))
    rec["pin_identity_matches"] = all(not (c["missing"] or c["unexpected"] or c["wrong_direction"]) for c in rec["corners"].values())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=2)+"\n")
    print(json.dumps(dict(pin_identity_matches=rec["pin_identity_matches"], native_pin_count=len(expected), output=str(a.output))))
    raise SystemExit(0 if rec["pin_identity_matches"] else 1)


if __name__ == "__main__":
    main()

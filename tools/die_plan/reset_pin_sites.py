#!/usr/bin/env python3
"""Explicit wavefront reset-entry pin repair; existing plans remain unchanged.

The solver can use the same face site for a type input and an output. These are
separate nets and cannot share a physical pin. Emit an existing reset.in_sites
plan override, rather than silently moving only the generated IO/LEF geometry.
The caller must publish reset offsets and recheck the plan after applying it.
"""
import argparse
import copy
import json
from pathlib import Path

import gen_phys
import reset_tree as RT
import schema


def control_pins(P, tn):
    return gen_phys.tap_pins(P, tn) + gen_phys.reset_out_pins(P, tn)


def conflicts(pins, clearance=1.0):
    return [(a[0], b[0]) for i, a in enumerate(pins) for b in pins[i + 1:]
            if abs(a[1] - b[1]) < clearance and abs(a[2] - b[2]) < clearance]


def choose_entry(P, tn, pins):
    old = next((tuple(p[1:]) for p in pins if p[0] == "arst_n"), None)
    if old is None:
        raise RT.ResetError(f"type {tn}: no reset entry pin")
    other = [p for p in pins if p[0] != "arst_n"]
    w, h = P.types[tn]["outline_um"]
    boxes = RT.blockages(P.types[tn])
    bounds = (RT.CLEAR_UM, RT.CLEAR_UM, w - RT.CLEAR_UM, h - RT.CLEAR_UM)
    candidates = []
    for k in (1, -1, 2, -2, 3, -3, 4, -4):
        for dx, dy in ((k * RT.START_DX_UM, 0), (0, k * RT.START_DX_UM)):
            q = RT._snap(P, min(max(old[0] + dx, RT.INSET_UM), w - RT.INSET_UM),
                         min(max(old[1] + dy, RT.INSET_UM), h - RT.INSET_UM))
            if RT._free(q, boxes, bounds) and not conflicts(other + [("arst_n", *q)]):
                candidates.append(q)
    if not candidates:
        raise RT.ResetError(f"type {tn}: no clear separate reset entry beside {old}")
    return min(candidates, key=lambda q: (RT._man(old, q), q))


def repair(P, tn):
    if not RT.wavefront(P) or P.types[tn].get("hard"):
        raise RT.ResetError("entry repair requires a soft wavefront type")
    pins = control_pins(P, tn)
    before = conflicts(pins)
    raw = copy.deepcopy(P.raw)
    if not before:
        return raw, dict(type=tn, changed=False, conflicts_before=[])
    if any("arst_n" not in pair for pair in before):
        raise RT.ResetError(f"type {tn}: collision does not involve its reset entry: {before}")
    site = choose_entry(P, tn, pins)
    raw.setdefault("reset", {}).setdefault("in_sites", {})[tn] = list(site)
    new = schema.Plan(raw, path=P.path)
    after = conflicts(control_pins(new, tn))
    if after:
        raise RT.ResetError(f"type {tn}: reset entry override still overlaps: {after}")
    return raw, dict(type=tn, changed=True, conflicts_before=before, conflicts_after=after,
                     old_entry=list(RT.in_pin(P, tn)), new_entry=list(RT.in_pin(new, tn)),
                     note="Explicit plan override; recheck actual relay/die hops and publish release offsets.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan", type=Path)
    ap.add_argument("--type", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    a = ap.parse_args()
    raw, receipt = repair(schema.Plan(schema.load(a.plan), path=a.plan), a.type)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(raw, indent=1) + "\n")
    a.receipt.parent.mkdir(parents=True, exist_ok=True)
    a.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()

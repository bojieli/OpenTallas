#!/usr/bin/env python3
"""HEAD-CORE-R17 (COORD ruling 3, task: plan cores/*_pins.json -> the REAL views): write a plan pin file
{source, source_sha256, macro, outline_um, pins[{name, layer, x, y}], pins_canon_sha256} from a real core LEF.
x/y = centre of the pin's first PORT RECT (core frame, um), the same convention as the closed-LEF pin files it replaces.
pins_canon_sha256 = sha256 over the sorted canonical (name, layer, x, y) rows + outline (GATE-PINS-2 content form;
the free-text 'source' is NOT hashed).  Fails closed on a pin without a RECT or a duplicate pin name.
HEAD-R19 (10-27): (1) USE POWER / USE GROUND pins (VDD/VSS M5 strap combs) are NOT plan signal pins (the closed-LEF pin
files never listed them; PG is the PG plan's job): they are left out and named in `excluded_pg`.  (2) a pin whose RECT
spans more than one routing track in its preferred direction (the R14 centre-entry FT pads + rst_n: 0.192 um squares) is
represented by its ACCESS point: the on-track coordinate inside the RECT nearest the RECT centre, on the core's own
track lattice = the residue shared by the narrow (single-track) pins of that direction (fails closed if they disagree).
Its centre is kept in `rect_centre` for audit.  Narrow pins are unchanged (centre of the first RECT).
   head_pins_from_lef.py LEF OUT.json [--source-label TEXT]"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


PITCH = {"M2": 0.036, "M3": 0.036, "M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064, "M8": 0.080, "M9": 0.080}
VERT = {"M3", "M5", "M7", "M9"}


def snap_pads(pins):
    """move multi-track pins to their nearest on-track access point inside the RECT (see module doc)."""
    res = {}
    for p in pins:
        L = p["layer"]
        if L not in PITCH or p["_span"] > PITCH[L] + 1e-9:
            continue
        c = p["x"] if L in VERT else p["y"]
        res.setdefault(L, set()).add(round(c % PITCH[L], 4) % PITCH[L])
    moved = 0
    for p in pins:
        L = p["layer"]
        if L not in PITCH or p["_span"] <= PITCH[L] + 1e-9:
            continue
        r = res.get(L)
        if not r or len(r) != 1:
            raise SystemExit(f"pin {p['name']} {L}: no unique narrow-pin track residue on {L} ({sorted(r or [])})")
        r, pt = next(iter(r)), PITCH[L]
        k = "x" if L in VERT else "y"
        lo, hi = p["_lo"], p["_hi"]
        c = p[k]
        best = min((round(r + n * pt, 4) for n in range(int((lo - r) // pt) - 1, int((hi - r) // pt) + 2)
                    if lo - 1e-9 <= r + n * pt <= hi + 1e-9), key=lambda v: (abs(v - c), v), default=None)
        if best is None:
            raise SystemExit(f"pin {p['name']}: no track inside its RECT")
        if abs(best - c) > 1e-9:
            p["rect_centre"] = [p["x"], p["y"]]
            p[k] = best
            moved += 1
    return moved


def parse(text):
    m = re.search(r"^\s*MACRO\s+(\S+)", text, re.M)
    if not m:
        raise SystemExit("no MACRO")
    macro = m.group(1)
    sz = re.search(r"^\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;", text, re.M)
    pins, seen, pg = [], set(), []
    for pm in re.finditer(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\s*$", text, re.M | re.S):
        name, body = pm.group(1), pm.group(2)
        if name in seen:
            raise SystemExit(f"duplicate pin {name}")
        seen.add(name)
        if re.search(r"^\s*USE\s+(POWER|GROUND)\s*;", body, re.M):
            pg.append(name)
            continue
        port = re.search(r"PORT(.*?)END", body, re.S)
        if not port:
            raise SystemExit(f"pin {name}: no PORT")
        lay = re.search(r"LAYER\s+(\S+)\s*;", port.group(1))
        rc = re.search(r"RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;", port.group(1))
        if not lay or not rc:
            raise SystemExit(f"pin {name}: no LAYER/RECT")
        x0, y0, x1, y1 = map(float, rc.groups())
        v = lay.group(1) in VERT
        pins.append(dict(name=name, layer=lay.group(1), x=round((x0 + x1) / 2, 4), y=round((y0 + y1) / 2, 4),
                         _span=(x1 - x0) if v else (y1 - y0), _lo=x0 if v else y0, _hi=x1 if v else y1))
    if not pins:
        raise SystemExit("no pins")
    moved = snap_pads(pins)
    for p in pins:
        for k in ("_span", "_lo", "_hi"):
            p.pop(k)
    return macro, [float(sz.group(1)), float(sz.group(2))] if sz else None, sorted(pins, key=lambda p: p["name"]), sorted(pg), moved


def canon_sha(pins, outline):
    rows = sorted((p["name"], p["layer"], round(p["x"], 4), round(p["y"], 4)) for p in pins)
    return hashlib.sha256(json.dumps(dict(pins=rows, outline_um=outline), separators=(",", ":")).encode()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("lef")
    ap.add_argument("out")
    ap.add_argument("--source-label", default=None)
    a = ap.parse_args(argv)
    t = Path(a.lef).read_text()
    macro, outline, pins, pg, moved = parse(t)
    d = dict(source=a.source_label or a.lef, source_sha256=hashlib.sha256(t.encode()).hexdigest(), macro=macro,
             outline_um=outline, excluded_pg=pg, pads_snapped_to_track=moved, pins=pins,
             pins_canon_sha256=canon_sha(pins, outline))
    Path(a.out).write_text(json.dumps(d, indent=0) + "\n")
    print(macro, outline, len(pins), "pins", d["pins_canon_sha256"][:12], "pg_excluded", pg, "pads_snapped", moved)
    return 0


if __name__ == "__main__":
    sys.exit(main())

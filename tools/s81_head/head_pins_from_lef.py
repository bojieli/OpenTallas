#!/usr/bin/env python3
"""HEAD-CORE-R17 (COORD ruling 3, task: plan cores/*_pins.json -> the REAL views): write a plan pin file
{source, source_sha256, macro, outline_um, pins[{name, layer, x, y}], pins_canon_sha256} from a real core LEF.
x/y = centre of the pin's first PORT RECT (core frame, um), the same convention as the closed-LEF pin files it replaces.
pins_canon_sha256 = sha256 over the sorted canonical (name, layer, x, y) rows + outline (GATE-PINS-2 content form;
the free-text 'source' is NOT hashed).  Fails closed on a pin without a RECT or a duplicate pin name.
   head_pins_from_lef.py LEF OUT.json [--source-label TEXT]"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def parse(text):
    m = re.search(r"^\s*MACRO\s+(\S+)", text, re.M)
    if not m:
        raise SystemExit("no MACRO")
    macro = m.group(1)
    sz = re.search(r"^\s*SIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;", text, re.M)
    pins, seen = [], set()
    for pm in re.finditer(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\s*$", text, re.M | re.S):
        name, body = pm.group(1), pm.group(2)
        if name in seen:
            raise SystemExit(f"duplicate pin {name}")
        seen.add(name)
        port = re.search(r"PORT(.*?)END", body, re.S)
        if not port:
            raise SystemExit(f"pin {name}: no PORT")
        lay = re.search(r"LAYER\s+(\S+)\s*;", port.group(1))
        rc = re.search(r"RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;", port.group(1))
        if not lay or not rc:
            raise SystemExit(f"pin {name}: no LAYER/RECT")
        x0, y0, x1, y1 = map(float, rc.groups())
        pins.append(dict(name=name, layer=lay.group(1), x=round((x0 + x1) / 2, 4), y=round((y0 + y1) / 2, 4)))
    if not pins:
        raise SystemExit("no pins")
    return macro, [float(sz.group(1)), float(sz.group(2))] if sz else None, sorted(pins, key=lambda p: p["name"])


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
    macro, outline, pins = parse(t)
    d = dict(source=a.source_label or a.lef, source_sha256=hashlib.sha256(t.encode()).hexdigest(), macro=macro,
             outline_um=outline, pins=pins, pins_canon_sha256=canon_sha(pins, outline))
    Path(a.out).write_text(json.dumps(d, indent=0) + "\n")
    print(macro, outline, len(pins), "pins", d["pins_canon_sha256"][:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())

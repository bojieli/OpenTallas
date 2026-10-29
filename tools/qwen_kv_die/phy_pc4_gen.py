#!/usr/bin/env python3
"""MODELED licensed-PHY abstract for the actual KV four-PC wrapper interface.

COORD 2026-10-29 07:54 authorizes a modeled black box, not a PHY design.
Footprint is supplied explicitly by the die owner; no area or timing signoff
claim is made for licensed IP. The wrapper's ordinary glue still needs routing
and TT setup / FF hold signoff. No RTL, cycle, or parent-plan edit is implicit.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hbm_phy_bb import CORNERS, lib_text

NAME = "qkd_hbm3e_phy_pc4"
PORTS = [("rst_n", 1, "input")] + [
    (f"{n}{k}", width, direction)
    for k in range(4)
    for n, width, direction in (("po", 328, "input"), ("pi", 289, "output"),
                                 ("fh", 4, "output"), ("rh", 4, "output"))]


def generate(out: Path, width: float, height: float, layout: dict | None = None) -> dict:
    # Four core-facing edges keep this 2502-pin interface from becoming one
    # impossible escape wall. The explicit footprint must fit the demand.
    if min(width, height) <= 0:
        raise ValueError("modeled PHY dimensions must be positive")
    bits = [("clk", "input")] + [(n if w == 1 else f"{n}[{b}]", d)
            for n, w, d in PORTS for b in range(w)]
    pitch, margin, plen, pw = .192, 4.32, .192, .024
    # Pin groups follow physical PC identity: each PC occupies one face.
    groups = [[("clk", "input"), ("rst_n", "input")]] + [[] for _ in range(3)]
    for n, w, d in PORTS[1:]:
        groups[int(n[-1])].extend((n if w == 1 else f"{n}[{b}]", d) for b in range(w))
    dims = (height, height, width, width)
    if layout is None and any(len(g) * pitch + 2 * margin > dim for g, dim in zip(groups, dims)):
        raise ValueError("modeled PHY footprint cannot fit four-PC pins at 0.192 um pitch")
    lef = ["# MODELED licensed PHY: geometry/timing assumptions, not silicon signoff", "VERSION 5.8 ;",
           'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {NAME}", " CLASS BLOCK ;",
           " ORIGIN 0 0 ;", " SYMMETRY X Y ;", f" SIZE {width:g} BY {height:g} ;"]
    sites = {}
    def emit_pin(n, direction, layer, rects, face):
        if layer not in {f"M{i}" for i in range(1,8)} or not rects:
            raise ValueError(f"invalid pin layer/access for {n}")
        for rect in rects:
            x0,y0,x1,y1=rect
            if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
                raise ValueError(f"pin {n} outside modeled footprint")
        lef.extend([f" PIN {n}", f"  DIRECTION {direction.upper()} ;", f"  USE {'CLOCK' if n == 'clk' else 'SIGNAL'} ;",
                    "  PORT", f"   LAYER {layer} ;"])
        lef.extend("   RECT " + " ".join(f"{v:.6f}" for v in rect) + " ;" for rect in rects)
        lef.extend(["  END", f" END {n}"])
        sites[n] = dict(face=face, layer=layer, rect_um=rects[0], access_rects_um=rects)
    if layout is not None:
        wanted = {n for n,_ in bits}
        if set(layout.get("pins",{})) != wanted:
            raise ValueError("explicit layout must contain exactly every four-PC pin")
        for n,direction in bits:
            p=layout["pins"][n]
            emit_pin(n,direction,p["layer"],p["rects_um"],p.get("face","interior"))
        rows=[(n,p["layer"],r) for n,p in sites.items() for r in p["access_rects_um"]]
        for i,(n,layer,a) in enumerate(rows):
            for other,l,b in rows[i+1:]:
                if n != other and l == layer and min(a[2],b[2]) > max(a[0],b[0])+1e-8 and min(a[3],b[3]) > max(a[1],b[1])+1e-8:
                    raise ValueError(f"overlapping modeled pins {n}/{other}")
    else:
        for face, group, dim in zip(("W", "E", "S", "N"), groups, dims):
            start = round((dim - (len(group) - 1) * pitch) / 2 / .048) * .048 + .024
            for i, (n, direction) in enumerate(group):
                c = round(start + i * pitch, 6)
                rect = {"W": (0, c-pw/2, plen, c+pw/2), "E": (width-plen, c-pw/2, width, c+pw/2),
                        "S": (c-pw/2, 0, c+pw/2, plen), "N": (c-pw/2, height-plen, c+pw/2, height)}[face]
                emit_pin(n,direction,"M4" if face in ("W","E") else "M5",[rect],face)
    for net, use, y in (("VDD", "POWER", margin), ("VSS", "GROUND", margin+2.4)):
        lef += [f" PIN {net}", "  DIRECTION INOUT ;", f"  USE {use} ;", "  PORT", "   LAYER M6 ;",
                f"   RECT {margin:g} {y:g} {width-margin:g} {y+.288:g} ;", "  END", f" END {net}"]
    lef += [" OBS"]
    for i in (layout.get("obstruction_layers", list(range(1,8))) if layout else range(1,8)):
        # pin access rim stays clear; analog body blocks ordinary signal routing.
        lef += [f"  LAYER M{i} ;", f"   RECT 0.4 0.4 {width-.4:g} {height-.4:g} ;"]
    lef += [" END", f"END {NAME}", "END LIBRARY", ""]
    d = out / NAME
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{NAME}.lef").write_text("\n".join(lef))
    for corner in ("tt", "ff"):
        lib = lib_text(NAME, width*height, "clk", PORTS, corner)
        # fh/rh mirror clk in the actual functional black box. They are
        # forwarded-clock arcs, never fresh registered data outputs.
        for k in range(4):
            for pref in ("fh", "rh"):
                pattern = rf"(        bus\({pref}{k}\) \{{.*?\n        \}})"
                lib = re.sub(pattern, lambda m: m[0].replace("timing_type : rising_edge; timing_sense : non_unate;",
                             "timing_type : combinational; timing_sense : positive_unate;"), lib, flags=re.S)
        (d / f"{NAME}_{corner}.lib").write_text("/* MODELED licensed PHY interface assumptions */\n" + lib)
    bb = ["// MODELED licensed PHY black box; functional simulation uses kv_phy_slices.sv.",
          "(* blackbox *)", f"module {NAME} (", "    input wire clk,"]
    for i, (n, w, direction) in enumerate(PORTS):
        bb += [f"    {direction} wire " + (f"[{w-1}:0] " if w > 1 else "") + n + ("," if i+1 < len(PORTS) else "")]
    bb += [");", "endmodule", ""]
    (d / f"{NAME}_bb.v").write_text("\n".join(bb))
    sheet = dict(schema="opentallas.kv-phy-pc4-modeled.v1", name=NAME, grade="MODELED",
                 footprint_um=[width, height], footprint_basis="explicit die-owner assumption; no vendor dimensions",
                 timing_basis="tools/hbm_phy_bb.py CORNERS registered-interface assumptions; fh/rh combinational clock forwarding",
                 corners={k:CORNERS[k] for k in ("tt", "ff")}, pins=sites,
                 controller_period_ps=833, cycles_added=0,
                 claim_boundary="Licensed PHY black box only. No PHY silicon, DRC, power, or timing signoff claim.")
    (d / f"{NAME}.json").write_text(json.dumps(sheet, indent=2)+"\n")
    assert len(sites) == len(bits)
    return sheet


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--width-um", type=float, required=True)
    p.add_argument("--height-um", type=float, required=True)
    p.add_argument("--layout", type=Path, help="explicit native per-bit pin/access geometry and obstruction layers")
    a = p.parse_args()
    sheet = generate(a.out, a.width_um, a.height_um, json.loads(a.layout.read_text()) if a.layout else None)
    print(f"MODELED {NAME}: {len(sheet['pins'])} pins, footprint {sheet['footprint_um']}")

if __name__ == "__main__":
    main()

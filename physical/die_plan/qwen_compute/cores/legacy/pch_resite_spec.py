#!/usr/bin/env python3
"""QC-SU-SRAMHALO (2026-10-27): keep clock-tree / repeater cells of a mscts spec OUT of the SRAM pin-column exclusion strips
(sram_pincol_halo.json from gen_core_kit_qc.py).  Plan rule, deterministic, no measured input: a cell whose site lies in a
strip moves to the nearest legal site outside every strip and every macro + rows halo (min Manhattan move, x on the
0.054 site grid, y on the 0.27 row grid); sizing is unchanged.  Also the gate: --check exits 1 when a cell sits in a strip.
    python3 pch_resite_spec.py SPEC.tcl HALO.json [--out NEW.tcl --moves MOVES.json] [--check]"""
import argparse
import json
import re
import sys
from pathlib import Path

CELL_W = {"BUFx24_ASAP7_75t_R": 1.512, "BUFx16f_ASAP7_75t_R": 1.296, "BUFx12f_ASAP7_75t_R": 1.08,
          "BUFx12_ASAP7_75t_R": 0.972, "BUFx10_ASAP7_75t_R": 0.864, "BUFx8_ASAP7_75t_R": 0.756}
ROW, SITE = 0.27, 0.054
LINE = (re.compile(r"(\s*\{(\S+) (\S+) )([\d.]+) ([\d.]+)( (\S+)\})\s*$"),          # {name parent x y cell}
        re.compile(r"(\s*\{(\S+) (\S+) \{)([\d.]+) ([\d.]+)(\}.* (\S+)\})\s*$"))    # {name parent {x y} {sinks} cell}


def blocked(x, y, w, strips):
    for s in strips:
        x0, y0, x1, y1 = s["rect"]
        if x0 - w < x < x1 and y0 - ROW < y < y1:
            return s
    for s in strips:
        x0, y0, x1, y1 = s["macro_rect"]
        h = s["rows_halo_um"]
        if x0 - h - w < x < x1 + h and y0 - h < y < y1 + h:
            return "macro"
    return None


def resite(x, y, w, strips):
    s = blocked(x, y, w, strips)
    if s is None or s == "macro":
        return x, y
    x0, y0, x1, y1 = s["rect"]
    cand = [(round((x0 - w - SITE) / SITE) * SITE, y), (round((x1 + SITE) / SITE) * SITE + SITE, y),
            (x, round((y0 - ROW) / ROW) * ROW), (x, round((y1 + ROW) / ROW) * ROW + ROW)]
    cand = [c for c in cand if blocked(c[0], c[1], w, strips) is None]
    return min(cand, key=lambda c: abs(c[0] - x) + abs(c[1] - y))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("halo")
    ap.add_argument("--out"); ap.add_argument("--moves"); ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    strips = json.load(open(a.halo))["strips"]
    out, moves = [], []
    for ln in Path(a.spec).read_text().split("\n"):
        for rx in LINE:
            m = rx.match(ln)
            if not m:
                continue
            x, y, cell = float(m.group(4)), float(m.group(5)), m.group(7)
            nx, ny = resite(x, y, CELL_W.get(cell, 1.6), strips)
            if (nx, ny) != (x, y):
                moves.append(dict(cell=m.group(2), frm=[x, y], to=[round(nx, 3), round(ny, 3)],
                                  move_um=round(abs(nx - x) + abs(ny - y), 3)))
                ln = m.group(1) + f"{nx:.3f} {ny:.3f}" + m.group(6)
            break
        out.append(ln)
    print(f"PCH_RESITE {len(moves)} cells in strips, max move {max([m['move_um'] for m in moves], default=0)} um")
    if a.check:
        sys.exit(1 if moves else 0)
    if a.out:
        Path(a.out).write_text("# QC-SU-SRAMHALO pch_resite_spec.py: tree cells re-sited out of the SRAM pin-column strips "
                               "(nearest legal site, sizing unchanged)\n" + "\n".join(out))
    if a.moves:
        Path(a.moves).write_text(json.dumps(moves, indent=1) + "\n")


if __name__ == "__main__":
    main()

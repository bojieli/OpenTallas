#!/usr/bin/env python3
"""Spread the existing south face register rows inside an unchanged QC core.

The btab/prog kits put ~1000 south registers in a 6.5um-deep band even
though the first SRAM starts at y86.4um. This physical-only option retains
every pin, cell, net, x position and pipeline cycle and uses the empty band.
Apply to an isolated kit snapshot, before its placement prototype.
"""
import argparse
import json
from pathlib import Path


def configure(kit, offset_um=8.64, stride=4):
    kit = Path(kit)
    if stride < 1 or offset_um < 0:
        raise ValueError("row stride >=1 and inward offset >=0 required")
    p = kit / "face_flops.tcl"
    src = p.read_text()
    old = 'set cy [expr {$face eq "S" ? $ff_y0 + $r * $ff_rh : $ff_y1 - ($r + 1) * $ff_rh}]'
    new = ('set cy [expr {$face eq "S" ? $ff_y0 + '
           f'round({offset_um:g} * $ff_dbu / $ff_rh) * $ff_rh + $r * {stride} * $ff_rh'
           ' : $ff_y1 - ($r + 1) * $ff_rh}]')
    if src.count(old) != 1:
        raise ValueError("south face allocation anchor missing or not unique")
    p.write_text(src.replace(old, new))
    manifest = dict(schema="opentallas.qc.south_spread.v1", offset_um=offset_um,
                    row_stride=stride, unchanged=["RTL", "netlist", "pins", "clock", "macros", "PDN"],
                    additional_cycles=0, reason="south-face local congestion; reuse macro-free band")
    (kit / "SOUTH_SPREAD.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kit")
    ap.add_argument("--offset-um", type=float, default=8.64)
    ap.add_argument("--stride", type=int, default=4)
    a = ap.parse_args()
    print(json.dumps(configure(a.kit, a.offset_um, a.stride)))


if __name__ == "__main__":
    main()

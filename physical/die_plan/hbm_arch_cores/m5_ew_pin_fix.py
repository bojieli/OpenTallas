#!/usr/bin/env python3
"""Stage-resume form of class M5-EW-PIN for a kit generated before the io_tcl fix (DIE-HBM-62/FLOW).

A signal pin on M5 on an E/W face has no M5 track through a horizontal stub: pin access stops with DRT-0422/DRT-0074
in the GRT step.  This moves the stub to the on-track entry form of gen_core_kit_hbm.clock_entry_pin, same face and y:
io.tcl for a re-run from floorplan, core_grt_pre.tcl for a resume after placement.  pins.json is unchanged
(pin_audit checks the face and y).  Usage: m5_ew_pin_fix.py KIT [KIT...]; idempotent; prints the moved pins.
"""
import json
import math
import re
import sys
from pathlib import Path

ROW = re.compile(r"^place_pin -pin_name \{([^}]+)\} -layer M5 -location \{([\d.]+) ([\d.]+)\} -pin_size \{([\d.]+) ([\d.]+)\}\s*$")
SIZE = (0.048, 0.48)
OFF, PITCH = 0.072, 0.096


def entry(x, y, w):
    """(cx, sx) of the on-track stub touching the near E/W face, as gen_core_kit_hbm.clock_entry_pin."""
    if x > w / 2:
        cx = OFF + math.floor((w - SIZE[0] / 2 - OFF) / PITCH + 1e-9) * PITCH
        return cx, max(SIZE[0], 2 * (w - cx))
    cx = OFF + math.ceil((SIZE[0] / 2 - OFF) / PITCH - 1e-9) * PITCH
    return cx, max(SIZE[0], 2 * cx)


def fix(kit):
    kit = Path(kit)
    w = float(re.search(r"^export DIE_AREA = \S+ \S+ (\S+) ", (kit / "config.mk").read_text(), re.M)[1])
    out, moved = [], []
    for line in (kit / "io.tcl").read_text().splitlines():
        m = ROW.match(line)
        if m and float(m[4]) > float(m[5]):
            cx, sx = entry(float(m[2]), float(m[3]), w)
            line = f"place_pin -pin_name {{{m[1]}}} -layer M5 -location {{{cx:.4f} {float(m[3]):.4f}}} -pin_size {{{sx:.4f} {SIZE[1]:.4f}}}"
            moved.append(line)
        out.append(line)
    if not moved:
        return []
    (kit / "io.tcl").write_text("\n".join(out) + "\n")
    (kit / "m5_ew_pin_fix.tcl").write_text("\n".join(moved) + "\n")
    pre = kit / "core_grt_pre.tcl"
    src = "source /work/m5_ew_pin_fix.tcl\n"
    if src not in pre.read_text():
        pre.write_text(src + pre.read_text())
    return moved


if __name__ == "__main__":
    for k in sys.argv[1:]:
        print(k, fix(k))

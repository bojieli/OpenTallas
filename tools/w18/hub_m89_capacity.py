#!/usr/bin/env python3
"""W18: M8/M9 tracks left over the hub after the die-level passes (trunk pass + rest pass), for the C_rotate
rotate legs.  Reads the bundled routes' 4x4-GCell usage (die_route.py gcell_usage.txt; capacity and usage are in
bundle tracks of k wires) inside the hub rectangle and reports, per layer, the free real wires per um of hub
section (cut across the layer's direction) and the free wires across the bank square.

    python3 tools/w18/hub_m89_capacity.py --floorplan F --trunk W1 --rest W2 --k 32 --output R.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_combine as R  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--floorplan", type=Path, required=True)
    ap.add_argument("--trunk", type=Path, required=True)
    ap.add_argument("--rest", type=Path, required=True)
    ap.add_argument("--k", type=int, default=32)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    fp = json.loads(a.floorplan.read_text())
    hr = fp["hub"]["rect"]
    vm = fp["hub"]["parts"]["HUB_VM"]
    lines = (a.trunk / "gcell_usage.txt").read_text().splitlines()
    gx = [int(v) / 1000 for v in lines[0].split()[1].split(",")]
    gy = [int(v) / 1000 for v in lines[1].split()[1].split(",")]
    T, Rr = R.load(a.trunk), R.load(a.rest)
    out = {}
    for L, horiz in (("M8", True), ("M9", False)):
        cap = use_t = use_r = 0.0
        rows = set()
        cols = set()
        for (l, j, i), (c, u) in T.items():
            if l != L:
                continue
            x0, y0 = gx[min(i * 4, len(gx) - 1)], gy[min(j, len(gy) - 1)]
            if hr[0] <= x0 < hr[0] + hr[2] and hr[1] <= y0 < hr[1] + hr[3]:
                cap += c
                use_t += u
                use_r += Rr.get((l, j, i), (0, 0))[1]
                rows.add(j)
                cols.add(i)
        # a horizontal layer's tracks run along x: the free tracks crossing a vertical cut = free / number of columns
        span_blocks = len(cols) if horiz else len(rows)
        free = max(0.0, cap - use_t - use_r)
        sect_um = hr[3] if horiz else hr[2]
        # a 4x4 block sums 4 GCells along the track direction, so per cut divide by 4 as well
        free_wires_section = free / max(1, span_blocks) / 4 * a.k
        pdn = 0.25 * cap / max(1, span_blocks) / 4 * a.k     # the die PDN's M8/M9 power share (25%) not reserved in the split passes
        out[L] = dict(direction="horizontal" if horiz else "vertical", capacity=cap, used_trunk=use_t, used_rest=use_r,
                      used_pct=round(100 * (use_t + use_r) / cap, 2) if cap else None,
                      free_wires_across_hub_section=round(free_wires_section),
                      free_wires_per_um=round(free_wires_section / sect_um, 2),
                      free_wires_across_bank_square=round(free_wires_section / sect_um * (vm["h"] if horiz else vm["w"])),
                      free_after_pdn_across_bank_square=round((free_wires_section - pdn) / sect_um * (vm["h"] if horiz else vm["w"])))
    rec = dict(schema="opentallas.v41.w18_hub_m89_capacity.v1", hub_rect_um=hr, bank_um=[vm["x"], vm["y"], vm["w"], vm["h"]],
               layers=out, k=a.k,
               basis="bundled GCell capacity is after the die PDN reserve already applied by die_route (M8/M9 power share); "
                     "usage of the M8/M9 trunk pass + the charged rest pass",
               inputs={str(a.trunk): sha(a.trunk / "gcell_usage.txt"), str(a.rest): sha(a.rest / "gcell_usage.txt"),
                       "floorplan": sha(a.floorplan), "tool_sha256": sha(Path(__file__))})
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

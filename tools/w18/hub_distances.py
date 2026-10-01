#!/usr/bin/env python3
"""W18: lane <-> VM distances and wire stages in a C_rotate hub (SU_VECTOR | VM strip | SU_VECTOR_E).

For every point of the SU lane halves on a grid: the Manhattan distance to the nearest point of the VM strip
(horizontal only when the strip spans the hub height), and the register stages at the serial-chain clock reach.

    python3 tools/w18/hub_distances.py --floorplan F --reach-um 481 --output R.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--floorplan", type=Path, required=True)
    ap.add_argument("--reach-um", type=float, required=True, help="um per register stage at the lane clock")
    ap.add_argument("--reach-basis", default="")
    ap.add_argument("--target-um", type=float, default=3850.0)
    ap.add_argument("--tile-um", type=float, default=433.0, help="lane-group tile side (W11: 8 lanes, ~433 um)")
    ap.add_argument("--reach2-um", type=float, default=0.0, help="a second reach for the stage count (e.g. M2-M5)")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    fp = json.loads(a.floorplan.read_text())
    parts = fp["hub"]["parts"]
    vm = parts["HUB_VM"]
    out = {}
    for nm in sorted(k for k in parts if k.startswith("HUB_SU_VECTOR")):
        r = parts[nm]
        worst, hist = 0.0, {}
        n = 40
        for i in range(n + 1):
            for j in range(n + 1):
                x, y = r["x"] + r["w"] * i / n, r["y"] + r["h"] * j / n
                dx = max(vm["x"] - x, 0.0, x - (vm["x"] + vm["w"]))
                dy = max(vm["y"] - y, 0.0, y - (vm["y"] + vm["h"]))
                d = dx + dy
                worst = max(worst, d)
                s = math.ceil(d / a.reach_um) if d > 0 else 0
                hist[s] = hist.get(s, 0) + 1
        out[nm] = dict(rect_um=[r["x"], r["y"], r["w"], r["h"]], worst_to_strip_um=round(worst, 1),
                       worst_stages=math.ceil(worst / a.reach_um), within_target=worst <= a.target_um,
                       stage_histogram=dict(sorted(hist.items())))
    # rotate span (W11: a fixed-latency rotate pays the worst bank -> lane distance on every op): lane-tile
    # centres over every SU part against the bank area's corners (the farthest bank of a Manhattan pair is a corner)
    tiles = []
    for nm in (k for k in parts if k.startswith("HUB_SU_VECTOR")):
        r = parts[nm]
        nx, ny = max(1, int(r["w"] // a.tile_um)), max(1, int(r["h"] // a.tile_um))
        for i in range(nx):
            for j in range(ny):
                tiles.append((r["x"] + (i + 0.5) * r["w"] / nx, r["y"] + (j + 0.5) * r["h"] / ny))
    corners = [(vm["x"] + fx * vm["w"], vm["y"] + fy * vm["h"]) for fx in (0, 1) for fy in (0, 1)]
    span = max(abs(cx_ - tx) + abs(cy_ - ty) for cx_, cy_ in corners for tx, ty in tiles)
    vc = (vm["x"] + vm["w"] / 2, vm["y"] + vm["h"] / 2)
    via_c = max(abs(cx_ - vc[0]) + abs(cy_ - vc[1]) for cx_, cy_ in corners) + \
        max(abs(tx - vc[0]) + abs(ty - vc[1]) for tx, ty in tiles)
    rot = dict(lane_tiles=len(tiles), worst_bank_to_lane_um=round(span, 1), via_centre_um=round(via_c, 1),
               stages={f"{a.reach_um:g}um": math.ceil(span / a.reach_um),
                       **({f"{a.reach2_um:g}um": math.ceil(span / a.reach2_um)} if a.reach2_um else {})})
    rec = dict(schema="opentallas.v41.w18_hub_lane_vm_distance.v1", rotate_span=rot, floorplan=str(a.floorplan),
               floorplan_sha256=sha(a.floorplan), vm_strip_um=[vm["x"], vm["y"], vm["w"], vm["h"]],
               reach_um=a.reach_um, reach_basis=a.reach_basis, target_um=a.target_um, halves=out,
               basis="rectangle-bound: lane tile corners to the nearest VM strip edge (Manhattan); W11's tile footprint refines it",
               tool_sha256=sha(Path(__file__)))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(rot=rot, halves={k: (v["worst_to_strip_um"], v["worst_stages"]) for k, v in out.items()})))


if __name__ == "__main__":
    main()

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
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    fp = json.loads(a.floorplan.read_text())
    parts = fp["hub"]["parts"]
    vm = parts["HUB_VM"]
    out = {}
    for nm in ("HUB_SU_VECTOR", "HUB_SU_VECTOR_E"):
        if nm not in parts:
            continue
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
    rec = dict(schema="opentallas.v41.w18_hub_lane_vm_distance.v1", floorplan=str(a.floorplan),
               floorplan_sha256=sha(a.floorplan), vm_strip_um=[vm["x"], vm["y"], vm["w"], vm["h"]],
               reach_um=a.reach_um, reach_basis=a.reach_basis, target_um=a.target_um, halves=out,
               basis="rectangle-bound: lane tile corners to the nearest VM strip edge (Manhattan); W11's tile footprint refines it",
               tool_sha256=sha(Path(__file__)))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: (v["worst_to_strip_um"], v["worst_stages"]) for k, v in out.items()}))


if __name__ == "__main__":
    main()

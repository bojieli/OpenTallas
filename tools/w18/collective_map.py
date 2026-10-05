#!/usr/bin/env python3
"""W18: collective-engine placement and link lane map of the V4.1 ROM layer die (adopted free fix, root
2026-09-30): the engine at the centre of each link edge, and the latency-critical peer (the next pipeline
stage's die) on the lanes nearest the VM.  Lane distances are Manhattan from the VM centre and from the edge
engine, in cycles at the SS reach (504 um / stage, 1.2 GHz).

    python3 tools/w18/collective_map.py --output results/physical_abi3/asap7/chip/v41_w18/collective_lane_map.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "results/floorplan/v41_pack_refit_w18_e8p5.json"
FP = ROOT / "results/physical_abi3/asap7/chip/v41_w18/die_floorplan_ch8.64.json"
REACH = 504.0


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--critical-lanes", type=int, default=4)
    a = ap.parse_args(argv)
    pk, fp = json.loads(PACK.read_text()), json.loads(FP.read_text())
    vm = fp["hub"]["parts"]["HUB_VM"]
    vmc = (vm["x"] + vm["w"] / 2, vm["y"] + vm["h"] / 2)
    d = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])  # noqa: E731
    cyc = lambda L: math.ceil(L / REACH)  # noqa: E731
    out = {}
    for grp, pin in (("SERDES", lambda x, y: (x + 1000.08, y + 200.88)), ("UCIE", lambda x, y: (x, y + 194.4))):
        lanes = [(n, pin(x, y)) for n, m, x, y, o, g in pk["instances"] if g == grp]
        ys = sorted(p[1] for _, p in lanes)
        eng = (lanes[0][1][0], (ys[0] + ys[-1]) / 2)
        order = sorted(lanes, key=lambda l: (d(vmc, l[1]), l[1][1]))
        rows = []
        for rank, (n, p) in enumerate(order):
            rows.append(dict(lane=n, rank_from_vm=rank, role="critical_peer" if rank < a.critical_lanes else "other",
                             pin_um=[round(p[0], 2), round(p[1], 2)],
                             vm_to_lane_um=round(d(vmc, p), 1), vm_to_lane_cycles=cyc(d(vmc, p)),
                             engine_to_lane_um=round(d(eng, p), 1), engine_to_lane_cycles=cyc(d(eng, p))))
        out[grp.lower()] = dict(engine_um=[round(eng[0], 1), round(eng[1], 1)],
                                vm_to_engine_cycles=cyc(d(vmc, eng)), lanes=rows,
                                critical_peer_worst_engine_to_lane_cycles=max(r["engine_to_lane_cycles"] for r in rows
                                                                              if r["role"] == "critical_peer"))
    rec = dict(schema="opentallas.v41.w18_collective_lane_map.v1", reach_um=REACH, vm_centre_um=[round(v, 1) for v in vmc],
               links=out, adopted="root 2026-09-30: engine at the edge centre + critical peer on the lanes nearest the VM",
               inputs=dict(pack_sha256=sha(PACK), floorplan_sha256=sha(FP)), tool_sha256=sha(Path(__file__)))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    for k, v in out.items():
        print(k, v["engine_um"], "VM->engine", v["vm_to_engine_cycles"], "critical", [r["lane"] for r in v["lanes"][:a.critical_lanes]],
              "worst crit engine->lane", v["critical_peer_worst_engine_to_lane_cycles"])


if __name__ == "__main__":
    main()

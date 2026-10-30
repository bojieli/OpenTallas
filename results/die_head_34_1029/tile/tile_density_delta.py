#!/usr/bin/env python3
"""DIE-HEAD-34 (2026-10-29): hd_tile fix-only plan delta = COORD 18:4x-b (A) clock.tap_mode density (r200, V1r sink bins,
Codex 1847 fields) + u_eA1 x -4.32 um (one macro lattice step) so the S/E street relays near the rst/run pads get a legal
tap (tile_tap_dead_zone.out).  Touches ONLY partition_types.hd_tile.clock (6 fields) and the u_eA1 hard-core origin.
usage: tile_density_delta.py IN_PLAN OUT_PLAN"""
import json, sys
p = json.load(open(sys.argv[1]))
t = p["partition_types"]["hd_tile"]
t["clock"].update({"tap_mode": "density", "tap_radius_um": 200, "tap_max_sinks": 1500, "tap_target_sinks": 1200,
                   "control_sinks": False, "sink_bins_file": "results/die_head_34_1029/tile/hd_tile_sink_bins.json"})
n = 0
for hc in t["hard_cores"]:
    if (hc.get("inst") or hc.get("name")).endswith("u_eA1"):
        assert hc["origin_um"] == [371.52, 8.64], hc["origin_um"]
        hc["origin_um"] = [367.2, 8.64]; n += 1
assert n == 1
json.dump(p, open(sys.argv[2], "w"), indent=1)
print("hd_tile delta applied ->", sys.argv[2])

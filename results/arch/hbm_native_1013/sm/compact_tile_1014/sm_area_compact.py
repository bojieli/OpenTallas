#!/usr/bin/env python3
"""SM area with the compact tile (owner 18:45 PT 10-14 pilot): re-stack the published native SM frame
(results/arch/hier_contract_1011/handoff/r25gq_sm_child_origins.json, 35 direct children) with the tile height
replaced, every other child outline and x unchanged, the same 8.64-um seam between the two tiles of a column and the
same 86.4-um backend row under the columns.  Inputs are MEASURED outlines only (the tile outline is the routed /
gated kit outline passed on the command line; std-cell areas come from the gate report when given)."""
import json, sys, argparse
ap = argparse.ArgumentParser()
ap.add_argument("--origins", required=True)
ap.add_argument("--tile-h", type=float, required=True)
ap.add_argument("--tile-w", type=float, default=630.72)
ap.add_argument("--slot", default="3214.08x1131.84")
a = ap.parse_args()
d = json.load(open(a.origins))
ch = d["sm_component"]["children"]
W0, H0 = d["sm_component"]["frame_outline_um"]
TH0 = 1252.8
tiles = [c for c in ch if "smh_tile" in c["cell"]]
other = [c for c in ch if "smh_tile" not in c["cell"]]
# column stack: backend row (y 0, 77.76), tile p1 at y 86.4, tile p0 at 86.4 + TH + seam (seam = 1347.84 - 86.4 - 1252.8)
seam = round(1347.84 - 86.4 - TH0, 3)
top_tiles = 86.4 + 2 * a.tile_h + seam
# front column: children above the old upper-tile origin move down by the tile-height change
dy = TH0 - a.tile_h
front_top = 0.0
for c in other:
    y = c["y"] - (dy if c["y"] >= 1347.84 else 0.0)
    front_top = max(front_top, y + c["outline_um"][1])
H = round(max(top_tiles, front_top) + (H0 - (86.4 + 2 * TH0 + seam)), 3)
leaf = lambda c: c["outline_um"][0] * c["outline_um"][1]
sw, sh = map(float, a.slot.split("x"))
out = {"tile_outline_um": [a.tile_w, a.tile_h], "tile_area_mm2": round(a.tile_w * a.tile_h / 1e6, 4),
       "old_tile_area_mm2": round(a.tile_w * TH0 / 1e6, 4),
       "sm_frame_um": [W0, H], "sm_frame_mm2": round(W0 * H / 1e6, 3), "old_sm_frame_mm2": round(W0 * H0 / 1e6, 3),
       "sixteen_tiles_mm2": round(16 * a.tile_w * a.tile_h / 1e6, 3),
       "non_tile_children_outline_mm2": round(sum(leaf(c) for c in other) / 1e6, 3),
       "die_32_sm_mm2": round(32 * W0 * H / 1e6, 1), "old_die_32_sm_mm2": round(32 * W0 * H0 / 1e6, 1),
       "hfd_sm_slot_mm2": round(sw * sh / 1e6, 3), "frame_over_slot": round(W0 * H / (sw * sh), 2),
       "front_column_top_um": round(front_top, 2), "tile_column_top_um": round(top_tiles, 2)}
print(json.dumps(out, indent=1))

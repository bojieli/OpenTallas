"""HEAD-PLAN-PG own check: clock straps (M9 x-lanes, M8 y-rows) + spine trunk lane vs the plan's die.pg.grid stripes.
Short = metal overlap; SPACE = edge gap < 1.0 um. Strap widths: M9 0.32 (16w lane metal, GEOM-27 basis), M8 0.32.
usage: strap_reprobe.py PLAN STRAPS"""
import json, sys
plan = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2]))
grid = {g["layer"]: g for g in plan["die"]["pg"]["grid"]}
def cls(layer, x, w=0.32):
    g = grid[layer]; W, P, O, nets = g["width_um"], g["pitch_um"], g["offset_um"], g["nets"]; step = P / len(nets)
    k = round((x - O) / step); c = O + k * step
    gap = abs(x - c) - W / 2 - w / 2
    return ("SHORT" if gap < -1e-9 else "SPACE" if gap < 1.0 - 1e-9 else "OK"), round(gap, 3), nets[k % len(nets)], round(c, 3)
for L in ("M9", "M8"):
    g = grid[L]; res = [cls(L, s[1]) for s in S if s[0] == L]
    print(f"{L} PG {g['width_um']}@{g['pitch_um']} off {g['offset_um']}: straps {len(res)} SHORT {sum(r[0]=='SHORT' for r in res)}"
          f" SPACE {sum(r[0]=='SPACE' for r in res)} min_gap {min(r[1] for r in res)}")
t = plan.get("clock", {}).get("spine", {}).get("trunk")
if t is None:
    for pt in plan["partition_types"].values():
        pass
print("spine.trunk", t)
if t:
    print("trunk lane", t["lane_x_um"], cls("M9", t["lane_x_um"]), "| node", t["node_x_um"], cls("M9", t["node_x_um"]))

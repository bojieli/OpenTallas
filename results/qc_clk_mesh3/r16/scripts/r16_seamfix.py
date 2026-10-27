"""Dry-build aid (NOT the plan): apply the R9 nearest seam move (<=0.81 um) to channel cells whose body leaves the
host, so die_clock_mesh build_explicit reaches its track / pin-stack stage. The real fix is the centre-channel plan delta."""
import json, sys
plan = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2]))
parts = {p["name"]: p for p in plan["partitions"]}
SX = 0.054
n = 0; mx = 0.0
for name, c in S["cell_sites"].items():
    p = parts.get(c["part"])
    if not p or not c["kind"].startswith("chan"):
        continue
    (x0, y0), (w, h) = p["origin_um"], plan["partition_types"][p["type"]]["outline_um"]
    x = c["origin_um"][0]
    dx = max(0.0, x0 + 1e-4 - x) - max(0.0, x + c["w"] - (x0 + w) + 1e-4)   # 1e-4: builder compares edges strictly
    if abs(dx) > 1e-9:
        k = round(dx / SX); k += (1 if dx > 0 else -1) if abs(k * SX) < abs(dx) - 1e-9 else 0
        c["origin_um"][0] = round(x + k * SX, 6); n += 1; mx = max(mx, abs(k * SX))
json.dump(S, open(sys.argv[3], "w"))
print(json.dumps(dict(moved_units=n, max_move_um=round(mx, 4))))

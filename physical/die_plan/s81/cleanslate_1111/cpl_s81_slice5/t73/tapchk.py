# list every added tap's load/radius on a plan (taps.grid_explicit_taps rules); optional moves JSON {name:[x,y]}
import json, sys
sys.path.insert(0, "."); import taps, schema
plan, tn = sys.argv[1], sys.argv[2]; mv = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
raw = json.load(open(plan))
for q in raw["partition_types"][tn]["clock"].get("added_taps") or []:
    if q["name"] in mv: q["xy"] = mv[q["name"]]
P = type("X", (), {"types": raw["partition_types"]})()
try:
    P = schema.Plan(raw) if hasattr(schema, "Plan") else P
except Exception: pass
out = taps.grid_explicit_sites(P, tn); n_grid = len(schema._grid_taps(P, tn))
sinks = taps.sink_sites(P, tn)
import reset_tree as RT
sinks = sinks + [(float(r["xy"][0]), float(r["xy"][1]), 1.0) for r in RT.for_type(P, tn).get("relays", [])]
ck = P.types[tn]["clock"]; cap = int(ck.get("tap_max_sinks", 1500)); rad = float(ck.get("tap_radius_um", 200.))
load, far, _ = taps.assign(out, sinks, cap, rad, max_distance_um=rad)
for i, ((nm, x, y), n, r) in enumerate(zip(out, load, far)):
    bad = i >= n_grid and (n > cap or r > rad * 1.1 or n == 0)
    if bad or (i >= n_grid and (n > 0.9 * cap or r > rad)): print(("BAD " if bad else "near"), nm, round(x, 2), round(y, 2), "load", n, "r", round(r, 1))
print("cap", cap, "radius", rad, "taps", len(out), "grid", n_grid)

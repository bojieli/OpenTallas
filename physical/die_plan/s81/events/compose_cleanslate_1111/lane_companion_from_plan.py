"""DS85-COMPOSE-1111 (DO_NOT_COUNT): mkcomp.py BASE.json LANE_PLAN.json DELTA.json OUT_COMPANION.json
companion for the composer from a lane's checked plan: per delta type, the lane plan's core taps (kind core) and the
internal_stations regs_um; prints which type keys differ between BASE and the lane plan (beyond hard_cores
origin/orient, core tap xy and station regs)."""
import json
import sys

B, L, D = (json.load(open(p)) for p in sys.argv[1:4])
out, diff = {}, {}
for tn in D:
    tb, tl = B["partition_types"][tn], L["partition_types"][tn]
    keys = sorted(k for k in set(tb) | set(tl) if tb.get(k) != tl.get(k))
    sub = {}
    if "internal_stations" in keys:
        sb, sl = tb.get("internal_stations") or [], tl.get("internal_stations") or []
        sub["n"] = (len(sb), len(sl))
        sub["fields"] = sorted({f for a, b in zip(sb, sl) for f in set(a) | set(b) if a.get(f) != b.get(f)})
    if "clock" in keys:
        sub["clock_fields"] = sorted(f for f in set(tb["clock"]) | set(tl["clock"]) if tb["clock"].get(f) != tl["clock"].get(f))
        tbt = {t["name"]: t for t in tb["clock"].get("taps", [])}
        sub["tap_fields"] = sorted({f for t in tl["clock"].get("taps", []) for f in set(t) | set(tbt.get(t["name"], {}))
                                    if t.get(f) != tbt.get(t["name"], {}).get(f)})
    if "hard_cores" in keys:
        hb = {h["inst"]: h for h in tb["hard_cores"]}
        sub["hc_fields"] = sorted({f for h in tl["hard_cores"] for f in set(h) | set(hb[h["inst"]])
                                   if h.get(f) != hb[h["inst"]].get(f)})
    diff[tn] = dict(keys=keys, **sub)
    out[tn] = dict(core_taps={t["name"]: t["xy"] for t in tl["clock"].get("taps", []) if t.get("kind") == "core"
                              and t["xy"] != next((x["xy"] for x in tb["clock"]["taps"] if x["name"] == t["name"]), None)},
                   internal_stations=[{k: s[k] for k in ("from_um", "to_um", "regs_um") if k in s}
                                      for s in tl.get("internal_stations") or []])
json.dump(out, open(sys.argv[4], "w"), indent=1)
print(json.dumps(diff, indent=1))

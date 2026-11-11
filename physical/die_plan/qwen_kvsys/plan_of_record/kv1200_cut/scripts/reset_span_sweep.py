import json, sys
p = json.load(open(sys.argv[1]))["partition_types"]
def pts(x):
    out = []
    if isinstance(x, list):
        if len(x) == 2 and all(isinstance(v, (int, float)) for v in x): out.append(tuple(x))
        else:
            for y in x: out += pts(y)
    elif isinstance(x, dict):
        for k, v in x.items():
            if k in ("regs_um", "from_um", "to_um", "xy", "sites_um", "origin_um"): out += pts(v)
            elif isinstance(v, (list, dict)): out += pts(v)
    return out
rows = []
for tn, t in p.items():
    r = t.get("reset") or {}
    tap = r.get("tap_um"); loc = r.get("local_taps_um") or []
    srcs = [tuple(tap)] if tap else []
    srcs += [tuple(v) for v in loc if isinstance(v, list) and len(v) == 2]
    if not srcs: continue
    sinks = []
    for k in ("internal_stations", "ft_slots", "relay_sites", "hard_cores"):
        sinks += pts(t.get(k) or [])
    if not sinks: continue
    d = max(min(abs(s[0]-q[0]) + abs(s[1]-q[1]) for q in srcs) for s in sinks)
    rows.append((round(d), tn, len(loc), t["outline_um"], r.get("sync_stages")))
rows.sort(reverse=True)
print("max Manhattan reset-source -> farthest station/ft/core point (um), type, n_local_taps, outline, sync")
for x in rows: 
    if x[0] > 1000: print(x)
print(len(rows), "types;", sum(1 for x in rows if x[0] > 1000), "over 1000 um;", sum(1 for x in rows if x[0] > 1000 and x[2] == 0), "of those without local taps")

#!/usr/bin/env python3
"""PATH-S81 10-26: regenerate explicit clock-tap tables whose sink inventory changed (PHY FT wrapper slots).

Rule kept (taps.explicit_taps): existing endpoints are never moved, renamed or dropped (control-relay/tap
coordinate feedback).  For a type whose explicit table fails the unchanged radius/cap check, the sinks no
existing tap can take within tap_radius_um are clustered by the same radius/capacity-bounded weighted bisection
the density mode uses (taps._bisect, target = tap_target_sinks), each new tap is legalised with schema.tap_clear
(strict) and APPENDED as clk_t<n>.  Iterate until explicit_taps passes (or report the failure).  Read-only on the
input plan; writes --out plan + ledger.
usage: regen_explicit_taps_1026.py SRC_ROOT PLAN_IN PLAN_OUT LEDGER [--check-only]
"""
import json, sys, os, copy
root, pin, pout, ledger = sys.argv[1:5]
check_only = "--check-only" in sys.argv
sys.path.insert(0, os.path.join(root, "tools/die_plan"))
import schema, taps

raw = json.load(open(pin))
mk = lambda: schema.Plan(raw)
P = mk()
types = [tn for tn, t in P.types.items() if (t.get("clock") or {}).get("tap_mode") == "explicit"]
rep = {"plan_in": pin, "explicit_types": len(types), "types": {}}

def check(P, tn):
    taps._CACHE.clear() if hasattr(taps, "_CACHE") else None
    try:
        r = taps.explicit_taps(P, tn); return None, r
    except ValueError as e:
        return str(e), None

for tn in sorted(types):
    err, r = check(P, tn)
    ent = {"before": "PASS" if err is None else err}
    if err is None or check_only:
        rep["types"][tn] = ent; continue
    ck = raw["partition_types"][tn]["clock"]
    cap = int(ck.get("tap_max_sinks", 1500)); radius = float(ck.get("tap_radius_um", 200.0))
    target = int(ck.get("tap_target_sinks", int(0.8 * cap)))
    added = []
    for it in range(8):
        P = mk()
        t = P.types[tn]
        cur = [(p["name"], *map(float, p["xy"])) for p in ck["taps"] if p.get("kind") != "core"]
        sinks = taps.sink_sites(P, tn)
        load_, far, asg = taps.assign(cur, sinks, cap, radius, max_distance_um=radius)
        # sinks outside every tap's radius (assign marks them; recompute directly)
        un = [s for s in sinks if min(abs(s[0]-x)+abs(s[1]-y) for _, x, y in cur) > radius + 1e-6]
        # also sinks over-assigned: if a tap is over cap or far > radius, its far sinks count as uncovered
        if not un:
            over = [i for i, (n, rr) in enumerate(zip(load_, far)) if n > cap or rr > radius + 1e-6]
            for i in over:
                _, x, y = cur[i]
                un += [s for k, s in enumerate(sinks) if asg[k] == i and abs(s[0]-x)+abs(s[1]-y) > radius - 1e-6]
        if not un:
            break
        leaves = taps._bisect(un, target, radius)
        taken = [(x, y) for _, x, y in cur] + [(x, y) for _, x, y, _ in schema.core_taps(P, tn)]
        for lf in leaves:
            x, y = lf[0], lf[1]
            try:
                xy = schema.tap_clear(t, x, y, taken=taken, strict=True)
            except ValueError as e:
                print(tn, "no legal site", e, flush=True); continue
            name = f"clk_t{len([p for p in ck['taps'] if p.get('kind') != 'core'])}"
            ck["taps"].append({"name": name, "xy": [round(xy[0], 4), round(xy[1], 4)], "kind": "leaf",
                               "note": "PATH-S81 10-26 appended for new FT/PHY sinks (radius/cap unchanged)"})
            taken.append(tuple(xy)); added.append(name); cur.append((name, *xy))
    # prune: drop APPENDED taps that end up empty (a later round took their sinks); existing endpoints untouched.
    base = len([p for p in ck["taps"] if p.get("kind") != "core"]) - len(added)
    for _ in range(len(added) + 1):
        P = mk()
        cur = [(p["name"], *map(float, p["xy"])) for p in ck["taps"] if p.get("kind") != "core"]
        sinks = taps.sink_sites(P, tn)
        cap_ = int(ck.get("tap_max_sinks", 1500)); rad_ = float(ck.get("tap_radius_um", 200.0))
        load_, far, _ = taps.assign(cur, sinks, cap_, rad_, max_distance_um=rad_)
        empty = [cur[i][0] for i in range(base, len(cur)) if load_[i] == 0]
        if not empty:
            break
        ck["taps"] = [p for p in ck["taps"] if p.get("name") != empty[-1]]
        added.remove(empty[-1])
    k = base
    for p in ck["taps"]:
        if p.get("kind") != "core" and p.get("name") in added:
            pass
    ren = {}
    for p in ck["taps"]:
        if p.get("kind") != "core" and p["name"] in added:
            ren[p["name"]] = f"clk_t{k}"; p["name"] = ren[p["name"]]; k += 1
    added = [ren[a] for a in added]
    P = mk()
    err2, r2 = check(P, tn)
    ent.update(added=added, after="PASS" if err2 is None else err2,
               loads=[[n, round(x, 3), round(y, 3), k, round(rr, 1)] for n, x, y, k, rr in (r2 or [])])
    rep["types"][tn] = ent
    print(tn, "added", len(added), "->", ent["after"][:160], flush=True)

rep["summary"] = {"before_fail": sum(v["before"] != "PASS" for v in rep["types"].values()),
                  "after_fail": sum(v.get("after", v["before"]) != "PASS" for v in rep["types"].values()),
                  "taps_added": sum(len(v.get("added", [])) for v in rep["types"].values())}
print(json.dumps(rep["summary"]))
json.dump(rep, open(ledger, "w"), indent=1)
if not check_only:
    json.dump(raw, open(pout, "w"))

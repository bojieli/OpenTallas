#!/usr/bin/env python3
"""DIE-HBM-33 V-E2 plan delta (die-local): re-window the lower block of ports on the b000|b010 edge of each HBM half at
the plan face budget (6 pins/um, schema.window_for, same layers/order), packed UPWARD against the first window at or above
--top-anchor, keeping their order.  Frees one contiguous window at the bottom of the edge for the hub->b102 row-1 feed.
Writes OUT/die_plan.json (every other file hard-linked) + OUT/repack_report.json.  Plan arithmetic = UNCHECKED until G0.
usage: repack_edge.py WT PLANDIR OUT [--below 7700] [--sep 0.58]"""
import argparse, json, os, sys, copy, hashlib
ap = argparse.ArgumentParser(); ap.add_argument("wt"); ap.add_argument("plan"); ap.add_argument("out")
ap.add_argument("--below", type=float, default=7700.0); ap.add_argument("--sep", type=float, default=0.58)
ap.add_argument("--anchor-guard", type=float, default=2.0)
ap.add_argument("--edge", action="append", default=[], help="A:B:BELOW (half-less part names, e.g. b010:b001:7186); default b000:b010:--below")
a = ap.parse_args()
sys.path.insert(0, a.wt + "/tools/die_plan")
import schema as S, lane_add as LA
raw = json.load(open(os.path.join(a.plan, "die_plan.json")))
P = S.Plan(raw)

def geom_elem(part, bus):
    t = P.ptype(part)
    for b in t.get("buses", []):
        if b["name"] == bus and "window_um" in b:
            return b, "window_um"
    for s_ in t.get("ft_slots", []):
        if bus == s_["name"] + "_i" and "in_window_um" in s_:
            return s_, "in_window_um"
        if bus == s_["name"] + "_o" and "out_window_um" in s_:
            return s_, "out_window_um"
    raise KeyError((part, bus))

def lo_for_hi(hi, pins, layers):
    per = 6.0 * len(layers) / float(P.budgets.get("face_pin_layers", 2))
    lo = hi - pins / per
    lo = round(lo - (lo % 0.016), 4)
    while S.window_for(lo, pins, layers, P.layers, per_um=per, track_max=float(P.budgets.get("pin_track_max", 0.6))) > hi + 1e-9:
        lo = round(lo - 0.016, 4)
    return lo

rep = dict(schema="opentallas.hbm.die_hbm_33.repack_edge.v1", base=a.plan, moves=[])
EDGES = [e.split(":") for e in a.edge] or [["b000", "b010", str(a.below)]]
for h, (ea, eb, ebelow) in [(h, e) for e in EDGES for h in ("NW", "NE")]:
    A, B = f"{h}_{ea}", f"{h}_{eb}"
    below = float(ebelow)
    df, elo, ehi = LA.shared_edge(P, A, B)
    rows = []
    for pid, pr in P.ports.items():
        s, d = pr["src"]["part"], pr["dst"]["part"]
        if {s, d} != {A, B} or "window_um" not in pr:
            continue
        if pr.get("segments"):
            raise SystemExit(f"{pid} has segments")
        w0, w1 = sorted(pr["window_um"])
        rows.append((w0, w1, pid, pr))
    rows.sort()
    block = [r for r in rows if r[0] < below]
    above = [r for r in rows if r[0] >= below]
    top = (min(r[0] for r in above) if above else ehi - 1.0) - a.anchor_guard
    cur = top
    for w0, w1, pid, pr in reversed(block):
        pins = S.port_pins_count(pr)
        lays = pr["layers"]
        lo = lo_for_hi(round(cur, 4), pins, lays)
        new = [lo, round(cur, 4)]
        # write both ends' type geometry (die face of src toward dst = pr["face"])
        for side in ("src", "dst"):
            part, bus = pr[side]["part"], pr[side]["bus"]
            el, key = geom_elem(part, bus)
            dface = pr["face"] if side == "src" else LA.OPP[pr["face"]]
            tf, tw, flip = LA.to_type_window(P, part, dface, new)
            old = list(el[key]); el[key] = tw
            rep["moves"].append(dict(port=pid, part=part, bus=bus, key=key, type_old=old, type_new=tw))
        rep.setdefault("ports", []).append(dict(port=pid, pins=pins, die_old=[w0, w1], die_new=new,
                                                dens_old=round(pins / (w1 - w0), 3), dens_new=round(pins / (new[1] - new[0]), 3),
                                                shift_centre=round((new[0] + new[1] - w0 - w1) / 2, 2)))
        cur = lo - a.sep
    rep.setdefault("free_bottom", {})[A + "|" + B] = [round(elo, 3), round(cur + a.sep, 3), round(cur + a.sep - elo, 2)]
os.makedirs(a.out, exist_ok=False)
for f in os.listdir(a.plan):
    if f in ("die_plan.json",):
        continue
    src = os.path.join(a.plan, f)
    os.link(src, os.path.join(a.out, f)) if os.path.isfile(src) else os.symlink(os.path.realpath(src), os.path.join(a.out, f))
raw["note"] = "DIE-HBM-33 V-E2 b000|b010 lower-block re-window at 6/um | " + raw.get("note", "")
json.dump(raw, open(os.path.join(a.out, "die_plan.json"), "w"), indent=1)
rep["out_sha"] = hashlib.sha256(open(os.path.join(a.out, "die_plan.json"), "rb").read()).hexdigest()[:12]
json.dump(rep, open(os.path.join(a.out, "repack_report.json"), "w"), indent=1)
print(json.dumps(rep["free_bottom"]), rep["out_sha"])
for r in rep["ports"]:
    print(r)

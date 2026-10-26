#!/usr/bin/env python3
"""KV-P6-SPINE 10-23 (COORD DIE-PLAN VISUAL REVIEW: north-half star / single W column): re-route die lanes onto a new
partition path -- a lane-router post step that touches lanes / ports / windows / ft_slots only (never hard_cores, so it
composes with KV-P6-PINS' core pins).

Measured on v3.7 (horizontal cuts y 21000..24000, G0 cut model): the north IO-row <-> hub traffic is 6,064 bits, W
corridor (hgi_WN, -> hub_Wi) 3,963 = 65 %, E corridor (hgi_EN, -> hub_Ei/hub_C) 1,998 = 33 %.  The W excess is the
hub_Wi endpoints (host, kvs_emb, serdes rx).  serdes_E.rx_flit (L2045, 522 b, sys_SE at the NE corner) ran WEST along the
IO row (io_E6, io_E5, sys_c, io_W3) and down the W corridor; its natural path is the E corridor (io_E6, io_E5, hgi_EN_0..7)
then W along the hub row (hub_Ei, hub_C) into hub_Wi: the same 12 crossings, so the station count -- and the R8
phy_rx_flit alignment with serdes_W.rx_flit (L2048, 36 bound stages) -- is unchanged.  After: W 3,441 (57 %), E 2,520.
No other move is cycle-neutral: every sys_c <-> hub_Wi lane gains 2 hub crossings (+5 stages) via the E corridor and is
in an R8 bus group (engine_result / record_tx / emb_tx); see the KV-P6-SPINE line in TOPDOWN-PLAN.md.

ROUTES: lane -> (partition path after the kept prefix ports, keep_ports).  The lane's first keep_ports ports stay
(windows and buses); the ft slot the last kept port feeds is re-faced toward the next partition; every later port is
re-made on the new path with a fresh ft slot per crossed partition (stations = ceil(route / ft_station_max_um)) and a
window in the first free span shared by every face of a straight run.  Slots no lane uses any more are dropped.

    python3 post_v37s.py die_plan_in.json > die_plan.json
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("OT_DIE_PLAN_TOOLS", os.path.join(HERE, "..", "..", "..", "tools", "die_plan")))
import schema as S  # noqa: E402
from check import zroute, plen  # noqa: E402

ROUTES = {   # lane: (path from the partition the last kept port feeds, kept ports, window preference per straight run,
            #        natural stages to keep: extra stations go to the longest-per-station crossing)
    "L2045": (["io_E5", "hgi_EN_0", "hgi_EN_1", "hgi_EN_2", "hgi_EN_3", "hgi_EN_4", "hgi_EN_5", "hgi_EN_6", "hgi_EN_7",
               "pv_N_7", "hgi_WN_7", "hub_Wi"], 2, ["high", "low", "high"], 36),
}
GAP = 8.64            # clearance to any other window on the same face line (one lattice step)
LAYERS = {"NS": ["M5", "M7"], "EW": ["M4", "M6"]}


def face_between(P, a, b):
    """die face of a that abuts b, and the shared span [lo, hi] along it."""
    ra, rb = P.rect(a), P.rect(b)
    E = 1e-3
    if abs(ra[2] - rb[0]) < E:
        return "E", max(ra[1], rb[1]), min(ra[3], rb[3])
    if abs(ra[0] - rb[2]) < E:
        return "W", max(ra[1], rb[1]), min(ra[3], rb[3])
    if abs(ra[3] - rb[1]) < E:
        return "N", max(ra[0], rb[0]), min(ra[2], rb[2])
    if abs(ra[1] - rb[3]) < E:
        return "S", max(ra[0], rb[0]), min(ra[2], rb[2])
    raise SystemExit(f"post_v37s: {a} and {b} do not abut")


def line_key(P, part, face):
    r = P.rect(part)
    return ("x", round(r[2] if face == "E" else r[0], 3)) if face in "EW" else ("y", round(r[3] if face == "N" else r[1], 3))


def occupied(P, raw, key, skip):
    occ = []
    for pr in raw["ports"]:
        if pr["id"] in skip or pr["src"]["part"] == S.DIE_PART or pr["dst"]["part"] == S.DIE_PART:
            continue
        fp = pr["src"]["part"]
        if line_key(P, fp, pr["face"]) == key:
            occ.append(tuple(pr["window_um"]))
    return occ


def free_span(spans, occ, w, pref):
    """first [lo, lo+w] inside every span (common intersection) clear of occ by GAP, on the 8.64 lattice."""
    lo = max(s[0] for s in spans) + 4 * GAP
    hi = min(s[1] for s in spans) - 4 * GAP
    cands = []
    x = math.ceil(lo / GAP) * GAP
    while x + w <= hi:
        if all(x + w + GAP <= a or x >= b + GAP for a, b in occ):
            cands.append(x)
        x += GAP
    if not cands:
        raise SystemExit(f"post_v37s: no free {w:.1f}-um span in {lo:.0f}..{hi:.0f}")
    if pref == "high":
        return max(cands)
    if pref == "low":
        return min(cands)
    mid = (lo + hi) / 2.0
    return min(cands, key=lambda c: abs(c + w / 2.0 - mid))


def main():
    raw = json.load(open(sys.argv[1]))
    log = []
    for lid, (path, keep, prefs, target) in ROUTES.items():
        P = S.Plan(raw)
        ln = P.lanes[lid]
        width = P.ports[ln["ports"][0]]["width"]
        old = list(ln["ports"])
        drop = set(old[keep:])
        old_nat = P.lane_natural(lid)
        old_slots = [(part, slot) for part, slot, _, _ in P.lane_crossings(lid)]
        last = P.ports[old[keep - 1]]
        assert last["dst"]["part"] == path[0], (lid, last["dst"], path[0])
        hops = list(zip(path, path[1:]))
        # windows: group consecutive hops on one straight line run (same face orientation + same along-axis)
        faces = [face_between(P, a, b) for a, b in hops]
        wins = [None] * len(hops)
        i = 0
        runs = 0
        while i < len(hops):
            j = i
            ax = "NS" if faces[i][0] in "NS" else "EW"
            while j + 1 < len(hops) and (faces[j + 1][0] in "NS") == (ax == "NS") and faces[j + 1][0] == faces[i][0]:
                j += 1
            run = range(i, j + 1)
            need = S.window_for(0.0, width, LAYERS[ax])
            occ = []
            for k in run:
                occ += occupied(P, raw, line_key(P, hops[k][0], faces[k][0]), drop)
            lo = free_span([(faces[k][1], faces[k][2]) for k in run], occ, need, prefs[runs])
            runs += 1
            for k in run:
                wins[k] = [round(lo, 3), round(lo + need, 3)]
            i = j + 1
        # strip the old ports, rebuild the tail
        raw["ports"] = [p for p in raw["ports"] if p["id"] not in drop]
        T = raw["partition_types"]
        pos = {p["name"]: p for p in raw["partitions"]}
        new_ids = []
        mine = {}                 # type -> the slot this lane got (instances of one type share it)
        prev_in = last            # the port feeding path[0]
        for k, (a, b) in enumerate(hops):
            f, _, _ = faces[k]
            ta = T[pos[a]["type"]]
            # slot of a: in = the face prev_in arrives on (die face of a), out = f
            in_face = OPP(faces[k - 1][0]) if k else OPP(face_of_port(P, prev_in, a))
            if k == 0:
                sname = prev_in["dst"]["bus"][:-2]
                slot = next(s for s in ta["ft_slots"] if s["name"] == sname)
                slot["out_face"] = P.type_face(a, f)
            else:
                tf = (P.type_face(a, in_face), P.type_face(a, f))
                if pos[a]["type"] in mine:
                    sname = mine[pos[a]["type"]]
                    s0 = next(s for s in ta["ft_slots"] if s["name"] == sname)
                    assert (s0["in_face"], s0["out_face"]) == tf, (a, sname, tf)
                else:
                    sname = next_slot(ta)
                    ta["ft_slots"].append(dict(name=sname, in_face=tf[0], out_face=tf[1], width=width, stations=1))
                    mine[pos[a]["type"]] = sname
                for pr in raw["ports"]:
                    if pr["id"] == new_ids[-1]:
                        pr["dst"]["bus"] = sname + "_i"
            pid = f"{lid}_{keep + k}"
            dst_bus = ln_last_bus(P, old) if b == path[-1] else "ftX_i"
            pr = dict(id=pid, src=dict(part=a, bus=sname + "_o"), dst=dict(part=b, bus=dst_bus), width=width,
                      kind=P.ports[old[0]]["kind"], face=f, layers=list(LAYERS["NS" if f in "NS" else "EW"]),
                      window_um=wins[k], order=P.ports[old[0]].get("order", "lsb_low"))
            raw["ports"].append(pr)
            new_ids.append(pid)
            prev_in = pr
        for x in raw["lanes"]:
            if x["id"] == lid:
                x["ports"] = old[:keep] + new_ids
                x["note"] = x.get("note", "") + " | v3.7s: re-routed " + "->".join(path)
        # stations from the routed length (<= ft_station_max_um per station)
        P = S.Plan(raw)
        smax = float(P.budgets.get("ft_station_max_um", 750.0))
        lens = {}
        for part, slot, pa, pb in P.lane_crossings(lid)[keep - 1:]:
            s = P.slot(part, slot)
            fin, fout = P.die_face(part, s["in_face"]), P.die_face(part, s["out_face"])
            L = plen(zroute(P.port_point(pa), P.port_point(pb), fin, fout))
            w, h = P.ptype(part)["outline_um"]          # G0 geometry: type span per station <= reach
            fs = {s["in_face"], s["out_face"]}
            span = w if fs == {"E", "W"} else h if fs == {"N", "S"} else (w + h) / 2.0
            s["stations"] = max(s["stations"] if id(s) in lens else 1, math.ceil(L / smax - 1e-9),
                                math.ceil(span / P.reach - 1e-9))
            lens[id(s)] = (max(L, lens.get(id(s), (0, s))[0]), s)
        P = S.Plan(raw)
        while P.lane_natural(lid)["cycles"] < target:      # keep the lane's stage count (R8 / latency tables stand)
            per = {}
            for part, slot, _, _ in P.lane_crossings(lid)[keep - 1:]:
                L, s = lens[id(P.slot(part, slot))]
                per[id(s)] = (L / s["stations"], s)
            max(per.values(), key=lambda v: v[0])[1]["stations"] += 1
            P = S.Plan(raw)
        # drop slots no lane uses any more
        P = S.Plan(raw)
        used = {}
        for l2 in P.lanes:
            for part, slot, _, _ in P.lane_crossings(l2):
                used.setdefault(P.parts[part]["type"], set()).add(slot)
        dropped = []
        for part, slot in old_slots:
            tn = P.parts[part]["type"]
            if slot and slot not in used.get(tn, set()):
                T[tn]["ft_slots"] = [s for s in T[tn]["ft_slots"] if s["name"] != slot]
                dropped.append(f"{tn}.{slot}")
        P = S.Plan(raw)
        nat = P.lane_natural(lid)
        assert nat["cycles"] == target, (lid, nat["cycles"], target)
        dropped = sorted(set(dropped))
        log.append(f"{lid} ({width} b): {old_nat['cycles']} -> {nat['cycles']} stages; dropped slots {dropped}")
    raw["note"] = raw.get("note", "") + (" | v3.7s (KV-P6-SPINE 10-23): " + "; ".join(log) +
                                         " (north W corridor 65% -> 57% of the IO-row<->hub bits)")
    sys.stderr.write("post_v37s: " + "\n  ".join(log) + "\n")
    json.dump(raw, sys.stdout, indent=1)
    sys.stdout.write("\n")


def OPP(f):
    return {"N": "S", "S": "N", "E": "W", "W": "E"}[f]


def face_of_port(P, pr, part):
    """die face of `part` on which port pr lies (pr's face is a face of its src part)."""
    return OPP(pr["face"]) if pr["src"]["part"] != part else pr["face"]


def next_slot(t):
    n = 0
    names = {s["name"] for s in t.get("ft_slots", [])}
    while f"ft{n}" in names:
        n += 1
    return f"ft{n}"


def ln_last_bus(P, old):
    return P.ports[old[-1]]["dst"]["bus"]


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""S81 relay-bay k -> k' lane cycle event for TOK (COORD 11-03 10:49: "+1/+2 lane cycles from relay bays: DIE-S81-51
issues the k->k' event, TOK-VERIFY-1 re-prices").

    relay_bay_cycle_event_1103.py PLAN OUT.json [--kit-decl DECLARED_CYCLES.json ...]

The relay-bay form (tools/die_plan/relay_bay.py, SAFE-STATION-1) applies to the wire-only station kits (S81
slice_station*).  Per ft slot of length L (in-pin -> out-pin window centre, Manhattan, type frame) with k planned
stations (ft_slots[].stations):  landed (landing-ring input, landing_contract.ring_input_ports)  k' = max(k, ceil(L/300));
plain (station 0 = in-face register)  k' = max(k, ceil(L/300) + 1); extra cycles k' - k.  Every die port whose receiver
is such a slot adds that slot's extra cycles to its lane (plan lanes[]), so per lane: k_old = planned station cycles
on the lane, k_new = k_old + extra.  near_hop_boundary: L within 2 um of a 300-um multiple, where ceil() decides k'
(the kit pin centroid may round the other way; the kit's declared_cycles.json then rules).  The kit's declared_cycles.json (written by relay_bay.py from the kit's real pin
centroids) stays the per-kit authority; --kit-decl cross-checks this plan-time table against built kits."""
import argparse, collections, hashlib, json, math, re, sys
from pathlib import Path
TD = Path(__file__).resolve().parents[3] / "tools/die_plan"
sys.path.insert(0, str(TD))
import schema as S, landing_contract as LC

ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("out")
ap.add_argument("--max-hop", type=float, default=300.0)
ap.add_argument("--types", default=r"^slice_station")
ap.add_argument("--kit-decl", nargs="*", default=[])
a = ap.parse_args()
raw = json.load(open(a.plan)); P = S.Plan(raw, a.plan)


def centre(t, face, win):
    w, h = t["outline_um"]; m = 0.5 * (win[0] + win[1])
    return {"E": (w, m), "W": (0.0, m), "N": (m, h), "S": (m, 0.0)}[face]


def inferred_in_window(tn, s):
    """type-frame in window of a slot that declares none (QC ft slots): the die-frame window of the abutted port landing
    on <slot>_i, mapped back through the instance origin / orientation.  All instances of the type must agree (1 um)."""
    t, out = P.types[tn], []
    for pr in P.ports.values():
        d = pr["dst"]
        if d["part"] == S.DIE_PART or d["bus"] != s["name"] + "_i" or P.parts[d["part"]]["type"] != tn or "window_um" not in pr:
            continue
        p = P.parts[d["part"]]; w, h = t["outline_um"]; o = p.get("orient", "R0"); a, b = pr["window_um"]
        base, ext, flip = (p["origin_um"][1], h, o in ("MX", "R180")) if s["in_face"] in "EW" else (p["origin_um"][0], w, o in ("MY", "R180"))
        a, b = a - base, b - base
        out.append([ext - b, ext - a] if flip else [a, b])
    if not out:
        raise SystemExit(f"{tn} {s["name"]}: no in_window_um and no port window")
    if max(abs(x[0] - out[0][0]) + abs(x[1] - out[0][1]) for x in out) > 1.0:
        raise SystemExit(f"{tn} {s["name"]}: instances disagree on the in window")
    return out[0]


slots = {}
for tn, t in sorted(P.types.items()):
    if not re.search(a.types, tn) or not t.get("ft_slots"):
        continue
    ring = {x.split("[")[0] for _c, sel in LC.ring_input_ports(P, tn) for x in sel}
    for s in t["ft_slots"]:
        A, B = centre(t, s["in_face"], s.get("in_window_um") or inferred_in_window(tn, s)), centre(t, s["out_face"], s["out_window_um"])
        L = abs(A[0] - B[0]) + abs(A[1] - B[1])
        landed = s["name"] + "_i" in ring
        k = int(s.get("stations", 1)); n = math.ceil(L / a.max_hop - 1e-9)
        k2 = max(k, n) if landed else max(k, n + 1)
        near = abs(L / a.max_hop - round(L / a.max_hop)) * a.max_hop <= 2.0
        slots.setdefault(tn, {})[s["name"]] = dict(landed=landed, L_um=round(L, 1), k=k, k_new=k2, extra_cycles=k2 - k,
                                                   **({"near_hop_boundary": True} if near else {}))
lanes, lane_of = {}, {p: l for l in raw["lanes"] for p in l["ports"]}
for pid, pr in P.ports.items():
    d = pr["dst"]
    if d["part"] == S.DIE_PART:
        continue
    tn = P.parts[d["part"]]["type"]; b = d["bus"]
    if tn not in slots or not b.endswith("_i") or b[:-2] not in slots[tn]:
        continue
    l = lane_of.get(pid)
    lid = l["id"] if l else pid
    e = lanes.setdefault(lid, dict(fixed_cycles=(l or {}).get("fixed_cycles"), k_old=0, k_new=0, extra_cycles=0, hops=[]))
    z = slots[tn][b[:-2]]
    e["k_old"] += z["k"]; e["k_new"] += z["k_new"]; e["extra_cycles"] += z["extra_cycles"]
    e["hops"].append(dict(port=pid, part=d["part"], type=tn, slot=b[:-2], **z))
chk = []
for f in a.kit_decl:
    dj = json.load(open(f)); tn = dj["kit"]
    for s, v in dj["lanes"].items():
        z = slots.get(tn, {}).get(s)
        chk.append(dict(kit=tn, slot=s, kit_k=v["stations_plan"], kit_k_new=v["stations_new"], kit_landed=v["landed"],
                        kit_L_um=v["L_um"], plan=z, match=bool(z) and z["k"] == v["stations_plan"]
                        and z["k_new"] == v["stations_new"] and z["landed"] == v["landed"]))
ext = collections.Counter(e["extra_cycles"] for e in lanes.values())
sl = collections.Counter(z["extra_cycles"] for v in slots.values() for z in v.values())
ev = {"schema": "opentallas.cycle_event.v1", "die": "s81", "event": "S81 relay-bay k->k' (DIE-S81-51/PLAN 11-03)",
      "form": "relay_bay_300", "max_hop_um": a.max_hop, "types_re": a.types,
      "plan": a.plan, "plan_sha256": hashlib.sha256(open(a.plan, "rb").read()).hexdigest(),
      "rule": "landed k'=max(k,ceil(L/300)); plain k'=max(k,ceil(L/300)+1); lane k_new = k_old + sum of the extra "
              "cycles of the relay-bay slots its die ports land on; kit declared_cycles.json is the per-kit authority",
      "summary": {"types": len(slots), "slots": sum(len(v) for v in slots.values()),
                  "slots_by_extra": dict(sorted(sl.items())), "lanes": len(lanes),
                  "lanes_changed": sum(1 for e in lanes.values() if e["extra_cycles"]),
                  "lanes_by_extra": dict(sorted(ext.items())), "max_lane_extra": max(ext, default=0),
                  "near_hop_boundary_slots": sum(1 for v in slots.values() for z in v.values() if z.get("near_hop_boundary")),
                  "kit_crosscheck": f"{sum(c['match'] for c in chk)}/{len(chk)}"},
      "kit_crosscheck": chk, "lanes": dict(sorted(lanes.items())), "slots": slots}
json.dump(ev, open(a.out, "w"), indent=1)
print(json.dumps(ev["summary"]), json.dumps([c for c in chk if not c["match"]])[:600])

#!/usr/bin/env python3
"""vl2_delta.py make BASE NEW TYPES OUT  |  vl2_delta.py apply BASE DELTA OUT
VISLAYOUT2-S81 positions-only plan delta (ladder format: base/plan sha256 + per-type edits).  Per type: every hard core
whose origin_um moved (kind core, was/now), every clock.added_taps site that moved (kind added_tap), and the derived clock
fields core_place recomputes from those positions (taps xy, tap_um, landing_contract) as kind clock_derived (now = value).
apply refuses a base whose sha256 differs, and checks that every 'was' still matches."""
import json, sys, hashlib, copy
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
DER = ("taps", "tap_um", "landing_contract")
if sys.argv[1] == "make":
    base, new, types, out = sys.argv[2:6]
    B = json.load(open(base)); N = json.load(open(new)); d = {"schema": "opentallas.vl2_position_delta.v1",
        "base_sha256": sha(base), "plan_sha256": sha(new), "types": {}}
    for T in types.split(","):
        bt, nt = B["partition_types"][T], N["partition_types"][T]; ed = []
        bp = {h["inst"]: h["origin_um"] for h in bt["hard_cores"]}
        for h in nt["hard_cores"]:
            if h["origin_um"] != bp[h["inst"]]: ed.append({"kind": "core", "inst": h["inst"], "was": bp[h["inst"]], "now": h["origin_um"]})
        ba = {p["name"]: p["xy"] for p in bt["clock"].get("added_taps") or []}
        for p in nt["clock"].get("added_taps") or []:
            if p["xy"] != ba.get(p["name"]): ed.append({"kind": "added_tap", "name": p["name"], "was": ba.get(p["name"]), "now": p["xy"]})
        for k in DER:
            if bt["clock"].get(k) != nt["clock"].get(k): ed.append({"kind": "clock_derived", "key": k, "now": nt["clock"].get(k)})
        d["types"][T] = ed
    json.dump(d, open(out, "w"), indent=1)
    print({T: len(e) for T, e in d["types"].items()}, d["plan_sha256"][:12])
else:
    base, delta, out = sys.argv[2:5]
    D = json.load(open(delta)); assert sha(base) == D["base_sha256"], "base sha differs"
    B = json.load(open(base))
    for T, ed in D["types"].items():
        t = B["partition_types"][T]; hc = {h["inst"]: h for h in t["hard_cores"]}; at = {p["name"]: p for p in t["clock"].get("added_taps") or []}
        for e in ed:
            if e["kind"] == "core":
                assert hc[e["inst"]]["origin_um"] == e["was"], (T, e["inst"]); hc[e["inst"]]["origin_um"] = e["now"]
            elif e["kind"] == "added_tap":
                assert at[e["name"]]["xy"] == e["was"], (T, e["name"]); at[e["name"]]["xy"] = e["now"]
            else:
                t["clock"][e["key"]] = copy.deepcopy(e["now"])
    json.dump(B, open(out, "w"), indent=1)
    s = sha(out); print("applied", s[:12], "MATCH" if s == D["plan_sha256"] else "differs from recorded plan_sha256 (json formatting?)")

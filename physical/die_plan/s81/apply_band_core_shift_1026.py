#!/usr/bin/env python3
"""PATH-S81-PD6 10-27: plan-declared clock-landing storage bands by rigid hard-core-set offsets.

The 17 PD4/PD5 storage-band FAILs (clock_landing_plan._storage_band) are dense-core types whose white space sits on the
wrong faces: e.g. the svc hcore array (72 cores) leaves 12.96 um free on W/S and 19.44 um on E, while a 2,133-bit
landing ring needs a 36.72-um-deep band within 403 um of its pin.  The fix moves the existing white space to the
faces that carry the landed inputs: every hard core of the type, its core clock-entry taps, the partition clock tap
and the internal (core-to-core) stations move by ONE vector (dx, dy) chosen per type by a replay of the unchanged band
search (results/path_s81_pd6_1026/bands/shift_sel.json).  Outline, face buses/pins, FT slots, partitions: unchanged.
Core-relative geometry (channels, core-to-core stations) is preserved exactly.

usage: apply_band_core_shift_1026.py PLAN_IN PLAN_OUT SHIFTS_JSON LEDGER_OUT
SHIFTS_JSON = {type: [dx_um, dy_um]} (multiples of 2.16 um = 8 rows x 0.27; keeps site/track alignment)."""
import json, sys
src, dst, shp, ledp = sys.argv[1:5]
raw = json.load(open(src)); sh = json.load(open(shp)); led = {}
G = 2.16
for tn, (dx, dy) in sorted(sh.items()):
    t = raw["partition_types"][tn]
    for v in (dx, dy):
        if abs(v / G - round(v / G)) > 1e-6:
            raise SystemExit(f"{tn}: shift {v} is not a multiple of {G}")
    w, h = t["outline_um"]
    mv = lambda p: [round(p[0] + dx, 6), round(p[1] + dy, 6)]
    n = dict(hard_cores=0, core_taps=0, tap_um=0, internal_stations=0)
    for c in t.get("hard_cores", []):
        c["origin_um"] = mv(c["origin_um"]); n["hard_cores"] += 1
        cw, ch = c["outline_um"]
        if c.get("orient") in ("R90", "R270", "MXR90", "MYR90"): cw, ch = ch, cw
        x, y = c["origin_um"]
        if x < 0 or y < 0 or x + cw > w + 1e-6 or y + ch > h + 1e-6:
            raise SystemExit(f"{tn}: core {c['inst']} leaves the outline after shift")
    ck = t.get("clock", {})
    for tp in ck.get("taps", []) or []:
        if tp.get("kind") == "core":
            tp["xy"] = mv(tp["xy"]); n["core_taps"] += 1
    if "tap_um" in ck:
        ck["tap_um"] = mv(ck["tap_um"]); n["tap_um"] = 1
    for s in t.get("internal_stations", []) or []:
        for k in ("from_um", "to_um"):
            if k in s: s[k] = mv(s[k])
        s["regs_um"] = [mv(p) for p in s.get("regs_um", [])]; n["internal_stations"] += 1
    t["note"] = (t.get("note", "") + f"; PATH-S81-PD6 10-27 band core shift ({dx:+.2f},{dy:+.2f}) um: "
                 "white space moved to the landed-input faces (clock landing storage bands)").strip("; ")
    led[tn] = dict(shift_um=[dx, dy], moved=n, instances=sorted(p["name"] for p in raw["partitions"] if p["type"] == tn))
json.dump(raw, open(dst, "w"), indent=1)
json.dump(led, open(ledp, "w"), indent=1)
print("RESULT types", len(led), "cores", sum(v["moved"]["hard_cores"] for v in led.values()))

#!/usr/bin/env python3
"""DIE-QC-97 HC1-STRIP 11-11 plan event: put the hc1 b_hw_i ring back over its own pins, then spread it over 3 rows.

What fails: sle_hc1__cl7d360508 fails GRT-0116 on 11-09 with 22,032 overflow (MEASURED, kit congestion.rpt).  Of that,
14,542 is vertical, at the edges of the u_cland_b_hw_i pinslot strip, and 7,490 is horizontal.  The b_hw_i bus
(1573 bits) has its S pins at x 4.32..276.29.  Its band is [108.528, 17.28, 380.496, 62.64], 104 um east of the pins,
because rs_n1 [17.28, 17.28, 69.12, 106.368] holds the SW corner.  So about 600 bits leave their pins westward under the
band (face_crossing demand 602.7 > the strip cap 536.5), and the ring flops pack into an 11.61-um strip at rows 1.
slw_hc1__cl3449ea95, slw_hc1__cl68f9248e__cl144ee7b3 and slw_hc1__cl68f9248e__cle683a076 have the same two band rects.
sle_hc1__cl22c1ff36 already has b_hw_i at [17.28, 17.28, 289.248, 62.64]; its bands are not touched.
This event does two things.
1. For each sle_hc1 / slw_hc1 type whose b_hw_i is not at HOME = [17.28, 17.28, 289.248, 62.64]:
   - b_hw_i moves to HOME.  It keeps its size (271.968 x 45.36) and sits over the pins (crossing 75.0 bits).
   - rs_n1 is the only band that overlaps HOME.  It moves north, to just above HOME plus one 2.16-um gap:
     [17.28, 64.8, 69.12, 153.888].  It keeps its size and its W face (face distance 17.28 as before).  Its crossing
     grows to 348.9 bits, which is inside the W strip cap of 555.
   - Each moved band gets a new max_pin_to_band_hop_um (b_hw_i 211.584, rs_n1 174.144, both <= 402.84),
     resized_from_um = its old rect, and a resize note.  Every other field and band stays byte-identical.
   - apply() refuses (no partial plan) unless each new rect is inside the 17.28-um margin, within the 402.84-um pin
     reach and the strip crossing cap, and clear of every planning obstacle of cland_band_fit.obstacles.  The one
     exception is the collector reset-relay sites, which the old rects already overlapped: the compose obstacle set
     leaves them out unless budgets.cland_avoid_reset_types names the type, and the hc1 types are not named there.
2. budgets.cland_strip_rows_types sle_hc1 = slw_hc1 = 3, the same knob as HC2-STRIP.  All five hc1 types export
   OT_CLAND_STRIP_ROWS = 3, clamped by the 45.36-um band depth.
No RTL, outline, pin, lane, clock-tap, reset-tree or collector-source change: the collector sources hop from the
pin xy to their reset node, and neither of those moves.  The event refuses to run when cland_strip_rows_types already
sets an hc1 key, and on a plan without hc1 types.
    delta_hc1_strip_1111.py PLAN.json OUT.json   -> prints {keys, types, moved, sha256_in, sha256_out}
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))

ROWS = 3
BASES = ("sle_hc1", "slw_hc1")
HOME = [17.28, 17.28, 289.248, 62.64]       # b_hw_i over its S pins x 4.32..276.29, same size as the old band
GAP = 2.16
MARGIN = 17.28
REACH = 405 - 2.16
NOTE = "DIE-QC-97 HC1-STRIP 11-11: b_hw_i back over its own S pins; rs_n1 north of it, same W face"


def hc1_types(raw):
    return sorted(t for t in raw.get("partition_types", {}) if t.split("__")[0] in BASES)


def _ov(a, o):
    return min(a[2], o[2]) > max(a[0], o[0]) + 1e-6 and min(a[3], o[3]) > max(a[1], o[1]) + 1e-6


def _same(a, b):
    return len(a) == len(b) and all(abs(x - y) < 1e-6 for x, y in zip(a, b))


def check_band(raw, plan_obj, tn, t, lc, bus, rect):
    """-> hop_um; SystemExit unless rect is a legal face band for bus in type t with lc's other bands."""
    import clock_landing_plan as C
    import cland_band_fit as F
    w, h = t["outline_um"]
    if rect[0] < MARGIN - 1e-6 or rect[1] < MARGIN - 1e-6 or rect[2] > w - MARGIN + 1e-6 or rect[3] > h - MARGIN + 1e-6:
        raise SystemExit(f"HC1-STRIP: {tn}.{bus} {rect} outside the {MARGIN}-um margin")
    width = int(lc["bands"][bus]["width"])
    px, py = C._bus_xy(t, bus)
    hop = max(abs(x - px) + abs(y - py) for x in (rect[0], rect[2]) for y in (rect[1], rect[3]))
    if hop > REACH + 1e-6:
        raise SystemExit(f"HC1-STRIP: {tn}.{bus} hop {hop:.3f} > {REACH}")
    dm, cap = C.face_crossing(t, bus, rect, width)
    if dm > cap + 1e-6:
        raise SystemExit(f"HC1-STRIP: {tn}.{bus} crossing {dm:.1f} bits > strip cap {cap:.1f}")
    resets = C.reset_site_rects(lc.get("collector_tree")) if not C._reset_sites_for_type(
        raw, tn, lc.get("collector_tree"), lc.get("base_type")) else []
    skip = {tuple(r) for r in resets}
    obs = [o for o in F.obstacles(t, tn, plan_obj, None, lc, bus) if tuple(o) not in skip]
    hit = [o for o in obs if _ov(rect, o)]
    if hit:
        raise SystemExit(f"HC1-STRIP: {tn}.{bus} {rect} hits {len(hit)} planning obstacles, e.g. {hit[:3]}")
    return round(hop, 3)


def apply(raw):
    types = hc1_types(raw)
    for b in BASES:
        if not any(t.split("__")[0] == b for t in types):
            raise SystemExit(f"HC1-STRIP: plan has no {b} type")
    bud = raw.setdefault("budgets", {})
    per = bud.get("cland_strip_rows_types")
    if per is None:
        per = {}
    have = [k for k in list(BASES) + types if k in per]
    if have:
        raise SystemExit(f"HC1-STRIP: cland_strip_rows_types already sets {have} (merge by hand)")
    import schema as S
    plan_obj = S.Plan(raw) if (raw.get("die") or {}).get("pg", {}).get("domains") and raw.get("partitions") else None
    moved = {}
    for tn in types:
        t = raw["partition_types"][tn]
        lc = t["clock"]["landing_contract"]
        bands = lc["bands"]
        if _same(bands["b_hw_i"]["rect_um"], HOME):
            continue
        over = sorted(k for k, o in bands.items() if k != "b_hw_i" and o.get("rect_um") and _ov(HOME, o["rect_um"]))
        if over != ["rs_n1"]:
            raise SystemExit(f"HC1-STRIP: {tn}: bands over b_hw_i home {HOME} are {over}, expected ['rs_n1']")
        r1 = bands["rs_n1"]["rect_um"]
        new = {"b_hw_i": list(HOME),
               "rs_n1": [r1[0], round(HOME[3] + GAP, 6), r1[2], round(HOME[3] + GAP + (r1[3] - r1[1]), 6)]}
        trial = copy.deepcopy(lc)
        for k, r in new.items():
            trial["bands"][k]["rect_um"] = r
        hops = {k: check_band(raw, plan_obj, tn, t, trial, k, r) for k, r in new.items()}
        for k, r in new.items():
            b = bands[k]
            moved.setdefault(tn, {})[k] = dict(old=list(b["rect_um"]), new=r, hop_um=hops[k])
            b["resized_from_um"] = list(b["rect_um"])
            b["rect_um"] = r
            b["max_pin_to_band_hop_um"] = hops[k]
            b["resize"] = NOTE
    for b in BASES:
        per[b] = ROWS
    bud["cland_strip_rows_types"] = per
    return raw, types, moved


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("output")
    a = p.parse_args()
    src = Path(a.input).read_bytes()
    raw, types, moved = apply(json.loads(src))
    out = (json.dumps(raw, separators=(",", ":")) + "\n").encode()
    Path(a.output).write_bytes(out)
    print(json.dumps({"keys": {b: ROWS for b in BASES}, "types": types, "moved": moved,
                      "sha256_in": hashlib.sha256(src).hexdigest(), "sha256_out": hashlib.sha256(out).hexdigest()}))


if __name__ == "__main__":
    main()

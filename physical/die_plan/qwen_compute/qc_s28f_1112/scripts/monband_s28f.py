#!/usr/bin/env python3
"""QC-S28-F F1 (MONITOR-BAND-SITE): re-site collector monitor landing bands that sit far from their own status pins.

Cause (measured on plan_qc99_s28): in 6 su types the monitor_<i> band (u_cland_monitor_<i>, a 2-bit forwarded-clock
landing ring) is the band of ANOTHER child slot (copied between sibling types whose children differ in order), 103-382
um from its child's cland_dn_ready/fault_<i> + fclk_in_cland_dn_<i> pins (slw_su_l1__clcc9d0155 monitor_0: pins on the W
face y 170-174, band on the S face x 250-298, pin->band far corner 448 um; its routed sign-off WRITE leg
cland_dn_fault_0 -> u_cland_monitor_0 is -161.2 ps TT).  Fix = positions only: the same band (w x h, area, flop count)
moved next to its pins.  0 cycles, ring/RTL unchanged.

Legal site: inside the outline by >= MARGIN, no overlap (with CLEAR um) with any hard core, any other landing band
(rect_um / rects_um), and no FIRM point inside it (ft_slots regs_um + bit_sites_um, internal_stations regs_um,
clock.landing_local_resets xy_um, clock.reset_tree_anchor relays xy).  Score = max over the 3 pins of the Manhattan
distance to the band's farthest corner (the plan's max_pin_to_band_hop_um definition); grid 2.16 um; both orientations.

usage: monband_s28f.py PLAN_IN PLAN_OUT REPORT_JSON TYPE:BAND[:MARGIN] [...]   (MARGIN default 17.28, the QC band convention)"""
import hashlib
import json
import sys

PIN, POUT, REP = sys.argv[1:4]
ITEMS = [a.split(":") for a in sys.argv[4:]]
CLEAR, GRID, WIN = 1.08, 2.16, 260.0
rb = open(PIN, "rb").read()
raw = json.loads(rb)


def overlap(a, b, c=0.0):
    return a[0] < b[2] + c and b[0] < a[2] + c and a[1] < b[3] + c and b[1] < a[3] + c


def far(p, r):
    return max(abs(p[0] - x) + abs(p[1] - y) for x in (r[0], r[2]) for y in (r[1], r[3]))


rep = dict(plan_in=hashlib.sha256(rb).hexdigest(), rows=[])
for it in ITEMS:
    tn, bname = it[0], it[1]
    FIX = None
    MARGIN = 17.28
    if len(it) > 2 and it[2].startswith("@"):
        FIX = tuple(float(v) for v in it[2][1:].split(","))     # explicit rect (sibling precedent), still checked
    elif len(it) > 2:
        MARGIN = float(it[2])
    t = raw["partition_types"][tn]
    W, H = t["outline_um"]
    ck = t["clock"]
    lc = ck["landing_contract"]
    band = lc["bands"][bname]
    i = bname.split("_")[1]
    pins = [p["xy_um"] for p in lc["pins"] if p["name"] in (f"cland_dn_ready_{i}", f"cland_dn_fault_{i}",
                                                             f"fclk_in_cland_dn_{i}")]
    if len(pins) != 3:
        raise SystemExit(f"{tn} {bname}: expected 3 pins, found {len(pins)}")
    r0 = band["rect_um"]
    w0, h0 = r0[2] - r0[0], r0[3] - r0[1]
    obst = []
    for h in t.get("hard_cores", []):
        (x, y), (w, hh) = h["origin_um"], h["outline_um"]
        if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        obst.append((x, y, x + w, y + hh))
    for k, b in lc["bands"].items():
        if k == bname:
            continue
        for r in [b["rect_um"]] + list(b.get("rects_um", [])):
            obst.append(tuple(r))
    pts = []
    for s in t.get("ft_slots", []) or []:
        pts += [tuple(p) for p in s.get("regs_um", [])]
        for bank in s.get("bit_sites_um", []) or []:
            pts += [tuple(p) for p in bank]
    for s in t.get("internal_stations", []) or []:
        if s.get("bit_route") != "per_bit":
            pts += [tuple(p) for p in s.get("regs_um", [])]
    pts += [tuple(s["xy_um"]) for s in ck.get("landing_local_resets", []) or []]
    pts += [tuple(r["xy"]) for r in (ck.get("reset_tree_anchor") or {}).get("relays", {}).values()]
    cx = sum(p[0] for p in pins) / 3
    cy = sum(p[1] for p in pins) / 3
    best = None
    if FIX is not None:
        r = FIX
        if abs((r[2] - r[0]) * (r[3] - r[1]) - w0 * h0) > 1e-3 or any(overlap(r, o, 0.0) for o in obst) or any(
                r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3] for p in pts):
            raise SystemExit(f"{tn} {bname}: explicit rect {r} illegal or not the band area")
        best = (max(far(p, r) for p in pins), r)
    for (w, h) in (((w0, h0), (h0, w0)) if FIX is None else ()):
        nx = int(2 * WIN / GRID)
        for ix in range(nx + 1):
            x0 = round((round((cx - WIN) / GRID) + ix) * GRID, 3)
            if x0 < MARGIN - 1e-6 or x0 + w > W - MARGIN + 1e-6:
                continue
            for iy in range(nx + 1):
                y0 = round((round((cy - WIN) / GRID) + iy) * GRID, 3)
                if y0 < MARGIN - 1e-6 or y0 + h > H - MARGIN + 1e-6:
                    continue
                r = (x0, y0, round(x0 + w, 3), round(y0 + h, 3))
                if any(overlap(r, o, CLEAR) for o in obst):
                    continue
                if any(r[0] - CLEAR <= p[0] <= r[2] + CLEAR and r[1] - CLEAR <= p[1] <= r[3] + CLEAR for p in pts):
                    continue
                sc = max(far(p, r) for p in pins)
                if best is None or sc < best[0] - 1e-9:
                    best = (sc, r)
    if best is None:
        raise SystemExit(f"{tn} {bname}: no legal site within {WIN} um of its pins")
    old_hop = max(far(p, r0) for p in pins)
    band["rect_um"] = list(best[1])
    band["max_pin_to_band_hop_um"] = round(best[0], 3)
    band["placement"] = (f"MONITOR-BAND-SITE QC-S28-F 11-12: re-sited next to its own status pins (was {r0}, "
                         f"pin->band far corner {old_hop:.1f} um, the band of another child slot); legal macro-free band")
    rep["rows"].append(dict(type=tn, band=bname, margin=MARGIN, pins=pins, old_rect=r0, old_hop_true=round(old_hop, 1),
                            old_hop_recorded=None, new_rect=list(best[1]), new_hop=round(best[0], 1)))
    print(tn, bname, "old", r0, "true hop %.1f" % old_hop, "-> new", list(best[1]), "hop %.1f" % best[0])
STYLES = (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
          lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n",
          lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p))
dump = next(f for f in STYLES if f(json.loads(rb)).encode() == rb)
txt = dump(raw)
open(POUT, "w").write(txt)
rep["plan_out"] = hashlib.sha256(txt.encode()).hexdigest()
json.dump(rep, open(REP, "w"), indent=1)

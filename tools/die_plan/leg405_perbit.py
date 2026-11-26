#!/usr/bin/env python3
"""leg405_perbit.py (C-LEG405-R3, 11-26): per-bit LEG405 station-hop census from the TRUE source, report only.

ADV-LEG405-STAGED (adv_fpconv.leg405_staged) reads relay_depth rows only: one path_um per row from the first planned station, so it
reads 0 on QC / KV while 25-29 types per die place hops over 405 um.  This module measures what the kit builds, per bit:

  (a) the chain starts at the real driver: the input pin (ring q pin of a landing core, die_hop_scan.type_tables) and ends at the
      out pin, not at the first planned station;
  (b) every bit has its own seat: bit_sites_um per bit, and for regs-only slots the kit's FT-LANE form
      (face_flops.tcl ff_lane_xy: plan stage site + (1-t)*(in pin - in centroid) + t*(out pin - out centroid)), not the slot centre line;
  (c) stale plan numbers and placed drift: the check recomputes every hop from the seats, never from leaf_um / path_um, and adds the
      drift margin DRIFT_UM calibrated on the 3_place OT_FT_LANE lines of the retained KV kits (CALIBRATION below): a hop is flagged
      when planned_hop + DRIFT_UM > 405.  When a placed ot_face_flops.txt exists, placed_hops() reads the real seats instead.

CALIBRATION (11-26; truth = the kit's own OT_FT_LANE line at 3_place, hops > 405 um; TP / FP / FN / TN):
  KV, 94 retained (type, wave) pairs on a mappable plan (65 placed over 405):
    relay_depth rows (old ADV-LEG405-STAGED, 3 cland hits)   0 / 3 / 65 / 26
    per-bit full chain, drift 0 um                            37 / 0 / 28 / 29
    per-bit full chain, drift 3 um  (DRIFT_UM, counted)       63 / 4 / 2 / 25
    per-bit full chain, drift 10 um (NEAR_UM, listed)         65 / 11 / 0 / 18
  KV, 63 distinct types, latest wave: before 0 / 1 / 43 / 19, drift 3: 42 / 3 / 1 / 17, drift 10: 43 / 8 / 0 / 12.
    FN kv3_pv_v5ne (placed 455.2, plan 396.9: placed drift 58 um); FP kv3_pv_v6e / hub_Ei / pc_v3 (placed 402-404 um, plan 402-404).
  QC, C9 c9eb8883ad40, 109 placed types (16 over 405): before 0 / 0 / 16 / 93, drift 3: 15 / 3 / 1 / 90, drift 10: 16 / 3 / 0 / 90.
  Live plans: KV 4c5a163e9a21 0 -> 58 types flagged; QC C9 0 -> 18 types.
  The planned hop tracks the placed one closely (hgi_v8 506.3 -> 506.2, hub_Wo 438 -> 460, pv_v12e 423.9 -> 418.8), so the margin is small.

Two numbers per slot: 'ss' = station -> station (what OT_FT_LANE reports) and 'full' = in pin -> s0 -> ... -> out pin.
Needs the plan loaded as schema.Plan (die_hop_scan.type_tables); never raises into plan_advisory."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

LIMIT_UM = 405.0
DRIFT_UM = 3.0           # KV calibration (91 placed type x wave pairs): planned hop + 3 um > 405 -> over (63 TP / 4 FP / 2 FN); see CALIBRATION
NEAR_UM = 10.0           # planned hop + 10 um > 405 -> near (65 TP / 10 FP / 0 FN): listed, not counted


def md(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def _centroid(pts):
    pts = list(pts)
    if not pts:
        return None
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def slot_chains(P, tn, slot, pins, normal, full):
    """{bit: [(x, y)]} = true source (in pin, inset) + stations 0..k-1 + out pin; type frame, um.  Same constructors as the kit."""
    import die_hop_scan as D
    from ft_full_stage import centre
    sn, k = slot["name"], int(slot.get("stations", 1))
    pi, po = pins.get(sn + "_i", {}), pins.get(sn + "_o", {})
    regs = slot.get("regs_um") or []
    only_regs = not slot.get("bit_sites_um") and len(regs) >= k and sn not in full
    cin, cout = _centroid((v[0], v[1]) for v in pi.values()), _centroid((v[0], v[1]) for v in po.values())
    out = {}
    for bit in sorted(set(pi) | set(po)):
        ap, bp = pi.get(bit) or po[bit], po.get(bit) or pi[bit]
        a, b = D.input_site(ap), (bp[0], bp[1])
        st = []
        for j in range(k):
            if sn in full:
                st.append(centre(full[sn][j, bit]))
            elif only_regs and cin and cout and ((normal and j >= 1) or (not normal and j + 1 < k)):
                jj = j if normal else j + 1                    # landed: station i takes plan stage i+1
                t = jj / k
                x, y = regs[jj][0], regs[jj][1]
                st.append((x + (1 - t) * (ap[0] - cin[0]) + t * (bp[0] - cout[0]), y + (1 - t) * (ap[1] - cin[1]) + t * (bp[1] - cout[1])))
            elif only_regs and not normal and j + 1 == k:
                st.append(b)                                   # landed: the last station is the out-face register
            else:
                st.append(D.station_site(slot, j, bit, ap, bp, normal=normal))
        out[bit] = [(a[0], a[1])] + st + [b]
    return out


def type_census(P, tn, limit=LIMIT_UM):
    """{slot: dict(k, bits, ss_max, ss_over, full_max, full_over, first_max, worst_bit)}; ss = station->station, full = incl. pin legs"""
    import die_hop_scan as D
    from ft_full_stage import load
    t = P.types[tn]
    pins = D.pin_table(P, tn)
    full = load(P, tn)
    res = {}
    for slot in t.get("ft_slots") or []:
        sn, k = slot["name"], int(slot.get("stations", 1))
        normal = D.normal_slot(P, tn, sn, full=full)
        ch = slot_chains(P, tn, slot, pins, normal, full)
        ss_max = full_max = first_max = 0.0
        ss_over = full_over = 0
        worst = None
        for bit, pts in ch.items():
            hops = [md(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
            inner = hops[1:-1] if len(hops) > 2 else []
            if inner and max(inner) > ss_max:
                ss_max = max(inner)
            ss_over += sum(1 for h in inner if h > limit)
            if hops and max(hops) > full_max:
                full_max, worst = max(hops), bit
            full_over += sum(1 for h in hops if h > limit)
            first_max = max(first_max, hops[0] if hops else 0.0)
        res[sn] = dict(k=k, bits=len(ch), normal=normal, ss_max=round(ss_max, 1), ss_over=ss_over, full_max=round(full_max, 1),
                       full_over=full_over, first_max=round(first_max, 1), worst_bit=worst)
    return res


def internal_census(t, src=None, limit=LIMIT_UM):
    """internal_stations chains (from_um -> regs_um -> to_um) of one type: {conn: dict(max_um, first_um, n_over, start, end, moved)}.  src =
    src_centroid.overrides(geom, t): an out bus starts at its real source register centroid, an in bus ends at its consumer centroid; the plan's
    leaf_um / from_um / to_um is the fallback (SRC-NOT-AT-LEAF: sle_su_c x_su_l0_o plan first hop 171 um, placed 565.8 um).  The override replaces only the
    pin-side hop by the worst real register edge; the centroid is reported, never used as a chain point."""
    res = {}
    for e in t.get("internal_stations") or []:
        if "from_um" not in e or "to_um" not in e:
            continue
        pts = [tuple(e["from_um"])] + [tuple(r[:2]) for r in e.get("regs_um") or []] + [tuple(e["to_um"])]
        conn = str(e.get("conn", ""))
        ov = (src or {}).get(conn)
        hops = [md(a, b) for a, b in zip(pts, pts[1:])]
        ch = (ov or {}).get("chain")
        if ch:   # SRC-NOT-AT-LEAF: the placed chain replaces the plan's: pin-side hop = worst REAL register edge (placed source reg -> first station, or last station ->
            # consumer reg), the stations between = the worst placed station -> station edge (plan regs_um are stale: sle_su_c x_su_l0_p1_o plan 474 um, placed <= 304 um);
            # only the far end (last station -> to_um / from_um -> first station) stays the plan's.  The centroid is NOT a chain point: sources of one bus sit in
            # several banks (x_su_l1_p1_o: 4 groups of 128 flops), their mean is no register.
            far = hops[-1] if ov["end"] == "src" else hops[0]
            mid = ch.get("inter_max_um") or 0.0
            hops = [ch["max_um"], mid, far] if ov["end"] == "src" else [far, mid, ch["max_um"]]
        mx, first, nov = max(hops), hops[0], sum(1 for h in hops if h > limit)
        res[conn] = dict(max_um=round(mx, 1), first_um=round(first, 1), n_over=nov, start=pts[0], end=pts[-1], moved=bool(ov), centroid=(ov or {}).get("xy"))
    return res


def type_flag(cen, drift=DRIFT_UM, limit=LIMIT_UM):
    """(n_slots flagged, worst planned hop um, slot list) for one type: a slot is flagged when its worst full-chain hop + drift > limit"""
    bad = [(sn, v["full_max"]) for sn, v in cen.items() if v["full_max"] + drift > limit]
    return len(bad), max((h for _s, h in bad), default=0.0), sorted(bad, key=lambda x: -x[1])


def placed_hops(ft_face_flops_txt, limit=LIMIT_UM):
    """(c) placed geometry: the kit's ot_face_flops.txt (run/results/*/*/base/) lists every ft station it seated as
    '<inst>\tst<j>|lst<j>|st0_explicit\t<x>\t<y>\t<input port of the bit>'.  Per bit (the port) the stations in j order give the real
    station -> station hops, exactly what OT_FT_LANE reports.  -> dict(bits, max_um, n_over, worst=[(port, um)])"""
    import re
    by = {}
    with open(ft_face_flops_txt, errors="replace") as f:
        for ln in f:
            p = ln.rstrip("\n").split("\t")
            if len(p) < 5:
                continue
            m = re.fullmatch(r"l?st(\d+)(?:_explicit)?", p[1])
            if not m:
                continue
            try:
                by.setdefault(p[4], {})[int(m.group(1))] = (float(p[2]), float(p[3]))
            except ValueError:
                continue
    mx, n, worst = 0.0, 0, []
    for port, st in by.items():
        js = sorted(st)
        hops = [md(st[a], st[b]) for a, b in zip(js, js[1:]) if b == a + 1]
        if hops:
            h = max(hops)
            mx = max(mx, h)
            n += sum(1 for x in hops if x > limit)
            if h > limit:
                worst.append((port, round(h, 1)))
    return dict(bits=len(by), max_um=round(mx, 1), n_over=n, worst=sorted(worst, key=lambda x: -x[1])[:5])

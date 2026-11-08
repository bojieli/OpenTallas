#!/usr/bin/env python3
"""S81 plan event COL-WALLGAP-1108 (S81-TYPES-7-COLH, class C col_h CHANNEL): widen the central gap of every
ROM-element wall row in the col_h9 / col_h10 types.

Why (measured 11-08 on the e9eda32d41c GRT fails): every col_h type has two rows of two ot_v41_rom_elem_q_qxpq_w10_gb
views (536.76 x 221.4 um, OBS M1-M7 = nothing crosses them) with ONE 24.84-um gap between the pair.  At 3_place,
1161 (col_h9_r0_p2), 1065 (col_h9_r0_p6) and 882 (col_h9_r1) nets cross the upper wall; the gap holds ~1595 raw
vertical tracks (M3+M5+M7) and is also filled with standard cells (895 local nets with GRT guides there on r0_p2),
so GRT routes over the walls: 3D overflow 97k-138k, 90 % of the 2D overflow on capacity-0 gcells over the walls.

What: per type and wall row, move the WEST element west (not below x 17.28, the W face-flop strip) and the EAST
element east (keeping >= 8.64 um to the next hard core whose y-span overlaps the row, and inside the outline) to open
the gap as far as both sides allow, capped at 60.48 um.  Only hard_cores[*].origin_um of the elements change; clock
taps, stations, ft slots, buses, windows, RTL and bind are unchanged (taps stay at their planned xy).  A moved element
must not newly cover any planned point (clock tap, station reg, ft bit site) or overlap another hard core.
11-08 b: every widening is also checked with the generator's own tap rule (taps.explicit_tap_sites /
grid_explicit_sites: outline, TAP_CLEAR_UM halo, spacing) and must leave the computed grid taps unchanged; a row whose
full widening fails shrinks in 2.16-um steps until it passes (gen phys rejected the first cut: added taps in the halo).
An added light tap (clock.added_taps) that sits in the strip just east of the east element (within TAP_CLEAR + the
move, inside the element's y band +- TAP_CLEAR) moves east with it by the same amount; the budget check
(taps.grid_explicit_taps: every planned sink within tap radius and cap) must still pass.
    python3 -I delta_col_wallgap_1108.py PLAN --src SRC_CHECKOUT [--dry] [--families col_h9,col_h10]
"""
import json
import os
import sys

ELEM = "ot_v41_rom_elem_q_qxpq_w10_gb"
W_MIN_X = 17.28
CLEAR = 8.64
GAP_CAP = 60.48
RAW = None
GRID = 0.108  # placement grid of the element origins in this plan (all origins are multiples of 0.108... checked below)


def rect(h):
    (x, y), (w, hh) = h["origin_um"], h["outline_um"]
    return x, y, x + w, y + hh


def overlap(a, b, eps=1e-6):
    return a[0] < b[2] - eps and b[0] < a[2] - eps and a[1] < b[3] - eps and b[1] < a[3] - eps


def inside(pt, r, eps=1e-6):
    return r[0] + eps < pt[0] < r[2] - eps and r[1] + eps < pt[1] < r[3] - eps


def points(t):
    pts = []
    for tp in (t.get("clock") or {}).get("taps") or []:
        if tp.get("xy"):
            pts.append(("tap " + tp.get("name", ""), tuple(tp["xy"])))
    for st in t.get("internal_stations") or []:
        for r in st.get("regs_um") or []:
            pts.append(("istn " + str(st.get("conn")), tuple(r)))
    for fs in t.get("ft_slots") or []:
        for group in fs.get("bit_sites_um") or []:
            for p in group:
                if isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p):
                    pts.append(("ft " + fs.get("name", ""), tuple(p)))
    return pts


def tap_state(tn):
    """(ok, grid, error): the generator's own tap geometry check for type tn on the live plan dict."""
    import schema
    import taps
    P = schema.Plan(RAW)
    t = P.types[tn]
    mode = (t.get("clock") or {}).get("tap_mode")
    try:
        grid = [tuple(g) for g in schema._grid_taps(P, tn)] if mode != "explicit" else []
        if mode == "grid+explicit":
            taps.grid_explicit_sites(P, tn)
            taps.grid_explicit_taps(P, tn)
        elif mode == "explicit":
            taps.explicit_tap_sites(P, tn)
        return True, grid, ""
    except Exception as e:  # noqa: BLE001 - any rejection of the generator counts as illegal
        return False, None, str(e)


def plan_type(tn, t):
    W, H = t["outline_um"]
    hc = t.get("hard_cores") or []
    elems = [h for h in hc if h.get("module") == ELEM]
    rows = {}
    for h in elems:
        rows.setdefault(round(h["origin_um"][1], 3), []).append(h)
    pts = points(t)
    moves = []
    for y, pair in sorted(rows.items()):
        if len(pair) != 2:
            continue
        pair.sort(key=lambda h: h["origin_um"][0])
        west, east = pair
        rw, re_ = rect(west), rect(east)
        gap = re_[0] - rw[2]
        others = [rect(h) for h in hc if h is not west and h is not east]
        band = [o for o in others if o[1] < re_[3] and o[3] > re_[1]]
        # east limit: nearest hard core east of the east element in the row band
        east_lim = min([o[0] - CLEAR for o in band if o[0] >= re_[2] - 1e-6] + [W - W_MIN_X])
        west_lim = max([o[2] + CLEAR for o in band if o[2] <= rw[0] + 1e-6] + [W_MIN_X])
        de = max(0.0, east_lim - re_[2])
        dw = max(0.0, rw[0] - west_lim)
        want = GAP_CAP - gap
        if want <= 0:
            continue
        # split the widening: east first (keeps the W face strip), then west
        de = min(de, want)
        dw = min(dw, want - de)
        de = round(int(de / GRID + 1e-9) * GRID, 3)
        dw = round(int(dw / GRID + 1e-9) * GRID, 3)
        ok0, grid0, err0 = tap_state(tn)
        assert ok0, (tn, "tap rule fails before the delta", err0)
        w0, e0 = list(west["origin_um"]), list(east["origin_um"])
        added = (t.get("clock") or {}).get("added_taps") or []
        a0 = [list(a["xy"]) for a in added]
        step = 20 * GRID
        while de + dw >= 0.5:
            nw = (rw[0] - dw, rw[1], rw[2] - dw, rw[3])
            ne = (re_[0] + de, re_[1], re_[2] + de, re_[3])
            for o in others:
                assert not overlap(nw, o) and not overlap(ne, o), (tn, y, o)
            legal = not any(inside(p, new) and not inside(p, old)
                            for name, p in pts for old, new in ((rw, nw), (re_, ne)))
            west["origin_um"] = [round(w0[0] - dw, 3), w0[1]]
            east["origin_um"] = [round(e0[0] + de, 3), e0[1]]
            rider = []
            for a, xy in zip(added, a0):
                if (re_[2] - 1e-6 <= xy[0] < re_[2] + CLEAR + de + 1e-6
                        and re_[1] - CLEAR <= xy[1] <= re_[3] + CLEAR):
                    a["xy"] = [round(xy[0] + de, 4), xy[1]]
                    rider.append(a["name"])
            if legal:
                ok, grid, _ = tap_state(tn)
                legal = ok and grid == grid0
            if legal:
                break
            west["origin_um"], east["origin_um"] = list(w0), list(e0)
            for a, xy in zip(added, a0):
                a["xy"] = list(xy)
            # shrink: take the step off the larger side first
            if de >= dw:
                de = round(max(0.0, de - step), 3)
            else:
                dw = round(max(0.0, dw - step), 3)
        if de + dw < 0.5:
            continue
        moves.append(dict(row_y=y, west=west["inst"], east=east["inst"], dw=dw, de=de, taps=rider,
                          gap_old=round(gap, 3), gap_new=round(gap + dw + de, 3)))
    return moves


def main():
    plan = sys.argv[1]
    dry = "--dry" in sys.argv
    fams = ("col_h9", "col_h10")
    if "--families" in sys.argv:
        fams = tuple(sys.argv[sys.argv.index("--families") + 1].split(","))
    src = sys.argv[sys.argv.index("--src") + 1]
    sys.path.insert(0, os.path.join(src, "tools", "die_plan"))
    p = json.load(open(plan))
    global RAW
    RAW = p
    before = json.dumps(p, sort_keys=True)
    report = {}
    for tn, t in p["partition_types"].items():
        if tn.split("_r")[0] in fams or any(tn.startswith(f + "_") for f in fams):
            mv = plan_type(tn, t)
            if mv:
                report[tn] = mv
    # only hard_cores origins changed
    q0, q1 = json.loads(before), p
    for tn in q0["partition_types"]:
        a, b = q0["partition_types"][tn], q1["partition_types"][tn]
        if a == b:
            continue
        d = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
        assert d <= {"hard_cores", "clock"}, (tn, d)
        ca, cb = a.get("clock") or {}, b.get("clock") or {}
        assert {k for k in set(ca) | set(cb) if ca.get(k) != cb.get(k)} <= {"added_taps"}, tn
        for ta, tb in zip(ca.get("added_taps") or [], cb.get("added_taps") or []):
            assert {k for k in set(ta) | set(tb) if ta.get(k) != tb.get(k)} <= {"xy"}, (tn, ta.get("name"))
        for ha, hb in zip(a["hard_cores"], b["hard_cores"]):
            dd = {k for k in set(ha) | set(hb) if ha.get(k) != hb.get(k)}
            assert dd <= {"origin_um"}, (tn, ha.get("inst"), dd)
    assert {k: v for k, v in q0.items() if k != "partition_types"} == {k: v for k, v in q1.items() if k != "partition_types"}
    for tn, mv in sorted(report.items()):
        print("COL_WALLGAP", tn, " ".join(f"y{m['row_y']}:{m['gap_old']}->{m['gap_new']}(dw{m['dw']},de{m['de']},taps{'+'.join(m['taps']) or '-'})" for m in mv))
    print("COL_WALLGAP types", len(report))
    if not dry:
        with open(plan, "w") as f:
            json.dump(p, f, indent=1)
            f.write("\n")
    return report


if __name__ == "__main__":
    main()

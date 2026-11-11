#!/usr/bin/env python3
"""DIE-S81-85 S4N-FTLANE-1111 (FEAS-AUDIT-1 S81-D1): take the dn_s_4N_L0 lane off the s_4N_L1 ft band (plan-only,
zero pin cycles, DO_NOT_COUNT until the 12:00 event takes it).

Finding (FEAS-AUDIT-1, re-measured on BASE_1200 b5faa1bacc5f with the same G0 cut model, check.py cuts / feas_die):
the s_4N_L1 (ot_s81sl_leaf__t43) partition segment at horizontal@19500 carries 4347 bits on 5257 tracks = 0.827.  The
hard cores of t43 leave few M5/M7 tracks free at that height, and the s_4N column sends six ft lanes through it: up_s
/ dn_s of L0, L3 and L4 (668 / 597 b).  dn_s_4N_L0 already leaves the column for the s_5N column (L1 -> s_4N_L3 ->
s_5N_L3 -> s_5N_L4 -> s_4N_L0).

Fix: the lane turns east one row earlier.  It leaves s_4N_L1 on its E face BELOW the 19500 cut (window centre between
the 19250 and 19500 cut lines), runs up the s_5N_L1 ft band and enters s_5N_L3 from the S:
    old  s_4N_C -> s_4N_L1[x1 S>N] -> s_4N_L3[x2 S>E] -> s_5N_L3[x3 W>N] -> s_5N_L4[x4] -> s_4N_L0
    new  s_4N_C -> s_4N_L1[x1 S>E] -> s_5N_L1[x2 W>N] -> s_5N_L3[x3 S>N] -> s_5N_L4[x4] -> s_4N_L0
Same port ids, same bus names, same number of crossed partitions, the SAME station total over x1..x3 (13) and the
same two clock-landing crossings (ports _1 and _2: x2_i and x3_i ring receivers) -> lane_natural (cycles 31,
stations 17, clock_landing 6) is unchanged, asserted.  No pin cycle, RTL, outline, core position, or other lane moves.

Keys written (everything else byte-identical to BASE, asserted):
  ports dn_s_4N_L0_1.dst.part / dn_s_4N_L0_2.src.part            s_4N_L3 -> s_5N_L1
  clock.landing_network.edges cland_clk__dn_s_4N_L0_1 / _2      the same endpoint parts
  partition_types (ft_slots, clock.landing_contract pins/bands/collector_local_sources, clock.edge_clocks) of:
    ot_s81sl_leaf__t43              x1: out face -> die E, new out window, stations re-sited; fclk_out pin moved
    ot_s81sl_leaf__t44__clf6cf8492  x2 slot, its ring band / local source / fclk pins / edge clock removed
    ot_s81sl_leaf__t52              x2 slot added (W>N), ring band + local source + fclk pins + edge clock added
    ot_s81sl_leaf__t53__cl958451dd  x3: in face -> die S, new in window, stations re-sited; ring band + pin re-sited
Windows: free intervals of both partitions on the shared edge (off every bus / slot window / landing pin, +2 um
guard), sized by schema.window_for at the plan face budget (lane_add rules).  Stations: station_resite.route (exact
count, macro + halo free lattice, every FF hop <= reach) over the three crossed partitions, re-solved at a shorter
reach until check.lane_pin_hops (mandatory seam pins) passes.  Ring bands: clock_landing_plan._storage_band with the
plan's padded reserve and ring_place ff, every other band / reset site / station an obstacle.

Result on BASE_1200 (epyc4 /srv/opentallas-scratch2/claude/die-s81-85/s4n/out/r1, DO_NOT_COUNT): s_4N_L1 h@19500
0.827 -> 0.713; s_5N_L1 worst stays 0.586 (h@19250, not crossed: the E1 window centre is 19375); no other segment
moves above its base value except s_5N_L1/s_5N_L3 bands that stay <= 0.50.  check.py G0: 0 new errors, and the base
ERROR "t53 slot dn_s_4N_L0x3: 598 station cells intersect macros (u_lf.u_vsw)" is gone.  The G0 cut ERROR on
s_4N_L1 stays (0.71 > cut_ratio_max 0.6); moving up_s_4N_L0 the same way (same four types) would take it to 0.59.
The t52 x2_i ring band sits 309 um from its pin (compose rule <= 405; the t44 band was 97 um).

usage: delta_s4n_ftlane_1111.py PLAN_IN PLAN_OUT [REPORT.json] [--base-sha SHA]
       delta_s4n_ftlane_1111.py --check PLAN_IN PLAN_OUT [--base-sha SHA]"""
import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[2] / "tools" / "die_plan")]
import numpy as np  # noqa: E402
import schema as S  # noqa: E402
import check as C  # noqa: E402
import lane_add as LA  # noqa: E402
import station_resite as SR  # noqa: E402
import clock_landing_plan as CLP  # noqa: E402
import reset_tree as RT  # noqa: E402
import gen_phys as GP  # noqa: E402
import landing_contract as LC  # noqa: E402

EVENT = "S4N-FTLANE-1111"
BASE_SHA = "b5faa1bacc5f6e80c6167856ee1597a7a775ea81dad9305424a3c47de0786d7b"   # BASE_1200 (64eb2c89 + FEED-BAL-2 + DS85-VIEWS)
LANE = "dn_s_4N_L0"
OLD, NEW = "s_4N_L3", "s_5N_L1"
CHAIN = ["s_4N_L1", "s_5N_L1", "s_5N_L3"]                  # the crossed partitions that change (x1, x2, x3)
SLOTS = ["dn_s_4N_L0x1", "dn_s_4N_L0x2", "dn_s_4N_L0x3"]
E1 = ("s_4N_L1", "s_5N_L1")        # x1 -> x2 edge (die x 17418.24)
E2 = ("s_5N_L1", "s_5N_L3")        # x2 -> x3 edge (die y 20424.96)
CUT_LO, CUT_HI = 19250.0, 19500.0  # E1 window centre strictly between these G0 cut lines (cut_step 250)
CUT_MARGIN = 8.0
GUARD = 2.0
TYPES = ("ot_s81sl_leaf__t43", "ot_s81sl_leaf__t44__clf6cf8492", "ot_s81sl_leaf__t52", "ot_s81sl_leaf__t53__cl958451dd")
EC_NOTE = "source-forwarded ring write clock; actual source-export/window STA required"


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def occupied(P, part, df):
    """die-frame intervals along die face df of `part` held by its type's buses, ft slot windows and landing pins."""
    t = P.ptype(part)
    tf = P.type_face(part, df)
    out = []

    def add(win):
        a, b = (P.to_die(part, (win[0], 0.0)), P.to_die(part, (win[1], 0.0))) if tf in "NS" else \
               (P.to_die(part, (0.0, win[0])), P.to_die(part, (0.0, win[1])))
        k = 0 if tf in "NS" else 1
        out.append(tuple(sorted((a[k], b[k]))))
    for b in t.get("buses", []):
        if b.get("face") == tf and b.get("window_um"):
            add(b["window_um"])
    for s in t.get("ft_slots", []):
        if s.get("in_face") == tf and s.get("in_window_um"):
            add(s["in_window_um"])
        if s.get("out_face") == tf and s.get("out_window_um"):
            add(s["out_window_um"])
    w, h = t["outline_um"]
    for p in (t.get("clock", {}).get("landing_contract", {}) or {}).get("pins", []):
        x, y = p["xy_um"]
        face = min(((x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")))[1]
        if face == tf:
            c = x if tf in "NS" else y
            add([c - 1.0, c + 1.0])
    return out


def alloc(P, a, b, width, prefer, lo_clip=None, hi_clip=None):
    """lane_add.Builder.alloc on the a|b edge with type-derived occupancy: (die face of a, die window, layers)."""
    df, lo, hi = LA.shared_edge(P, a, b)
    layers = LA.face_layers(P, a, df)
    assert LA.face_layers(P, b, LA.OPP[df]) == layers, (a, b, "face layers differ")
    per = float(P.budgets.get("face_pins_per_um", 6.0)) * len(layers) / float(P.budgets.get("face_pin_layers", 2))
    tmax = float(P.budgets.get("pin_track_max", 0.6))
    pins = width + 1
    occ = occupied(P, a, df) + occupied(P, b, LA.OPP[df])
    glo, ghi = lo + 1.0, hi - 1.0
    best = None
    for g0, g1 in LA.free_gaps(glo, ghi, occ, GUARD):
        L = S.window_for(0.0, pins, layers, P.layers, per_um=per, track_max=tmax)
        if g1 - g0 < L + 0.1:
            continue
        x = min(max(prefer - L / 2, g0), g1 - L)
        x = max(round(math.floor(x / 0.016) * 0.016, 4), g0)
        hw = S.window_for(x, pins, layers, P.layers, per_um=per, track_max=tmax)
        if hw > g1:
            x = max(g0, round(g1 - (hw - x) - 0.016, 4))
            hw = S.window_for(x, pins, layers, P.layers, per_um=per, track_max=tmax)
            if hw > g1:
                continue
        c = (x + hw) / 2
        if lo_clip is not None and not (lo_clip < c < hi_clip):
            continue
        cost = abs(c - prefer)
        if best is None or cost < best[0]:
            best = (cost, [x, hw])
    assert best is not None, (a, b, "no free window")
    return df, best[1], layers


def face_pt(P, part, df, win):
    x0, y0, x1, y1 = P.rect(part)
    c = (win[0] + win[1]) / 2
    return {"E": (x1, c), "W": (x0, c), "N": (c, y1), "S": (c, y0)}[df]


def part_free(P, part, ylo=None, yhi=None):
    """macro + halo free station lattice of one partition (die frame, station_resite.G pitch from the part's corner)."""
    G, H = SR.G, SR.HALO
    x0, y0, x1, y1 = P.rect(part)
    xs = x0 + np.arange(int((x1 - x0) / G) + 1) * G
    ys = y0 + np.arange(int((y1 - y0) / G) + 1) * G
    m = (xs[:, None] > x0 + H) & (xs[:, None] < x1 - H) & (ys[None, :] > y0 + H) & (ys[None, :] < y1 - H)
    if ylo is not None:
        m &= ys[None, :] > ylo
    if yhi is not None:
        m &= ys[None, :] < yhi
    for bx0, by0, bx1, by1 in S.placed_macro_boxes(P.ptype(part), halo=H).values():
        c0, c1 = P.to_die(part, (bx0, by0)), P.to_die(part, (bx1, by1))
        ux0, ux1 = sorted((c0[0], c1[0])); uy0, uy1 = sorted((c0[1], c1[1]))
        m &= ~((xs[:, None] > ux0 - 1e-6) & (xs[:, None] < ux1 + 1e-6) & (ys[None, :] > uy0 - 1e-6) & (ys[None, :] < uy1 + 1e-6))
    return xs, ys, m


def seg_route(F, a, b, n, ra, rb, reach):
    """n FF homes in one partition: dist(a, r1) <= ra, every inner hop <= reach, dist(rn, b) <= rb (Manhattan), on
    the free lattice F; station_resite.route's layered reachability + back-trace to the straight a->b line."""
    xs, ys, free = F
    G = SR.G
    xx, yy = xs[:, None], ys[None, :]
    da = abs(xx - a[0]) + abs(yy - a[1]); db = abs(xx - b[0]) + abs(yy - b[1])
    rs = int(reach // G)
    layers = [free & (da <= ra + 1e-6)]
    for _ in range(1, n):
        layers.append(free & SR._dilate(layers[-1], rs))
    cand = layers[-1] & (db <= rb + 1e-6)
    if not cand.any():
        return None
    tx = a[0] + (b[0] - a[0]) * n / (n + 1); ty = a[1] + (b[1] - a[1]) * n / (n + 1)
    cur = np.unravel_index(np.where(cand, abs(xx - tx) + abs(yy - ty), 1e20).argmin(), free.shape)
    rev = [cur]
    for k in range(n - 2, -1, -1):
        cx, cy = xs[cur[0]], ys[cur[1]]
        good = layers[k] & (abs(xx - cx) + abs(yy - cy) <= reach + 1e-6)
        for q in rev:
            good[q] = False
        if not good.any():
            return None
        tx = a[0] + (b[0] - a[0]) * (k + 1) / (n + 1); ty = a[1] + (b[1] - a[1]) * (k + 1) / (n + 1)
        cur = np.unravel_index(np.where(good, abs(xx - tx) + abs(yy - ty), 1e20).argmin(), free.shape)
        rev.append(cur)
    regs = [(round(float(xs[i]), 4), round(float(ys[j]), 4)) for i, j in rev[::-1]]
    pts = [a] + regs + [b]
    hops = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])]
    assert hops[0] <= ra + 1e-5 and hops[-1] <= rb + 1e-5 and max(hops[1:-1] or [0]) <= reach + 1e-5
    return regs


def solve_chain(P, frees, pins, ends, K, reach, split):
    """per-partition FF homes for CHAIN: pins = [in pin, seam 1, seam 2, out pin] (die); ends = (first-hop budget,
    last-hop budget); seam hop budget split (out side share = split).  Fewest FFs per partition first, the rest of K
    to the partition with the longest route per FF."""
    ra = [ends[0], reach * (1 - split), reach * (1 - split)]
    rb = [reach * split, reach * split, ends[1]]
    kmin = []
    for i in range(3):
        k = 1
        while k <= K and seg_route(frees[i], pins[i], pins[i + 1], k, ra[i], rb[i], reach) is None:
            k += 1
        if k > K:
            return None
        kmin.append(k)
    if sum(kmin) > K:
        return None
    ks = list(kmin)
    L = [abs(pins[i][0] - pins[i + 1][0]) + abs(pins[i][1] - pins[i + 1][1]) for i in range(3)]
    while sum(ks) < K:
        i = max(range(3), key=lambda j: (L[j] / ks[j], -j))
        ks[i] += 1
    out = [seg_route(frees[i], pins[i], pins[i + 1], ks[i], ra[i], rb[i], reach) for i in range(3)]
    return out if all(out) else None


def scalar_point(P, t, bus):
    """clock_landing_plan._scalar + _finish: the landing scalar pin site of a bus (window centre on its face)."""
    b = CLP._scalar(t, "x", "in", CLP._bus_xy(t, bus), "clock")
    at = sum(b["window_um"]) / 2
    f = b["face"]
    w, h = t["outline_um"]
    point = [2.16 if f == "W" else w - 2.16, at] if f in "EW" else [at, 2.16 if f == "S" else h - 2.16]
    return list(GP._snap_tap(P, *point))


def derive(pin_path, base_sha):
    text = open(pin_path).read()
    assert sha(text) == base_sha, f"base sha {sha(text)[:12]} != {base_sha[:12]}"
    assert json.dumps(json.loads(text)) + "\n" == text, "base is not in the compact json.dumps form"
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    ppath = HERE / "die_plan.json"            # sidecars resolve in physical/die_plan/s81 (as check.py G0 runs)
    P = S.Plan(json.loads(text), ppath)
    parts = {p["name"]: p for p in raw["partitions"]}
    T = raw["partition_types"]
    tn = {p: parts[p]["type"] for p in CHAIN + [OLD]}
    assert tuple(sorted(set(tn.values()))) == tuple(sorted(TYPES)), tn
    for t_ in TYPES:
        assert sum(1 for p in raw["partitions"] if p["type"] == t_) == 1, (t_, "type is shared: a slot move would leak")
    ports = {p["id"]: p for p in raw["ports"]}
    lane = next(l for l in raw["lanes"] if l["id"] == LANE)
    pid = lane["ports"]
    assert [ports[q]["src"]["part"] for q in pid] == ["s_4N_C", "s_4N_L1", OLD, "s_5N_L3", "s_5N_L4"], "lane path moved"
    nat0 = P.lane_natural(LANE)
    slot0 = {s: P.slot(p, s) for p, s in zip(["s_4N_L1", OLD, "s_5N_L3"], SLOTS)}
    K = sum(int(s["stations"]) for s in slot0.values())
    width = int(ports[pid[0]]["width"])
    rep = dict(event=EVENT, base_plan_sha256=base_sha, lane=LANE, width=width,
               old_chain=["s_4N_L1", OLD, "s_5N_L3"], new_chain=CHAIN, stations_total_x1_x3=K,
               old_slots={s: dict(in_face=v["in_face"], out_face=v["out_face"], stations=v["stations"],
                                  in_window_um=v["in_window_um"], out_window_um=v["out_window_um"]) for s, v in slot0.items()},
               lane_natural_before=nat0)

    # ---- windows on the two new edges
    p_in = P.port_point(pid[0])                      # C -> L1 (S face of s_4N_L1): unchanged
    p_out = P.port_point(pid[3])                     # s_5N_L3 -> s_5N_L4 (N face of s_5N_L3): unchanged
    df1, w1, lay1 = alloc(P, *E1, width, prefer=(CUT_LO + CUT_HI) / 2,
                          lo_clip=CUT_LO + CUT_MARGIN, hi_clip=CUT_HI - CUT_MARGIN)
    df2, w2, lay2 = alloc(P, *E2, width, prefer=p_out[0])
    assert (df1, df2) == ("E", "N"), (df1, df2)
    rep["windows_die"] = {f"{E1[0]}|{E1[1]}": dict(face=df1, window_um=w1, layers=lay1),
                          f"{E2[0]}|{E2[1]}": dict(face=df2, window_um=w2, layers=lay2)}

    # ---- ft slots (type frame, orient aware) + ports
    t1, t2, t3, t_old = (T[tn[p]] for p in CHAIN + [OLD])
    s1 = next(s for s in t1["ft_slots"] if s["name"] == SLOTS[0])
    s3 = next(s for s in t3["ft_slots"] if s["name"] == SLOTS[2])
    tf, tw, fl = LA.to_type_window(P, E1[0], df1, w1)
    s1.update(out_face=tf, out_window_um=tw, out_layers=list(lay1), out_order="lsb_high" if fl else "lsb_low")
    tfi, twi, fli = LA.to_type_window(P, E1[1], LA.OPP[df1], w1)
    tfo, two, flo = LA.to_type_window(P, E2[0], df2, w2)
    s2 = dict(name=SLOTS[1], in_face=tfi, out_face=tfo, width=width, stations=1, in_window_um=twi, in_layers=list(lay1),
              in_order="lsb_high" if fli else "lsb_low", out_window_um=two, out_layers=list(lay2),
              out_order="lsb_high" if flo else "lsb_low", regs_um=[])
    t2["ft_slots"].append(s2)
    tf3, tw3, fl3 = LA.to_type_window(P, E2[1], LA.OPP[df2], w2)
    s3.update(in_face=tf3, in_window_um=tw3, in_layers=list(lay2), in_order="lsb_high" if fl3 else "lsb_low")
    t_old["ft_slots"] = [s for s in t_old["ft_slots"] if s["name"] != SLOTS[1]]
    # in-face key order of an in-face change keeps the slot's own key order (dict.update keeps positions)
    ports[pid[1]]["dst"]["part"] = NEW
    ports[pid[2]]["src"]["part"] = NEW
    edges = {e["id"]: e for e in raw["clock"]["landing_network"]["edges"]}
    edges["cland_clk__" + pid[1]]["dst"]["part"] = NEW
    edges["cland_clk__" + pid[2]]["src"]["part"] = NEW

    # ---- stations: K over x1..x3, exact count solve, re-solved shorter until the mandatory-pin hops pass
    P1 = S.Plan(copy.deepcopy(raw), ppath)
    reach = min(float(P1.lanes[LANE].get("reach_um", P1.reach)), P1.reach)
    smax = C.station_max(P1)
    pins = [P1.port_point(pid[0]), P1.port_point(pid[1]), P1.port_point(pid[2]), P1.port_point(pid[3])]
    x4 = P1.slot("s_5N_L4", "dn_s_4N_L0x4")
    x4r0 = P1.to_die("s_5N_L4", tuple(x4["regs_um"][0]))
    end_budget = reach - (abs(x4r0[0] - pins[3][0]) + abs(x4r0[1] - pins[3][1]))
    frees = [part_free(P1, CHAIN[0], yhi=CUT_HI - CUT_MARGIN), part_free(P1, CHAIN[1], ylo=CUT_LO + CUT_MARGIN),
             part_free(P1, CHAIN[2])]
    got = None
    tried = []
    for split in (0.5, 0.4, 0.6, 0.3, 0.7):
        sol = solve_chain(P1, frees, pins, (reach, end_budget - 1e-3), K, reach, split)
        if sol is None:
            tried.append((split, "no solve"))
            continue
        for (p, sn, sl), regs in zip([(CHAIN[0], SLOTS[0], s1), (CHAIN[1], SLOTS[1], s2), (CHAIN[2], SLOTS[2], s3)], sol):
            sl["stations"] = len(regs)
            sl["regs_um"] = [[round(v, 4) for v in P1.to_type(p, r)] for r in regs]
        Pt = S.Plan(copy.deepcopy(raw), ppath)
        pts, regs, xs = C.lane_geometry(Pt, LANE)
        hops = C.lane_pin_hops(Pt, LANE, regs)
        r3 = max(x["len_um"] / x["stations"] for x in xs)
        tried.append((split, [len(s) for s in sol], round(max(hops), 1), round(r3, 1)))
        if max(hops) <= reach + 1e-6 and r3 <= smax + 1e-6:
            got = (sol, hops, xs)
            break
    assert got is not None, ("no station chain", tried)
    sol, hops, xs = got
    rep["stations"] = dict(reach_um=reach, ft_station_max_um=smax, tries=tried,
                           per_slot={sn: len(r) for sn, r in zip(SLOTS, sol)},
                           max_pin_hop_um=round(max(hops), 2), crossings=xs)

    # ---- clock landing infrastructure (receivers x2_i in t52 [moved from t44] and x3_i in t53 [face moved])
    P2 = S.Plan(copy.deepcopy(raw), ppath)
    bus2i, bus2o, bus3i, bus1o = SLOTS[1] + "_i", SLOTS[1] + "_o", SLOTS[2] + "_i", SLOTS[0] + "_o"
    lco = t_old["clock"]["landing_contract"]
    old_band = lco["bands"][bus2i]
    drop = {"fclk_in_" + bus2i, "fclk_out_" + bus2o}
    assert {p["name"] for p in lco["pins"]} >= drop
    lco["pins"] = [p for p in lco["pins"] if p["name"] not in drop]
    del lco["bands"][bus2i]
    lco["collector_local_sources"] = [s for s in lco["collector_local_sources"] if s["name"] != bus2i]
    t_old["clock"]["edge_clocks"] = [e for e in t_old["clock"]["edge_clocks"] if e["port"] != "fclk_in_" + bus2i]

    saved = (CLP.BAND_RESERVE, CLP.BAND_SPREAD, CLP.BAND_RING)
    bands_rep = {}
    try:
        for part, t, bus, new in ((CHAIN[1], t2, bus2i, True), (CHAIN[2], t3, bus3i, False)):
            ttn = tn[part]
            lc = t["clock"]["landing_contract"]
            rings = {bb.get("ring_place", "all") for k, bb in lc["bands"].items() if bb.get("rect_um") and not k.startswith("monitor_")}
            assert len(rings) == 1, (ttn, rings)
            assert old_band.get("ring_place", "all") in rings
            CLP.BAND_RESERVE, CLP.BAND_SPREAD, CLP.BAND_RING = "padded", 1.0, rings.pop()
            tt = copy.deepcopy(P2.types[ttn])        # loaded type (ft_slots with the new regs as obstacles)
            used = [list(r) for k, o in lc["bands"].items() if k != bus and o.get("rect_um")
                    for r in (o.get("rects_um") or [o["rect_um"]])]
            phy = CLP.phy_supply_rects(P2, ttn)
            resets = CLP.reset_site_rects(lc.get("collector_tree"))
            import landing_place as LP
            resets += [list(rect) for _p, rect, _t in (LP._reader_start_groups(t) + LP._writer_start_groups(t) + LP._status_reset_groups(t))]
            resets += [list(rect) for rect in lc.get("group_rects_um", {}).values()]
            resets = [list(r) for r in dict.fromkeys(tuple(r) for r in resets)]
            try:
                nb = CLP._storage_band(tt, bus, width, used, phy=phy, resets=resets)
            except ValueError:
                nb = CLP._storage_rects_staged(tt, bus, width, used, phy=phy, resets=resets)
            assert abs(nb["area_reserve_um2"] - (old_band["area_reserve_um2"] if new else lc["bands"][bus]["area_reserve_um2"])) < 1e-3
            nb["instance"] = "u_cland_" + bus
            if new:
                lc["bands"][bus] = nb
            else:
                bands_rep[bus + "_old"] = lc["bands"][bus]["rect_um"]
                lc["bands"][bus] = nb
            bands_rep[f"{ttn}.{bus}"] = nb
            # local source (compose rule: nearest delivered-reset tap to the pin; band centre when the pin is > 405)
            tree = lc["collector_tree"]
            point = CLP._bus_xy(tt, bus)
            tapxy = {int(r["q"].split("rst_n_t")[1]): r["xy"] for r in tree["relays"] if r["q"].startswith("rst_n_t")}
            n = RT.consumer_count(tree)
            tap = min(range(n), key=lambda i: abs(tapxy[i][0] - point[0]) + abs(tapxy[i][1] - point[1]))
            status = None
            if abs(tapxy[tap][0] - point[0]) + abs(tapxy[tap][1] - point[1]) > 405:
                x0, y0, x1, y1 = nb["rect_um"]
                status = [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3)]
                tap = min(range(n), key=lambda i: abs(tapxy[i][0] - status[0]) + abs(tapxy[i][1] - status[1]))
            src = dict(name=bus, ready="landing_ready_" + bus, fault="landing_fault_" + bus, tap=tap,
                       xy_um=status or point, pin_xy_um=point, band={k: v for k, v in nb.items() if k != "ring_place"})
            cls = lc["collector_local_sources"]
            if new:
                cls.append(src)
            else:
                i = next(i for i, s in enumerate(cls) if s["name"] == bus)
                cls[i] = src
            # forwarded write clock input pin + its edge clock
            pin = dict(name="fclk_in_" + bus, dir="in", kind="clock", layer=P2.layer_budget["partition_signal_max"],
                       xy_um=scalar_point(P2, tt, bus), epoch=False)
            ecs = t["clock"].setdefault("edge_clocks", [])
            if new:
                lc["pins"].append(pin)
                ecs.append(dict(port=pin["name"], tap_um=pin["xy_um"], period_mult=1, note=EC_NOTE))
            else:
                q = next(p for p in lc["pins"] if p["name"] == pin["name"])
                q["xy_um"] = pin["xy_um"]
                e = next(e for e in ecs if e["port"] == pin["name"])
                e["tap_um"] = pin["xy_um"]
    finally:
        CLP.BAND_RESERVE, CLP.BAND_SPREAD, CLP.BAND_RING = saved
    rep["bands"] = bands_rep
    # forwarded clock outputs: x1_o (t43, face moved) and x2_o (t52, new)
    for part, t, bus, new in ((CHAIN[0], t1, bus1o, False), (CHAIN[1], t2, bus2o, True)):
        ttn = tn[part]
        tt = P2.types[ttn]
        point = scalar_point(P2, tt, bus)
        roots = GP.clock_pins(P2, ttn)
        src_tap = min(roots, key=lambda r: abs(r[1] - point[0]) + abs(r[2] - point[1]))[0]
        lc = t["clock"]["landing_contract"]
        if new:
            lc["pins"].append(dict(name="fclk_out_" + bus, dir="out", kind="clock", layer=P2.layer_budget["partition_signal_max"],
                                   xy_um=point, epoch=False, source_clock_port=src_tap))
        else:
            q = next(p for p in lc["pins"] if p["name"] == "fclk_out_" + bus)
            q["xy_um"] = point
            q["source_clock_port"] = src_tap
    # loader pin separation, written into the plan (FEED-BAL-2 form: raw == loaded for the changed types)
    Q = S.Plan(copy.deepcopy(raw), ppath)
    sep = {}
    for part in CHAIN + [OLD]:
        ttn = tn[part]
        t, sk = T[ttn]["clock"], Q.types[ttn]["clock"]
        for x, y in zip(t["landing_contract"]["pins"], sk["landing_contract"]["pins"]):
            if x["xy_um"] != y["xy_um"]:
                sep[f"{ttn}.{x['name']}"] = [x["xy_um"], y["xy_um"]]
                x["xy_um"] = copy.deepcopy(y["xy_um"])
        for i, (x, y) in enumerate(zip(t.get("edge_clocks") or [], sk.get("edge_clocks") or [])):
            if x != y:
                t["edge_clocks"][i] = copy.deepcopy(y)
    rep["pins_separated"] = sep

    out_text = json.dumps(raw) + "\n"
    # ---- EQ / scope gate
    for k in raw:
        if k not in ("partition_types", "ports", "clock"):
            assert raw[k] == orig[k], k
    for k in raw["clock"]:
        if k != "landing_network":
            assert raw["clock"][k] == orig["clock"][k], k
    for k in raw["clock"]["landing_network"]:
        if k != "edges":
            assert raw["clock"]["landing_network"][k] == orig["clock"]["landing_network"][k], k
    ch_e = [e["id"] for e, o in zip(raw["clock"]["landing_network"]["edges"], orig["clock"]["landing_network"]["edges"]) if e != o]
    assert ch_e == ["cland_clk__" + pid[1], "cland_clk__" + pid[2]] and len(raw["clock"]["landing_network"]["edges"]) == len(orig["clock"]["landing_network"]["edges"]), ch_e
    ch_p = [p["id"] for p, o in zip(raw["ports"], orig["ports"]) if p != o]
    assert ch_p == [pid[1], pid[2]] and len(raw["ports"]) == len(orig["ports"]), ch_p
    assert list(raw["partition_types"]) == list(orig["partition_types"])
    for t_ in raw["partition_types"]:
        if t_ not in TYPES:
            assert raw["partition_types"][t_] == orig["partition_types"][t_], t_
            continue
        a_, o_ = raw["partition_types"][t_], orig["partition_types"][t_]
        for k in set(a_) | set(o_):
            if k not in ("ft_slots", "clock"):
                assert a_[k] == o_[k], (t_, k)
        for k in set(a_["clock"]) | set(o_["clock"]):
            if k not in ("landing_contract", "edge_clocks"):
                assert a_["clock"][k] == o_["clock"][k], (t_, k)
        for k in set(a_["clock"]["landing_contract"]) | set(o_["clock"]["landing_contract"]):
            if k not in ("pins", "bands", "collector_local_sources"):
                assert a_["clock"]["landing_contract"][k] == o_["clock"]["landing_contract"][k], (t_, k)
        so = {s["name"]: s for s in o_["ft_slots"]}
        sa = {s["name"]: s for s in a_["ft_slots"]}
        for n_ in set(so) | set(sa):
            if n_ not in SLOTS:
                assert so.get(n_) == sa.get(n_), (t_, n_)
    for p in raw["partitions"]:
        assert p == next(q for q in orig["partitions"] if q["name"] == p["name"])
    P3 = S.Plan(json.loads(out_text), ppath)
    nat1 = P3.lane_natural(LANE)
    assert nat1 == nat0, (nat0, nat1)
    assert raw["latency"]["lanes"][LANE]["cycles"] == nat1["cycles"]
    for lid in P.lanes:
        if lid != LANE:
            assert P3.lane_natural(lid) == P.lane_natural(lid), lid
    for t_ in TYPES:
        for k in ("ft_slots",):
            assert P3.types[t_][k] == raw["partition_types"][t_][k], (t_, k)
    rep["lane_natural_after"] = nat1
    rep["eq_gate"] = dict(rtl_change=False, pin_cycle_change=False, outline_change=False, core_position_change=False,
                          lane_cycles_identical=True, other_lanes_natural_identical=True,
                          changed_paths=[f"ports.{pid[1]}.dst.part", f"ports.{pid[2]}.src.part",
                                         f"clock.landing_network.edges.cland_clk__{pid[1]}.dst.part",
                                         f"clock.landing_network.edges.cland_clk__{pid[2]}.src.part"] +
                                        [f"partition_types.{t_}.(ft_slots|clock.landing_contract|clock.edge_clocks)" for t_ in TYPES],
                          kit_input_types=list(TYPES))
    rep["new_slots"] = {SLOTS[0]: s1, SLOTS[1]: s2, SLOTS[2]: s3}
    return out_text, rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--base-sha", default=BASE_SHA)
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("report", nargs="?")
    a = ap.parse_args()
    if a.check:
        text, _ = derive(a.plan_in, a.base_sha)
        assert open(a.plan_out).read() == text, "output differs from re-derivation"
        print("CHECK PASS", sha(text))
        return
    text, rep = derive(a.plan_in, a.base_sha)
    open(a.plan_out, "w").write(text)
    rep["output_plan_sha256"] = sha(text)
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1, default=str) + "\n")
    print(json.dumps(dict(out=rep["output_plan_sha256"], windows=rep["windows_die"], stations=rep["stations"]["per_slot"],
                          max_pin_hop_um=rep["stations"]["max_pin_hop_um"])))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""S81-LEAF-REGRID (FABLE-FIX-S81-LEAF-R3 11-21, FABLE-CLOSURE-STRATEGY lever 4): lane-core re-grid of an S81 leaf type.

Measured cause of the vp block GRT overflow (t44 J5 wave kit, t39 p3): the 16 lane cores stand 2 to 28 um apart, the hi
station banks (1,025 flops per shared quad stage, 257 per lane stage) have their site at / next to the lane nearest the
block centroid, the legaliser wraps them round that core (free-area utilisation 0.76 to 0.88) and every bank bus then
crosses lane cores, where only M6-M8 route.  61 to 71 % of the overflow is inside lane boxes.

Form (moves only: no core is re-shaped or re-oriented, the outline is unchanged):
  * lanes go to columns parallel to the vn hi pin face, on the side they are on today; column gap COL_GAP, row gap
    >= ROW_GAP, on the 4.32 grid, clear of every non-lane core (+ gap) and of every ft bit / ft register site;
  * a strip of STRIP um between the vn face and the first column carries the buses;
  * every hi / ho row gets PER-LANE register sites at equal arc on the path face -> strip -> row gap -> lane pin
    (the form of CS_HI_GS = CS_HO_GS = 0; counts, cycles and bits are unchanged).

  slots PLAN --types RE [--json OUT]           per type: the slot grid found, 16 lanes fit?
  apply PLAN --types RE --out PLAN_OUT --report REP.json
                                               slots -> Hungarian (displacement) -> s81_hi_corridor.move_lanes ->
                                               per-lane hi / ho sites -> seat; a type that fails any step keeps its rows
  check PLAN --types RE [--json OUT] [--gs 0]  the gates of the form, per type (exit 1 when any type fails):
                                               sites_in_core 0, min lane gap, worst hop <= 405, bank spill radius

After apply, in this order and with bind tools == gen tools: istation_clear.py, leaf_slot_clear.py, then the re-solves on
the moved cores (vp_sr stations, reach_rules.py fix --rules 1, taps, fstart_reset_delta.py), then `check` again.
"""
import argparse, copy, json, math, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1])]
import s81_hi_corridor as H  # noqa: E402
import kit_istations as KI  # noqa: E402

G = 4.32
LW = 114.48
COL_GAP = 28.08
ROW_GAP = 25.92
STRIP = 43.2
OBS_GAP = 12.96        # lane to a non-lane core (SRAM / vn / vq body)
EDGE = 4.32
HOP = 405.0
SEAT = 8.64
FLOP_UM2 = 0.5832       # one station flop on the 2.16 x 0.27 um station comb
SPILL_MAX = 30.0        # um a bank may spread from its site before it is called a pile-up
md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])      # noqa: E731
snap = lambda v: round(round(v / G) * G, 3)                  # noqa: E731


def obox(t):
    return [b for b in H.boxes(t) if not H.LN.search(b[0])]


def lbox(t):
    return [b for b in H.boxes(t) if H.LN.search(b[0])]


def ft_points(t):
    pts = []
    for s in t.get("ft_slots") or []:
        for row in s.get("bit_sites_um") or []:
            for p in (row if row and isinstance(row[0], (list, tuple)) else [row]):
                if isinstance(p, (list, tuple)) and len(p) >= 2:
                    pts.append((p[0], p[1]))
        for p in s.get("regs_um") or []:
            if isinstance(p, (list, tuple)) and len(p) >= 2 and isinstance(p[0], (int, float)):
                pts.append((p[0], p[1]))
    return pts


def hi_face(t):
    """(x of the vn core face on the lane side, y range of the hi launch points, side of the lanes: -1 west / +1 east)"""
    fr = [e["from_um"] for es in H.hi_rows(t).values() for e in es]
    vn = [b for b in H.boxes(t) if ".u_vn." in b[0] or b[0].endswith("u_vn")]
    if not fr or not vn:
        return None
    ys = sorted(p[1] for p in fr)
    L = lbox(t)
    cx = sum((b[1] + b[3]) / 2 for b in L) / len(L)
    side = -1 if cx < sum((b[1] + b[3]) / 2 for b in vn) / len(vn) else 1
    return (min(b[1] for b in vn) if side < 0 else max(b[3] for b in vn)), (ys[0], ys[-1]), side


def find_slots(t, col_gap=COL_GAP, row_gap=ROW_GAP, strip=STRIP):
    """[(x, y)] lane origins: columns from the vn face outward, rows packed outward from the face centre."""
    W, Ht = t["outline_um"]
    f = hi_face(t)
    if f is None:
        return None, "no hi rows"
    fx, (y0, y1), side = f
    yc = (y0 + y1) / 2
    O = obox(t); FT = ft_points(t)
    # as many columns as fit between the face and the tile edge with a strip >= `strip`; the slack widens the strip
    avail = (fx - EDGE if side < 0 else W - EDGE - fx) - strip
    ncol = int((avail + col_gap) // (LW + col_gap))
    cols = []
    for k in range(ncol):
        x = (EDGE + (ncol - 1 - k) * (LW + col_gap)) if side < 0 else (W - EDGE - LW - (ncol - 1 - k) * (LW + col_gap))
        cols.append(round(math.floor(x / G + 1e-6) * G if side > 0 else math.ceil(x / G - 1e-6) * G, 3))
    strip = (fx - (cols[0] + LW)) if (cols and side < 0) else ((cols[0] - fx) if cols else strip)
    def ok(x, y):
        if y < EDGE - 1e-6 or y + LW > Ht - EDGE + 1e-6:
            return False
        for _, a, b, c, d in O:
            if x < c + OBS_GAP and a < x + LW + OBS_GAP and y < d + OBS_GAP and b < y + LW + OBS_GAP:
                return False
        for p in FT:
            if x - 2.16 < p[0] < x + LW + 2.16 and y - 2.16 < p[1] < y + LW + 2.16:
                return False
        return True
    out = []
    for x in cols:
        ys = []
        n = int((Ht - LW) / G) + 1
        cand = sorted((round(i * G, 3) for i in range(1, n)), key=lambda y: abs(y + LW / 2 - yc))
        for y in cand:                      # greedy outward from the face centre
            if ok(x, y) and all(abs(y - u) >= LW + row_gap - 1e-6 for u in ys):
                ys.append(y)
        out += [(x, y) for y in sorted(ys)]
    return dict(face_x=fx, face_y=[y0, y1], side=side, cols=cols, slots=out, strip=round(strip, 3)), None


def hungarian(a):
    n = len(a); m = len(a[0]); INF = math.inf
    u = [0] * (n + 1); v = [0] * (m + 1); p = [0] * (m + 1); way = [0] * (m + 1)
    for i in range(1, n + 1):
        p[0] = i; j0 = 0; minv = [INF] * (m + 1); used = [False] * (m + 1)
        while True:
            used[j0] = True; i0 = p[j0]; d = INF; j1 = 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = a[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur; way[j] = j0
                    if minv[j] < d:
                        d = minv[j]; j1 = j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += d; v[j] -= d
                else:
                    minv[j] -= d
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]; p[j0] = p[j1]; j0 = j1
            if j0 == 0:
                break
    r = [0] * n
    for j in range(1, m + 1):
        if p[j]:
            r[p[j] - 1] = j - 1
    return r


def plen(pts):
    return sum(md(a, b) for a, b in zip(pts, pts[1:]))


def at(pts, s):
    for a, b in zip(pts, pts[1:]):
        d = md(a, b)
        if s <= d + 1e-9:
            f = s / d if d else 0
            return [round(a[0] + (b[0] - a[0]) * f, 3), round(a[1] + (b[1] - a[1]) * f, 3)]
        s -= d
    return list(pts[-1])


def lane_path(vn, lp, S, rows):
    """vn point -> strip centre -> through the row gap of every column between the strip and the lane's column -> lp"""
    fx, side, cols = S["face_x"], S["side"], S["cols"]
    xs = fx + side * S["strip"] / 2
    pts = [list(vn), [xs, vn[1]]]
    dst = min(range(len(cols)), key=lambda i: abs((cols[i] + (LW if side < 0 else 0)) - lp[0]) + (0 if cols[i] - 30 <= lp[0] <= cols[i] + LW + 30 else 1e6))
    for j in range(0, dst):                    # column j is crossed through its nearest row gap
        ys = rows.get(cols[j]) or []
        gaps = [(a + LW + b) / 2 for a, b in zip(ys, ys[1:])] + ([ys[0] - ROW_GAP / 2] if ys else []) + ([ys[-1] + LW + ROW_GAP / 2] if ys else [])
        yg = min(gaps, key=lambda y: abs(y - lp[1]) + abs(y - pts[-1][1])) if gaps else lp[1]
        xc = cols[j] + (LW + COL_GAP / 2 if side > 0 else -COL_GAP / 2)
        pts += [[pts[-1][0], yg], [xc, yg]]
    pts += [[pts[-1][0], lp[1]], list(lp)]
    return pts


def regrid_type(tn, t, P, col_gap, row_gap, strip):
    S, err = find_slots(t, col_gap, row_gap, strip)
    if err:
        return dict(type=tn, result="REFUSED " + err)
    lanes = {h["inst"]: h for h in t["hard_cores"] if H.LN.search(h["inst"])}
    if len(S["slots"]) < len(lanes):
        return dict(type=tn, result=f"REFUSED {len(S['slots'])} slots for {len(lanes)} lanes", cols=S["cols"], side=S["side"])
    fx, yc = S["face_x"], sum(S["face_y"]) / 2
    sl = sorted(S["slots"], key=lambda s: abs(s[0] + LW / 2 - fx) + abs(s[1] + LW / 2 - yc))[:len(lanes)]
    names = sorted(lanes)
    C = [[md(lanes[n]["origin_um"], s) for s in sl] for n in names]
    asg = hungarian(C)
    seed = {names[i]: dict(origin_um=[sl[asg[i]][0], sl[asg[i]][1]], orient=lanes[names[i]].get("orient", "R0")) for i in range(len(names))}
    rows = {}
    for x, y in sl:
        rows.setdefault(x, []).append(y)
    for x in rows:
        rows[x].sort()
    mv = H.move_lanes(t, seed, 0, budgets=P.get("budgets"))
    nre, worst, bad = 0, 0.0, []
    for e in t["internal_stations"]:
        try:
            c, fwd, lane = KI.core_class(e)
        except Exception:
            continue
        if c not in ("hi", "ho") or not e.get("regs_um"):
            continue
        D = len(e["regs_um"])
        vn, lp = (e["from_um"], e["to_um"]) if c == "hi" else (e["to_um"], e["from_um"])
        pts = lane_path(vn, lp, S, rows)
        if c == "ho":
            pts = pts[::-1]
        Lp = plen(pts)
        e["regs_um"] = [at(pts, Lp * (j + 1) / (D + 1)) for j in range(D)]
        e["note"] = e.get("note", "") + f" | S81-LEAF-REGRID per-lane {c} sites (GS 0), {Lp:.0f} um / {D + 1} hops"
        h = Lp / (D + 1); worst = max(worst, h); nre += 1
        if h > HOP + 1e-6:
            bad.append(dict(conn=e["conn"][:80], hop=round(h, 1), stations=D))
    t["note"] = t.get("note", "") + f" | S81-LEAF-REGRID 11-21: {len(names)} lanes on {len(rows)} columns (col gap {col_gap}, row gap >= {row_gap}, strip {strip}), per-lane hi/ho banks"
    return dict(type=tn, result="moved" if not bad else "REFUSED hop", side=S["side"], face_x=fx, cols=sorted(rows), rows={str(k): v for k, v in rows.items()},
                slots_found=len(S["slots"]), move=mv, resited_rows=nre, worst_planned_hop_um=round(worst, 1), hop_over=bad[:8], n_hop_over=len(bad))


def seat(t, clr=SEAT):
    """every relay site and non hi/ho station register nearer than clr to a core box (or inside) goes to the nearest
    4.32-grid point with clearance >= clr; hop growth is reported, not limited (istation_clear owns the hop rule)."""
    B = H.boxes(t); W, Ht = t["outline_um"]
    moved = []

    def near(p):
        if H.clear(p, B) >= clr:
            return None
        best = None
        r = 1
        while r < 60 and best is None:
            for dx in range(-r, r + 1):
                for dy in (-(r - abs(dx)), r - abs(dx)):
                    q = (round(p[0] + dx * G / 2, 3), round(p[1] + dy * G / 2, 3))
                    if EDGE <= q[0] <= W - EDGE and EDGE <= q[1] <= Ht - EDGE and H.clear(q, B) >= clr:
                        if best is None or md(p, q) < md(p, best):
                            best = q
            r += 1
        return best
    rs = t.get("relay_sites") or {}
    for k, v in list(rs.items()):
        if isinstance(v, list) and len(v) >= 2 and isinstance(v[0], (int, float)):
            q = near(v)
            if q:
                moved.append(dict(kind="relay_site", name=k, old=list(v[:2]), new=list(q))); rs[k] = [q[0], q[1]] + list(v[2:])
    for e in t.get("internal_stations") or []:
        for j, r in enumerate(e.get("regs_um") or []):
            q = near(r)
            if q:
                moved.append(dict(kind="internal_station", name=e["conn"][:90], old=list(r[:2]), new=list(q))); e["regs_um"][j] = [q[0], q[1]]
    return moved


def check_type(tn, t, gs=0):
    B = H.boxes(t); L = lbox(t); W, Ht = t["outline_um"]
    inn = lambda p: [b[0] for b in B if b[1] < p[0] < b[3] and b[2] < p[1] < b[4]]      # noqa: E731
    st_in = sum(1 for e in t.get("internal_stations") or [] for r in e.get("regs_um") or [] if inn(r))
    rl_in = sum(1 for v in (t.get("relay_sites") or {}).values() if isinstance(v, list) and len(v) >= 2 and isinstance(v[0], (int, float)) and inn(v))
    ck = t.get("clock") or {}
    start_in = 0
    for key in ("landing_writer_start", "landing_reader_start", "landing_local_resets"):
        def walk(o):
            n = 0
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("xy", "site_um", "regs_um", "um") and isinstance(v, list):
                        for p in (v if v and isinstance(v[0], list) else [v]):
                            if len(p) >= 2 and isinstance(p[0], (int, float)) and inn(p):
                                n += 1
                    else:
                        n += walk(v)
            elif isinstance(o, list):
                for v in o:
                    n += walk(v)
            return n
        start_in += walk(ck.get(key))
    gaps, ogaps = [], []
    for i, a in enumerate(B):
        for b in B[i + 1:]:
            la, lb_ = bool(H.LN.search(a[0])), bool(H.LN.search(b[0]))
            if la or lb_:
                (gaps if la and lb_ else ogaps).append(max(max(a[1] - b[3], b[1] - a[3]), max(a[2] - b[4], b[2] - a[4])))
    worst = 0.0
    for e in t.get("internal_stations") or []:
        if e.get("regs_um"):
            pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
            worst = max(worst, max(md(a, b) for a, b in zip(pts, pts[1:])))
    # bank spill: flops per 4.32 cell, spread to the nearest free cells (free = outside every core box + 2.16)
    # demand: non-lane rows by their bits; hi / ho rows are one bank per (lane, stage): 257 / 18 flops as built (the rows
    # of one lane repeat the bundle bits), at the bit-weighted centroid of that lane-stage's sites
    dem = {}
    lane_st = {}
    for e in t.get("internal_stations") or []:
        try:
            c, fwd, lane = KI.core_class(e)
        except Exception:
            c, lane = None, None
        for j, r in enumerate(e.get("regs_um") or []):
            if c in ("hi", "ho") and lane is not None:
                if c == "hi" and j < gs:
                    continue
                v = lane_st.setdefault((c, lane, j), [0.0, 0.0, 0]); b_ = e.get("bits", 1)
                v[0] += r[0] * b_; v[1] += r[1] * b_; v[2] += b_
            else:
                k = (int(r[0] // G), int(r[1] // G)); dem[k] = dem.get(k, 0) + e.get("bits", 1)
    for (c, lane, j), v in lane_st.items():
        k = (int(v[0] / v[2] // G), int(v[1] / v[2] // G)); dem[k] = dem.get(k, 0) + min(v[2], 257 if c == "hi" else 18)
    if gs:
        for g, es in H.hi_rows(t).items():
            for j in range(gs):
                c = H.centroid(es, j)
                if c:
                    k = (int(c[0] // G), int(c[1] // G)); dem[k] = dem.get(k, 0) + 1025
    cap = G * G / FLOP_UM2 * 0.5
    nx, ny = int(W // G) + 1, int(Ht // G) + 1
    free = [[all(not (b[1] - 2.16 < (i + .5) * G < b[3] + 2.16 and b[2] - 2.16 < (j + .5) * G < b[4] + 2.16) for b in B) for j in range(ny)] for i in range(nx)]
    used = {}
    spill = []
    for k, n in sorted(dem.items(), key=lambda kv: -kv[1]):
        r = 0; left = n
        while left > 0 and r < 40:
            for dx in range(-r, r + 1):
                for dy in ({-(r - abs(dx)), r - abs(dx)}):
                    i, j = k[0] + dx, k[1] + dy
                    if 0 <= i < nx and 0 <= j < ny and free[i][j]:
                        a = min(left, cap - used.get((i, j), 0))
                        if a > 0:
                            used[(i, j)] = used.get((i, j), 0) + a; left -= a
            if left > 0:
                r += 1
        spill.append((r * G, n, [round((k[0] + .5) * G, 1), round((k[1] + .5) * G, 1)]))
    spill.sort(reverse=True)
    rep = dict(type=tn, sites_in_core=st_in, relay_in_core=rl_in, start_in_core=start_in, min_lane_gap_um=round(min(gaps), 2) if gaps else None,
               lane_gaps_under=sum(1 for g in gaps if g < ROW_GAP - 0.01), min_lane_to_other_core_um=round(min(ogaps), 2) if ogaps else None, worst_hop_um=round(worst, 1),
               bank_spill_max_um=round(spill[0][0], 1) if spill else 0, bank_spill_top=spill[:4],
               corridor=(lambda r: {k: r.get(k) for k in ("verdict", "banks_inside_core", "banks", "worst_ratio")})(H.check({"partition_types": {tn: t}}, ".", gs).get(tn, {})))
    rep["pass"] = (st_in == 0 and rl_in == 0 and start_in == 0 and rep["lane_gaps_under"] == 0 and worst <= HOP + 1e-6)
    rep["bank_spill_advisory"] = "OK" if rep["bank_spill_max_um"] <= SPILL_MAX else "PILE-UP"      # estimator, not calibrated against a kit yet
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("slots", "apply", "check"))
    ap.add_argument("plan")
    ap.add_argument("--types", default=r"^ot_s81sl_leaf__t")
    ap.add_argument("--out"); ap.add_argument("--report"); ap.add_argument("--json")
    ap.add_argument("--col-gap", type=float, default=COL_GAP); ap.add_argument("--row-gap", type=float, default=ROW_GAP)
    ap.add_argument("--strip", type=float, default=STRIP); ap.add_argument("--gs", type=int, default=0)
    a = ap.parse_args()
    P = json.load(open(a.plan))
    rep = []
    if a.cmd == "slots":
        for tn, t in H.matching(P, a.types):
            S, err = find_slots(t, a.col_gap, a.row_gap, a.strip)
            n = len(S["slots"]) if S else 0
            rep.append(dict(type=tn, slots=n, fit=n >= len(lbox(t)), side=S and S["side"], cols=S and len(S["cols"]), err=err))
            print("LEAF_REGRID_SLOTS", tn, "slots", n, "cols", S and len(S["cols"]), "side", S and S["side"], "FIT" if n >= len(lbox(t)) else "NOFIT", err or "")
    elif a.cmd == "apply":
        for tn, t in H.matching(P, a.types):
            keep = copy.deepcopy(t)
            r = regrid_type(tn, t, P, a.col_gap, a.row_gap, a.strip)
            if r["result"] == "moved":
                r["seated"] = seat(t)
                r["check"] = check_type(tn, t, 0)
            if r["result"] != "moved":
                P["partition_types"][tn] = keep
            rep.append(r)
            c = r.get("check") or {}
            print("LEAF_REGRID_APPLY", tn, r["result"], "hop", r.get("worst_planned_hop_um"), "seated", len(r.get("seated") or []),
                  "in_core", c.get("sites_in_core"), "gap", c.get("min_lane_gap_um"), "spill", c.get("bank_spill_max_um"), c.get("bank_spill_advisory"), "PASS" if c.get("pass") else "CHECK-FAIL" if c else "")
        json.dump(P, open(a.out, "w"))
    else:
        for tn, t in H.matching(P, a.types):
            r = check_type(tn, t, a.gs); rep.append(r)
            print("LEAF_REGRID_CHECK", tn, "PASS" if r["pass"] else "FAIL", {k: r[k] for k in ("sites_in_core", "relay_in_core", "start_in_core", "min_lane_gap_um", "lane_gaps_under", "worst_hop_um", "bank_spill_max_um")}, r["corridor"])
    o = a.report or a.json
    if o:
        json.dump(rep, open(o, "w"), indent=1)
    if a.cmd == "check" and any(not r["pass"] for r in rep):
        sys.exit(1)


if __name__ == "__main__":
    main()

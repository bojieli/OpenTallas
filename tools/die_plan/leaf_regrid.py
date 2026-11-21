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
  apply PLAN --types RE --out PLAN_OUT --report REP.json [--no-2d] [--no-add-stage] [--no-hop-fix]
                                               slots -> Hungarian (displacement) -> s81_hi_corridor.move_lanes ->
                                               per-lane hi / ho sites -> seat; a type that fails any step keeps its rows
  check PLAN --types RE [--json OUT] [--gs 0]  the gates of the form, per type (exit 1 when any type fails):
                                               sites_in_core 0, min lane gap, worst hop <= 405, bank spill radius

2-D SLOTS (FABLE-FIX-S81-LEAF-R5 11-21): a type whose columns beside the vn face hold fewer slots than lanes (43 of 79 on
the J7 base) is done again in the 2-D form: slots anywhere on the lane side of the vn cores and north / south of them
(never in the strip in front of the face), nearest the face centre first, any two lanes >= COL_GAP apart in x or >=
ROW_GAP apart in y, every keep-out of the column form kept.  The hi / ho path of a lane is then the shortest path on the
4.32 grid that stays SEAT um off every core and landing band (round the vn corner, through the lane gaps); the per-lane
sites stand at equal arc on it.  A type the column form fits is NOT touched by the 2-D form (same rows as before).
HI STAGE: a type whose per-lane hi path needs a hop over 405 um gets +1 per-lane hi stage on EVERY hi row (plan hi depth
+1, +1 cycle on the hi lanes, restage LF_CS_HI_D; the s81_hi_corridor --add-stage form), unless --no-add-stage.
HOP FIX: a non hi/ho row that seat() or a lane move left over 405 um (and longer than before) gets its registers re-sited
for the hop (one site per bus group, 0 cycles); a group (rows of one bus to one core) that still cannot meet 405 gets
+1 station on each of its rows (+1 cycle, reported as `grown`: the latency of those rows is re-priced by the bind).

After apply, in this order and with bind tools == gen tools: istation_clear.py, leaf_slot_clear.py, then the re-solves on
the moved cores (vp_sr stations, reach_rules.py fix --rules 1, taps, fstart_reset_delta.py), then `check` again.
"""
import argparse, bisect, copy, heapq, json, math, re, sys
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
BAND_GAP = 8.64        # lane to a clock landing band (the J5 t44 kit placed its bands with a lane 8.3 um away)
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
    O = obox(t); FT = ft_points(t); BD = H.band_rects(t)
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
        for a, b, c, d in BD:          # S81-LEAF-REGRID BAND KEEP-OUT (t44 kit A: ln_7 / ln_2 on the ft3_i / up_s bands, OT_CLAND BAND FAIL)
            if x < c + BAND_GAP and a < x + LW + BAND_GAP and y < d + BAND_GAP and b < y + LW + BAND_GAP:
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

def vn_boxes(t):
    return [b for b in H.boxes(t) if ".u_vn." in b[0] or b[0].endswith("u_vn")]


def find_slots_2d(t, n, base=(), col_gap=COL_GAP, row_gap=ROW_GAP, strip=STRIP):
    """S81-LEAF-REGRID 2-D: `base` slots kept, then grid origins nearest the face centre first, on the lane side of the vn
    cores and north / south of them (x never past the far end of vn), outside the strip in front of the face; any two
    slots >= col_gap apart in x or >= row_gap apart in y; cores (+ OBS_GAP), landing bands (+ BAND_GAP), ft sites and
    the tile edge closed as in the column form.  Stops at n slots."""
    W, Ht = t["outline_um"]
    f = hi_face(t)
    if f is None:
        return None, "no hi rows"
    fx, (y0, y1), side = f
    yc = (y0 + y1) / 2
    V = vn_boxes(t)
    O = obox(t); BD = H.band_rects(t)
    FT = sorted(ft_points(t))
    ftx = [p[0] for p in FT]
    xlo, xhi = (EDGE, max(b[3] for b in V) - LW) if side < 0 else (min(b[1] for b in V), W - EDGE - LW)
    sx0, sx1 = (fx - strip, fx) if side < 0 else (fx, fx + strip)          # the bus strip in front of the face stays open
    sy0, sy1 = y0 - row_gap, y1 + row_gap
    out = [tuple(s) for s in base]

    def sep(x, y):
        return all(abs(x - a) >= LW + col_gap - 1e-6 or abs(y - b) >= LW + row_gap - 1e-6 for a, b in out)
    cand = []
    i0, i1 = int(math.ceil(xlo / G - 1e-6)), int(math.floor(xhi / G + 1e-6))
    for i in range(i0, i1 + 1):
        x = round(i * G, 3)
        a, b = bisect.bisect_right(ftx, x - 2.16), bisect.bisect_left(ftx, x + LW + 2.16)
        fy = sorted(p[1] for p in FT[a:b])                                   # ft sites over this lane column
        blk = [(b_[2] - OBS_GAP, b_[4] + OBS_GAP) for b_ in O if x < b_[3] + OBS_GAP and b_[1] < x + LW + OBS_GAP]
        blk += [(r[1] - BAND_GAP, r[3] + BAND_GAP) for r in BD if x < r[2] + BAND_GAP and r[0] < x + LW + BAND_GAP]
        if x < sx1 and sx0 < x + LW:
            blk.append((sy0, sy1))
        for j in range(1, int((Ht - LW) / G) + 1):
            y = round(j * G, 3)
            if y < EDGE - 1e-6 or y + LW > Ht - EDGE + 1e-6:
                continue
            if any(y < hi_ and lo_ < y + LW for lo_, hi_ in blk):
                continue
            k = bisect.bisect_right(fy, y - 2.16)
            if k < len(fy) and fy[k] < y + LW + 2.16:
                continue
            cand.append((abs(x + LW / 2 - fx) + abs(y + LW / 2 - yc), x, y))
    cand.sort()
    for _, x, y in cand:
        if len(out) >= n:
            break
        if sep(x, y):
            out.append((x, y))
    return dict(face_x=fx, face_y=[y0, y1], side=side, cols=sorted({s[0] for s in out}), slots=out, strip=strip, form="2d"), None


class Router:
    """shortest Manhattan paths on the G grid of one type, SEAT um off every core box and landing band"""

    def __init__(self, t, clr=SEAT):
        W, Ht = t["outline_um"]
        B = H.boxes(t)
        blk = [(b[1] - clr, b[2] - clr, b[3] + clr, b[4] + clr) for b in B] + [(a - clr, b - clr, c + clr, d + clr) for a, b, c, d in H.band_rects(t)]
        self.nx, self.ny = int((W - EDGE) / G + 1e-6) + 1, int((Ht - EDGE) / G + 1e-6) + 1
        free = [[i >= 1 and j >= 1 for j in range(self.ny)] for i in range(self.nx)]
        for a, b, c, d in blk:               # closed: strictly inside the grown box (a point exactly clr away is free)
            for i in range(max(int(math.floor(a / G + 1e-6)) + 1, 0), min(int(math.ceil(c / G - 1e-6)), self.nx)):
                col = free[i]
                for j in range(max(int(math.floor(b / G + 1e-6)) + 1, 0), min(int(math.ceil(d / G - 1e-6)), self.ny)):
                    col[j] = False
        self.free = free

    def node(self, p, rmax=24):
        i0, j0 = int(round(p[0] / G)), int(round(p[1] / G))
        best = None
        for r in range(0, rmax + 1):
            for di in range(-r, r + 1):
                for dj in {-(r - abs(di)), r - abs(di)}:
                    i, j = i0 + di, j0 + dj
                    if 0 <= i < self.nx and 0 <= j < self.ny and self.free[i][j]:
                        d = md(p, (i * G, j * G))
                        if best is None or d < best[0]:
                            best = (d, i, j)
            if best is not None and r >= 2:
                break
        return best and (best[1], best[2])

    def path(self, a, b):
        """[a, grid points ..., b] or None"""
        s, e = self.node(a), self.node(b)
        if s is None or e is None:
            return None
        if s == e:
            return [list(a), [round(s[0] * G, 3), round(s[1] * G, 3)], list(b)]
        free, nx, ny = self.free, self.nx, self.ny
        hq = [(abs(s[0] - e[0]) + abs(s[1] - e[1]), 0, s)]
        g = {s: 0}; par = {}
        while hq:
            _, d, u = heapq.heappop(hq)
            if u == e:
                break
            if d > g[u]:
                continue
            for v in ((u[0] + 1, u[1]), (u[0] - 1, u[1]), (u[0], u[1] + 1), (u[0], u[1] - 1)):
                if 0 <= v[0] < nx and 0 <= v[1] < ny and free[v[0]][v[1]] and d + 1 < g.get(v, 1 << 30):
                    g[v] = d + 1; par[v] = u
                    heapq.heappush(hq, (d + 1 + abs(v[0] - e[0]) + abs(v[1] - e[1]), d + 1, v))
        if e not in par:
            return None
        nodes = [e]
        while nodes[-1] != s:
            nodes.append(par[nodes[-1]])
        nodes.reverse()
        pts = [list(a)]
        for k, u in enumerate(nodes):        # corners only
            if 0 < k < len(nodes) - 1 and (nodes[k - 1][0] == u[0] == nodes[k + 1][0] or nodes[k - 1][1] == u[1] == nodes[k + 1][1]):
                continue
            pts.append([round(u[0] * G, 3), round(u[1] * G, 3)])
        return pts + [list(b)]


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


def regrid_type(tn, t, P, col_gap, row_gap, strip, two_d=True, add_stage=True):
    S, err = find_slots(t, col_gap, row_gap, strip)
    if err:
        return dict(type=tn, result="REFUSED " + err)
    lanes = {h["inst"]: h for h in t["hard_cores"] if H.LN.search(h["inst"])}
    ncol = len(S["slots"])
    if ncol < len(lanes):
        if not two_d:
            return dict(type=tn, result=f"REFUSED {ncol} slots for {len(lanes)} lanes", cols=S["cols"], side=S["side"])
        # 2-D form: the column slots first (they keep the strip and the regular gaps), then free 2-D slots; if that
        # still does not fit, 2-D slots alone (columns pinned to the tile edge can waste the room an ft site closes)
        S2, _ = find_slots_2d(t, len(lanes), S["slots"], col_gap, row_gap, strip)
        if len(S2["slots"]) < len(lanes):
            S3, _ = find_slots_2d(t, len(lanes), (), col_gap, row_gap, strip)
            if len(S3["slots"]) > len(S2["slots"]):
                S2 = S3
        if len(S2["slots"]) < len(lanes):
            return dict(type=tn, result=f"REFUSED {len(S2['slots'])} slots for {len(lanes)} lanes (2-D; {ncol} in columns)", cols=S["cols"], side=S["side"])
        S = S2
    two = S.get("form") == "2d"
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
    RT = Router(t) if two else None
    todo = []
    for e in t["internal_stations"]:
        try:
            c, fwd, lane = KI.core_class(e)
        except Exception:
            continue
        if c not in ("hi", "ho") or not e.get("regs_um"):
            continue
        vn, lp = (e["from_um"], e["to_um"]) if c == "hi" else (e["to_um"], e["from_um"])
        pts = RT.path(vn, lp) if two else lane_path(vn, lp, S, rows)
        if pts is None:
            return dict(type=tn, result="REFUSED no path", conn=e["conn"][:80], side=S["side"], form="2d")
        if c == "ho":
            pts = pts[::-1]
        todo.append((e, c, pts, plen(pts)))
    def over(ex):
        return [(e, c, Lp) for e, c, pts, Lp in todo if Lp / (len(e["regs_um"]) + ex.get(c, 0) + 1) > HOP + 1e-6]
    extra = {}
    if over(extra) and add_stage:
        # S81-HI-STAGE: one CS_HI_D / CS_HO_D per leaf, so EVERY row of a class with a hop over 405 um gets the stage
        # (ot_s81sl_vp derives its write-back timeline from CS_HI_D + CS_HO_D, so the classes move independently)
        ex = {c: 1 for _, c, _ in over(extra)}
        if not over(ex):
            extra = ex
    nre, worst, bad = 0, 0.0, []
    for e, c, pts, Lp in todo:
        D = len(e["regs_um"]) + extra.get(c, 0)
        e["regs_um"] = [at(pts, Lp * (j + 1) / (D + 1)) for j in range(D)]
        e["note"] = e.get("note", "") + f" | S81-LEAF-REGRID per-lane {c} sites (GS 0{', 2-D path' if two else ''}), {Lp:.0f} um / {D + 1} hops"
        if extra.get(c):
            e["note"] += f" | S81-HI-STAGE +1 per-lane {c} stage (+1 cycle, restage LF_CS_{c.upper()}_D): the lane path was over 405 um a hop"
        h = Lp / (D + 1); worst = max(worst, h); nre += 1
        if h > HOP + 1e-6:
            bad.append(dict(conn=e["conn"][:80], hop=round(h, 1), stations=D))
    t["note"] = t.get("note", "") + (f" | S81-LEAF-REGRID 11-21: {len(names)} lanes on {len(rows)} columns (col gap {col_gap}, row gap >= {row_gap}, strip {strip}), per-lane hi/ho banks"
                                     if not two else f" | S81-LEAF-REGRID 11-21 2-D: {len(names)} lanes ({ncol} column slots + 2-D slots round the vn cores; x gap >= {col_gap} or y gap >= {row_gap}), per-lane hi/ho banks on grid paths")
    if extra:
        t["note"] += f" | S81-HI-STAGE: {' and '.join(sorted(extra))} depth +1 (+1 cycle each)"
    r = dict(type=tn, result="moved" if not bad else "REFUSED hop", side=S["side"], face_x=fx, cols=sorted(rows), rows={str(k): v for k, v in rows.items()},
             slots_found=len(S["slots"]), move=mv, resited_rows=nre, worst_planned_hop_um=round(worst, 1), hop_over=bad[:8], n_hop_over=len(bad))
    if two:
        r["form"] = "2d"; r["column_slots"] = ncol
    if extra:
        r["add_stage"] = dict(extra); r["cycles"] = "+1 on " + " and ".join(f"CS_{c.upper()}_D" for c in sorted(extra))
        r["depth"] = {c: max(len(e["regs_um"]) for e, c2, _, _ in todo if c2 == c) for c in sorted(extra)}
    return r


def _hops(e):
    pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
    return [md(a, b) for a, b in zip(pts, pts[1:])]


def _is_h(e):
    try:
        return KI.core_class(e)[0] in ("hi", "ho")
    except Exception:
        return False


def fix_hops(t, before, clr=SEAT, reach=220.0):
    """S81-LEAF-REGRID HOP FIX.  before = the type's internal_stations before the re-grid (same order).  Every non hi/ho
    row now over HOP and longer than before: (1) the rows of its group (same conn, launch, capture core, station count)
    take ONE new site per stage, the grid point clr off every core with the least worst hop of the group (0 cycles);
    (2) a group still over HOP: +1 station on every row of the group, equal arc on the shortest grid path clr off every core (+1 cycle)."""
    B = H.boxes(t); W, Ht = t["outline_um"]
    ist = t.get("internal_stations") or []
    was = [max(_hops(o)) if o.get("regs_um") else 0.0 for o in before]
    grp = {}
    for i, e in enumerate(ist):
        if not e.get("regs_um") or not e.get("from_um") or not e.get("to_um") or _is_h(e):
            continue
        k = (e.get("conn"), e.get("launch"), str(e.get("capture", "")).rsplit(".", 1)[0], len(e["regs_um"]))
        grp.setdefault(k, []).append(i)
    rep = dict(resited=[], grown=[], left=[])
    grow = {}
    RT = None
    for k, idx in sorted(grp.items(), key=lambda kv: str(kv[0])):
        bad = [i for i in idx if max(_hops(ist[i])) > HOP + 1e-6 and (i >= len(was) or max(_hops(ist[i])) > was[i] + 1e-6)]
        if not bad:
            continue
        mem = [ist[i] for i in idx]
        w0 = max(max(_hops(e)) for e in mem)
        for _ in range(3):
            for j in range(k[3]):
                cx = sum(e["regs_um"][j][0] for e in mem) / len(mem); cy = sum(e["regs_um"][j][1] for e in mem) / len(mem)
                def wst(q):
                    w = 0.0
                    for e in mem:
                        a = e["regs_um"][j - 1] if j else e["from_um"]
                        b = e["regs_um"][j + 1] if j + 1 < k[3] else e["to_um"]
                        w = max(w, md(a, q), md(q, b))
                    return w
                cur = max(max(md(e["regs_um"][j - 1] if j else e["from_um"], e["regs_um"][j]),
                              md(e["regs_um"][j], e["regs_um"][j + 1] if j + 1 < k[3] else e["to_um"])) for e in mem)
                best = None
                st = G / 2
                n = int(reach / st)
                i0, j0 = int(round(cx / st)), int(round(cy / st))
                for di in range(-n, n + 1):
                    for dj in range(-(n - abs(di)), n - abs(di) + 1):
                        q = (round((i0 + di) * st, 3), round((j0 + dj) * st, 3))
                        if not (EDGE <= q[0] <= W - EDGE and EDGE <= q[1] <= Ht - EDGE):
                            continue
                        key = (max(wst(q), HOP - 5.0), abs(di) + abs(dj))
                        if (best is None or key < best[0]) and H.clear(q, B) >= clr:
                            best = (key, q)
                if best and best[0][0] < cur - 1e-6:          # never a worse hop than the group has now
                    for e in mem:
                        e["regs_um"][j] = [best[1][0], best[1][1]]
            if max(max(_hops(e)) for e in mem) <= HOP + 1e-6:
                break
        w1 = max(max(_hops(e)) for e in mem)
        for e in mem:
            e["note"] = (e.get("note") or "") + f" | S81-LEAF-REGRID hop fix: group re-sited for the hop ({w0:.0f} -> {w1:.0f} um)"
        rep["resited"].append(dict(conn=str(k[0])[:80], capture=k[2], rows=len(mem), hop_before=round(w0, 1), hop_after=round(w1, 1)))
        if w1 > HOP + 1e-6:
            grow[k] = idx
    for key, idx in grow.items():
        rows_ = [ist[i] for i in idx]
        n0 = {len(e["regs_um"]) for e in rows_}
        ok = len(n0) == 1
        if ok:
            RT = RT or Router(t, clr)
            new = []
            for e in rows_:
                pts = RT.path(e["from_um"], e["to_um"])
                own = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
                if pts is None or plen(pts) > plen(own) + 200.0:     # an end in a pocket between cores: the row's own polyline
                    pts = own
                Lp = plen(pts); D = len(e["regs_um"]) + 1
                new.append([at(pts, Lp * (j + 1) / (D + 1)) for j in range(D)])
                ok = ok and Lp / (D + 1) <= HOP + 1e-6
        if not ok:
            rep["left"].append(dict(conn=str(key[0])[:80], capture=key[2], rows=len(rows_), hop=round(max(max(_hops(e)) for e in rows_), 1)))
            continue
        for e, r in zip(rows_, new):
            e["regs_um"] = r
            e["note"] = (e.get("note") or "") + f" | S81-LEAF-REGRID hop fix: +1 station ({len(r) - 1}->{len(r)}, +1 cycle on these rows), equal arc"
        rep["grown"].append(dict(conn=str(key[0])[:80], capture=key[2], rows=len(rows_), bits=sum(e.get("bits", 1) for e in rows_), stations=[len(new[0]) - 1, len(new[0])], cycles="+1"))
    return rep


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
    on_band = sorted({b[0] for b in L for a, bb, c, d in H.band_rects(t) if b[1] < c and a < b[3] and b[2] < d and bb < b[4]})
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
    rep["lanes_on_band"] = on_band
    rep["pass"] = (not on_band and st_in == 0 and rl_in == 0 and start_in == 0 and rep["lane_gaps_under"] == 0 and worst <= HOP + 1e-6)
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
    ap.add_argument("--no-2d", action="store_true", help="apply: column form only (a type with too few column slots is refused)")
    ap.add_argument("--no-add-stage", action="store_true", help="apply: no +1 per-lane hi stage on a type whose lane path needs a hop over 405 um")
    ap.add_argument("--no-hop-fix", action="store_true", help="apply: leave non hi/ho rows that the move put over 405 um")
    a = ap.parse_args()
    P = json.load(open(a.plan))
    rep = []
    if a.cmd == "slots":
        for tn, t in H.matching(P, a.types):
            S, err = find_slots(t, a.col_gap, a.row_gap, a.strip)
            n = len(S["slots"]) if S else 0
            n2 = n
            if S and n < len(lbox(t)) and not a.no_2d:
                n2 = max(len(find_slots_2d(t, len(lbox(t)), b, a.col_gap, a.row_gap, a.strip)[0]["slots"]) for b in (S["slots"], ()))
            rep.append(dict(type=tn, slots=n, slots_2d=n2, fit=max(n, n2) >= len(lbox(t)), side=S and S["side"], cols=S and len(S["cols"]), err=err))
            print("LEAF_REGRID_SLOTS", tn, "slots", n, "cols", S and len(S["cols"]), "side", S and S["side"],
                  "FIT" if n >= len(lbox(t)) else f"FIT-2D {n2}" if n2 >= len(lbox(t)) else f"NOFIT (2-D {n2})", err or "")
    elif a.cmd == "apply":
        for tn, t in H.matching(P, a.types):
            keep = copy.deepcopy(t)
            r = regrid_type(tn, t, P, a.col_gap, a.row_gap, a.strip, two_d=not a.no_2d, add_stage=not a.no_add_stage)
            if r["result"] == "moved":
                r["seated"] = seat(t)
                if not a.no_hop_fix:
                    hf = fix_hops(t, keep.get("internal_stations") or [])
                    if hf["resited"] or hf["grown"] or hf["left"]:
                        r["hop_fix"] = hf
                        if hf["grown"]:
                            r["seated"] += seat(t)
                r["check"] = check_type(tn, t, 0)
            if r["result"] != "moved":
                P["partition_types"][tn] = keep
            rep.append(r)
            c = r.get("check") or {}
            print("LEAF_REGRID_APPLY", tn, r["result"], "hop", r.get("worst_planned_hop_um"), "seated", len(r.get("seated") or []),
                  "in_core", c.get("sites_in_core"), "gap", c.get("min_lane_gap_um"), "spill", c.get("bank_spill_max_um"), c.get("bank_spill_advisory"), "PASS" if c.get("pass") else "CHECK-FAIL" if c else "",
                  *(["2D"] if r.get("form") == "2d" else []), *(["STAGE+1 " + "+".join(sorted(r["add_stage"]))] if r.get("add_stage") else []),
                  *([f"HOPFIX resited {len(r['hop_fix']['resited'])} grown {len(r['hop_fix']['grown'])} left {len(r['hop_fix']['left'])}"] if r.get("hop_fix") else []))
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

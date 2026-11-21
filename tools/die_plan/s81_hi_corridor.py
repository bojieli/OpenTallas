#!/usr/bin/env python3
"""S81-HI-CORRIDOR (FABLE-FIX-S81-LEAF 11-19, COORD lever 5): vp HI-quad buses over the lane hard cores.

The leaf RTL shares the first CS_HI_GS (2) hi station stages per quad (lanes 4g..4g+3, CS_H_G 4): one 1,0xx-flop bank
per quad stage.  kit_istations places each shared bank at the bit-weighted centroid of its member lanes' plan sites,
and that centroid often lands INSIDE a lane / vn core (t28 4/8, t31 5/8 shared banks), so the placer splits the bank to
both sides and the bus crosses the core twice (measured t28/t27 GRT hot gcells: cap 5-8 over lane boxes, usage 7-12).

  check PLAN [--types RE] [--json OUT]      estimator (PRECHECK): per shared bank: site inside a core?; per hard core:
                                            HI bus bits crossing it vs over-core tracks (extent x TRK tracks/um)
  seed  PLAN --types RE --form A|B --out SEED.json [--corridor 30.24]
        A = corridor: keep the lane -> quad map, widen every lane column / row gap below --corridor to --corridor
        B = remap: keep the 16 lane sites, give each quad 4 sites in one lane column (nearest the vn face first)
        (SEED = core_place.py --seed input {type: {inst: {origin_um, orient}}})
  apply PLAN --seed SEED.json --out PLAN_OUT  rigid lane moves with their riding coordinates (clock / landing records,
                                            station end points, per-lane registers near the lane); then
                                            istation_clear.py / leaf_slot_clear.py, then `sites`
  sites PLAN --types RE --out PLAN_OUT      every shared bank gets ONE explicit site in a free channel (all member
                                            lanes' regs_um[j] = that point): s0 nearest free point to the old centroid,
                                            s1 the free point with the least max hop to the members' next points.
                                            Station counts, cycles, bits, pins unchanged; hops <= max(400, before).
        BANK FOOTPRINT (FABLE-FIX-S81-LEAF-R4 11-21): a site is a BANK, not a point.  seat_bank() seats the bank's flops
        the way face_flops.tcl ff_put_near does (spiral on the 2.16 x 0.27 um station grid, cells on a core box + halo
        closed; banks of one type stack).  A bank that ends on two opposite sides of one core is SPLIT: a bad site,
        `check` counts it (shared and per-lane banks) and calls the type OVER.  A bank that needs more than FP_SPILL x
        its free-field radius is a PILE-UP: counted and printed, advisory.  `sites` takes the first candidate that is
        neither, else the least bad one.
  lane-sites PLAN --types RE --out PLAN_OUT [--gs N]   (S81-LANE-BANK) every per-lane bank (hi stage >= gs, every ho
        stage) gets ONE site whose footprint is clean: kit_istations seats the whole lane stage (about 1,046 flops) at
        the bits-weighted centroid of its rows, and rows that leave two vn cores put that centroid in a lane core
        (t44 ln_0 stage 0 inside ln_9).  All rows of the lane stage take the site; hops <= max(LIMIT, before); a lane
        that cannot keep its hops keeps its old rows.  Counts, cycles, bits, pins unchanged.
        --add-stage (S81-HI-STAGE)          a type with refused rows: +1 per-lane hi stage on every hi row of that type
                                            (plan hi depth +1, +1 cycle, restage LF_CS_HI_D), then all hops <= 400.
"""
import argparse, itertools, json, math, re, sys
from collections import defaultdict

LN = re.compile(r"g_ln\[(\d+)\]\.u_l$")
TRK = 10.0          # measured over-core tracks/um per direction (t28 GRT gcell 0.57 um: H cap 5-8, V cap 6)
import os as _os_cbc, sys as _sys_cbc
_sys_cbc.path.insert(0, _os_cbc.path.dirname(_os_cbc.path.abspath(__file__)))
import cbc_rules as _CBC  # noqa: E402  OWNER 11-20 #6: generator hop default (300 um), one knob for every die
LIMIT = _CBC.REACH_UM_PER_HOP - _CBC.SITE_MARGIN_UM
G = 4.32
SEP = 21.6         # um between two shared banks
md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])          # noqa: E731
snap = lambda v: round(round(v / G) * G, 3)                      # noqa: E731


CP, RH, FW = 2.16, 0.27, 1.08     # face_flops.tcl station grid: column pitch (40 sites), row height, flop width
FP_HALO = 1.08                    # ff_put_near keeps a cell this far off a placed core (OT_FF_CORE_HALO_UM)
FP_SPILL = 2.5                    # seated radius / free-field radius above which a bank is a pile-up: against one core face
                                  # 1.4, in a core corner 2.0, alone in a 28-um channel 1.8 / a 26-um row gap 2.2 (all fine);
                                  # in a 10.8-um gap 5.6, or stacked on earlier banks (measured t44 ln_9: 8 banks in 11-28 um gaps)
FP_SIDE = 0.05                    # share of a bank on each of two opposite sides of one core = split bank
FP_RMAX = 200                     # ff_put_near spiral limit (station-grid cells)


def bank_rad(n):
    """station-grid radius of an n-flop bank on a free grid (diamond of radius R holds 2R(R+1)+1 cells)"""
    R = 0
    while 2 * R * (R + 1) + 1 < n:
        R += 1
    return R


def _cut(iv, a, b):
    out = []
    for lo, hi in iv:
        if b < lo or a > hi:
            out.append((lo, hi))
            continue
        if lo < a:
            out.append((lo, a - 1))
        if hi > b:
            out.append((b + 1, hi))
    return out


def seat_bank(p, n, B, outline=None, occ=(), halo=FP_HALO, grid=None):
    """Footprint of an n-flop bank sited at p: the cells ff_put_near's spiral takes around p when every cell touching a
    core box of B (+ halo) or a rectangle of occ (earlier banks) is closed.  Returns fit, R (seated radius), R0 (free
    field), spill = R / R0, bbox_um, split = cores with >= FP_SIDE of the bank on each of two opposite sides, ok (it fits
    and is not split: the hard verdict), pile (spill > FP_SPILL: advisory until calibrated on a placed kit).
    grid ({row: [(c_lo, c_hi)]}, optional): cells taken by earlier banks; they are closed and this bank's cells are added,
    so banks sited on one spot stack outwards exactly as ff_gocc makes them."""
    c0, r0 = int(p[0] // CP), int(p[1] // RH)
    R0 = max(bank_rad(n), 1)
    blk = [(x0 - halo, y0 - halo, x1 + halo, y1 + halo, nm) for nm, x0, y0, x1, y1 in B] + [(a, b, c, d, None) for a, b, c, d in occ]
    cmax = int((outline[0] - FW) // CP) if outline else None
    rmax = int(outline[1] // RH) - 1 if outline else None

    def rows(R):
        near = [b for b in blk if b[0] < (c0 + R) * CP + FW and b[2] > (c0 - R) * CP and b[1] < (r0 + R + 1) * RH and b[3] > (r0 - R) * RH]
        out = []
        for dr in range(-R, R + 1):
            r = r0 + dr
            if r < 0 or (rmax is not None and r > rmax):
                continue
            lo, hi = max(c0 - (R - abs(dr)), 0), c0 + (R - abs(dr))
            if cmax is not None:
                hi = min(hi, cmax)
            if hi < lo:
                continue
            iv = [(lo, hi)]
            y = r * RH
            for b in near:
                if b[1] < y + RH and b[3] > y:
                    iv = _cut(iv, math.floor((b[0] - FW) / CP) + 1, math.ceil(b[2] / CP) - 1)
            for a, b in (grid.get(r, ()) if grid else ()):
                iv = _cut(iv, a, b)
            if iv:
                out.append((r, iv))
        return out

    count = lambda R: sum(hi - lo + 1 for _, iv in rows(R) for lo, hi in iv)      # noqa: E731
    if count(FP_RMAX) < n:
        return dict(fit=False, ok=False, pile=True, R=None, R0=R0, spill=None, split=[], bbox_um=None)
    lo, hi = 0, FP_RMAX
    while lo < hi:
        m = (lo + hi) // 2
        if count(m) >= n:
            hi = m
        else:
            lo = m + 1
    R = lo
    cells = rows(R)
    if grid is not None:
        for r, iv in cells:
            grid.setdefault(r, []).extend(iv)
    xs = [v for _, iv in cells for a, b in iv for v in (a * CP, b * CP + FW)]
    ys = [v for r, _ in cells for v in (r * RH, r * RH + RH)]
    split = []
    for nm, x0, y0, x1, y1 in B:
        left = right = below = above = 0
        ca, cb = math.floor((x0 - FW) / CP) + 1, math.ceil(x1 / CP) - 1
        for r, iv in cells:
            y = r * RH
            for a, b in iv:
                if y < y1 and y + RH > y0:
                    left += max(0, min(b, ca - 1) - a + 1); right += max(0, b - max(a, cb + 1) + 1)
                k = max(0, min(b, cb) - max(a, ca) + 1)
                if y >= y1:
                    above += k
                elif y + RH <= y0:
                    below += k
        if min(left, right) >= FP_SIDE * n or min(above, below) >= FP_SIDE * n:
            split.append(nm)
    spill = round(R / R0, 2)
    return dict(fit=True, R=R, R0=R0, spill=spill, split=split, ok=not split, pile=spill > FP_SPILL,
                bbox_um=[round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)])


def _fp_key(f):
    """worse footprint = larger key"""
    return (0 if f["fit"] else 1, len(f["split"]), f["spill"] if f["spill"] is not None else 1e9)


def lane_flops(es):
    """flops of one per-lane bank as built: the rows of one lane repeat the bundle bits, so the bank is the widest row
    + its valid (measured in t44 3_place.odb: 257 per hi lane stage, 1,025 per shared quad stage)"""
    return max(e["bits"] for e in es) + 1 if es else 0


def quad_flops(es):
    by = defaultdict(list)
    for e in es:
        by[e["capture"]].append(e)
    return sum(lane_flops(v) for v in by.values())


def band_rects(t):
    """clock landing bands of the type (plan clock.band_fixed_um rect_um): closed to register banks and to lane cores
    (t44 kit A 11-21: two moved lanes on the ft3_i / up_s bands, OT_CLAND BAND FAIL in global_place)"""
    out = []
    for v in ((t.get("clock") or {}).get("band_fixed_um") or {}).values():
        for r in ([v.get("rect_um")] if v.get("rect_um") else []) + list(v.get("rects_um") or []):
            if r and len(r) == 4:
                out.append(tuple(r))
    return out


def lane_rows(t):
    """(class, lane inst) -> rows: hi = vn -> lane (hi_rows), ho = lane -> vn; one kit bank per (class, lane, stage)"""
    by = defaultdict(list)
    for es in hi_rows(t).values():
        for e in es:
            by[("hi", e["capture"])].append(e)
    for e in t.get("internal_stations") or []:
        m = LN.search(e.get("launch", "").split(":")[-1].rsplit(".", 1)[0])
        if m and "u_vn" in e.get("capture", "") and e.get("regs_um"):
            by[("ho", e["launch"].split(":")[-1].rsplit(".", 1)[0])].append(e)
    return by


def lane_banks(t, gs):
    """per-lane banks as kit_istations sites them (hi stage >= gs, every ho stage; CS_HO_GS 0): (lane, stage, centroid,
    flops, class)"""
    out = []
    for (c, cap), es in sorted(lane_rows(t).items()):
        for j in range(gs if c == "hi" else 0, max(len(e["regs_um"]) for e in es)):
            mem = [e for e in es if len(e["regs_um"]) > j]
            out.append((cap, j, centroid(mem, j), lane_flops(mem), c))
    return out


def lane_sites(P, rex, gs, mincl, reach=160.0, tries=160):
    """S81-LANE-BANK: one clean-footprint site per (class, lane, stage) bank; see the module docstring."""
    rows = []
    for tn, t in matching(P, rex):
        B = boxes(t); OUT = t.get("outline_um")
        occ = list(band_rects(t))
        FP = [q[0] for q in free_points(t, B, mincl) if not any(a - mincl < q[0][0] < c + mincl and b - mincl < q[0][1] < d + mincl for a, b, c, d in occ)]
        for g, es in sorted(hi_rows(t).items()):          # shared banks keep their sites and their room
            for j in range(gs):
                c = centroid(es, j)
                if c:
                    f = seat_bank(c, quad_flops([e for e in es if len(e["regs_um"]) > j]), B, OUT, occ)
                    if f["bbox_um"]:
                        occ.append(f["bbox_um"])
        for (cls, cap), es in sorted(lane_rows(t).items()):
            keep = [([list(r) for r in e["regs_um"]], e.get("note")) for e in es]
            hop0 = max(max(_hops(e)) for e in es)
            lim = max(LIMIT, hop0)
            mine, bad = [], None
            j0 = gs if cls == "hi" else 0
            for j in range(j0, max(len(e["regs_um"]) for e in es)):
                mem = [e for e in es if len(e["regs_um"]) > j]
                c = centroid(mem, j); n = lane_flops(mem)

                def hop(p):
                    w = 0
                    for e in mem:
                        w = max(w, md(e["regs_um"][j - 1] if j else e["from_um"], p))
                        if len(e["regs_um"]) == j + 1:
                            w = max(w, md(p, e["to_um"]))
                    return w
                cand = sorted((q for q in FP if md(q, c) <= reach), key=lambda q: md(q, c))
                cand = [q for q in cand if hop(q) <= lim]
                best = None
                for q in cand[:tries]:
                    f = seat_bank(q, n, B, OUT, occ + mine)
                    if f["ok"] and not f["pile"]:
                        best = (q, f); break
                    if best is None or _fp_key(f) < _fp_key(best[1]):
                        best = (q, f)
                if best is None:
                    bad = dict(type=tn, lane=cap, cls=cls, stage=j, result="REFUSED no site within the hop limit", lim=round(lim, 1)); break
                q, f = best
                for e in mem:
                    e["regs_um"][j] = [q[0], q[1]]
                if f["bbox_um"]:
                    mine.append(f["bbox_um"])
                rows.append(dict(type=tn, lane=cap, cls=cls, stage=j, result="sited", old=[round(c[0], 2), round(c[1], 2)], new=list(q), flops=n,
                                 fp_ok=f["ok"], fp_pile=f["pile"], fp_spill=f["spill"], fp_split=f["split"]))
            if bad is None and max(max(_hops(e)) for e in es) > lim + 1e-6:
                bad = dict(type=tn, lane=cap, cls=cls, result="REFUSED final hop", hop=round(max(max(_hops(e)) for e in es), 1), before=round(hop0, 1))
            if bad:
                for e, (regs, note) in zip(es, keep):
                    e["regs_um"] = regs
                rows[:] = [r for r in rows if not (r["type"] == tn and r.get("lane") == cap and r.get("cls") == cls)]
                bad["kept_old"] = True
                rows.append(bad)
                for j in range(j0, max(len(e["regs_um"]) for e in es)):      # the old banks still take their room
                    mem = [e for e in es if len(e["regs_um"]) > j]
                    f = seat_bank(centroid(mem, j), lane_flops(mem), B, OUT, occ)
                    if f["bbox_um"]:
                        occ.append(f["bbox_um"])
            else:
                for e in es:
                    e["note"] = (e.get("note") or "") + f" | S81-LANE-BANK {cls} stages >= {j0} on one clean-footprint site per lane stage"
                occ += mine
    return rows


def matching(P, rex):
    """(name, type) of every partition type matching rex that has hard cores; a matching type with no hard_cores entry
    (a hard type such as ot_s81sl_kv_leaf__t2) has no lane cores to route around, so it is skipped with a warning."""
    for tn, t in sorted(P["partition_types"].items()):
        if not re.search(rex, tn):
            continue
        if not t.get("hard_cores"):
            print(f"HI_CORRIDOR_WARN {tn}: no hard_cores entry, skipped", file=sys.stderr)
            continue
        yield tn, t


def boxes(t):
    out = []
    for h in t["hard_cores"]:
        w, hh = h["outline_um"]
        if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        x, y = h["origin_um"]
        out.append((h["inst"], x, y, x + w, y + hh))
    return out


def clear(p, B):
    """distance from p to the nearest core box (0 inside)"""
    d = 1e9
    for _, x0, y0, x1, y1 in B:
        dx = max(x0 - p[0], 0, p[0] - x1); dy = max(y0 - p[1], 0, p[1] - y1)
        d = min(d, (dx * dx + dy * dy) ** 0.5)
    return d


def hi_rows(t):
    """quad -> stage j -> [entry] for the vn -> lane (hi) rows"""
    q = defaultdict(list)
    for e in t.get("internal_stations") or []:
        m = LN.search(e.get("capture", ""))
        if m and "u_vn" in e.get("launch", "") and e.get("regs_um"):
            q[int(m[1]) // 4].append(e)
    return q


def centroid(es, j):
    es = [e for e in es if len(e["regs_um"]) > j]
    w = sum(e["bits"] for e in es)
    return (sum(e["regs_um"][j][0] * e["bits"] for e in es) / w, sum(e["regs_um"][j][1] * e["bits"] for e in es) / w) if w else None


def lane_bits(es):
    by = defaultdict(int)
    for e in es:
        by[e["capture"]] += e["bits"]
    return max(by.values()) if by else 0


def nxt(e, j):
    return e["regs_um"][j + 1] if len(e["regs_um"]) > j + 1 else e["to_um"]


def legs(a, b):
    """two L paths a->b (x first / y first) as segment lists"""
    c1, c2 = (b[0], a[1]), (a[0], b[1])
    return [[(a, c1), (c1, b)], [(a, c2), (c2, b)]]


def crossing(seg, box):
    """(direction, um of the segment inside the box, box extent across the segment)"""
    (x0, y0), (x1, y1) = seg; _, bx0, by0, bx1, by1 = box
    if abs(y0 - y1) < 1e-6 and by0 < y0 < by1:
        o = min(max(x0, x1), bx1) - max(min(x0, x1), bx0)
        return ("H", o, by1 - by0) if o > 0 else None
    if abs(x0 - x1) < 1e-6 and bx0 < x0 < bx1:
        o = min(max(y0, y1), by1) - max(min(y0, y1), by0)
        return ("V", o, bx1 - bx0) if o > 0 else None
    return None


def check(P, rex, gs):
    rep = {}
    for tn, t in matching(P, rex):
        B = boxes(t); Q = hi_rows(t)
        if not Q:
            continue
        banks, load = [], defaultdict(lambda: dict(H=0, V=0))
        grid = {}          # station-grid cells taken so far: banks of one type stack (shared banks first, as the kit seats them)
        bands = band_rects(t)
        for g, es in sorted(Q.items()):
            bits = lane_bits(es)
            for j in range(gs):
                c = centroid(es, j)
                if c is None:
                    continue
                ins = [b[0] for b in B if b[1] < c[0] < b[3] and b[2] < c[1] < b[4]]
                nfl = quad_flops([e for e in es if len(e["regs_um"]) > j])
                fp = seat_bank(c, nfl, B, t.get("outline_um"), bands, grid=grid)
                banks.append(dict(quad=g, stage=j, site=[round(c[0], 2), round(c[1], 2)], inside=ins, clear_um=round(clear(c, B), 1),
                                  flops=nfl, fp_ok=fp["ok"], fp_pile=fp["pile"], fp_spill=fp["spill"], fp_split=fp["split"], fp_bbox_um=fp["bbox_um"]))
                # bus legs: shared bank j -> next point of every member (j < gs-1: next shared bank; else each lane)
                if j < gs - 1:
                    targets = [centroid(es, j + 1)]
                else:
                    targets = list({tuple(nxt(e, j)) for e in es if len(e["regs_um"]) > j})
                for tg in targets:
                    if tg is None:
                        continue
                    best = min(legs(c, tg), key=lambda L: sum(1 for s in L for b in B if crossing(s, b)))
                    for s in best:
                        for b in B:
                            x = crossing(s, b)
                            if x:
                                load[b[0]][x[0]] += bits
                                load[b[0]]["ext_" + x[0]] = round(x[2], 1)
        cores = {}
        for k, v in load.items():
            for d in "HV":
                if v[d]:
                    sup = v["ext_" + d] * TRK
                    cores.setdefault(k, {})[d] = dict(bits=v[d], tracks=round(sup), ratio=round(v[d] / sup, 2))
        worst = max([c[d]["ratio"] for c in cores.values() for d in c] or [0])
        n_in = sum(1 for b in banks if b["inside"])
        lanes = []
        for cap, j, c, n, cls in lane_banks(t, gs):
            fp = seat_bank(c, n, B, t.get("outline_um"), bands, grid=grid)
            if not fp["ok"] or fp["pile"]:
                lanes.append(dict(lane=cap, cls=cls, stage=j, site=[round(c[0], 2), round(c[1], 2)], flops=n, fp_ok=fp["ok"], fp_pile=fp["pile"],
                                  fp_spill=fp["spill"], fp_split=fp["split"], fp_bbox_um=fp["bbox_um"]))
        n_fp = sum(1 for b in banks + lanes if not b["fp_ok"])
        n_pile = sum(1 for b in banks + lanes if b["fp_pile"])
        rep[tn] = dict(banks_inside_core=n_in, banks=len(banks), worst_ratio=worst, banks_fp_bad=n_fp, banks_pile_up=n_pile, lane_banks_fp_bad=lanes,
                       verdict="OVER" if worst > 1 or n_in or n_fp else ("RISK" if worst > 0.5 else "OK"), bank_sites=banks, cores=cores)
    return rep


def free_points(t, B, mincl, step=4.32):
    W, H = t["outline_um"]
    pts = []
    y = step
    while y < H - step:
        x = step
        while x < W - step:
            c = clear((x, y), B)
            if c >= mincl:
                pts.append(((round(x, 3), round(y, 3)), c))
            x += step
        y += step
    return pts


def _hops(e):
    return [md(x, y) for x, y in zip([e["from_um"]] + e["regs_um"], e["regs_um"] + [e["to_um"]])]


def _site_type(tn, t, gs, mincl, extra=False):
    """one type.  extra=True (S81-HI-STAGE, +1 cycle on the hi lanes of this leaf): every hi row has ONE more per-lane
    stage at index gs (after the shared banks); the last shared bank may then sit up to two hops from the lane's next
    point, and the new stage is placed on a free point between them (both sub-hops <= LIMIT)."""
    rows = []
    Q = hi_rows(t)
    if not Q:
        return rows
    B = boxes(t)
    FP = free_points(t, B, mincl)
    if not FP:
        return [dict(type=tn, result="no free point")]
    used = []          # banks already sited in this type: keep >= SEP um apart (one bank per channel spot)
    fpbox = {}         # pick -> seated footprint bbox: later banks seat round it
    BANDS = list(band_rects(t))
    OUT = t.get("outline_um")

    def best_fp(points, n, tries=60):
        """first candidate (in preference order) whose bank footprint is clean; else the least bad of the first `tries`"""
        occ = BANDS + [fpbox[u] for u in used if u in fpbox]
        worst_seen = None
        for q in points[:tries]:
            f = seat_bank(q, n, B, OUT, occ)
            if f["ok"] and not f["pile"]:
                return q, f
            if worst_seen is None or _fp_key(f) < _fp_key(worst_seen[1]):
                worst_seen = (q, f)
        return worst_seen if worst_seen else (None, None)
    hop0 = {id(e): max(_hops(e)) for es in Q.values() for e in es}
    if extra:
        for es in Q.values():
            for e in es:
                if len(e["regs_um"]) < gs:
                    return [dict(type=tn, capture=e["capture"], result="REFUSED add-stage: row has fewer than gs stages")]
                a, c = e["regs_um"][gs - 1], nxt(e, gs - 1)
                e["regs_um"].insert(gs, [round((a[0] + c[0]) / 2, 3), round((a[1] + c[1]) / 2, 3)])     # placeholder
    snap = {g: [(e, [list(r) for r in e["regs_um"]], e.get("note")) for e in es] for g, es in Q.items()}
    picks = defaultdict(list)
    for g, es in sorted(Q.items()):
        prev = None
        for j in range(gs):
            mem = [e for e in es if len(e["regs_um"]) > j]
            if not mem:
                continue
            c = centroid(mem, j)
            before = max(max(_hops(e)) for e in mem)
            lim = LIMIT if extra else max(LIMIT, before)

            def worst(p):
                w = 0
                for e in mem:
                    a = prev if prev is not None else (e["regs_um"][j - 1] if j else e["from_um"])
                    w = max(w, md(a, p))
                    if j == gs - 1:                  # extra: two hops to the point after the new stage, 10 um for the detour
                        w = max(w, (md(p, nxt(e, j + 1)) + 10.0) / 2 if extra else md(p, nxt(e, j)))
                return w
            FPu = [q for q in FP if md(q[0], c) <= 2 * LIMIT and all(md(q[0], u) >= SEP for u in used)]
            nfl = quad_flops(mem)
            if j == 0:
                cand = sorted(FPu, key=lambda q: md(q[0], c))[:400]
                cand = [q[0] for q in cand if worst(q[0]) <= lim]
            else:
                cand = [(worst(q[0]), -q[1], q[0]) for q in FPu]
                cand = [q[2] for q in sorted(q for q in cand if q[0] <= lim)]
            pick, fp = best_fp(cand, nfl)
            if pick is None:
                rows.append(dict(type=tn, quad=g, stage=j, result="REFUSED no site within hop limit", lim=lim)); prev = None; continue
            for e in mem:
                e["regs_um"][j] = [pick[0], pick[1]]
                e["note"] = e.get("note", "") + f" | S81-HI-CORRIDOR shared quad{g} stage {j} site {pick[0]},{pick[1]} (was centroid {c[0]:.1f},{c[1]:.1f})"
            after = max(max(_hops(e)) for e in mem)
            rows.append(dict(type=tn, quad=g, stage=j, result="sited", old=[round(c[0], 2), round(c[1], 2)], new=pick,
                             clear_um=round(clear(pick, B), 1), max_hop_before=round(before, 1), max_hop_after=round(after, 1),
                             flops=nfl, fp_ok=fp["ok"], fp_pile=fp["pile"], fp_spill=fp["spill"], fp_split=fp["split"]))
            prev = pick
            used.append(pick); picks[g].append(pick)
            if fp["bbox_um"]:
                fpbox[pick] = fp["bbox_um"]
    if extra:              # the new per-lane stage: free point with the least longer sub-hop, >= SEP / 2 from banks and each other
        for g, es in sorted(Q.items()):
            for e in es:
                a, c = e["regs_um"][gs - 1], nxt(e, gs)
                cand = [(max(md(a, q[0]), md(q[0], c)), md(a, q[0]) + md(q[0], c), q[0]) for q in FP
                        if md(q[0], a) <= LIMIT and md(q[0], c) <= LIMIT and all(md(q[0], u) >= SEP / 2 for u in used)]
                if not cand:
                    rows.append(dict(type=tn, capture=e["capture"], result="REFUSED add-stage: no free point within one hop of both ends"))
                    continue
                q, fp = best_fp([x[2] for x in sorted(cand)], e["bits"] + 1, tries=24)
                e["regs_um"][gs] = [q[0], q[1]]; used.append(q)
                e["note"] = e.get("note", "") + f" | S81-HI-STAGE +1 per-lane hi stage at {q[0]},{q[1]} (index {gs}, +1 cycle; shared bank to lane was over {LIMIT:g} um)"
    for g, es in sorted(Q.items()):          # final hop check over the whole rows (both stages moved)
        bad = []
        for e in es:
            h = max(_hops(e))
            if h > (LIMIT if extra else max(LIMIT, hop0[id(e)])) + 1e-6:
                bad.append(dict(type=tn, quad=g, capture=e["capture"], result="REFUSED final hop", hop=round(h, 1),
                                before=round(hop0[id(e)], 1)))
        if (bad or any(r.get("quad") == g and r["result"] != "sited" for r in rows)) and not extra:
            # REFUSED-KEEPS-OLD (FABLE-PD-S81-0015 11-20: plan_j4a carried 491 rows over 405 um, max 626.4): a refused row
            # used to keep the moved site.  The quad is one bank per stage, so the WHOLE quad goes back to its old rows.
            for e, regs, note in snap[g]:
                e["regs_um"] = [list(r) for r in regs]
                if note is None:
                    e.pop("note", None)
                else:
                    e["note"] = note
            for r in rows:
                if r.get("quad") == g and r["result"] == "sited":
                    r["result"] = "REFUSED quad kept its old sites (a member row would exceed the hop limit)"
            for q in picks[g]:
                used.remove(q)
            for b in bad:
                b["kept_old"] = True
        rows += bad
    return rows


def sites(P, rex, gs, mincl, add_stage=False):
    """add_stage (S81-HI-STAGE, COORD 11-19, cycles pre-approved): a type whose plain siting refuses any row is done again
    from its untouched rows with one more per-lane hi stage on EVERY hi row of the type (one CS_HI_D per leaf, so the
    depth stays uniform: plan hi depth +1, +1 cycle on the hi lanes, restage LF_CS_HI_D).  A type that still refuses
    keeps its untouched rows and its refusals are reported."""
    import copy
    rows = []
    for tn, t in matching(P, rex):
        keep = copy.deepcopy(t.get("internal_stations"))
        r = _site_type(tn, t, gs, mincl)
        if add_stage and any(x["result"] != "sited" for x in r):
            t["internal_stations"] = copy.deepcopy(keep)
            r2 = _site_type(tn, t, gs, mincl, extra=True)
            if any(x["result"] != "sited" for x in r2):
                t["internal_stations"] = keep
                r = [dict(x, add_stage="tried") for x in r2 if x["result"] != "sited"]
            else:
                n = sum(len(es) for es in hi_rows(t).values())
                r = r2 + [dict(type=tn, result="sited", add_stage=1, hi_rows=n,
                               hi_depth=max(len(e["regs_um"]) for es in hi_rows(t).values() for e in es),
                               max_hop_after=round(max(max(_hops(e)) for es in hi_rows(t).values() for e in es), 1))]
        rows += r
    return rows


def lanes_of(t):
    L = {}
    for h in t["hard_cores"]:
        m = LN.search(h["inst"])
        if m:
            L[int(m[1])] = h
    return L


def vn_face(t):
    va = [h for h in t["hard_cores"] if h["inst"].endswith("u_vn.u_a")][0]
    w, hh = va["outline_um"]
    o = va.get("orient", "R0")
    fx = va["origin_um"][0] + (w if o in ("MY", "R180") else 0)
    return fx, va["origin_um"][1] + hh / 2


def columns(L, tol=30.0):
    xs = sorted(L.items(), key=lambda kv: kv[1]["origin_um"][0])
    cols = []
    for k, h in xs:
        if cols and h["origin_um"][0] - cols[-1][-1][1]["origin_um"][0] <= tol:
            cols[-1].append((k, h))
        else:
            cols.append([(k, h)])
    return cols


def seed(P, rex, form, cor):
    out, rep = {}, {}
    for tn, t in matching(P, rex):
        L = lanes_of(t)
        if len(L) != 16:
            continue
        lw, lh = L[0]["outline_um"]
        fx, fy = vn_face(t)
        cols = columns(L)
        sd = {}
        if form == "A":
            # pairwise relaxation: two lanes facing each other across a gap < cor (overlapping in the other axis) ->
            # the lane farther from the vn face (along that axis) moves away by the deficit; repeat to a fixpoint
            pos = {k: list(h["origin_um"]) for k, h in L.items()}
            for _ in range(200):
                moved = False
                for i, j in itertools.combinations(sorted(pos), 2):
                    a_, b_ = pos[i], pos[j]
                    ox = min(a_[0], b_[0]) + lw - max(a_[0], b_[0])      # x overlap (>0: stacked in y)
                    oy = min(a_[1], b_[1]) + lh - max(a_[1], b_[1])
                    if ox > 0 and (oy <= 0 or ox >= oy):     # stacked in y (an overlap separates along y)
                        lo_, hi_ = (i, j) if a_[1] < b_[1] else (j, i)
                        gap = pos[hi_][1] - pos[lo_][1] - lh
                        if gap < cor - 1e-6:
                            far = hi_ if abs(pos[hi_][1] + lh / 2 - fy) >= abs(pos[lo_][1] + lh / 2 - fy) else lo_
                            pos[far][1] = snap(pos[far][1] + (cor - gap + G / 2) * (1 if far == hi_ else -1)); moved = True
                    elif oy > 0:
                        lo_, hi_ = (i, j) if a_[0] < b_[0] else (j, i)
                        gap = pos[hi_][0] - pos[lo_][0] - lw
                        if gap < cor - 1e-6:
                            far = hi_ if abs(pos[hi_][0] + lw / 2 - fx) >= abs(pos[lo_][0] + lw / 2 - fx) else lo_
                            pos[far][0] = snap(pos[far][0] + (cor - gap + G / 2) * (1 if far == hi_ else -1)); moved = True
                if not moved:
                    break
            for k, h in L.items():
                sd[h["inst"]] = dict(origin_um=pos[k], orient=h.get("orient", "R0"))
            W, H = t["outline_um"]
            span = [min(p[0] for p in pos.values()), min(p[1] for p in pos.values()), max(p[0] for p in pos.values()) + lw, max(p[1] for p in pos.values()) + lh]
            rep[tn] = dict(form="A", lane_bbox=[round(v, 2) for v in span], inside_outline=span[0] >= 0 and span[1] >= 0 and span[2] <= W and span[3] <= H)
        else:
            Qe = hi_rows(t)
            pin_c = {}
            for g, es in Qe.items():
                w = sum(e["bits"] for e in es)
                pin_c[g] = (sum(e["from_um"][0] * e["bits"] for e in es) / w, sum(e["from_um"][1] * e["bits"] for e in es) / w)
            cs = sorted(cols, key=lambda c: abs(sum(h["origin_um"][0] for _, h in c) / len(c) + lw / 2 - fx))
            chunks, left = [], []
            for c in cs:
                s = sorted(c, key=lambda kv: kv[1]["origin_um"][1])
                while len(s) >= 4:          # the 4 consecutive sites nearest the vn centre y
                    i = min(range(len(s) - 3), key=lambda i: abs(sum(h["origin_um"][1] for _, h in s[i:i + 4]) / 4 + lh / 2 - fy))
                    chunks.append(s[i:i + 4]); s = s[:i] + s[i + 4:]
                left += s
            left.sort(key=lambda kv: md(kv[1]["origin_um"], (fx, fy)))
            while len(left) >= 4:
                chunks.append(left[:4]); left = left[4:]
            chunks = chunks[:4]
            cen = lambda ch: (sum(h["origin_um"][0] for _, h in ch) / 4 + lw / 2, sum(h["origin_um"][1] for _, h in ch) / 4 + lh / 2)  # noqa
            best = min(itertools.permutations(range(4)), key=lambda p: sum(md(pin_c.get(g, (fx, fy)), cen(chunks[p[g]])) for g in range(4)))
            for g in range(4):
                ch = chunks[best[g]]
                lanes = list(range(4 * g, 4 * g + 4))
                lp = {}
                for l in lanes:
                    es = [e for e in Qe.get(g, []) if LN.search(e["capture"])[1] == str(l)]
                    w = sum(e["bits"] for e in es) or 1
                    lp[l] = (sum(e["from_um"][0] * e["bits"] for e in es) / w, sum(e["from_um"][1] * e["bits"] for e in es) / w) if es else (fx, fy)
                perm = min(itertools.permutations(range(4)), key=lambda p: sum(md(lp[l], ch[p[i]][1]["origin_um"]) for i, l in enumerate(lanes)))
                for i, l in enumerate(lanes):
                    site = ch[perm[i]][1]
                    sd[L[l]["inst"]] = dict(origin_um=list(site["origin_um"]), orient=L[l].get("orient", "R0"))
            pure = sum(1 for ch in chunks if max(h["origin_um"][0] for _, h in ch) - min(h["origin_um"][0] for _, h in ch) <= 30)
            moved = sum(1 for k, h in L.items() if sd[h["inst"]]["origin_um"] != list(h["origin_um"]))
            rep[tn] = dict(form="B", quads_in_one_column=pure, lanes_moved=moved)
        out[tn] = sd
    return out, rep


def _shift(v, d):
    return [round(v[0] + d[0], 4), round(v[1] + d[1], 4)] + list(v[2:])


def move_lanes(t, sd, gs, near=30.0, budgets=None):
    """rigid lane moves (same orient): the lane, every clock / landing record of that lane (inst / name prefix),
    the end points of station rows on it, and the registers of those rows near the old lane box (hi rows: the
    per-lane stages >= gs only; the shared banks are re-sited by `sites`) move by the lane's delta."""
    L = {h["inst"]: h for h in t["hard_cores"] if LN.search(h["inst"])}
    D, old = {}, {}
    for inst, v in sd.items():
        h = L[inst]
        if v.get("orient", h.get("orient", "R0")) != h.get("orient", "R0"):
            raise SystemExit(f"HI_CORRIDOR_APPLY refuses an orient change on {inst}")
        d = (v["origin_um"][0] - h["origin_um"][0], v["origin_um"][1] - h["origin_um"][1])
        if abs(d[0]) + abs(d[1]) > 1e-6:
            w, hh = h["outline_um"]
            old[inst] = (h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + w, h["origin_um"][1] + hh)
            D[inst] = d
            h["origin_um"] = [round(v["origin_um"][0], 4), round(v["origin_um"][1], 4)]
    n = dict(lanes=len(D), clock=0, ends=0, regs=0)

    def walk(o):
        if isinstance(o, dict):
            inst = o.get("inst") if o.get("inst") in D else next((k for k in D if str(o.get("name", "")).startswith(k + ".")), None)
            if inst:
                for k in ("xy", "pin_um", "tap_um"):
                    if isinstance(o.get(k), list) and len(o[k]) >= 2 and all(isinstance(x, (int, float)) for x in o[k][:2]):
                        o[k] = _shift(o[k], D[inst]); n["clock"] += 1
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(t.get("clock") or {})
    for e in t.get("internal_stations") or []:
        for inst, d in D.items():
            cap = e.get("capture") == inst
            lau = e.get("launch", "").startswith("core:" + inst + ".")
            if not (cap or lau):
                continue
            if cap:
                e["to_um"] = _shift(e["to_um"], d); n["ends"] += 1
            if lau:
                e["from_um"] = _shift(e["from_um"], d); n["ends"] += 1
            hi = cap and "u_vn" in e.get("launch", "")
            b = old[inst]
            for j, r in enumerate(e.get("regs_um") or []):
                if hi and j < gs:
                    continue
                dx = max(b[0] - r[0], 0, r[0] - b[2]); dy = max(b[1] - r[1], 0, r[1] - b[3])
                if max(dx, dy) <= near:
                    e["regs_um"][j] = _shift(r, d); n["regs"] += 1
            e["note"] = e.get("note", "") + f" | S81-HI-CORRIDOR lane move {inst} by {d[0]:.2f},{d[1]:.2f}"
    n["taps_moved"] = clear_added_taps(t, only=set(D), budgets=budgets)
    return n


def _tap_rule(t, budgets=None):
    """the bind's own added-tap rule (taps.grid_explicit_sites): clear = schema.type_tap_clear, obstacles =
    placement_obstacles.placement_boxes(halo=clear) (every placed macro and probe blockage, not only hard_cores), and the
    R4 grid taps of the type AS IT IS NOW (schema._grid_taps: a grid tap moves when a core moves under it)."""
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:                    # python3 -I leaves the script directory off sys.path
        sys.path.insert(0, here)
    import schema
    from placement_obstacles import placement_boxes

    class _P:                                   # _grid_taps / tap_pitch read only P.types[tn] and P.budgets
        types = {"_": t}
    _P.budgets = dict(budgets or {})
    clear = schema.type_tap_clear(t)
    grid = [(x, y) for _, x, y in schema._grid_taps(_P, "_")]
    return clear, list(placement_boxes(t, halo=clear).values()), grid


def added_tap_errors(t, budgets=None):
    """names of clock.added_taps the bind would refuse ("violates outline/halo/tap spacing"), checked in table order
    against the grid taps and the added taps before them, exactly as taps.grid_explicit_sites does."""
    adds = (t.get("clock") or {}).get("added_taps") or []
    if not adds:
        return []
    clear, B, grid = _tap_rule(t, budgets)
    W, H = t["outline_um"]; eps = 1e-8; taken = list(grid); bad = []
    for tp in adds:
        x, y = map(float, tp["xy"][:2])
        if not (clear - eps <= x <= W - clear + eps and clear - eps <= y <= H - clear + eps
                and not any(abs(x - a) < clear - eps and abs(y - c) < clear - eps for a, c in taken)
                and not any(a + eps < x < c - eps and b2 + eps < y < d - eps for a, b2, c, d in B)):
            bad.append(tp.get("name"))
        taken.append((x, y))
    return bad


def clear_added_taps(t, rmax=200.0, step=2.16, only=None, budgets=None, margin=0.01):
    """after a lane move: every clock.added_tap the bind's rule refuses (under a moved core + halo, inside any placed
    macro / probe blockage + halo, closer than the tap clear to a GRID tap or to another added tap, outside the outline
    margin) -> the nearest point that passes that rule against the grid taps and ALL other added taps.  The rule is
    _tap_rule (the bind's taps.grid_explicit_sites), so a plan this leaves is one the bind accepts.  `only` is kept for
    callers and ignored: a tap can become illegal without sitting under a moved lane (a grid tap re-centres)."""
    adds = (t.get("clock") or {}).get("added_taps") or []
    if not adds:
        return []
    clear, B, grid = _tap_rule(t, budgets)
    W, H = t["outline_um"]; c = clear + margin
    B = [(x0 - margin, y0 - margin, x1 + margin, y1 + margin) for x0, y0, x1, y1 in B]

    def ok(x, y, me):
        return (c <= x <= W - c and c <= y <= H - c
                and not any(x0 < x < x1 and y0 < y < y1 for x0, y0, x1, y1 in B)
                and not any(abs(x - gx) < c and abs(y - gy) < c for gx, gy in grid)
                and not any(abs(x - float(o["xy"][0])) < c and abs(y - float(o["xy"][1])) < c for o in adds if o is not me))
    moved = []
    for _ in range(3):                           # a moved tap never lands near another one, so one pass settles; 3 = guard
        bad = set(added_tap_errors(t, budgets))
        if not bad:
            break
        for tp in adds:
            if tp.get("name") not in bad:
                continue
            x, y = map(float, tp["xy"][:2])
            best = None
            for r in range(1, int(rmax / step) + 1):
                for i in range(-r, r + 1):
                    for j in ((-r, r) if abs(i) != r else range(-r, r + 1)):
                        q = (round(x + i * step, 3), round(y + j * step, 3))
                        if ok(*q, tp) and (best is None or md(q, (x, y)) < md(best, (x, y))):
                            best = q
                if best:
                    break
            if best is None:
                raise SystemExit(f"HI_CORRIDOR_APPLY: added tap {tp.get('name')} has no legal point within {rmax} um")
            tp["xy"] = [best[0], best[1]] + list(tp["xy"][2:])
            moved.append([tp.get("name"), round(x, 3), round(y, 3), best[0], best[1]])
    left = added_tap_errors(t, budgets)
    if left:
        raise SystemExit(f"HI_CORRIDOR_APPLY: added taps still refused by the bind rule: {left}")
    return moved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("check", "seed", "sites", "apply", "lane-sites"))
    ap.add_argument("--seed")
    ap.add_argument("plan")
    ap.add_argument("--types", default=r"ot_s81sl_leaf__t\d+")
    ap.add_argument("--gs", type=int, default=2)
    ap.add_argument("--form", choices=("A", "B"))
    ap.add_argument("--corridor", type=float, default=30.24)
    ap.add_argument("--min-clear", type=float, default=8.64)
    ap.add_argument("--out"); ap.add_argument("--json")
    ap.add_argument("--add-stage", action="store_true",
                    help="sites: a type with refused rows gets one more per-lane hi stage on every hi row (+1 cycle) and is sited again")
    a = ap.parse_args()
    P = json.load(open(a.plan))
    if a.cmd == "check":
        rep = check(P, a.types, a.gs)
        for tn, r in rep.items():
            print(tn, r["verdict"], "banks_inside_core", f"{r['banks_inside_core']}/{r['banks']}", "worst_bits_per_track", r["worst_ratio"],
                  "banks_fp_bad", r["banks_fp_bad"], "banks_pile_up", r["banks_pile_up"])
        if a.json:
            json.dump(rep, open(a.json, "w"), indent=1)
        print("HI_CORRIDOR_CHECK", {v: sum(1 for r in rep.values() if r["verdict"] == v) for v in ("OK", "RISK", "OVER")})
    elif a.cmd == "lane-sites":
        rows = lane_sites(P, a.types, a.gs, a.min_clear)
        json.dump(P, open(a.out, "w"), indent=1)
        json.dump(rows, open(a.out + ".lane_sites.json", "w"), indent=1)
        bad = [r for r in rows if r["result"] != "sited"]
        dirty = [r for r in rows if r["result"] == "sited" and (not r["fp_ok"] or r["fp_pile"])]
        print("HI_CORRIDOR_LANE_SITES", len(rows) - len(bad), "sited", len(bad), "lanes refused (kept old rows)", len(dirty), "sited with a split / pile-up footprint")
        for r in bad + dirty:
            print(r)
        sys.exit(1 if bad else 0)
    elif a.cmd == "seed":
        sd, rep = seed(P, a.types, a.form, a.corridor)
        json.dump(sd, open(a.out, "w"), indent=1)
        for tn, r in rep.items():
            print(tn, r)
    elif a.cmd == "apply":
        S = json.load(open(a.seed))
        ok = dict(matching(P, a.types))
        for tn, sd in S.items():
            if tn in ok:
                print(tn, "HI_CORRIDOR_APPLY", move_lanes(ok[tn], sd, a.gs, budgets=P.get("budgets")))
        json.dump(P, open(a.out, "w"), indent=1)
    else:
        rows = sites(P, a.types, a.gs, a.min_clear, a.add_stage)
        json.dump(P, open(a.out, "w"), indent=1)
        json.dump(rows, open(a.out + ".sites.json", "w"), indent=1)
        bad = [r for r in rows if r["result"] != "sited"]
        print("HI_CORRIDOR_SITES", len(rows) - len(bad), "sited", len(bad), "refused")
        for r in bad:
            print(r)
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

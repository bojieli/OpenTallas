#!/usr/bin/env python3
"""HBM-CHANNELS 11-11 (DIE-HBM-97 sub-lane; COORD ruling on hbm-channels-ask, relayed by DIE-HBM-97). DO_NOT_COUNT.
HBM plan event 'hbm-channels-1111' on plan_p11t_taps_cyc (29333b2b).
 (A) SU-CHAN on q_su11, q_su11__physical_v1, q_su01, q_su01__physical_v1: same outline; the three hard-core columns
     spread to open two 120 um V streets, the four core row bands move down (+24 um between rows, +40 um above the top
     row).  One piecewise-linear map X(x), Y(y) (fixed at the outline edges and die_ft_bands +20 um) moves the core
     origins, the core clock taps (clock.taps[].xy) and the internal-station end points (from_um / to_um, on core pins
     or faces).  Station SITES are NOT mapped: every ft slot and internal station of the type is re-derived by the
     generator rule (b2n.restation: RelayRouter HOP 360, free_point, spacing L/stations <= 405).
 (B) q_b000/q_b000__physical_v1/q_b011/q_b011__physical_v1:
     V1 internal stations with a reg in the W face strip (x < first core x) re-derived by the same rule with the core
        column + W strip as one keep-out, so the regs land in the E street (land next to the capture pin unchanged).
     V2 straight opposite-face crossings: an E<->W ft slot whose downstream neighbour is an ft slot (pass-through) gets
        out_window = in_window (no along-face leg in the type); the neighbour slot's in_window moves to the same die y
        (neighbours share orient group and origin y).  Skipped when the new window overlaps another window on either
        face (any layer) or the neighbour slot then needs more stations; bus-ended neighbours are listed, not changed.
 Contract: every ft slot keeps its station count and every internal station its reg count (a shorter generator chain
 is padded with a co-sited reg, the b2n spacing pad); a chain that needs MORE is recorded as a cycle delta.
usage: mk_chan_event.py BASE_PLAN OUT_DIR REPO"""
import bisect, copy, hashlib, json, math, os, sys
BASE, OUT, REPO = sys.argv[1:4]
sys.path.insert(0, os.path.join(REPO, "physical/die_plan/hbm_arch"))
sys.path.insert(0, os.path.join(REPO, "tools/die_plan"))
import schema as S  # noqa: E402
import check as CK  # noqa: E402
from cores_b2 import RelayRouter, free_point  # noqa: E402
BASE_SHA = "29333b2b19c992511d31720f0b80ae1c7fe4021036a59b0fd417f950b42162d1"
REACH, HOP = 405.0, 360.0
raw = open(BASE, "rb").read()
assert hashlib.sha256(raw).hexdigest() == BASE_SHA
plan = json.loads(raw)
base = json.loads(raw)
T = plan["partition_types"]
SU = ["q_su11", "q_su11__physical_v1", "q_su01", "q_su01__physical_v1"]
BT = ["q_b000", "q_b000__physical_v1", "q_b011", "q_b011__physical_v1"]
TAG = "HBM-CHANNELS hbm-channels-1111"
M, BM, G = 17.28, 20.0, 8.64   # core origins stay on the 8.64-um lattice (G0C)
snap = lambda v: round(round(v / G) * G, 3)
R3 = lambda p: [round(p[0], 3), round(p[1], 3)]
rep = dict(su={}, b={}, straight=[], straight_skipped=[], neighbour_types={}, cycle_delta=[], fails=[])


def pwl(pairs):
    xs = [a for a, _ in pairs]; ys = [b for _, b in pairs]
    def f(x):
        i = max(0, min(len(xs) - 2, bisect.bisect_right(xs, x) - 1))
        x0, x1, y0, y1 = xs[i], xs[i + 1], ys[i], ys[i + 1]
        return y0 if x1 == x0 else y0 + (x - x0) * (y1 - y0) / (x1 - x0)
    return f


def su_map(t, ST=120.0, RG=24.0, TOP=40.0):
    """mk_chan_su2.py map (pv_su3_120_24_40), returns X, Y, report"""
    W, H = t["outline_um"]; hc = t["hard_cores"]; bands = t.get("die_ft_bands") or []
    big = sorted({round(h["origin_um"][0], 2) for h in hc if h["outline_um"][0] > 300})
    cuts = []
    for s in big:
        if not cuts or s - cuts[-1] > 300: cuts.append(s)
    col = lambda h: max([i for i, s in enumerate(cuts) if h["origin_um"][0] + h["outline_um"][0] / 2 >= s] or [0])
    ext = {}
    for h in hc:
        c = col(h); a, b = h["origin_um"][0], h["origin_um"][0] + h["outline_um"][0]
        ext[c] = (min(a, ext.get(c, (a, b))[0]), max(b, ext.get(c, (a, b))[1]))
    # content leaves with a footprint (probe blockages, not hard cores) within JOIN um of a core column / row band
    # move rigidly with it (they are part of that block); farther ones stay fixed
    JOIN = 60.0
    hci = {h["inst"] for h in hc}
    cb = [c for c in probe_blockages(t) if c["inst"] not in hci]
    fixed_x1 = 0.0
    for c in cb:
        a, b = c["origin_um"][0], c["origin_um"][0] + c["outline_um"][0]
        near = [k for k, (e0, e1) in ext.items() if a < e1 + JOIN and b > e0 - JOIN]
        if near:
            k = min(near, key=lambda k: abs((a + b) / 2 - (ext[k][0] + ext[k][1]) / 2))
            ext[k] = (min(a, ext[k][0]), max(b, ext[k][1]))
        elif b < min(e0 for e0, _ in ext.values()):
            fixed_x1 = max(fixed_x1, b)          # a fixed leaf W of the array bounds how far column 0 may move
    cs = sorted(ext); widths = [ext[c][1] - ext[c][0] for c in cs]
    ns_hi = max([b["span_um"][1] for b in bands if b["dir"] == "NS" and b["span_um"][1] < ext[cs[0]][0]] or [0.0])
    ew_hi = max([b["span_um"][1] for b in bands if b["dir"] == "EW"] or [0.0])
    x_lo = max(M, ns_hi + BM, fixed_x1 + BM); x_hi = W - M
    nst = len(cs) - 1
    up = lambda v: round(math.ceil(v / G - 1e-9) * G, 3)
    dn = lambda v: round(math.floor(v / G + 1e-9) * G, 3)
    room_x = max(0.0, (x_hi - x_lo) - sum(widths)) / max(nst, 1)
    st = min(up(ST), dn(room_x))                   # street on the 8.64 lattice (120 -> 120.96 when it fits)
    total = sum(widths) + nst * st
    x0 = max(up(x_lo), min(ext[cs[0]][0], dn(x_hi - total)))
    newx = {}; cur = x0
    for c in cs:
        newx[c] = cur; cur = round(cur + (ext[c][1] - ext[c][0]) + st, 3)
    xp = [(0.0, 0.0), (x_lo, x_lo)] if x_lo < min(ext[cs[0]][0], newx[cs[0]]) else [(0.0, 0.0)]
    for c in cs:
        xp += [(ext[c][0], newx[c]), (ext[c][1], newx[c] + ext[c][1] - ext[c][0])]
    xp += [(W, W)]
    iv = sorted((h["origin_um"][1], h["origin_um"][1] + h["outline_um"][1]) for h in hc)
    for c in cb:
        a, b = c["origin_um"][1], c["origin_um"][1] + c["outline_um"][1]
        if any(a < y1 + JOIN and b > y0 - JOIN for y0, y1 in iv):
            iv.append((a, b))
    iv.sort()
    rb = []
    for a, b in iv:
        if rb and a <= rb[-1][1] + 1.0 and (b - a) < 150 and (rb[-1][1] - rb[-1][0]) < 150:
            rb[-1] = (rb[-1][0], max(b, rb[-1][1]))
        elif rb and a <= rb[-1][1] + 1e-3 and (b - a) < 150 and (rb[-1][1] - rb[-1][0]) >= 100 and abs(a - rb[-1][1]) < 1e-3:
            rb[-1] = (rb[-1][0], max(b, rb[-1][1]))
        elif rb and a < rb[-1][1] - 1e-3:
            rb[-1] = (rb[-1][0], max(b, rb[-1][1]))
        else:
            rb.append((a, b))
    y_floor = max(M, ew_hi + BM)
    k = len(rb) - 1
    room = rb[0][0] - y_floor
    top = min(TOP, max(0.0, room))
    add = min(RG, max(0.0, room - top) / max(k, 1)) if k else 0.0
    dy = [-round(math.floor((top + (k - i) * add) / G + 1e-9) * G, 3) for i in range(len(rb))]
    yp = [(0.0, 0.0), (y_floor, y_floor)] if y_floor < rb[0][0] + dy[0] else [(0.0, 0.0)]
    for (a, b), d in zip(rb, dy):
        yp += [(a, a + d), (b, b + d)]
    yp += [(H, H)]
    return pwl(xp), pwl(yp), dict(street_um=round(st, 2), col_x_old=[round(ext[c][0], 3) for c in cs],
                                  col_x_new=[newx[c] for c in cs], row_y_old=[round(a, 3) for a, _ in rb], row_dy=dy)


class FineRouter(RelayRouter):
    """cores_b2.RelayRouter (shortest-hop relay chain on free macro edges, every hop < limit) with the macro-edge
    candidate points sampled every `step` um instead of limit/3 (same rule, finer site grid)."""
    def __init__(self, boxes, W, H, limit=REACH - 1.0, margin=4.32, step=10.8):
        import numpy as np
        self.limit = limit
        pts = set()
        def add(x, y):
            if margin <= x <= W - margin and margin <= y <= H - margin and not any(
                bx - margin + 1e-6 < x < bx + bw + margin - 1e-6 and by - margin + 1e-6 < y < by + bh + margin - 1e-6
                for bx, by, bw, bh in boxes):
                pts.add((round(x, 4), round(y, 4)))
        def edge(a, b):
            n = max(1, math.ceil((abs(a[0] - b[0]) + abs(a[1] - b[1])) / step))
            for j in range(n + 1):
                add(a[0] + (b[0] - a[0]) * j / n, a[1] + (b[1] - a[1]) * j / n)
        for x, y, w, h in boxes + [(margin * 2, margin * 2, W - margin * 4, H - margin * 4)]:
            x0, y0, x1, y1 = max(margin, x - margin), max(margin, y - margin), min(W - margin, x + w + margin), min(H - margin, y + h + margin)
            for a, b in [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]:
                edge(a, b)
        self.points = sorted(pts)
        self.xy = np.asarray(self.points)
        self.near = lambda p: np.flatnonzero(np.abs(self.xy - p).sum(axis=1) < limit - 1e-5).tolist()
        self.neighbors = [self.near(p) for p in self.points]


_FR = {}


def fine_router(tn, t, extra=()):
    key = (tn, tuple(extra))
    if key not in _FR:
        w, h = t["outline_um"]
        _FR[key] = FineRouter(boxes_of(t) + list(extra), w, h)
    return _FR[key]


from placement_obstacles import probe_blockages  # noqa: E402
import die_hop_scan as DH  # noqa: E402


def boxes_of(t):
    """hard cores (b2n _boxes) + every obstacle check_ft_macro_sites uses (placed macros, probe blockages)"""
    bx = []
    for hc in t.get("hard_cores", []):
        dx, dy = hc.get("track_offset_um", [0.0, 0.0])
        bx.append((hc["origin_um"][0] + dx, hc["origin_um"][1] + dy, hc["outline_um"][0], hc["outline_um"][1]))
    seen = set(bx)
    for x0, y0, x1, y1 in S.placed_macro_boxes(t).values():
        b = (x0, y0, x1 - x0, y1 - y0)
        if b not in seen: bx.append(b); seen.add(b)
    for c in probe_blockages(t):
        b = (c["origin_um"][0], c["origin_um"][1], c["outline_um"][0], c["outline_um"][1])
        if b not in seen: bx.append(b); seen.add(b)
    return bx


def inside(p, bx, m=0.0):
    return any(x - m < p[0] < x + w + m and y - m < p[1] < y + h + m for x, y, w, h in bx)


def type_routes(P, want):
    out = {}
    for lid in P.lanes:
        for part, slot, a, b in P.lane_crossings(lid):
            if not slot:
                continue
            key = (P.parts[part]["type"], slot)
            if key in out or key not in want:
                continue
            s = P.slot(part, slot) or {}
            seg = CK.zroute(P.port_point(a), P.port_point(b), P.die_face(part, s.get("in_face", "W")),
                            P.die_face(part, s.get("out_face", "E")))
            out[key] = [P.to_type(part, q) for q in seg]
    return out


def at(path, d):
    for p, q in zip(path, path[1:]):
        L = abs(p[0] - q[0]) + abs(p[1] - q[1])
        if d <= L + 1e-9 and L > 0:
            f = d / L
            return (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)
        d -= L
    return tuple(path[-1])


def even_chain(path, k, t, first_at_start):
    """b2n count-kept form: k regs evenly spaced on the rectilinear path, each snapped off the macros (free_point);
    ft: the first reg at the in face (as _chain); internal: the last reg = the land next to the capture pin."""
    w, h = t["outline_um"]; bx = boxes_of(t)
    L = CK.plen(path)
    if first_at_start:
        pts = [at(path, L * i / k) for i in range(k)]
    else:
        pts = [at(path, L * i / k) for i in range(1, k)] + [tuple(path[-1])]
    return [free_point(p, bx, w, h) for p in pts]


def ft_chain(t, seg, k0=None):
    w, h = t["outline_um"]; bx = boxes_of(t)
    first = free_point(seg[0], bx, w, h)
    L = CK.plen(seg)
    best = None
    for lim in (HOP, REACH - 1.0):
        try:
            regs = [first] + RelayRouter(bx, w, h, lim)(first, seg[-1])
        except ValueError:
            continue
        while L / len(regs) > REACH:
            regs.append(regs[-1])
        if best is None or len(regs) < len(best):
            best = regs
    if k0 and (best is None or len(best) > k0):
        try:
            fr = FineRouter(bx, w, h)
            regs = [first] + fr(first, seg[-1])
            while L / len(regs) > REACH:
                regs.append(regs[-1])
            if best is None or len(regs) < len(best):
                best = regs; rep.setdefault("fine_ft", []).append(len(regs))
        except ValueError:
            pass
    if k0 and (best is None or len(best) > k0) and L / k0 <= REACH:
        ev = even_chain(seg, k0, t, True)
        if CK._hops_ok(seg[0], ev, seg[-1], REACH) and not any(inside(q, bx) for q in ev):
            best = ev
            rep.setdefault("even_ft", []).append(len(ev))
    if best is None:
        raise ValueError("no chain")
    return best


_LB = {}
_SB = {}
# (F, optional) lanes cleaned end to end: every hop of the listed lanes within reach in the re-stationed slots
FORCE_STRICT = set(x for x in os.environ.get("CHAN_STRICT_LANES", "").split(",") if x)
EXTRA_SLOTS = set(tuple(x.split(":")) for x in os.environ.get("CHAN_EXTRA_SLOTS", "").split(",") if x)
# (F) rev 3 (DIE-HBM-98 11-11): extra slots re-stationed strictly (every hop <= reach), lane-wide strict not required
STRICT_SLOTS = set(EXTRA_SLOTS)


def lane_max(P, lid):
    geo = CK.lane_geometry(P, lid)
    h = CK.lane_pin_hops(P, lid, geo[1])
    return max(h) if h else 0.0


def slot_hops(P, lid, tn, sn):
    """pin hops of lane lid that touch slot (tn, sn): (interior hops, boundary hops in, out) per crossing"""
    geo = CK.lane_geometry(P, lid); hops = CK.lane_pin_hops(P, lid, geo[1])
    out, idx, touch = [], 1, set()
    for part, slot, a, b in P.lane_crossings(lid):
        n = int((P.slot(part, slot) or {}).get("stations", 1))
        if slot == sn and P.parts[part]["type"] == tn:
            seg = hops[idx - 1: idx + n]
            out.append((seg[1:-1], seg[0], seg[-1]))
            touch |= set(range(idx - 1, idx + n))
        idx += n
    outside = max((h for i, h in enumerate(hops) if i not in touch), default=0.0)
    return [(a, b, c, outside) for a, b, c in out]


def slot_ok(P, tn, sl, lanes, base_lane, base_slot_hops=None):
    """the G0 checks on one slot (check_hops R3 + first input hop, check_ft_macro_sites centres, lane pin hops):
    no new violation against the base plan"""
    t = P.types[tn]; bx = boxes_of(t)
    k = int(sl.get("stations", 1))
    first = DH.first_internal_hops(P, tn, sl, pins=DH.pin_table(P, tn))
    f = max((d for _, d in first), default=0.0)
    if f > REACH + 1e-6:
        return False, f"first input hop {f:.0f}"
    normal = DH.normal_slot(P, tn, sl["name"])
    for j, q in enumerate(sl["regs_um"]):
        if j == 0 and normal:
            continue
        if inside(q, bx, -1e-3):
            return False, f"reg {j} in macro"
    for lid in lanes:
        h = lane_max(P, lid)
        if h > max(P.reach, base_lane.get(lid, 0.0)) + 1e-6:
            return False, f"lane {lid} hop {h:.0f}"
        # HBM-COMPOSE 11-11 (DIE-HBM-98): every hop inside this slot within reach (registered stages, no squeeze);
        # the two boundary hops within reach or not worse than the same boundary hop in the base
        # strict (<= reach) when the base lane is clean outside this slot; when the base lane already fails outside it
        # (L8007/L8008: other partitions' pre-existing hops), no in-slot hop may be worse than the base slot's worst
        bb = (base_slot_hops or {}).get((lid, tn, sl["name"]), [])
        for i, (inner, hin, hout, _o) in enumerate(slot_hops(P, lid, tn, sl["name"])):
            if i < len(bb):
                b_inner, b_in, b_out, b_out_side = bb[i]
                strict = lid in FORCE_STRICT or (tn, sl["name"]) in STRICT_SLOTS
                lim = P.reach if (b_out_side <= P.reach + 1e-6 or strict) else max(P.reach, max(list(b_inner) + [b_in, b_out]))
                if strict: b_in = b_out = 0.0
            else:
                b_in = b_out = 0.0; lim = P.reach
            if any(x > lim + 1e-6 for x in inner):
                return False, f"lane {lid} slot hop {max(inner):.0f} > {lim:.0f}"
            if hin > max(lim, b_in) + 1e-6 or hout > max(lim, b_out) + 1e-6:
                return False, f"lane {lid} boundary hop {max(hin, hout):.0f}"
    return True, ""


def slot_candidates(t, seg, k0):
    w, h = t["outline_um"]; bx = boxes_of(t)
    L = CK.plen(seg)
    first = free_point(seg[0], bx, w, h)
    seen = []
    def emit(regs):
        regs = list(regs)
        while L / len(regs) > REACH:
            regs.append(regs[-1])
        key = tuple((round(a, 2), round(b, 2)) for a, b in regs)
        if key not in seen:
            seen.append(key); return [regs]
        return []
    out = []
    for lim in (HOP, 300.0, 240.0, 180.0):          # b2n rule chain (shortest-hop relays on free macro edges)
        for R_ in (RelayRouter(bx, w, h, lim), FineRouter(bx, w, h, lim)):
            try:
                ch = [first] + R_(first, seg[-1])
                out += emit(ch)
                if len(ch) >= 2:   # +1 registered stage between S0 and S1 (first input hop), placed free
                    m = ((ch[0][0] + ch[1][0]) / 2, (ch[0][1] + ch[1][1]) / 2)
                    out += emit([ch[0], free_point(m, bx, w, h)] + ch[1:])
            except ValueError:
                pass
    for k in range(max(1, k0), k0 + 4):              # count-kept, then +1.. (cycle delta) even chains
        out += emit(even_chain(seg, k, t, True))
    # fewest stations first (ties: rule chains first, in order)
    return sorted(out, key=lambda r: max(len(r), k0))


def restation_slots(P, want, note, commit=True):
    """generator rule on the (type, slot) set; keep counts (pad); every candidate checked with the G0 slot checks;
    returns {(type,slot): (n_base, n_new, regs)}"""
    routes = type_routes(P, want)
    lanes_of = {}
    for lid in P.lanes:
        for part, slot, a, b in P.lane_crossings(lid):
            if slot and (P.parts[part]["type"], slot) in want:
                lanes_of.setdefault((P.parts[part]["type"], slot), set()).add(lid)
    res = {}
    for (tn, sn) in sorted(want):
        t = P.types[tn]
        sl = next(s for s in t["ft_slots"] if s["name"] == sn)
        seg = routes.get((tn, sn))
        if not seg:
            rep["fails"].append(f"{tn}.{sn}: no lane route"); continue
        n0 = BASE_N.get((tn, sn), int(sl.get("stations", 1)))
        lanes = sorted(lanes_of.get((tn, sn), ()))
        for lid in lanes:
            if lid not in _LB:
                _LB[lid] = lane_max(PB, lid)
            if (lid, tn, sn) not in _SB:
                _SB[(lid, tn, sn)] = slot_hops(PB, lid, tn, sn)
        keep = (copy.deepcopy(sl.get("regs_um")), sl.get("stations"), sl.get("bit_sites_um"), sl.get("bit_site_cell_um"))
        sl.pop("bit_sites_um", None); sl.pop("bit_site_cell_um", None)
        chosen, why = None, []
        for regs in slot_candidates(t, seg, n0):
            regs = list(regs)
            while len(regs) < n0:
                regs.append(regs[-1])
            sl["regs_um"] = [R3(p) for p in regs]; sl["stations"] = len(regs)
            ok, w_ = slot_ok(P, tn, sl, lanes, _LB, _SB)
            if ok:
                chosen = regs; break
            why.append(f"{len(regs)}:{w_}")
        if chosen is None:
            rep["fails"].append(f"{tn}.{sn}: no candidate passes ({why[:4]})")
            chosen = None
        if not commit or chosen is None:
            sl["regs_um"], sl["stations"] = keep[0], keep[1]
            if keep[2] is not None: sl["bit_sites_um"] = keep[2]
            if keep[3] is not None: sl["bit_site_cell_um"] = keep[3]
            if chosen is not None:
                res[(tn, sn)] = (n0, len(chosen), chosen)
            continue
        if len(chosen) > n0:
            rep.setdefault("why", {})[tn + "." + sn] = why[:16]
        res[(tn, sn)] = (n0, len(chosen), chosen)
        sl["note"] = sl.get("note", "").split(" | HBM-CHANNELS")[0] + f" | {note}"
    return res


def restation_ist(tn, t, pick, block=None):
    """internal stations in `pick` re-derived (b2n rule); block = extra router keep-out box (x, y, w, h)"""
    w, h = t["outline_um"]; bx = boxes_of(t)
    routers = [RelayRouter(bx + ([tuple(block[:4])] if block else []), w, h, HOP)]
    if block:
        routers.append(RelayRouter(bx, w, h, HOP))
    routers.append(RelayRouter(bx, w, h, REACH - 1.0))
    n0 = n1 = changed = up = blocked_ok = 0
    for e in t.get("internal_stations", []):
        if not pick(e):
            continue
        a, b = tuple(e["from_um"]), tuple(e["to_um"])
        land = free_point(b, bx, w, h)
        regs = None
        # b2n rule: HOP-360 router, REACH-1 router as its fallback; the shortest chain of the two (fewest regs)
        cands = []
        for i, r in enumerate(routers):
            try:
                c = list(r(a, land))
                if not c or abs(c[-1][0] - land[0]) + abs(c[-1][1] - land[1]) > 1.0:
                    c.append(land)
                cands.append((len(c), i, c))
            except ValueError as ex:
                err = ex
        if block:
            pb = [c for c in cands if c[1] == 0]
            if pb and pb[0][0] <= len(e["regs_um"]):
                cands = pb
            elif any(c[1] != 0 for c in cands):
                cands = [c for c in cands if c[1] != 0]
        if cands:
            n_, i_, regs = min(cands)
            if block and i_ == 0: blocked_ok += 1
        k0 = len(e["regs_um"])
        if regs is None or len(regs) > k0:
            for ex in (([tuple(block[:4])],) if block else ()) + ((),):
                try:
                    c = list(fine_router(tn, t, ex)(a, land))
                    if not c or abs(c[-1][0] - land[0]) + abs(c[-1][1] - land[1]) > 1.0:
                        c.append(land)
                    if CK._hops_ok(a, c, b, REACH) and (regs is None or len(c) < len(regs)):
                        regs = c; rep.setdefault("fine_ist", []).append(tn)
                        if len(c) <= k0: break
                except ValueError:
                    pass
        if regs is None or len(regs) > k0 or (block and any(q[0] < block[2] for q in regs[:-1])):
            # count-kept form on the rectilinear path (via the E street for the b types)
            paths = ([[a, (xs, a[1]), (xs, land[1]), land] for xs in block[4]] if block else
                     [[a, (land[0], a[1]), land], [a, (a[0], land[1]), land]])
            done = False
            for pth in paths:
                for mode in ("land", "mid"):
                    if mode == "land":
                        ev = even_chain(pth, k0, t, False)
                    else:   # k0 regs at L*i/(k0+1) on the path a -> b (no forced land reg)
                        pth2 = pth[:-1] + [b]
                        L2 = CK.plen(pth2)
                        ev = [free_point(at(pth2, L2 * i / (k0 + 1)), bx, t["outline_um"][0], t["outline_um"][1])
                              for i in range(1, k0 + 1)]
                    if CK._hops_ok(a, ev, b, REACH) and not any(inside(q, bx) for q in ev) and \
                            not (block and any(q[0] < block[2] for q in ev[:-1])):
                        regs = ev; rep.setdefault("even_ist", []).append(tn); done = True; break
                if done:
                    break
        if regs is None:
            rep["fails"].append(f"{tn} internal {e.get('conn')}: {err}"); continue
        regs = list(regs)
        if not CK._hops_ok(a, regs, b, REACH):
            rep["fails"].append(f"{tn} internal {e.get('conn')}: hop > 405 after re-stationing")
        if len(regs) > k0:
            up += 1
            rep["cycle_delta"].append(dict(type=tn, internal=e.get("conn"), regs_base=k0, regs_new=len(regs),
                                           bits=e.get("bits")))
        while len(regs) < k0:
            regs.append(regs[-1])
        n0 += k0; n1 += len(regs); changed += 1
        e["regs_um"] = [R3(p) for p in regs]
        e["note"] = e.get("note", "").split(" | HBM-CHANNELS")[0] + \
            f" | {TAG}: re-derived (b2n rule, hops <= 405 um{', E street' if block else ''}), count kept"
    return dict(links=changed, regs_base=n0, regs_new=n1, links_up=up, blocked_route_ok=blocked_ok)


PB = S.Plan(copy.deepcopy(base))
BASE_N = {(tn, sl["name"]): int(sl.get("stations", 1)) for tn, t in base["partition_types"].items() for sl in t.get("ft_slots", [])}
# ---------------------------------------------------------------- (A) SU-CHAN
for tn in SU:
    t = T[tn]
    X, Y, r = su_map(t)
    for hc in t["hard_cores"]:
        hc["origin_um"] = R3((X(hc["origin_um"][0]), Y(hc["origin_um"][1])))
        hc["note"] = hc.get("note", "") + f" | {TAG}: SU-CHAN core move (two 120 um V streets, rows +24/+40 um)"
    for c in t.get("contents", []):
        if "origin_um" in c and "outline_um" in c:
            x0_, y0_ = c["origin_um"]; w_, h_ = c["outline_um"]
            # rigid: the shift of the box centre (inside its block the map is a pure shift)
            cx, cy = x0_ + w_ / 2, y0_ + h_ / 2
            c["origin_um"] = R3((x0_ + X(cx) - cx, y0_ + Y(cy) - cy))
    for tp in t.get("clock", {}).get("taps", []):
        if "xy" in tp:
            tp["xy"] = R3((X(tp["xy"][0]), Y(tp["xy"][1])))
    for e in t.get("internal_stations", []):
        e["from_um"] = R3((X(e["from_um"][0]), Y(e["from_um"][1])))
        e["to_um"] = R3((X(e["to_um"][0]), Y(e["to_um"][1])))
    bx = boxes_of(t)
    W, H = t["outline_um"]
    for key in ("clock", "reset"):
        tu = t.get(key, {}).get("tap_um")
        if tu and inside(tu, bx):
            t[key]["tap_um"] = R3(free_point(tuple(tu), bx, W, H))
            r[f"{key}_tap_moved"] = t[key]["tap_um"]
    def geom_bad(t):
        bad = []
        hc_ = t["hard_cores"]; hci_ = {h["inst"] for h in hc_}
        R_ = [(h["inst"], h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]) for h in hc_]
        R_ += [(c["inst"], c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1])
               for c in probe_blockages(t) if c["inst"] not in hci_]
        W_, H_ = t["outline_um"]
        for (nm, a, b, c, d) in R_:
            if a < M - 1e-6 or b < M - 1e-6 or c > W_ - M + 1e-6 or d > H_ - M + 1e-6: bad.append(("outline", nm))
            for bd in t.get("die_ft_bands") or []:
                lo, hi = bd["span_um"]
                if bd["dir"] == "NS" and a < hi + BM - 1e-6 and c > lo - BM + 1e-6: bad.append(("NSband", nm))
                if bd["dir"] == "EW" and b < hi + BM - 1e-6 and d > lo - BM + 1e-6: bad.append(("EWband", nm))
        for i, p_ in enumerate(R_):
            for q in R_[i + 1:]:
                if p_[1] < q[3] - 1e-6 and q[1] < p_[3] - 1e-6 and p_[2] < q[4] - 1e-6 and q[2] < p_[4] - 1e-6: bad.append(("overlap", p_[0], q[0]))
        return bad
    r["geom_errors"] = sorted(set(geom_bad(t)) - set(geom_bad(base["partition_types"][tn])))
    r["geom_preexisting"] = geom_bad(base["partition_types"][tn])
    bad = []
    hc_ = t["hard_cores"]
    R_ = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]) for h in hc_]
    R_ += [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1])
           for c in probe_blockages(t) if c["inst"] not in {h["inst"] for h in hc_}]
    r["lattice_off"] = sum(1 for h in hc_ for v in h["origin_um"] if abs(v / 8.64 - round(v / 8.64)) > 1e-6)
    for (a, b, c, d) in R_:
        if a < M - 1e-6 or b < M - 1e-6 or c > W - M + 1e-6 or d > H - M + 1e-6: bad.append("outline")
        for bd in t.get("die_ft_bands") or []:
            lo, hi = bd["span_um"]
            if bd["dir"] == "NS" and a < hi + BM - 1e-6 and c > lo - BM + 1e-6: bad.append("NSband")
            if bd["dir"] == "EW" and b < hi + BM - 1e-6 and d > lo - BM + 1e-6: bad.append("EWband")
    for i, p in enumerate(R_):
        for q in R_[i + 1:]:
            if p[0] < q[2] - 1e-6 and q[0] < p[2] - 1e-6 and p[1] < q[3] - 1e-6 and q[1] < p[3] - 1e-6: bad.append("overlap")
    rep["su"][tn] = r

# ---------------------------------------------------------------- (B) V2 straight crossings
parts = {p["name"]: p for p in plan["partitions"]}
inst_of = {}
for p in plan["partitions"]:
    inst_of.setdefault(p["type"], []).append(p["name"])
by_src = {}
for pr in plan["ports"]:
    by_src.setdefault((pr["src"]["part"], pr["src"]["bus"]), []).append(pr)


def face_windows(t, face, skip=None):
    out = []
    for s in t.get("ft_slots", []):
        for fk, wk in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
            if s.get(fk) == face and wk in s and (s["name"], wk) != skip:
                out.append((s[wk][0], s[wk][1], f"{s['name']}.{wk[:-10]}"))
    for b in t.get("buses", []):
        if b.get("face") == face and "window_um" in b:
            out.append((b["window_um"][0], b["window_um"][1], b["name"]))
    return out


def overl(win, ws):
    return [n for a, b, n in ws if win[0] < b - 0.01 and a < win[1] - 0.01]


P0 = S.Plan(copy.deepcopy(plan))
cand = []
for tn in BT:
    assert len(inst_of[tn]) == 1
    part = inst_of[tn][0]
    for s in T[tn]["ft_slots"]:
        if {s["in_face"], s["out_face"]} != {"E", "W"} or abs(s["in_window_um"][0] - s["out_window_um"][0]) < 0.5:
            continue
        for pr in by_src.get((part, s["name"] + "_o"), []):
            d = pr["dst"]
            nt = parts[d["part"]]["type"] if d["part"] in parts else None
            ns = next((x for x in T[nt].get("ft_slots", []) if d["bus"] == x["name"] + "_i"), None) if nt else None
            cand.append((s["width"], tn, part, s["name"], d["part"], nt, ns["name"] if ns else None, d["bus"]))
cand.sort(key=lambda c: -c[0])
for wdt, tn, part, sn, npart, nt, nsn, nbus in cand:
    s = next(x for x in T[tn]["ft_slots"] if x["name"] == sn)
    row = dict(type=tn, part=part, slot=sn, width=wdt, face=f"{s['in_face']}->{s['out_face']}",
               offset_um=round(s["in_window_um"][0] - s["out_window_um"][0], 3), neighbour=npart, neighbour_type=nt,
               neighbour_bus=nbus)
    if nsn is None:
        rep["straight_skipped"].append(dict(row, why="neighbour end is a bus, not an ft slot (bus pin move not in scope)"))
        continue
    if len(inst_of[nt]) != 1:
        rep["straight_skipped"].append(dict(row, why="neighbour type has >1 instance")); continue
    pa, pb = parts[part], parts[npart]
    if abs(pa["origin_um"][1] - pb["origin_um"][1]) > 1e-6 or \
            (pa.get("orient", "R0") in ("MX", "R180")) != (pb.get("orient", "R0") in ("MX", "R180")):
        rep["straight_skipped"].append(dict(row, why="neighbour y frame differs")); continue
    nsl = next(x for x in T[nt]["ft_slots"] if x["name"] == nsn)
    new = list(s["in_window_um"])
    # the neighbour's in face (type frame) for the abutting face
    ov1 = overl(new, face_windows(T[tn], s["out_face"], skip=(sn, "out_window_um")))
    ov2 = overl(new, face_windows(T[nt], nsl["in_face"], skip=(nsn, "in_window_um")))
    if ov1 or ov2:
        rep["straight_skipped"].append(dict(row, why=f"window overlap own {ov1[:3]} neighbour {ov2[:3]}")); continue
    old_o, old_n = list(s["out_window_um"]), list(nsl["in_window_um"])
    assert abs(old_o[0] - old_n[0]) < 0.01 and abs(old_o[1] - old_n[1]) < 0.01, (tn, sn, old_o, nt, nsn, old_n)
    s["out_window_um"] = new; nsl["in_window_um"] = list(new)
    Pt = S.Plan(plan)
    nf = len(rep["fails"])
    res = restation_slots(Pt, {(tn, sn), (nt, nsn)}, "", commit=False)
    del rep["fails"][nf:]
    if (nt, nsn) not in res or (tn, sn) not in res or res[(nt, nsn)][1] > res[(nt, nsn)][0] or res[(tn, sn)][1] > res[(tn, sn)][0]:
        s["out_window_um"] = old_o; nsl["in_window_um"] = old_n
        why = "neighbour/own chain needs more stations" if (nt, nsn) in res else "no route"
        rep["straight_skipped"].append(dict(row, why=why,
                                            stations={f"{k[0]}.{k[1]}": v[:2] for k, v in res.items()})); continue
    rep["straight"].append(dict(row, neighbour_slot=nsn, window_old=old_o, window_new=new,
                                stations={f"{k[0]}.{k[1]}": [v[0], v[1]] for k, v in res.items()}))
    rep["neighbour_types"].setdefault(nt, []).append(dict(slot=nsn, in_window_old=old_n, in_window_new=new))

# ---------------------------------------------------------------- generator-rule re-stationing
P1 = S.Plan(plan)
want = {(tn, s["name"]) for tn in SU for s in T[tn].get("ft_slots", [])}
want |= {(r["type"], r["slot"]) for r in rep["straight"]} | {(r["neighbour_type"], r["neighbour_slot"]) for r in rep["straight"]}
want |= EXTRA_SLOTS
res = restation_slots(P1, want, f"{TAG}: regs re-derived (b2n rule, HOP 360), count kept")
for (tn, sn), (n0, n1, _) in res.items():
    if n1 > n0:
        rep["cycle_delta"].append(dict(type=tn, slot=sn, stations_base=n0, stations_rule=n1))
rep["ft_restation"] = {f"{k[0]}.{k[1]}": [v[0], v[1]] for k, v in sorted(res.items())}
for tn in SU:
    rep["su"][tn]["ist"] = restation_ist(tn, T[tn], lambda e: True)
for tn in BT:
    t = T[tn]
    x0 = min(h["origin_um"][0] for h in t["hard_cores"])
    x1 = max(h["origin_um"][0] + h["outline_um"][0] for h in t["hard_cores"])
    strip = lambda e, x0=x0: any(r[0] < x0 - 1e-6 for r in e["regs_um"])
    n_strip = sum(1 for e in t.get("internal_stations", []) if strip(e))
    rb0 = sum(len(e["regs_um"]) * int(e.get("bits", 1)) for e in t.get("internal_stations", []) if strip(e))
    Wt = t["outline_um"][0]
    xs = [round((x1 + Wt) / 2, 3), round(x1 + 8.64, 3), round(Wt - 8.64, 3)]
    r = restation_ist(tn, t, strip, block=(0.0, 0.0, x1, t["outline_um"][1], xs))
    left = sum(1 for e in t.get("internal_stations", []) for q in e["regs_um"] if q[0] < x0 - 1e-6)
    rep["b"][tn] = dict(r, strip_links=n_strip, strip_reg_bits=rb0, regs_left_in_w_strip=left,
                        street_x=[round(x1 + 4.32, 3), round(t["outline_um"][0] - 4.32, 3)])

# ---------------------------------------------------------------- (F) rev 3: L8008 su11pv1 hand siting (DIE-HBM-98 11-11)
# The b2n router zig-zags L8008x2 between y 786 (inside the plain p3 band) and y 885.6 (the 17-um channel between the
# plain p3 tops 881.28 and the exp row 898.56), leaving three 436-um hops. Same 7 stations, re-sited on one line:
# reg0 stays at the E pin row, regs 1-4 run on the y 885.6 channel, reg5/reg6 drop to the pin row W of the plain block
# (x < 760.32). Lattice 4.32 um; every hop <= 372 um, first input hop (S0->S1) <= 405 (checked below).
if "q_su11__physical_v1" in T:
    sl = next(x for x in T["q_su11__physical_v1"]["ft_slots"] if x["name"] == "L8008x2")
    r0 = sl["regs_um"][0]
    assert int(sl["stations"]) == 7 and abs(r0[0] - 2354.4) < 1e-6, (sl["stations"], r0)
    old = [list(q) for q in sl["regs_um"]]
    yc, yp = 885.6, r0[1]
    sl["regs_um"] = [list(r0), [2095.2, yc], [1723.68, yc], [1352.16, yc], [980.64, yc], [708.48, yp], [336.96, yp]]
    sl["note"] = (sl.get("note", "") + f" | {TAG} rev3: L8008x2 hand-sited on one line (7 stations kept, hops <= 372 um)").lstrip(" |")
    P3 = S.Plan(plan); tb = P3.types["q_su11__physical_v1"]; bxx = boxes_of(tb)
    assert not any(inside(q, bxx, -1e-3) for q in sl["regs_um"][1:]), "L8008x2 reg in macro"
    fh = max((d for _, d in DH.first_internal_hops(P3, "q_su11__physical_v1", sl, pins=DH.pin_table(P3, "q_su11__physical_v1"))), default=0.0)
    assert fh <= REACH + 1e-6, fh
    lm = lane_max(P3, "L8008")
    rep["l8008_su11pv1_hand"] = dict(old=old, new=sl["regs_um"], first_input_hop=round(fh, 1), lane_L8008_max_hop=round(lm, 1))

# ---------------------------------------------------------------- (C) kv_line south grow (DIE-HBM-98 ruling 11-11)
KV_OLD, KV_NEW, KV_Y = [734.4, 233.28], [734.4, 388.8], 1848.96
KV_PINS = "cores/ot_hbm_sm_kv_line__734.4x388.8__kvs1111.json"
BASEDIR = os.path.dirname(os.path.abspath(BASE))
kv_rep = dict(types=[], pins_file=KV_PINS)
dh = KV_NEW[1] - KV_OLD[1]
for tn in ("q_sm0", "q_sm1", "q_sm2", "q_sm3"):
    t = T[tn]
    hc = [h for h in t["hard_cores"] if h["inst"] == "u_sm_front_kv"]
    assert len(hc) == 1 and hc[0]["outline_um"] == KV_OLD and hc[0]["module"] == "ot_hbm_sm_kv_line", tn
    h = hc[0]
    x0, y0 = h["origin_um"]
    assert abs(y0 - dh - KV_Y) < 1e-6, (tn, y0)
    # slot check: nothing (core, content leaf, ft reg, station reg, band) in the grown strip + 17.28 um clearance
    strip = (x0, KV_Y - 17.28, x0 + KV_NEW[0], y0)
    hits = [c["inst"] for c in probe_blockages(t) if c["inst"] != h["inst"] and c["origin_um"][0] < strip[2] - 1e-6
            and c["origin_um"][0] + c["outline_um"][0] > strip[0] + 1e-6 and c["origin_um"][1] < strip[3] - 1e-6
            and c["origin_um"][1] + c["outline_um"][1] > strip[1] + 1e-6]
    regs = [s["name"] for s in t.get("ft_slots", []) for q in s.get("regs_um", []) if strip[0] <= q[0] <= strip[2] and KV_Y <= q[1] <= y0]
    regs += [e["conn"] for e in t.get("internal_stations", []) for q in e["regs_um"] if strip[0] <= q[0] <= strip[2] and KV_Y <= q[1] <= y0]
    bands = [b["span_um"] for b in t.get("die_ft_bands", []) if b["dir"] == "EW" and b["span_um"][0] < y0 and b["span_um"][1] > KV_Y]
    assert not hits and not regs and not bands, (tn, hits, regs, bands)
    h["origin_um"] = [x0, KV_Y]; h["outline_um"] = list(KV_NEW); h["pins_file"] = KV_PINS
    h["note"] = h.get("note", "") + " | DIE-HBM-98 11-11 kvline-floorplan ruling (HBM-CHANNELS event): outline grows south only 734.4x233.28 -> 734.4x388.8, origin y 2004.48 -> 1848.96; W/E/N faces fixed"
    for c in t.get("contents", []):
        if c["inst"] == "u_sm_front_kv" and "outline_um" in c:
            c["origin_um"] = [x0, KV_Y]; c["outline_um"] = list(KV_NEW)
    kv_rep["types"].append(dict(type=tn, origin_old=[x0, y0], origin_new=[x0, KV_Y], slot_check="clear (cores/leaves/ft/stations/bands, 17.28 um S clearance)"))
pins = json.load(open(os.path.join(BASEDIR, "cores/ot_hbm_sm_kv_line__734.4x233.28__smab1108.json")))
W0, H0 = KV_OLD
npins, faces = [], {}
for q in pins:
    q = dict(q); x, y = q["x"], q["y"]
    f = "W" if abs(x) < 1 else "E" if abs(x - W0) < 1 else "S" if abs(y) < 1 else "N" if abs(y - H0) < 1 else "I"
    faces[f] = faces.get(f, 0) + 1
    if f != "S":
        q["y"] = round(y + dh, 3)      # N / E / W / interior clock pin keep their die position; S face moves south
    npins.append(q)
kv_rep["pins_by_face"] = faces
os.makedirs(os.path.join(OUT, "cores"), exist_ok=True)
json.dump(npins, open(os.path.join(OUT, KV_PINS), "w"))
ce = json.load(open(os.path.join(BASEDIR, "clock_entries.json")))
for tn in ("q_sm0", "q_sm1", "q_sm2", "q_sm3"):
    e = ce[tn]["u_sm_front_kv"]
    e["xy_um"] = [e["xy_um"][0], round(e["xy_um"][1] + dh, 3)]
    e["island_um"] = [e["island_um"][0], round(e["island_um"][1] + dh, 3), e["island_um"][2], round(e["island_um"][3] + dh, 3)]
    e["source"] = e.get("source", "") + " | kvs1111: same die point on the 734.4x388.8 outline (+155.52 local y)"
json.dump(ce, open(os.path.join(OUT, "clock_entries.json"), "w"), indent=1)
rep["kv_line"] = kv_rep

# ---------------------------------------------------------------- (D) q_mcb split (DIE-HBM-98 ruling 11-11, COORD fail_watch)
# q_mcb has 2 instances with different S_u_refcfg_Q_tgt (NE 8b10000001, NW 8b01111111): kit-rtl cannot kit a
# per-instance-parameterised type.  Split into single-instance types q_mcb_ne (NE_mcb) / q_mcb_nw (NW_mcb); each is
# json-equal to q_mcb except the module name (hbm_arch_<type>); only the instance-to-type map changes.
assert "q_mcb_ne" not in T and "q_mcb_nw" not in T
mparts = sorted(x["name"] for x in plan["partitions"] if x["type"] == "q_mcb")
assert mparts == ["NE_mcb", "NW_mcb"], mparts
qm = T.pop("q_mcb"); assert qm["module"] == "hbm_arch_q_mcb"
for tn in ("q_mcb_ne", "q_mcb_nw"):
    T[tn] = copy.deepcopy(qm); T[tn]["module"] = "hbm_arch_" + tn
    T[tn]["note"] = (qm.get("note", "") + " | " if qm.get("note") else "") +         "hbm-channels-1111 (D): split of q_mcb (per-instance S_u_refcfg_Q_tgt), json-equal except module"
for x in plan["partitions"]:
    if x["type"] == "q_mcb": x["type"] = "q_mcb_ne" if x["name"] == "NE_mcb" else "q_mcb_nw"
assert "q_mcb" not in json.dumps(plan["partitions"]) .replace("q_mcb_ne", "").replace("q_mcb_nw", "")
rep["mcb_split"] = dict(old_type="q_mcb", new_types={"q_mcb_ne": "NE_mcb", "q_mcb_nw": "NW_mcb"},
                        param="S_u_refcfg_Q_tgt (NE 8b10000001, NW 8b01111111) -> u_refcfg_Q.tgt")

# ---------------------------------------------------------------- (E) root tkm reset source text (DIE-HBM-98 11-11, note only)
RT = [h for h in T["root"]["hard_cores"] if h["inst"] == "u_tkm_SW_root"]
assert len(RT) == 1 and RT[0]["module"] == "ot_hgi_coll_tkm_m_tp192__root"
rfm = RT[0]["reset_from_master"]; assert "static_p" in rfm["source"] and rfm["pin"] == "rst_n", rfm
rep["root_reset_source"] = dict(old=rfm["source"])
rfm["source"] = ("ot_hgi_coll_tkm_m_tp192__root = rest_extract_mem.sh part 19 extraction of ot_hgi_coll_tkm_m_tp192_pfdh32 "
                 "(static_pdh, PTILE 32) minus the 64 half-tile cells (BIND-SUBTYPE-2); u.rst_n -> root flops + u_buffer, "
                 "tiles reset-free.  Replaces the 10-23 static_p extraction citation (hbm-channels-1111 (E), note only)")
rep["root_reset_source"]["new"] = rfm["source"]

# ---------------------------------------------------------------- native internal-station lanes: fixed_cycles follows the
# source station count (bind native_istations.annotate: fixed_cycles == source regs + destination regs)
rep["fixed_cycles_changed"] = {}
LN = {x["id"]: x for x in plan["lanes"]}
for d in rep["cycle_delta"]:
    if "internal" not in d: continue
    nm = d["internal"][4:]; assert nm.endswith("_o"), d
    lid = nm[:-2]; ln = LN[lid]
    assert int(ln.get("fixed_cycles", 0)) == d["regs_base"], (lid, ln.get("fixed_cycles"), d)
    ln["fixed_cycles"] = d["regs_new"]
    ln["note"] = ln.get("note", "") + f" | hbm-channels-1111: fixed_cycles {d["regs_base"]} -> {d["regs_new"]} (q_su01__physical_v1 SU-CHAN internal stations)"
    rep["fixed_cycles_changed"][lid] = [d["regs_base"], d["regs_new"]]

# ---------------------------------------------------------------- latency, checks, write
P2 = S.Plan(plan)
Pb = S.Plan(copy.deepcopy(base))
lat = {lid: P2.lane_latency(lid) for lid in P2.lanes}
latb = {lid: Pb.lane_latency(lid) for lid in Pb.lanes}
dc = {lid: lat[lid]["cycles"] - latb[lid]["cycles"] for lid in latb}
for lid, v in dc.items():
    if v:
        plan["latency"]["lanes"][lid] = dict(plan["latency"]["lanes"].get(lid, {}), **lat[lid])   # keep param etc.
rep["lane_cycles_changed"] = {k: v for k, v in dc.items() if v}
rep["stored_latency_stale_in_base"] = sum(1 for lid in latb if base["latency"]["lanes"].get(lid, {}).get("cycles") != latb[lid]["cycles"])
# off-core / hop audit on every touched type
aud = {}
for tn in sorted(set(SU) | set(BT) | set(rep["neighbour_types"])):
    t = T[tn]; bx = boxes_of(t)
    ft_in = sum(1 for s in t.get("ft_slots", []) for q in s.get("regs_um", []) if inside(q, bx))
    ist_in = sum(1 for e in t.get("internal_stations", []) for q in e["regs_um"] if inside(q, bx))
    ist_hop = sum(1 for e in t.get("internal_stations", []) if not CK._hops_ok(e["from_um"], e["regs_um"], e["to_um"], REACH))
    aud[tn] = dict(ft_regs_in_core=ft_in, ist_regs_in_core=ist_in, ist_links_hop_gt_405=ist_hop)
rep["audit"] = aud
os.makedirs(OUT, exist_ok=True)
plan["note"] = plan.get("note", "") + f" | {TAG} (DO_NOT_COUNT): SU-CHAN q_su11/q_su01(+pv1), b-type E-street stations + straight crossings, kv_line S grow, q_mcb split"
txt = json.dumps(plan, indent=1)
open(os.path.join(OUT, "die_plan.json"), "w").write(txt)
sha = hashlib.sha256(txt.encode()).hexdigest()
ev = dict(schema="opentallas.hbm_plan_event.v1", event="hbm-channels-1111", by="DIE-HBM-97/HBM-CHANNELS", do_not_count=True,
          ruling="COORD ruling on hbm-channels-ask (relayed by DIE-HBM-97 11-11): (1) SU-CHAN q_su11/pv1 q_su01/pv1; (2) b-type "
                 "E-street stations + straight opposite-face crossings",
          base_plan=os.path.abspath(BASE), base_sha256=BASE_SHA, plan=os.path.abspath(os.path.join(OUT, "die_plan.json")),
          plan_sha256=sha, tool="mk_chan_event.py", tool_sha256=hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
          report=rep)
json.dump(ev, open(os.path.join(OUT, "channels_1111_event.json"), "w"), indent=1)
import collections
print(sha)
print("fine ft", len(rep.get("fine_ft", [])), "fine ist", collections.Counter(rep.get("fine_ist", [])))
print("even ft", len(rep.get("even_ft", [])), "even ist", collections.Counter(rep.get("even_ist", [])))
print("cycle_delta by type/kind", dict(collections.Counter((d["type"], "ft" if "slot" in d else "ist") for d in rep["cycle_delta"])))
print(json.dumps(dict(su={k: dict(geom=v["geom_errors"], ist=v["ist"]) for k, v in rep["su"].items()}, b=rep["b"],
                      straight=len(rep["straight"]), skipped=len(rep["straight_skipped"]),
                      neighbours={k: len(v) for k, v in rep["neighbour_types"].items()},
                      cycle_delta=rep["cycle_delta"][:20], n_cycle_delta=len(rep["cycle_delta"]),
                      lanes_changed=len(rep["lane_cycles_changed"]), fails=rep["fails"][:10], audit=aud), indent=0))

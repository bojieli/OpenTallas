#!/usr/bin/env python3
"""adv_fp_floorplan.py -- PRECHECK FP-FLOORPLAN (FP-CONVERGE-KV, OWNER 11-25 03:5x: converge each die floorplan before kit volume).

Plan-only floorplan classes that no static check named, so 10-29 h type kits found them:

  FP-STREET    street / channel lane demand over 1.0: the bits of every internal_stations / ft_slots leg that crosses a cut through the
               hard cores, against the free street at that cut (width x M2-M8 tracks per um x 0.6 usable).  KV A5t7: 33 types over 1.0
               (kv3_hg 3.56, kv3_pv_v3n 3.54, kv3_hg_v3 2.91), 23 on A5t8; GRT overflow 59k on kv3_pv_v12 was this class.
               Core interiors have zero routing capacity (cap-0 gcells: hgi_v8 21.7k of 33.5k overflow sat inside head2_e4/head3_e4/head2_e5),
               so a leg whose straight pin-to-pin path crosses a hard-core box cannot run there: it detours through the streets that
               border that core, and its bits are also counted on those streets (KV-NOROW 11-25, COORD ruling 2).
  FT-CROSSES-CORE (report only, always WARN) the lanes/bits whose planned legs cross hard-core interiors, per type.
  FP-OVERSIZE  plan `cells` over the 400k single-run cap (kv3_pc_v3 998k).
  FP-OVERLAP   two hard cores of one type that overlap, or a core outside the type outline (KITFIT / site-grid errors start here).

Report only; plan_advisory forces WARN.  With OT_FP_BLOCK=1 the lines start FAIL (for plan_gate_pre once the live counts are stable).
findings(raw, plan_path, tree=None, **kw) -> lines, never raises.
"""
import collections
import math

CHECK = "FP-FLOORPLAN"
TV, TH = 48.18, 57.55          # tracks per um M2-M8 (auto_geom), vertical / horizontal street
USABLE = 0.6
STREET_MAX = 1.0
CELL_CAP = 400000
MIN_CORE_UM2 = 20000.0         # only cores that split the die into streets define a cut
CROSS_MIN_UM = 2.0             # a leg segment must run >= this far inside a core box (shrunk by 1 um) to count as crossing it


def _box(c):
    x, y = c["origin_um"]
    w, h = c["outline_um"]
    return x, y, x + w, y + h


def _free(blocked, length):
    cur, out = 0.0, []
    for a, b in sorted(blocked):
        if a > cur:
            out.append((cur, a))
        cur = max(cur, b)
    if cur < length:
        out.append((cur, length))
    return out


def _inside_um(a, b, box, shrink=1.0):
    """length (um) of the straight segment a->b inside `box` shrunk by `shrink` (Liang-Barsky)."""
    x0, y0, x1, y1 = box[0] + shrink, box[1] + shrink, box[2] - shrink, box[3] - shrink
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                return 0.0
            continue
        r = q / p
        if p < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 > t1:
            return 0.0
    return (t1 - t0) * math.hypot(dx, dy)


def _lanes(t):
    """[(bits, [points], name)] planned multi-bit legs of type dict t (internal_stations + ft_slots)."""
    bw = {b.get("name"): b.get("width", 1) for b in t.get("buses", [])}
    lanes = []
    for s in t.get("internal_stations", []):
        nm = (s.get("launch", "") or "").replace("bus ", "").strip()
        w = bw.get(nm)
        if w is None:
            w = bw.get((s.get("conn", "") or "").replace("bus:", ""), 1)
        pts = [q for q in [s.get("from_um")] + list(s.get("regs_um", [])) + [s.get("to_um")] if q]
        lanes.append((w, pts, nm or s.get("conn", "")))
    for s in t.get("ft_slots", []):
        lanes.append((s.get("width", 1), list(s.get("regs_um", [])), s.get("name")))
    return lanes


def core_crossings(t):
    """[(lane name, core name, bits, um inside, (a, b))] planned legs whose straight path crosses a street-defining hard-core box."""
    cores = [c for c in t.get("hard_cores", []) if c.get("origin_um") and c.get("outline_um")]
    bx = [(_box(c), c.get("name") or c.get("inst")) for c in cores if c["outline_um"][0] * c["outline_um"][1] > MIN_CORE_UM2]
    out = []
    for w, pts, nm in _lanes(t):
        for a, b in zip(pts, pts[1:]):
            for box, cn in bx:
                d = _inside_um(a, b, box)
                if d >= CROSS_MIN_UM:
                    out.append((nm, cn, w, d, (a, b)))
    return out


def street_worst(t):
    """(ratio, orient, cut_um, street, bits, cap, top lanes) of the worst street of type dict t, or None."""
    cores = [c for c in t.get("hard_cores", []) if c.get("origin_um") and c.get("outline_um")]
    if not cores:
        return None
    W, H = t["outline_um"]
    bx = [_box(c) for c in cores]
    lanes = _lanes(t)
    worst = None
    for axis in (0, 1):                     # axis 1: horizontal cuts y = c ; axis 0: vertical cuts x = c
        length, tracks = (W, H)[1 - axis], (TH, TV)[axis]
        cuts = sorted({(b[axis] + b[axis + 2]) / 2 for b in bx if (b[2] - b[0]) * (b[3] - b[1]) > MIN_CORE_UM2})
        for c in cuts:
            fr = _free([(b[1 - axis], b[3 - axis]) for b in bx if b[axis] < c < b[axis + 2]], length)
            if not fr:
                continue
            spanning = [b for b in bx if b[axis] < c < b[axis + 2] and (b[2] - b[0]) * (b[3] - b[1]) > MIN_CORE_UM2]
            dem, who = collections.Counter(), collections.defaultdict(collections.Counter)
            for w, pts, nm in lanes:
                for a, e in zip(pts, pts[1:]):
                    lo, hi = sorted((a[axis], e[axis]))
                    if lo < c < hi:
                        m = (a[1 - axis] + e[1 - axis]) / 2
                        k = min(range(len(fr)), key=lambda i: 0 if fr[i][0] <= m <= fr[i][1] else min(abs(m - fr[i][0]), abs(m - fr[i][1])))
                        dem[k] += w
                        who[k][nm] += w
                        # core interiors have no routing capacity: a leg whose straight path crosses a core box that spans this
                        # cut detours round it, so the streets on both sides of that core carry its bits too
                        for cb in spanning:
                            if _inside_um(a, e, cb) < CROSS_MIN_UM:
                                continue
                            for j2 in range(len(fr)):
                                if j2 != k and (abs(fr[j2][1] - cb[1 - axis]) < 1e-6 or abs(fr[j2][0] - cb[3 - axis]) < 1e-6):
                                    dem[j2] += w
                                    who[j2][nm] += w
            for k, d in dem.items():
                cap = (fr[k][1] - fr[k][0]) * tracks * USABLE
                r = d / cap if cap > 0 else 99.0
                if worst is None or r > worst[0]:
                    worst = (r, "V" if axis else "H", round(c), [round(x) for x in fr[k]], d, round(cap), who[k].most_common(3))
    return worst


def overlaps(t):
    """names of hard-core pairs that overlap, and of cores outside the outline."""
    cores = [c for c in t.get("hard_cores", []) if c.get("origin_um") and c.get("outline_um")]
    W, H = t.get("outline_um", [0, 0])
    nm = [c.get("name") or c.get("inst") for c in cores]
    bx = [_box(c) for c in cores]
    pairs, outside = [], []
    for i, a in enumerate(bx):
        if a[0] < -1e-6 or a[1] < -1e-6 or a[2] > W + 1e-6 or a[3] > H + 1e-6:
            outside.append(nm[i])
        for j in range(i + 1, len(bx)):
            b = bx[j]
            if min(a[2], b[2]) - max(a[0], b[0]) > 1e-6 and min(a[3], b[3]) - max(a[1], b[1]) > 1e-6:
                pairs.append((nm[i], nm[j]))
    return pairs, outside


def findings(raw, plan_path=None, tree=None, **kw):
    import os
    lvl = "FAIL" if os.environ.get("OT_FP_BLOCK") == "1" else "WARN"
    out = []
    try:
        pt = (raw or {}).get("partition_types") or {}
    except AttributeError:
        return out
    n_street = n_big = n_ovl = 0
    for name, t in sorted(pt.items()):
        try:
            w = street_worst(t)
            if w and w[0] > STREET_MAX:
                n_street += 1
                out.append(f"{lvl} ADV-FP-STREET {name}: lane demand {w[0]:.2f} > {STREET_MAX} on {w[1]} cut {w[2]} um street {w[3]} um "
                           f"({w[4]} bits vs {w[5]} usable tracks); load {', '.join(f'{a}:{b}' for a, b in w[6])}; "
                           "fix: widen the street / grow the outline / re-seat lanes onto another cut")
            cells = t.get("cells") or 0
            if isinstance(cells, (int, float)) and cells > CELL_CAP:
                n_big += 1
                out.append(f"{lvl} ADV-FP-OVERSIZE {name}: {int(cells)} cells > {CELL_CAP} single-run cap; fix: split the type")
            cr = core_crossings(t)
            if cr:
                agg = collections.Counter()
                for nm, cn, w, d, _ in cr:
                    agg[(nm, cn)] += w
                nb = sum(agg.values())
                out.append(f"WARN ADV-FT-CROSSES-CORE {name}: {len(agg)} lane x core crossing(s), {nb} bit-legs run through hard-core interiors "
                           f"(zero routing capacity); worst {', '.join(f'{a}>{b}:{n}b' for (a, b), n in agg.most_common(3))}; "
                           "fix: re-site the stations / pins so no leg crosses a core, or open a street")
            pairs, outside = overlaps(t)
            if pairs or outside:
                n_ovl += 1
                out.append(f"{lvl} ADV-FP-OVERLAP {name}: {len(pairs)} overlapping hard-core pair(s) {pairs[:3]}, "
                           f"{len(outside)} core(s) outside the outline {outside[:3]}")
        except Exception as e:  # a malformed type never stops the others
            out.append(f"WARN ADV-FP-FLOORPLAN {name}: not checked ({type(e).__name__}: {str(e)[:80]})")
    out.append(f"WARN ADV-FP-FLOORPLAN summary {n_street} type(s) street demand > {STREET_MAX}, {n_big} over {CELL_CAP} cells, "
               f"{n_ovl} with core overlap/outside, of {len(pt)} types")
    return out

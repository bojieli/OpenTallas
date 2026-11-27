#!/usr/bin/env python3
"""adv_fp_floorplan.py -- PRECHECK FP-FLOORPLAN (FP-CONVERGE-KV, OWNER 11-25 03:5x: converge each die floorplan before kit volume).

Plan-only floorplan classes that no static check named, so 10-29 h type kits found them:

  FP-STREET    street / channel lane demand over 1.0: the bits of every internal_stations / ft_slots leg that crosses a cut through the
               hard cores, against the free street at that cut (width x M2-M8 tracks per um x 0.6 usable).  KV A5t7: 33 types over 1.0
               (kv3_hg 3.56, kv3_pv_v3n 3.54, kv3_hg_v3 2.91), 23 on A5t8; GRT overflow 59k on kv3_pv_v12 was this class.
               Core interiors have zero routing capacity (cap-0 gcells: hgi_v8 21.7k of 33.5k overflow sat inside head2_e4/head3_e4/head2_e5),
               so a leg whose straight pin-to-pin path crosses a hard-core box cannot run there: it detours through the streets that
               border that core, and its bits are also counted on those streets (KV-NOROW 11-25, COORD ruling 2).
  H9 R0 P2 frame_int aligned edge ranks: the same street warning includes a
               local stripe estimate from overlapping serial rank spans.
  ADV-FP-STREET-BUS (C-STREET-R3 11-27, own WARN tag, default on, OT_STREET_BUS=0 off): the face buses (face + window_um + leaf) are priced
               as lanes too (face window -> owning hard cores) at the AUTO-GEOM 0.45 usable share, PG-adjusted, limit 0.9.  The stock check
               read 0 on HEAD W12f (607dd5dd5c82) while placed views failed: it counts only internal_stations / ft_slots legs.  Caught:
               hd_lep0N 5.45 (placed channel_h 2.246), hd_tile 3.96 (73 GRT overflow); sister hd_lep0N_w 2.94.  Still missed: hd_host_w (no plan
               lane: 0 stations, buses price 0.5; its 0.78 is internal net bboxes among 55 SRAMs) and hd_ctl_n (coreless, needs the lane band;
               0.73 vs placed 0.613).  Other dies (extra types over 0.9, not already over 1.0): S81 36, QC 8, KV 0.
  FT-CROSSES-CORE (report only, always WARN) the lanes/bits whose planned legs cross hard-core interiors, per type.
  FP-OVERSIZE  plan `cells` over the 400k single-run cap (kv3_pc_v3 998k).  Default: the plan number as written.  With
               OT_FP_OVERSIZE_FLAT=1 (C-OVERSIZE 11-26): a type with hard_cores has type.cells = its hard-core content too, so
               the run only sees the FLAT std cells; the count becomes the flat projection (adv_cell_budget.project, floored by the
               newest retained kit synth count, at most 5 days old) and OT_FP_OVERSIZE_REPAIR_GROWTH=<f> (default 1.0; 1.2 matches
               lepw_mus_C 333k synth -> >400k after TD repair) scales it before the cap test.  Live 11-26: S81 kv_leaf t1/t3/t4/t5
               1.9M, HEAD hd_tile 1.07M and KV kv3_pc_v3 998k plan cells are 41-313k flat in kits that placed (false positives).
               NETLIST (C-OVERSIZE 11-27, default on, OT_FP_OVERSIZE_NETLIST=0 off): when the PRECHECK flop cache (adv_tap_load.load_cache)
               has the type's synthesized netlist flops (exact type, else base type), that count is the authority: flops > CELL_CAP is
               oversize (cells >= flops, a lower bound; catches S81 svc_lo rs t5/t7 and rs_w t1 with no plan `cells`), and a type
               with hard cores whose netlist flops are under the cap is NOT flagged on its plan `cells` (which includes the cores'
               content: kv_leaf t1/t3/t4/t5 1.9M plan cells vs 28-60k flops).  No cache entry: the rules above are unchanged.
  FP-OVERLAP   two hard cores of one type that overlap, or a core outside the type outline (KITFIT / site-grid errors start here).

Report only; plan_advisory forces WARN.  With OT_FP_BLOCK=1 the lines start FAIL (for plan_gate_pre once the live counts are stable).
findings(raw, plan_path, tree=None, **kw) -> lines, never raises.
"""
import collections
import math
import os

from schema import placed_macro_boxes
import street_pg as SP
from infra_sites import station_bits, station_epoch_modes

CHECK = "FP-FLOORPLAN"
TV, TH = 48.18, 57.55          # tracks per um M2-M8 (auto_geom), vertical / horizontal street
USABLE = 0.6
RANK_WINDOW_UM = 10.0       # same local stripe as AUTO-GEOM; tests full M2-M8 capacity
ALIGNED_RANK_FAMILY = "col_h9_r0_p2__"  # validated against the bound, placed frame_int cohort
STREET_MAX = 1.0
CELL_CAP = 400000
FLAT_KIT_MAX_AGE_S = 5 * 86400   # OT_FP_OVERSIZE_FLAT: oldest retained kit synth count taken as the flat count
MIN_CORE_UM2 = 20000.0         # only cores that split the die into streets define a cut
GEOM_EPS = 1e-6
CROSS_MIN_UM = 2.0             # a leg segment must run >= this far inside a core box (shrunk by 1 um) to count as crossing it


def _box(c):
    return placed_macro_boxes({"hard_cores": [dict(c, inst="core")]})["core"]


def _free(blocked, length):
    cur, out = 0.0, []
    for start, end in sorted(blocked):
        a, b = max(0.0, start), min(length, end)
        if b <= a:
            continue
        if a - cur > GEOM_EPS:
            out.append((cur, a))
        cur = max(cur, b)
    if length - cur > GEOM_EPS:
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


def _face_center(face, window, w, h):
    center = (window[0] + window[1]) / 2
    return {"N": (center, h), "S": (center, 0), "E": (w, center), "W": (0, center)}.get(face)


def _lanes(t):
    """(bits, points, label) for each planned lane, including FT face legs."""
    bw = {b.get("name"): b.get("width", 1) for b in t.get("buses", [])}
    lanes = []
    for s in t.get("internal_stations", []):
        nm = (s.get("launch") or "").removeprefix("bus ").strip()
        conn = s.get("conn") or ""
        banks = s.get("bit_sites_um")
        bits = s.get("bits") or (len(banks[0]) - 1 if banks else 0)
        bits = bits or bw.get(nm, bw.get(conn.removeprefix("bus:"), 1))
        pts = [q for q in [s.get("from_um"), *(s.get("regs_um") or []), s.get("to_um")] if q]
        lanes.append((bits, pts, nm or conn))
    w, h = t.get("outline_um", (0, 0))
    for s in t.get("ft_slots", []):
        pts = list(s.get("regs_um") or [])
        for end, i in (("in", 0), ("out", len(pts) + 1)):
            face = s.get(f"{end}_face")
            window = s.get(f"{end}_window_um")
            if face and window:
                point = _face_center(face, window, w, h)
                if point:
                    pts.insert(i, point)
        lanes.append((s.get("width", 1), pts, s.get("name")))
    return lanes

def _l_clear(a, b, bx):
    """True when a Manhattan L (either corner) between a and b crosses no box in bx (the router is Manhattan)."""
    def clear(p, q):
        return all(_inside_um(p, q, x) < CROSS_MIN_UM for x in bx)
    return any(clear(a, c) and clear(c, b) for c in ((a[0], b[1]), (b[0], a[1])))


def core_crossings(t, manhattan=False):
    """[(lane name, core name, bits, um inside, (a, b))] planned legs whose straight path crosses a street-defining hard-core box.
    manhattan=True (OT_FT_CROSS_MANHATTAN=1 in findings, C-FT-CROSSES-CORE): a leg whose Manhattan L between the same two points
    clears every core is not a crossing (the straight diagonal over-counts: S81 53 %, QC 70 %, KV 66 % of the 09:00 bit-legs)."""
    cores = [c for c in t.get("hard_cores", []) if c.get("origin_um") and c.get("outline_um")]
    bx = [(_box(c), c.get("name") or c.get("inst")) for c in cores if c["outline_um"][0] * c["outline_um"][1] > MIN_CORE_UM2]
    out = []
    for w, pts, nm in _lanes(t):
        for a, b in zip(pts, pts[1:]):
            for box, cn in bx:
                d = _inside_um(a, b, box)
                if d >= CROSS_MIN_UM:
                    if manhattan and _l_clear(a, b, [x for x, _ in bx]):
                        break
                    out.append((nm, cn, w, d, (a, b)))
    return out


BUSLANE_USABLE = 0.45          # AUTO-GEOM: 0.6 utilisation limit x 0.75 track derate = 0.45 of the raw tracks
BUSLANE_MAX = 0.9              # plan model tolerance below the AUTO-GEOM limit (HEAD ctl_n measured 0.613 vs 0.60 reads 0.98 here)


def buslane_enabled():
    """ADV-FP-STREET-BUS (report-only, WARN, own tag so the counted C-STREET class does not move) is on unless OT_STREET_BUS=0."""
    import os
    return os.environ.get("OT_STREET_BUS") != "0"


def bus_lanes(t):
    """(bits, points, label) per face bus with a face window: the straight leg from the face window centre to the centroid of the hard
    cores that own the bus leaf (first path component of `leaf` == a core inst prefix; else every hard core).  Buses that an
    internal_stations row already carries (conn `bus:<name>` or launch `bus <name>`) are not counted twice.  Plan-only proxy for the
    AUTO-GEOM net-bbox channel demand: HEAD 11-27 measured channel_h 2.246 / col_v 1.602 (lep0N), H 0.78 (host_w), 73 GRT overflow
    (tile), col_v 0.613 (ctl_n) on plans that read 0 here because their data buses were not lanes."""
    W, H = t.get("outline_um", (0, 0))
    cores = [c for c in t.get("hard_cores", []) if c.get("origin_um") and c.get("outline_um")]
    if not W or not H:
        return []
    done = set()
    for s in t.get("internal_stations", []):
        done.add((s.get("launch") or "").removeprefix("bus ").strip())
        done.add((s.get("conn") or "").removeprefix("bus:"))
    centers = [(c.get("inst") or c.get("name") or "", [(_box(c)[0] + _box(c)[2]) / 2, (_box(c)[1] + _box(c)[3]) / 2]) for c in cores]
    out = []
    for b in t.get("buses", []):
        face, win, nm = b.get("face"), b.get("window_um"), b.get("name")
        if not face or not win or nm in done:
            continue
        pt = _face_center(face, win, W, H)
        if not pt:
            continue
        head = str(b.get("leaf") or "").split(".")[0]
        own = [c for n, c in centers if head and n.split(".")[0] == head] or [c for _, c in centers]
        if not own:
            continue
        tgt = [sum(c[0] for c in own) / len(own), sum(c[1] for c in own) / len(own)]
        out.append((b.get("width", 1), [pt, tgt], nm))
    return out


def pg_enabled(raw, name=None):
    """C-STREET-R2 opt-in: plan top-level street_sizing.pg (or OT_STREET_PG=1) derates street capacity by the PG stripe bands.
    FLAG-SCOPE 11-27: with street_sizing.types and a type name, only a matching type (re.search) is derated by the plan flag."""
    import re
    f = (raw or {}).get("street_sizing") if isinstance(raw, dict) else None
    rx = f.get("types") if isinstance(f, dict) else None
    if isinstance(f, dict) and "types" in f:                 # validated in every reading (as street_rule.street_types)
        if not isinstance(rx, str) or not rx:
            raise ValueError(f"street_sizing.types must be a non-empty regex string, got {rx!r}")
        try:
            re.compile(rx)
        except re.error as e:
            raise ValueError(f"street_sizing.types is not a valid regex {rx!r}: {e}") from None
    if os.environ.get("OT_STREET_PG") == "1":
        return True
    if not (isinstance(f, dict) and f.get("pg")):
        return False
    if rx is None or name is None:
        return True
    return re.search(rx, name) is not None


PILE_BIN_UM = 25.92            # coreless lane band: 3 x 8.64 (the HEAD SPN hotspot lane was x222-250, 28 um wide)


def lane_band_worst(t, pg=True, extra=None, usable=USABLE):
    """Coreless types have no macro streets, so street_worst is blind to them (HEAD hd_spn: 3.11 measured lane, no verdict).
    Same tuple as street_worst: the worst PILE_BIN_UM-wide x band, demand = the bits of every planned leg crossing one horizontal
    cut inside it, capacity = band width x vertical tracks/um x USABLE x PG factor.  Only used with the PG flag (opt-in)."""
    W, H = t.get("outline_um", (0, 0))
    lanes = _lanes(t) + list(extra or [])
    if not W or not H or not lanes:
        return None
    nb = max(1, int(W // PILE_BIN_UM) + 1)
    tracks = TV * (SP.pg_factor("V") if pg else 1.0)
    best = None
    cuts = sorted({round(q[1] / 10.0) * 10.0 for _, pts, _ in lanes for q in pts if 0 < q[1] < H})
    for c in cuts or [H / 2]:
        dem, who = collections.Counter(), collections.defaultdict(collections.Counter)
        for w, pts, nm in lanes:
            for a, e in zip(pts, pts[1:]):
                lo, hi = sorted((a[1], e[1]))
                if not lo <= c < hi:
                    continue
                al = (c - a[1]) / (e[1] - a[1])
                m = a[0] + al * (e[0] - a[0])
                k = min(nb - 1, max(0, int(m // PILE_BIN_UM)))
                dem[k] += w
                who[k][nm] += w
        for k, d in dem.items():
            cap = PILE_BIN_UM * tracks * usable
            r = d / cap
            if best is None or r > best[0]:
                best = (r, "V", round(c), [round(k * PILE_BIN_UM), round((k + 1) * PILE_BIN_UM)], d, round(cap), who[k].most_common(3))
    return best


def street_worst(t, pg=False, extra=None, usable=USABLE):
    """(ratio, orient, cut_um, street, bits, cap, top lanes) of the worst street of type dict t, or None.
    pg=True: usable tracks per um are scaled by street_pg.pg_factor (PART_PG_BANDS exclusion), default off."""
    cores = [c for c in t.get("hard_cores", []) if c.get("origin_um") and c.get("outline_um")]
    if not cores:
        return lane_band_worst(t, pg, extra, usable) if (pg or extra) else None
    W, H = t["outline_um"]
    bx = [_box(c) for c in cores]
    lanes = _lanes(t) + list(extra or [])
    worst = None
    for axis in (0, 1):                     # axis 1: horizontal cuts y = c ; axis 0: vertical cuts x = c
        length, tracks = (W, H)[1 - axis], (TH, TV)[axis]
        if pg:
            tracks *= SP.pg_factor("V" if axis else "H")
        cuts = sorted({(b[axis] + b[axis + 2]) / 2 for b in bx if (b[2] - b[0]) * (b[3] - b[1]) > MIN_CORE_UM2})
        for c in cuts:
            fr = _free([(b[1 - axis], b[3 - axis]) for b in bx if b[axis] < c < b[axis + 2]], length)
            spanning = [b for b in bx if b[axis] < c < b[axis + 2] and (b[2] - b[0]) * (b[3] - b[1]) > MIN_CORE_UM2]
            dem, who = collections.Counter(), collections.defaultdict(collections.Counter)
            for w, pts, nm in lanes:
                for a, e in zip(pts, pts[1:]):
                    lo, hi = sorted((a[axis], e[axis]))
                    if not lo <= c < hi:
                        continue
                    if not fr:
                        dem[0] += w
                        who[0][nm] += w
                        continue
                    # Intersect at this cut. A segment's midpoint is generally on a different street.
                    along = (c - a[axis]) / (e[axis] - a[axis])
                    m = a[1 - axis] + along * (e[1 - axis] - a[1 - axis])
                    k = min(range(len(fr)), key=lambda i: max(fr[i][0] - m, 0, m - fr[i][1]))
                    streets = {k}
                    for cb in spanning:
                        if _inside_um(a, e, cb) < CROSS_MIN_UM:
                            continue
                        for j, (left, right) in enumerate(fr):
                            if abs(right - cb[1 - axis]) < GEOM_EPS or abs(left - cb[3 - axis]) < GEOM_EPS:
                                streets.add(j)
                    # Both neighbouring cores can name the same gap. This leg occupies it once.
                    for j in streets:
                        dem[j] += w
                        who[j][nm] += w
            for k, d in dem.items():
                street = fr[k] if fr else (0.0, 0.0)
                cap = (street[1] - street[0]) * tracks * usable
                r = d / cap if cap > 0 else math.inf
                if worst is None or r > worst[0]:
                    worst = (r, "V" if axis else "H", round(c), [round(x) for x in street], d, round(cap), who[k].most_common(3))
    return worst



def aligned_edge_rank_worst(t, epochs, typename):
    """Shared edge stripe pressure from undispersed H9 R0 P2 frame_int station legs.

    Consecutive legs end where the next starts. Price simultaneous opposing
    buses at each true overlap; a serial chain does not multiply its width.
    Rank centres with explicitly spread seats or route geometry cannot justify
    an aligned-span estimate.
    """
    outline = t.get("outline_um")
    if not outline or not typename.startswith(ALIGNED_RANK_FAMILY):
        return None
    buses = {b["name"]: b for b in t.get("buses", []) if b["name"].startswith("frame_int_")}
    spans = collections.defaultdict(list)
    rank_seats = t.get("relay_rank_sites") or {}
    for st in t.get("internal_stations", []):
        conn = st.get("conn") or ""
        bus = conn.removeprefix("bus:")
        if bus not in buses or not conn.startswith("bus:"):
            continue
        if any(st.get(k) for k in ("bit_sites_um", "face_bit_sites_um", "bit_route", "leg_order", "sites")):
            continue
        if any(bus in name for name in rank_seats):
            continue
        bits = station_bits(st, buses, epochs, typename)
        if bits is None:
            continue
        points = [st["from_um"], *st.get("regs_um", []), st["to_um"]]
        for a, b in zip(points, points[1:]):
            for axis in (0, 1):
                pos, end = a[1 - axis], outline[1 - axis]
                if abs(b[1 - axis] - pos) > GEOM_EPS or abs(b[axis] - a[axis]) <= GEOM_EPS:
                    continue
                edge = min(pos, end - pos)
                if edge < -GEOM_EPS or edge >= RANK_WINDOW_UM:
                    continue
                low, high = sorted((a[axis], b[axis]))
                spans[axis, round(pos, 6)].append((low, high, bus, bits))

    best = None
    for (axis, pos), legs in spans.items():
        if len({bus for _, _, bus, _ in legs}) < 2:
            continue
        ends = sorted({x for lo, hi, _, _ in legs for x in (lo, hi)})
        cap = min(outline[1 - axis], RANK_WINDOW_UM) * (TH, TV)[axis]
        for lo, hi in zip(ends, ends[1:]):
            at = (lo + hi) / 2
            demand = collections.Counter()
            for start, end, bus, bits in legs:
                if start <= at < end:
                    demand[bus] += bits
            if len(demand) < 2:
                continue
            ratio = sum(demand.values()) / cap
            direction = ("H", "V")[axis]
            ranked = demand.most_common()
            if best is None or ratio > best["ratio"]:
                best = dict(ratio=ratio, direction=direction, rank_um=pos,
                            span_um=(lo, hi), cut_um=at, bits=sum(demand.values()),
                            tracks=cap, buses=ranked)
            elif (best["direction"], best["rank_um"], best["span_um"][1], best["buses"]) == (direction, pos, lo, ranked):
                # Preserve the individual legs above, but report the whole
                # continuous span when their overlapping load stays equal.
                first = best["span_um"][0]
                best.update(span_um=(first, hi), cut_um=(first + hi) / 2)
    return best


def overlaps(t):
    """names of hard-core pairs that overlap, and of cores outside the outline."""
    cores = [c for c in t.get("hard_cores", []) if c.get("origin_um") and c.get("outline_um")]
    W, H = t.get("outline_um", [0, 0])
    nm = [c.get("name") or c.get("inst") for c in cores]
    bx = [_box(c) for c in cores]
    pairs, outside = [], []
    for i, a in enumerate(bx):
        if a[0] < -GEOM_EPS or a[1] < -GEOM_EPS or a[2] > W + GEOM_EPS or a[3] > H + GEOM_EPS:
            outside.append(nm[i])
        for j in range(i + 1, len(bx)):
            b = bx[j]
            if min(a[2], b[2]) - max(a[0], b[0]) > GEOM_EPS and min(a[3], b[3]) - max(a[1], b[1]) > GEOM_EPS:
                pairs.append((nm[i], nm[j]))
    return pairs, outside


def flat_cells(name, t, cache=None, modules=None):
    """(flat std cells one run sees, basis).  Hard cores are separate runs: their content is not in this run."""
    import adv_cell_budget as B
    r = B.project(name, t, B.load_modules() if modules is None else modules, cache or {})
    est, basis = r["est"], r["basis"]
    # a kit up to 5 days old (t1/t3/t4 kv_leaf 3-4 d); older ones predate the hard-core structure (svc 3.4-5.1M flat kits of 11-20)
    import time
    kit, kname = B.kit_cells(name, cache or {}, now=time.time() - (FLAT_KIT_MAX_AGE_S - B.KIT_MAX_AGE_S))
    if kit and kit > est:
        est, basis = kit, f"retained kit synth {kit:,} ({kname})"
    return est, basis


def netlist_flops(name, kw, _cache={}):
    """(flops, kit label) of the newest kit netlist of this type or its base type from the PRECHECK flop cache, else (None, None)."""
    try:
        import adv_tap_load as L
        src = kw.get("flops_cache")
        key = repr(src)[:200] if not isinstance(src, dict) else id(src)
        if key not in _cache:
            _cache[key] = L.load_cache(src)[0] or {}
        fl = _cache[key].get("flops") or {}
        by_base = {}
        for n in fl:
            by_base.setdefault(L.base_type(n), []).append(n)
        rec, basis = L.lookup(fl, name, by_base)
        n = (rec or {}).get("flops")
        if not isinstance(n, int) or n <= 0:
            return None, None
        return n, f"{basis}: {str(rec.get('kit', '')).split(':')[-1][:60]}"
    except Exception:
        return None, None


def findings(raw, plan_path=None, tree=None, **kw):
    import os
    flat = os.environ.get("OT_FP_OVERSIZE_FLAT") == "1"
    if flat:
        try:
            growth = float(os.environ.get("OT_FP_OVERSIZE_REPAIR_GROWTH") or 1.0)
        except ValueError:
            growth = 1.0
        try:
            import adv_cell_budget as B
            cache = B._cache(kw.get("cells_cache"), ((raw or {}).get("die") or {}).get("name"))
        except Exception:
            cache = {}
    lvl = "FAIL" if os.environ.get("OT_FP_BLOCK") == "1" else "WARN"
    out = []
    try:
        raw = raw or {}
        pt = raw.get("partition_types") or {}
    except AttributeError:
        return out
    n_street = n_big = n_ovl = n_bus = 0
    try:
        pg_enabled(raw, "")                            # FLAG-SCOPE 11-27: validate street_sizing.types once
        pg_bad = None
    except ValueError as e:
        pg_bad = str(e)
        out.append(f"FAIL ADV-FP-STREET street_sizing: {pg_bad}; PG sizing off for every type until fixed")
    bus_on = buslane_enabled()
    parts = {part["name"]: part for part in (raw.get("partitions") or [])
             if isinstance(part, dict) and "name" in part and str(part.get("type")).startswith(ALIGNED_RANK_FAMILY)}
    epochs = station_epoch_modes(parts, raw.get("ports") or []) if parts else {}
    for name, t in sorted(pt.items()):
        pg = pg_enabled(raw, name) if pg_bad is None else os.environ.get("OT_STREET_PG") == "1"   # FLAG-SCOPE 11-27
        try:
            w = street_worst(t, pg)
            street_over = bool(w and w[0] > STREET_MAX)
            if street_over:
                tracks = (TV if w[1] == "V" else TH) * (SP.pg_factor("V" if w[1] == "V" else "H") if pg else 1.0)
                required = w[4] / (tracks * USABLE)
                out.append(f"{lvl} ADV-FP-STREET {name}{' [PG-adjusted]' if pg else ''}: lane demand {w[0]:.2f} > {STREET_MAX} on {w[1]} cut {w[2]} um street {w[3]} um "
                           f"({w[4]} bits vs {w[5]} usable tracks); load {', '.join(f'{a}:{b}' for a, b in w[6])}; "
                           f"fix: reserve at least {required:.2f} um or re-seat lanes onto another cut")
            if bus_on and not street_over:
                ex = bus_lanes(t)
                wb = street_worst(t, True, ex, BUSLANE_USABLE) if ex else None
                if wb and wb[0] > BUSLANE_MAX:
                    n_bus += 1
                    out.append(f"WARN ADV-FP-STREET-BUS {name}: lane demand {wb[0]:.2f} > {BUSLANE_MAX} (face-bus legs + stations, PG-adjusted, "
                               f"{BUSLANE_USABLE} usable share) on {wb[1]} cut {wb[2]} um street {wb[3]} um ({wb[4]} bits vs {wb[5]} tracks); "
                               f"load {', '.join(f'{a}:{b}' for a, b in wb[6])}; AUTO-GEOM channel limit 0.6 would read this placed view as FAIL; "
                               "fix: open the street / re-seat the bus landing, REPORT ONLY")
            rank = aligned_edge_rank_worst(t, epochs, name)
            rank_over = bool(rank and rank["ratio"] > STREET_MAX)
            if rank_over:
                lo, hi = rank["span_um"]
                out.append(f"{lvl} ADV-FP-STREET {name}: aligned {rank['direction']} edge rank at {rank['rank_um']:.2f} um, "
                           f"span {lo:.2f}-{hi:.2f} um: demand {rank['ratio']:.2f} > {STREET_MAX} "
                           f"({rank['bits']} bits vs {rank['tracks']:.2f} tracks per {RANK_WINDOW_UM:g} um); "
                           f"load {', '.join(f'{bus}:{bits}' for bus, bits in rank['buses'][:3])}; "
                           "fix: spread coincident ranks over independent stripes")
            n_street += int(street_over or rank_over)
            cells = t.get("cells") or 0
            nflops, nbasis = (netlist_flops(name, kw) if os.environ.get("OT_FP_OVERSIZE_NETLIST") != "0" and not t.get("hard")
                              else (None, None))
            if nflops is not None:
                if nflops > CELL_CAP:
                    n_big += 1
                    out.append(f"{lvl} ADV-FP-OVERSIZE {name}: netlist flops {nflops:,} > {CELL_CAP:,} single-run cap (cells >= flops; "
                               f"plan type.cells {int(cells) if isinstance(cells, (int, float)) else 0:,}, {len(t.get('hard_cores') or [])} hard core(s); {nbasis}); "
                               "fix: split the type")
                elif not t.get("hard_cores") and isinstance(cells, (int, float)) and cells > CELL_CAP:
                    n_big += 1
                    out.append(f"{lvl} ADV-FP-OVERSIZE {name}: {int(cells)} cells > {CELL_CAP} single-run cap (netlist flops {nflops:,}); fix: split the type")
            elif flat:
                est, basis = flat_cells(name, t, cache)
                proj = est * growth
                if proj > CELL_CAP:
                    n_big += 1
                    out.append(f"{lvl} ADV-FP-OVERSIZE {name}: flat {est:,} cells x repair growth {growth:g} = {int(proj):,} > {CELL_CAP} "
                               f"single-run cap (plan type.cells {int(cells):,}, {len(t.get('hard_cores') or [])} hard core(s) run separately; {basis}); "
                               "fix: split the type")
            elif isinstance(cells, (int, float)) and cells > CELL_CAP:
                n_big += 1
                out.append(f"{lvl} ADV-FP-OVERSIZE {name}: {int(cells)} cells > {CELL_CAP} single-run cap; fix: split the type")
            cr = core_crossings(t, manhattan=os.environ.get("OT_FT_CROSS_MANHATTAN") == "1")
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
    out.append(f"WARN ADV-FP-FLOORPLAN summary {n_street} type(s) street demand > {STREET_MAX} (+{n_bus} bus-lane model > {BUSLANE_MAX}), {n_big} over {CELL_CAP} cells, "
               f"{n_ovl} with core overlap/outside, of {len(pt)} types")
    return out

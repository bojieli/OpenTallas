#!/usr/bin/env python3
"""adv_fpconv.py -- FP-CONVERGE-S81 11-25 (COORD ruling 05:5x item 2): ten report-only plan checks from the Fable reviews of 13 S81 types.

All WARN ADV-<NAME> lines, one per type, never a gate, every die; cheap geometry over the plan only (no netlist, no liberty).

IN-OUTLINE      any planned xy outside the type outline: station regs and bit-site footprints, relay sites, landing bands, reach-fix /
                sink sites, added taps, edge-clock taps, the reset root (reset.in_sites).  S81 t70 root (1611.8, 12.9) on a 1494.7 um
                outline, t35 ft3 station y -4.3.  (ADV-FT-OUTSIDE keeps the ft slots; this one covers everything else.)
LEG405-ZERO     relay_depth entry with path_um > 405 and stages_existing == 0 (S81 vn_a.c_s -> vn_b 406 / 436 um, rxsf 417 um).
                Also (C9-KVPV-CLAND-LEG, KV-OWN-PV-R2 11-25): a clock-landing type (clock.landing_contract) with no
                clock.landing_reader_start whose cland origin (landing_raw_branches consumer 'origin', last stage) is > 405 um
                (Manhattan) from an input ring's cland_fstart_in_<bus> pin: origin -> reader_start is one cycle (kv3_pv_v4n
                route setup -1117 ps on u_cland_origin -> u_cland_reader_start_ft42).  Fix: kv_start_corridor_event.py start.
LEG405-STAGED   (C-LEG405-R2) the staged-aware form: relay_depth entry with stages_existing + D < ceil(path_um / 405) - 1 (the stations
                that make every hop <= 405 um), plus the cland legs above.  LEG405-ZERO stays as the legacy scan.
                C-LEG405 cover (P-FALSE-GREEN; HEAD hd_host_w 11-26: landing_reader_start + no relay_depth passed vacuously over 1,511
                placed hops > 405 um): also every hop of the landing reader/writer start chains, raw-reset branches, landing_status_input_stages
                (face pin -> stages -> nearest agg anchor / sink pin; unstaged status rings too) and internal_stations chains (a reg pair
                'a|b' is a macro-pin pair; > 810 um with <= 1 stage is IMPOSSIBLE with one flop).  The summary counts legs measured per
                kind, and 'WARN LEG405-STAGED-UNCHECKED <type>: <kinds>' names every leg kind the plan carries but the check cannot see
                (macro pin-to-pin nets, relay_sites without relay_depth, reset relay -> sink, ft_slots, clock sinks).  WARN not FAIL: a
                missing coordinate is missing evidence, not a measured violation (PRE promotes only UNCHECKED lines naming an exception).
RELAY-SEAT      a relay site inside a hard core, or more than RELAY_STACK relays on one point (S81 t15 32 seats in lane cores).
SEAT-DENSITY    station + ft register flops (bits x 0.38 um2) over free area (bin minus cores) per 100 um bin > 0.5 (t15 1.09).
PIN-FACE-CLEAR  a station endpoint on a core face with < 43 um clear in front of it (neighbour core or outline).
HUB-BOX         a core with > 200 station bits needs >= 2 faces with >= 60 um clear (vn_a / vn_b / vs boxed in at 8.6-17 um).
FT-CLEAR        an ft register hop (straight segment) that crosses a hard core by > 10 um (t57: four chains over vsw, 225 um each).
TAP-STEP-DUP    two added (explicit) taps < 40 um apart (t54 five taps within 11-13 um); core-pin taps are excluded (macro_follow).
BAND-AT-PIN     a landing band farther than 180 um from its pins (max_pin_to_band_hop_um) or overlapping a hard core.
SEAT-UNIQUE     >= 4 station registers of different stations on one point (reader-start duplicate seats)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_geom_static as G  # noqa: E402

TOL = 0.01
LEG_UM = 405.0
RELAY_STACK = 4
CELL_UM2 = 0.38
BIN_UM = 100.0
DENS_MAX = 0.5
CLEAR_PIN_UM = 43.0
HUB_BITS = 200
CLEAR_HUB_UM = 60.0
FT_OVER_UM = 10.0
TAP_STEP_UM = 40.0
BAND_HOP_UM = 180.0
SEAT_STACK = 4
MAX_EX = 3


def _w(check, *parts):
    return f"WARN ADV-{check} " + " ".join(str(p) for p in parts)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def pts(o):
    """yield (x, y) of every [x, y] / [x, y, w] number list nested in o"""
    if isinstance(o, (list, tuple)):
        if 2 <= len(o) <= 3 and all(_num(v) for v in o):
            yield float(o[0]), float(o[1])
        else:
            for v in o:
                yield from pts(v)


def _over(x, y, W, H, cw=0.0, ch=0.0):
    return max(-x, -y, x + cw - W, y + ch - H)


def outline_points(t, tn, raw):
    """{category: [(x, y, cw, ch)]} the planned positions that must lie inside the outline"""
    cat = {}
    ck = t.get("clock") or {}
    cat["station reg"] = [(x, y, 0, 0) for s in t.get("internal_stations") or [] if isinstance(s, dict) for x, y in pts(s.get("regs_um"))]
    sc = []
    for s in t.get("internal_stations") or []:
        if isinstance(s, dict):
            cw, ch = (s.get("bit_site_cell_um") or t.get("bit_site_cell_um") or [0.0, 0.0])[:2]
            sc += [(x, y, cw, ch) for x, y in pts(s.get("bit_sites_um"))]
    cat["station bit site"] = sc
    cat["relay site"] = [(x, y, 0, 0) for x, y in pts(list((t.get("relay_sites") or {}).values()))]
    cat["reach/sink site"] = [(x, y, 0, 0) for k in ("reach_fix_sinks", "sink_sites_um") for x, y in pts(ck.get(k))]
    cat["added tap"] = [(float(a["xy"][0]), float(a["xy"][1]), 0, 0) for a in ck.get("added_taps") or [] if isinstance(a, dict) and a.get("xy")]
    cat["edge clock tap"] = [(x, y, 0, 0) for e in ck.get("edge_clocks") or [] if isinstance(e, dict) for x, y in pts(e.get("tap_um"))]
    br = []
    for b in ((ck.get("landing_contract") or {}).get("bands") or {}).values():
        r = b.get("rect_um") if isinstance(b, dict) else None
        if r and len(r) == 4:
            br += [(r[0], r[1], 0, 0), (r[2], r[3], 0, 0)]
    cat["landing band"] = br
    root = ((raw.get("reset") or {}).get("in_sites") or {}).get(tn)
    cat["reset root"] = [(float(root[0]), float(root[1]), 0, 0)] if root and len(root) >= 2 else []
    return cat


def in_outline(t, tn, raw):
    o = t.get("outline_um")
    if not o:
        return []
    W, H = o
    hits = []
    for name, ps in outline_points(t, tn, raw).items():
        bad = [_over(x, y, W, H, cw, ch) for x, y, cw, ch in ps]
        bad = [b for b in bad if b > TOL]
        if bad:
            hits.append((name, len(bad), round(max(bad), 2)))
    return hits


def cland_origin_xy(t):
    """last stage xy of the clock.landing_raw_branches branch whose consumers include 'origin' (the cland origin seat), else None"""
    for b in (t.get("clock") or {}).get("landing_raw_branches") or []:
        if isinstance(b, dict) and "origin" in (b.get("consumers") or []) and b.get("stages"):
            xy = b["stages"][-1].get("xy_um")
            if isinstance(xy, (list, tuple)) and len(xy) == 2 and _num(xy[0]) and _num(xy[1]):
                return float(xy[0]), float(xy[1])
    return None


def cland_reader_legs(t):
    """C9: [(origin, reader_start_<bus>, Manhattan um, 0)] over 405 for a landing type without clock.landing_reader_start"""
    c = t.get("clock") or {}
    if not c.get("landing_contract") or c.get("landing_reader_start") is not None:
        return []
    o = cland_origin_xy(t)
    if o is None:
        return []
    out = []
    for p in (c["landing_contract"] or {}).get("pins") or []:
        nm, xy = p.get("name", ""), p.get("xy_um")
        if not nm.startswith("cland_fstart_in_") or not isinstance(xy, (list, tuple)) or len(xy) != 2:
            continue
        d = round(abs(float(xy[0]) - o[0]) + abs(float(xy[1]) - o[1]), 1)
        if d > LEG_UM:
            out.append(("cland_origin", "reader_start_" + nm[len("cland_fstart_in_"):], d, 0))
    return sorted(out, key=lambda h: -h[2])


def leg405_zero(t):
    return [(r.get("inst"), r.get("port"), r.get("path_um"), r.get("D")) for r in t.get("relay_depth") or []
            if isinstance(r, dict) and _num(r.get("path_um")) and r["path_um"] > LEG_UM and not (r.get("stages_existing") or 0)] \
        + cland_reader_legs(t)


def staged_short(r, limit=LEG_UM):
    """stations missing on one relay_depth entry: ceil(path_um / limit) - 1 stations make every hop <= limit, stages_existing + D are
    the stations the plan already carries (relay_depth.py rows are D = needed - existing).  0 = compliant by construction"""
    p = r.get("path_um")
    if not _num(p) or p <= limit:
        return 0
    need = int(-(-p // limit)) - 1
    return max(0, need - int(r.get("stages_existing") or 0) - int(r.get("D") or 0))


def _xy(v):
    return (float(v[0]), float(v[1])) if isinstance(v, (list, tuple)) and len(v) >= 2 and _num(v[0]) and _num(v[1]) else None


def _md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _short_hop(d, limit=LEG_UM):
    """stations a hop of d um still lacks between its two ends (a bare hop carries none): ceil(d / limit) - 1"""
    return int(-(-d // limit)) - 1 if d > limit + TOL else 0


def _pin_xy(t):
    c = (t.get("clock") or {}).get("landing_contract") or {}
    return {p["name"]: _xy(p.get("xy_um")) for p in c.get("pins") or [] if isinstance(p, dict) and p.get("name") and _xy(p.get("xy_um"))}


def _origin_xy(t):
    """cland origin seat: landing_reader_start.origin_rect_um centre, else the raw-branch origin stage"""
    r = ((t.get("clock") or {}).get("landing_reader_start") or {}).get("origin_rect_um")
    if isinstance(r, (list, tuple)) and len(r) == 4 and all(_num(v) for v in r):
        return (r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0
    return cland_origin_xy(t)


def _chain(kind, tag, start, stages, end, end_tag, limit=LEG_UM):
    """hops of start -> stages -> end ((None ends are skipped), each > limit flagged; -> (findings, legs measured)"""
    pts_ = [("start", start)] + [(f"s{k}", _xy(s.get("xy_um")) if isinstance(s, dict) else None) for k, s in enumerate(stages)] + [(end_tag, end)]
    out, n = [], 0
    for (an, a), (bn, b) in zip(pts_, pts_[1:]):
        if a is None or b is None:
            continue
        n += 1
        d = round(_md(a, b), 1)
        if d > limit + TOL:
            out.append((f"{kind}:{tag}.{an}", bn, d, 0, _short_hop(d, limit)))
    return out, n


def leg405_measure(t):
    """C-LEG405 cover: -> (findings, {kind: legs measured}).  Findings are (inst, port, um, D, stations short) like leg405_staged rows."""
    ck = t.get("clock") or {}
    fnd, cnt = [], {}

    def add(kind, res):
        f, n = res
        fnd.extend(f)
        if n:
            cnt[kind] = cnt.get(kind, 0) + n

    rows = [r for r in t.get("relay_depth") or [] if isinstance(r, dict) and _num(r.get("path_um"))]
    if rows:
        cnt["relay_depth"] = len(rows)
    fnd += [(r.get("inst"), r.get("port"), r.get("path_um"), r.get("D"), staged_short(r)) for r in rows if staged_short(r)]
    cl = cland_reader_legs(t)
    fnd += [h + (1,) for h in cl]
    pins = _pin_xy(t)
    origin = _origin_xy(t)
    if ck.get("landing_contract") and ck.get("landing_reader_start") is None and origin is not None:
        cnt["cland_origin"] = sum(1 for n in pins if n.startswith("cland_fstart_in_"))
    for key, pfx, kind in (("landing_reader_start", "cland_fstart_in_", "reader_start"), ("landing_writer_start", "cland_fstart_out_", "writer_start")):
        d = ck.get(key)
        for b, v in sorted(((d or {}).get("branches") or {}).items()) if isinstance(d, dict) else ():
            if isinstance(v, dict):
                add(kind, _chain(kind, b, origin, v.get("stages") or [], pins.get(pfx + b), pfx + b))
    for br in ck.get("landing_raw_branches") or []:
        if isinstance(br, dict) and br.get("stages"):
            st = br["stages"]
            add("raw_branch", _chain("raw_branch", str(br.get("name")), _xy(st[0].get("xy_um")), st[1:], None, "end"))
    anchors = [_xy(v) for v in (ck.get("landing_status_anchors") or {}).values() if _xy(v)]
    staged = ck.get("landing_status_input_stages") if isinstance(ck.get("landing_status_input_stages"), dict) else {}
    seen_agg = set()
    for tgt, rings in sorted(staged.items()):
        for ring, st in sorted((rings or {}).items()) if isinstance(rings, dict) else ():
            if not isinstance(st, list):
                continue
            src = pins.get("cland_dn_ready_" + ring) or pins.get("cland_up_ready_" + ring)
            if tgt == "agg":
                seen_agg.add(ring)
                last = _xy(st[-1].get("xy_um")) if st and isinstance(st[-1], dict) else src
                end = min(anchors, key=lambda a: _md(a, last)) if anchors and last else None
            else:
                end = pins.get("cland_up_ready_" + tgt)
            add("status_stage", _chain("status", f"{tgt}/{ring}", src, st, end, "agg" if tgt == "agg" else tgt))
    # status rings (collector children) with no input stages: the face pin reaches the nearest agg anchor in one hop
    for ch in ((ck.get("landing_contract") or {}).get("collector_children") or []):
        if isinstance(ch, dict) and ch.get("bus") not in seen_agg and anchors:
            src = pins.get("cland_dn_ready_" + str(ch.get("bus"))) or _xy(ch.get("xy"))
            if src and not ch.get("seam"):
                end = min(anchors, key=lambda a: _md(a, src))
                add("status_stage", _chain("status", f"agg/{ch.get('bus')}(unstaged)", src, [], end, "agg"))
    for i, s in enumerate(t.get("internal_stations") or []):
        if not isinstance(s, dict):
            continue
        a, b = _xy(s.get("from_um")), _xy(s.get("to_um"))
        regs = [_xy(r) for r in s.get("regs_um") or [] if isinstance(r, (list, tuple)) and _xy(r)]
        conn = str(s.get("conn") or i)
        pair = "|" in conn
        kind = "macro_pair" if pair else "station"
        f, n = _chain(kind, conn, a, [{"xy_um": r} for r in regs], b, "to")
        if pair and a and b and len(regs) <= 1 and _md(a, b) > 2 * LEG_UM + TOL:
            f = [(x[0] + "[IMPOSSIBLE >810 um with <=1 stage]",) + x[1:] for x in f] or [(f"{kind}:{conn}[IMPOSSIBLE >810 um with <=1 stage]", "to", round(_md(a, b), 1), 0, _short_hop(_md(a, b)) - len(regs))]
        add(kind, (f, n))
    return fnd, cnt


def leg405_unchecked(t, cnt):
    """leg kinds this type carries that the check cannot measure (plan holds no coordinates for the far end): [description]"""
    ck = t.get("clock") or {}
    out = []
    hc = [h for h in t.get("hard_cores") or [] if isinstance(h, dict)]
    if hc:
        out.append(f"macro-pin-to-pin data legs ({len(hc)} hard cores; the plan has no pin-level netlist, only reg-pair stations {cnt.get('macro_pair', 0)} are measured)")
    if t.get("relay_sites") and not t.get("relay_depth"):
        out.append(f"relay_sites legs ({len(t['relay_sites'])} sites, no relay_depth rows)")
    rta = (ck.get("reset_tree_anchor") or {}).get("relays")
    if isinstance(rta, dict) and rta:
        out.append(f"reset relay -> sink legs ({len(rta)} relays, no sink coordinates)")
    for k, nm in (("ft_slots", "ft_slots"),):
        if t.get(k):
            out.append(f"{nm} hops ({len(t[k])})")
    sk = [x for key in ("sink_sites_um", "reach_fix_sinks") for x in (ck.get(key) or [])]
    if sk:
        out.append(f"clock sink legs ({len(sk)})")
    return out


def leg405_staged(t):
    """C-LEG405-R2 + cover: staged-aware LEG405-ZERO.  LEG405-ZERO ignores D, so every relay_depth row the generator already staged is a false
    positive (S81 plan_t14_b8_coll0_1125: 1638 of 1644 flagged legs carry stations_existing + D >= ceil(path / 405) - 1).  Flags relay_depth
    entries still short of that count, the cland origin -> reader_start legs, and (cover) every measurable hop of the landing start chains,
    status input stages and station chains: see leg405_measure."""
    return leg405_measure(t)[0]


def relay_seats(t):
    rects = G.hard_rects(t)
    sites = (t.get("relay_sites") or {})
    inside, stack = [], {}
    for n, p in sites.items():
        try:
            x, y = float(p[0]), float(p[1])
        except (TypeError, ValueError, IndexError):
            continue
        for x0, y0, x1, y1, nm in rects:
            if x0 + 0.5 < x < x1 - 0.5 and y0 + 0.5 < y < y1 - 0.5:
                inside.append((n, nm))
                break
        stack.setdefault((round(x, 1), round(y, 1)), []).append(n)
    stacked = [(k, len(v)) for k, v in stack.items() if len(v) > RELAY_STACK]
    return inside, stacked


def _free_area(bx0, by0, bx1, by1, W, H, rects):
    x1, y1 = min(bx1, W), min(by1, H)
    a = max(0.0, x1 - bx0) * max(0.0, y1 - by0)
    for r in rects:
        ox = min(x1, r[2]) - max(bx0, r[0])
        oy = min(y1, r[3]) - max(by0, r[1])
        if ox > 0 and oy > 0:
            a -= ox * oy
    return max(a, 0.0)


def seat_density(t):
    o = t.get("outline_um")
    if not o:
        return []
    W, H = o
    rects = G.hard_rects(t)
    fl = {}

    def add(x, y, bits):
        k = (int(x // BIN_UM), int(y // BIN_UM))
        fl[k] = fl.get(k, 0) + bits
    for s in t.get("internal_stations") or []:
        if isinstance(s, dict):
            b = int(s.get("bits") or 0)
            for x, y in pts(s.get("regs_um")):
                add(x, y, b)
    for s in t.get("ft_slots") or []:
        if isinstance(s, dict):
            b = int(s.get("width") or 0)
            for x, y in pts(s.get("regs_um")):
                add(x, y, b)
    out = []
    for (i, j), n in fl.items():
        fa = _free_area(i * BIN_UM, j * BIN_UM, (i + 1) * BIN_UM, (j + 1) * BIN_UM, W, H, rects)
        if fa < 100.0:
            fa = 100.0
        u = n * CELL_UM2 / fa
        if u > DENS_MAX:
            out.append((round(u, 2), n, (i * BIN_UM, j * BIN_UM)))
    return sorted(out, reverse=True)


def _core_pin_points(t):
    """[(inst, pin, bits, x, y)] of station endpoints at a core pin: launch at from_um, capture at to_um"""
    out = []
    for s in t.get("internal_stations") or []:
        if not isinstance(s, dict):
            continue
        b = int(s.get("bits") or 0)
        for key, xy in (("launch", s.get("from_um")), ("capture", s.get("to_um"))):
            v = str(s.get(key) or "")
            if v.startswith("core:") and xy and len(xy) >= 2:
                inst = v[5:].rsplit(".", 1)[0]
                out.append((inst, v[5:], b, float(xy[0]), float(xy[1])))
    return out


def _face_clear(rect, face, rects, W, H, lo=None, hi=None):
    """clearance in front of a face of rect: nearest other rect overlapping the lateral span [lo, hi] (default the whole face), else the outline"""
    x0, y0, x1, y1 = rect[:4]
    best = {"W": x0, "E": W - x1, "S": y0, "N": H - y1}[face]
    for r in rects:
        if r is rect:
            continue
        if face in "WE":
            a, b = (lo, hi) if lo is not None else (y0, y1)
            if min(b, r[3]) - max(a, r[1]) <= 0:
                continue
            g = (x0 - r[2]) if face == "W" else (r[0] - x1)
        else:
            a, b = (lo, hi) if lo is not None else (x0, x1)
            if min(b, r[2]) - max(a, r[0]) <= 0:
                continue
            g = (y0 - r[3]) if face == "S" else (r[1] - y1)
        if g >= -TOL:
            best = min(best, max(g, 0.0))
    return best


def _face_of(rect, x, y, tol=1.0):
    x0, y0, x1, y1 = rect[:4]
    if not (x0 - tol <= x <= x1 + tol and y0 - tol <= y <= y1 + tol):
        return None
    d = {"W": abs(x - x0), "E": abs(x - x1), "S": abs(y - y0), "N": abs(y - y1)}
    f = min(d, key=d.get)
    return f if d[f] <= tol else None


def pin_face_clear(t):
    o = t.get("outline_um")
    if not o:
        return []
    W, H = o
    rects = G.hard_rects(t)
    byname = {r[4]: r for r in rects}
    agg = {}
    for inst, pin, bits, x, y in _core_pin_points(t):
        r = byname.get(inst)
        if not r:
            continue
        f = _face_of(r, x, y)
        if not f:
            continue
        lo, hi = (y - 0.5, y + 0.5) if f in "WE" else (x - 0.5, x + 0.5)
        c = _face_clear(r, f, rects, W, H, lo, hi)
        if c < CLEAR_PIN_UM:
            k = (inst, f)
            a = agg.setdefault(k, [0, c])
            a[0] += bits
            a[1] = min(a[1], c)
    return sorted(((round(c, 2), bits, inst, f) for (inst, f), (bits, c) in agg.items()), key=lambda r: (r[0], -r[1]))


def hub_box(t):
    o = t.get("outline_um")
    if not o:
        return []
    W, H = o
    rects = G.hard_rects(t)
    byname = {r[4]: r for r in rects}
    bits = {}
    for inst, pin, b, x, y in _core_pin_points(t):
        bits[inst] = bits.get(inst, 0) + b
    out = []
    for inst, n in bits.items():
        r = byname.get(inst)
        if not r or n <= HUB_BITS:
            continue
        cl = {f: _face_clear(r, f, rects, W, H) for f in "WESN"}
        ok = sum(1 for v in cl.values() if v >= CLEAR_HUB_UM)
        if ok < 2:
            out.append((n, inst, {f: round(v, 1) for f, v in cl.items()}))
    return sorted(out, reverse=True)


def _seg_inside_len(p, q, r):
    """length of segment p-q inside the open rect r (Liang-Barsky)"""
    (x0, y0), (x1, y1) = p, q
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, x0 - r[0]), (dx, r[2] - x0), (-dy, y0 - r[1]), (dy, r[3] - y0)):
        if pp == 0:
            if qq <= 0:
                return 0.0
        else:
            tt = qq / pp
            if pp < 0:
                t0 = max(t0, tt)
            else:
                t1 = min(t1, tt)
            if t0 >= t1:
                return 0.0
    return (t1 - t0) * (dx * dx + dy * dy) ** 0.5


def ft_clear(t):
    rects = G.hard_rects(t)
    out = []
    for s in t.get("ft_slots") or []:
        if not isinstance(s, dict):
            continue
        regs = list(pts(s.get("regs_um")))
        tot, worst, n = 0.0, None, 0
        for a, b in zip(regs, regs[1:]):
            for r in rects:
                L = _seg_inside_len(a, b, r)
                if L > FT_OVER_UM:
                    tot += L
                    n += 1
                    if worst is None or L > worst[0]:
                        worst = (L, r[4])
        if n:
            out.append((s.get("name"), int(s.get("width") or 0), n, round(tot), worst[1]))
    return out


def tap_step_dup(t):
    taps = [(float(a["xy"][0]), float(a["xy"][1]), a.get("name")) for a in (t.get("clock") or {}).get("added_taps") or []
            if isinstance(a, dict) and a.get("xy")]
    g = {}
    for x, y, n in taps:
        g.setdefault((int(x // TAP_STEP_UM), int(y // TAP_STEP_UM)), []).append((x, y, n))
    out = []
    for (i, j), v in g.items():
        for a in v:
            for di in (0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj < 0:
                        continue
                    for b in g.get((i + di, j + dj), []):
                        if a is b or (di == 0 and dj == 0 and a[2] >= b[2]):
                            continue
                        d = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
                        if d < TAP_STEP_UM:
                            out.append((round(d, 1), a[2], b[2]))
    return sorted(out)


def band_at_pin(t):
    rects = G.hard_rects(t)
    out = []
    for n, b in (((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}).items():
        if not isinstance(b, dict):
            continue
        hop = b.get("max_pin_to_band_hop_um")
        r = b.get("rect_um")
        ov = None
        if r and len(r) == 4:
            for c in rects:
                if min(r[2], c[2]) - max(r[0], c[0]) > 1.0 and min(r[3], c[3]) - max(r[1], c[1]) > 1.0:
                    ov = c[4]
                    break
        if (_num(hop) and hop > BAND_HOP_UM) or ov:
            out.append((n, hop, ov))
    return out


def seat_unique(t):
    g = {}
    for i, s in enumerate(t.get("internal_stations") or []):
        if isinstance(s, dict):
            for x, y in set(pts(s.get("regs_um"))):
                g.setdefault((round(x, 1), round(y, 1)), set()).add(i)
    return sorted(((len(v), k) for k, v in g.items() if len(v) >= SEAT_STACK), reverse=True)


def _types(raw):
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if isinstance(t, dict):
            yield tn, t


def _run(check, fn, fmt, raw):
    out, n = [], 0
    for tn, t in _types(raw):
        v = fn(t, tn, raw)
        if v:
            n += 1
            out.append(_w(check, tn, f"{len(v)} finding(s):", "; ".join(fmt(x) for x in v[:MAX_EX]) + (" ..." if len(v) > MAX_EX else "")))
    return out + [_w(check, f"summary {n} types flagged (report only)")]


def _f_in_outline(raw, plan_path, tree=None, **_k):
    return _run("IN-OUTLINE", lambda t, tn, r: in_outline(t, tn, r),
                lambda h: f"{h[1]} {h[0]}(s) outside, worst +{h[2]} um", raw)


def _f_leg(raw, plan_path, tree=None, **_k):
    return _run("LEG405-ZERO", lambda t, tn, r: leg405_zero(t), lambda h: f"{h[0]}.{h[1]} path {h[2]} um D={h[3]} 0 stages", raw)


def _f_leg_staged(raw, plan_path, tree=None, **_k):
    lines, unchecked, kinds = [], [], {}
    n = 0
    for tn, t in _types(raw):
        v, cnt = leg405_measure(t)
        for k, c in cnt.items():
            kinds[k] = kinds.get(k, 0) + c
        if v:
            n += 1
            lines.append(_w("LEG405-STAGED", tn, f"{len(v)} finding(s):",
                            "; ".join(f"{h[0]}.{h[1]} path {h[2]} um D={h[3]} short {h[4]} station(s)" for h in v[:MAX_EX]) + (" ..." if len(v) > MAX_EX else "")))
        u = leg405_unchecked(t, cnt)
        if u:
            unchecked.append(f"WARN LEG405-STAGED-UNCHECKED {tn}: " + "; ".join(u))
    summ = _w("LEG405-STAGED", f"summary {n} types flagged (report only); legs measured " + (", ".join(f"{k}={v}" for k, v in sorted(kinds.items())) or "none")
              + f"; {len(unchecked)} type(s) carry legs the check cannot see (WARN LEG405-STAGED-UNCHECKED)")
    return lines + unchecked + [summ]


def _f_relay(raw, plan_path, tree=None, **_k):
    def fn(t, tn, r):
        ins, st = relay_seats(t)
        return [("inside core " + c, n) for n, c in ins] + [(f"{k} x{m} on one point", "") for k, m in st]
    return _run("RELAY-SEAT", fn, lambda h: f"{h[0]} {h[1]}".strip(), raw)


def _f_dens(raw, plan_path, tree=None, **_k):
    return _run("SEAT-DENSITY", lambda t, tn, r: seat_density(t), lambda h: f"bin {h[2]} util {h[0]} ({h[1]} flops)", raw)


def _f_pin(raw, plan_path, tree=None, **_k):
    return _run("PIN-FACE-CLEAR", lambda t, tn, r: pin_face_clear(t), lambda h: f"{h[2]} {h[3]} face {h[0]} um clear ({h[1]} bits)", raw)


def _f_hub(raw, plan_path, tree=None, **_k):
    return _run("HUB-BOX", lambda t, tn, r: hub_box(t), lambda h: f"{h[1]} {h[0]} bits clear {h[2]}", raw)


def _f_ft(raw, plan_path, tree=None, **_k):
    return _run("FT-CLEAR", lambda t, tn, r: ft_clear(t), lambda h: f"{h[0]} ({h[1]} b) {h[2]} hop(s) over cores {h[3]} um, worst {h[4]}", raw)


def _f_tap(raw, plan_path, tree=None, **_k):
    return _run("TAP-STEP-DUP", lambda t, tn, r: tap_step_dup(t), lambda h: f"{h[1]}/{h[2]} {h[0]} um apart", raw)


def _f_band(raw, plan_path, tree=None, **_k):
    return _run("BAND-AT-PIN", lambda t, tn, r: band_at_pin(t), lambda h: f"{h[0]} pin hop {h[1]} um" + (f", overlaps {h[2]}" if h[2] else ""), raw)


def _f_seat(raw, plan_path, tree=None, **_k):
    return _run("SEAT-UNIQUE", lambda t, tn, r: seat_unique(t), lambda h: f"{h[0]} stations at {h[1]}", raw)


F = {"IN-OUTLINE": _f_in_outline, "LEG405-ZERO": _f_leg, "LEG405-STAGED": _f_leg_staged, "RELAY-SEAT": _f_relay, "SEAT-DENSITY": _f_dens,
     "PIN-FACE-CLEAR": _f_pin, "HUB-BOX": _f_hub, "FT-CLEAR": _f_ft, "TAP-STEP-DUP": _f_tap, "BAND-AT-PIN": _f_band, "SEAT-UNIQUE": _f_seat}
findings_by_check = {k: G._safe(k, v) for k, v in F.items()}

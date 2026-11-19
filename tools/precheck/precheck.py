#!/usr/bin/env python3
"""precheck.py -- PRECHECK-1119 (owner 11-19): fast STATIC pre-build estimator over every type of a die plan.

  precheck.py --die DIE --plan PLAN.json [--types GLOB] --out DIR [--tools DIR] [--checks a,b] [--known FILE]

It is an ESTIMATOR, not a gate (owner r703/r704): it never blocks, holds or approves.  It reads the plan (and the
die_plan tools that the kits use: schema, taps, gen_phys) and writes, per type, the findings of the failure classes
seen on 11-18:

  REACH       a station chain hop (internal_stations from -> regs -> to, ft_slots in pin -> regs -> out pin,
              relay_polylines) longer than the per-cycle reach (405 um, Manhattan).
  MISAIM      a face-bus receiver chain (internal_stations conn bus:X, launch "face flop") sited toward a capture pin
              that carries a small fraction of the bus bits (col_h9_r1 frame_int_i1 -> 1-bit u_bn5.rs, 1,100 bits end
              at t3_payload): the chain heads to the wrong sink centroid.
  TAP-CAP     planned clock sinks (taps.sink_sites: face / ft / station registers, plus the plan's sink bins) on the
              nearest tap above the CTS cap (clock.tap_max_sinks, else 1200).
  TAP-COVER   free area (outline minus hard cores) farther than clock.tap_radius_um (200) from every tap: GPL can put
              flops there and they stay on the root tap (KV kv3_pv_v8: clk keeps 10,056 sinks, clk_t34 10,234).
  TAP-EDGE    the non-core taps sit on one or two edges only and none in the interior (S81 leaf t25: 9 taps on W/S).
  FACE-BANK   an N/S face bank under budgets.face_flop_ns_types row_stride > 1 that cannot take its face-near
              stations inside the 27 um retention of face_flops.tcl ff_put_near ("NS face bank cannot fit").
  RESET-FANOUT a type whose boundary registers (bus + ft + station bits) exceed 2,000 with no reset relay structure
              in the plan (S81 phy__t1: ~11k RESETN pins on one raw net).
  STALE-BINS  (with --kit-sinks) the clock sinks the newest kit saw (clock_taps.tcl OT_CLOCK_TAPS line, kit_sinks.py)
              differ from the plan's clock.sink_bins_file count by more than 10 %: density taps follow the stale bins and
              the new flops land on the root tap (KV kv3_pv_v8: bins 99,260, kit 120,625 -> clk 10,056, clk_t34 10,234).
  BOUNDARY-REG (CBC r713) a port bit with no planned register (taps.planned_sinks) within 50 um of its pin.
  Thresholds come from tools/die_plan/cbc_rules.py (owner r713 close-by-construction), shared with the CBC generator:
  reach 300 um per hop, tap <= 1,000 sinks, reset leaf <= 32, boundary register <= 50 um, aim >= 10 % of the bus bits,
  depth <= 13 levels (precheck_synth).
  FOLD / DEPTH (precheck_synth.py, optional): station registers merged by synthesis; logic depth per D cone.

Outputs in --out: findings.tsv (type, check, value, threshold, family, detail), family_summary.md, suggested_rows.json
(plan rows where the fix is a plan row), and precheck.json (run record).
"""
import argparse
import collections
import contextlib
import io
import fnmatch
import json
import math
import re
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "die_plan"))
import cbc_rules as CBC  # noqa: E402  owner r713 close-by-construction: ONE rule module shared with the CBC generator
sys.path.pop(0)
REACH_UM = CBC.REACH_UM_PER_HOP
TAP_CAP = CBC.TAP_MAX_SINKS
TAP_RADIUS_UM = CBC.TAP_RADIUS_UM
RESET_FLOPS = 2000
RESET_LEAF = CBC.RESET_LEAF_MAX_FANOUT
BOUNDARY_UM = CBC.BOUNDARY_REG_UM
FF_CPITCH_UM = 2.16      # face_flops.tcl ff_cpitch = 40 sites x 0.054 um
FF_ROW_UM = 0.27
FF_RETENTION_UM = 27.0   # ff_put_near: |dx| + |dy| <= 27 um around the request
FF_NEAR_FACE_UM = 10.0   # a request within 10 um of the N/S face takes the face-bank search
FF_DEPTH_ROWS = 120
CHECKS = ("REACH", "MISAIM", "TAP-CAP", "TAP-COVER", "TAP-EDGE", "STALE-BINS", "BOUNDARY-REG", "FACE-BANK", "RESET-FANOUT")
STALE_FRAC = CBC.SINK_BINS_STALE_FRAC
# COORD 11-19: checks that do not predict on a die (they flag signed types there) are off for it.  QC: TAP-COVER flagged
# 15 of 27 signed, plan-coordinate REACH 6 of 27 -> QC reach comes from the placed-hop kit scan (kit_scan.py) only.
DIE_SKIP = {"qwen_compute": {"TAP-COVER", "REACH"}}


def bins_count(ctx, ck):
    """sink count recorded in the plan's clock.sink_bins_file (its n, else the sum of the bin weights), or None"""
    f = ck.get("sink_bins_file")
    if not f:
        return None
    pd = Path(ctx.plan_path).resolve().parent
    cands = [pd / f, pd / Path(f).name, pd / "sink_bins" / Path(f).name]
    for anc in pd.parents:                      # repo-relative paths (physical/die_plan/<die>/...)
        cands.append(anc / f)
    for c in cands:
        if c.is_file():
            try:
                d = json.loads(c.read_text())
            except ValueError:
                return None
            if isinstance(d, dict):
                if d.get("n"):
                    return int(d["n"])
                b = d.get("bins") or []
                return int(sum((x[2] if isinstance(x, (list, tuple)) and len(x) > 2 else 1) for x in b)) or None
            return None
    return None


def stale_bins(plan_n, kit, frac=STALE_FRAC):
    """(ratio, detail) when the kit's sink count differs from the plan bins by more than frac"""
    if not plan_n or not kit or not kit.get("sinks"):
        return None
    r = kit["sinks"] / plan_n
    if abs(r - 1) <= frac:
        return None
    return round(r, 3), (f"kit saw {kit['sinks']} clock sinks over {kit.get('taps')} taps, plan sink_bins hold {plan_n} "
                         f"({r:.2f}x); density taps follow stale bins (refresh sink_bins from the newest placed kit: {kit.get('log', '?')})")


def family(t):
    return re.split(r"__(?:t\d+|cl[0-9a-f]{6,}|pv[0-9a-f]{6,})", t)[0]


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def face_point(face, window, w, h, toward=None):
    """the point of a face window [lo, hi] (along the face) nearest `toward` (else its centre) on face N/S/E/W"""
    lo, hi = sorted((float(window[0]), float(window[1])))
    c = (lo + hi) / 2.0
    if toward is not None:
        c = min(hi, max(lo, toward[0] if face in "NS" else toward[1]))
    return {"N": (c, h), "S": (c, 0.0), "E": (w, c), "W": (0.0, c)}[face]


# ---------------------------------------------------------------- pure geometry checks (unit tested)

def chain_hops(points):
    return [man(a, b) for a, b in zip(points, points[1:])]


WIDE_BITS = 256
# Reach is 405 um on PLACED hops (CBC.REACH_UM_PER_HOP; placed_hops.py measures it on 3_place.odb).  On PLAN
# coordinates the limit carries the 11-19 calibration on 43 signed S81 types: widest signed hop on a >= 256-bit chain
# 436.8 um (slice_station t27/t37) -> x 1.085; narrow chains up to 501.9 um (t37 ft7, 32 b) -> x 1.25.
WIDE_MARGIN = 1.085
NARROW_MARGIN = 1.25


def reach_findings(t, reach=REACH_UM, margin=None):
    """[(value, detail)] station hops above the calibrated limit: reach x 1.085 on >= 256-bit chains, reach x 1.25 on
    narrower ones (margin overrides both).  internal_stations from -> regs -> to, ft_slots in pin -> regs -> out pin."""
    w, h = t.get("outline_um") or (0, 0)
    out = []
    widths = {b.get("name"): int(b.get("width") or 0) for b in t.get("buses") or []}

    def limit(bits):
        if margin is not None:
            return reach * margin
        return reach * (WIDE_MARGIN if (bits or 0) >= WIDE_BITS else NARROW_MARGIN)
    for i, e in enumerate(t.get("internal_stations") or []):
        if not e.get("from_um") or not e.get("to_um"):
            continue
        pts = [tuple(e["from_um"])] + [tuple(r) for r in (e.get("regs_um") or [])] + [tuple(e["to_um"])]
        hops = chain_hops(pts)
        conn = e.get("conn", "")
        bits = int(e.get("bits") or 0) or widths.get(conn[4:] if conn.startswith("bus:") else "", 0)
        if hops and max(hops) > limit(bits):
            j = max(range(len(hops)), key=hops.__getitem__)
            out.append((round(max(hops), 1), f"internal_stations[{i}] {e.get('conn', '')} bits {e.get('bits', '?')} hop {j} "
                        f"{pts[j]} -> {pts[j + 1]} ({len(hops)} hops)"))
    for s in t.get("ft_slots") or []:
        regs = s.get("regs_um") or []
        k = int(s.get("stations", 1) or 1)
        if not (s.get("in_face") and s.get("out_face") and s.get("in_window_um") and s.get("out_window_um")):
            continue
        if len(regs) < k - 1:
            continue          # stations spread along the slot route by the kit: hop = L / k, checked by gen_phys
        mid = [tuple(r) for r in regs[-(k - 1):]] if k > 1 else []
        a = face_point(s["in_face"], s["in_window_um"], w, h, mid[0] if mid else None)
        b = face_point(s["out_face"], s["out_window_um"], w, h, mid[-1] if mid else None)
        pts = [a] + mid + [b]
        hops = chain_hops(pts)
        if hops and max(hops) > limit(int(s.get("width") or 0)):
            j = max(range(len(hops)), key=hops.__getitem__)
            out.append((round(max(hops), 1), f"ft_slot {s.get('name')} width {s.get('width')} hop {j} {pts[j]} -> {pts[j + 1]}"))
    # relay_polylines are not checked: the kit places relay_depth relays along each polyline at <= max_hop_um
    return out


def tap_assign(taps_xy, sinks):
    """{tap name: weight} nearest (Euclidean) tap per sink; taps_xy [(name, x, y)], sinks [(x, y, w)]"""
    cnt = collections.Counter()
    if not taps_xy:
        return cnt
    # bucket taps on a coarse grid for speed
    cell = 100.0
    grid = collections.defaultdict(list)
    for n, x, y in taps_xy:
        grid[(int(x // cell), int(y // cell))].append((n, x, y))
    for x, y, wt in sinks:
        cx, cy = int(x // cell), int(y // cell)
        best = None
        for rad in range(0, 64):
            cand = [tp for dx in range(-rad, rad + 1) for dy in range(-rad, rad + 1)
                    if max(abs(dx), abs(dy)) == rad for tp in grid.get((cx + dx, cy + dy), ())]
            for n, a, b in cand:
                d = (a - x) ** 2 + (b - y) ** 2
                if best is None or d < best[0]:
                    best = (d, n)
            if best is not None and math.sqrt(best[0]) <= rad * cell:
                break
        if best is None:
            best = min(((a - x) ** 2 + (b - y) ** 2, n) for n, a, b in taps_xy)
        cnt[best[1]] += wt
    return cnt


def tap_rebalance(taps_xy, load, cap, radius):
    """clock_taps.tcl cap pass: move a tap's excess to taps with room within `radius` (Euclidean, tap to tap);
    -> {tap: load left over cap}"""
    xy = {n: (x, y) for n, x, y in taps_xy}
    left = dict(load)
    for n in sorted(left, key=lambda k: -left[k]):
        ex = left[n] - cap
        if ex <= 0:
            continue
        x, y = xy[n]
        for m in sorted((m for m in xy if m != n), key=lambda m: (xy[m][0] - x) ** 2 + (xy[m][1] - y) ** 2):
            if (xy[m][0] - x) ** 2 + (xy[m][1] - y) ** 2 > radius * radius or ex <= 0:
                break
            room = cap - left.get(m, 0)
            if room > 0:
                mv = min(room, ex)
                left[m] = left.get(m, 0) + mv
                left[n] -= mv
                ex -= mv
    return {n: v - cap for n, v in left.items() if v > cap}


def core_rects(t):
    out = []
    for c in t.get("hard_cores") or []:
        o, s = c.get("origin_um"), c.get("outline_um")
        if not o or not s:
            continue
        sw, sh = s
        if str(c.get("orient", "R0")) in ("R90", "R270", "MXR90", "MYR90"):
            sw, sh = sh, sw
        out.append((o[0], o[1], o[0] + sw, o[1] + sh))
    return out


def in_rects(x, y, rects):
    return any(a <= x <= c and b <= y <= d for a, b, c, d in rects)


def tap_cover(t, taps_xy, radius, step=10.0):
    """(uncovered free area um2, free area um2, centroid of uncovered) for taps_xy over the free outline"""
    w, h = t.get("outline_um") or (0, 0)
    rects = core_rects(t)
    free = unc = 0
    sx = sy = 0.0
    r2 = radius * radius
    pts = [(x, y) for _, x, y in taps_xy]
    cell = max(radius, 50.0)
    grid = collections.defaultdict(list)
    for x, y in pts:
        grid[(int(x // cell), int(y // cell))].append((x, y))
    y = step / 2
    while y < h:
        x = step / 2
        while x < w:
            if not in_rects(x, y, rects):
                free += 1
                cx, cy = int(x // cell), int(y // cell)
                ok = any((a - x) ** 2 + (b - y) ** 2 <= r2 for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                         for a, b in grid.get((cx + dx, cy + dy), ()))
                if not ok:
                    unc += 1
                    sx += x
                    sy += y
            x += step
        y += step
    a = step * step
    return unc * a, free * a, ((sx / unc, sy / unc) if unc else None)


def tap_span(t, taps_xy):
    """(x span / width, y span / height) of the taps"""
    w, h = t.get("outline_um") or (1, 1)
    xs = [x for _, x, _ in taps_xy]
    ys = [y for _, _, y in taps_xy]
    return (max(xs) - min(xs)) / w, (max(ys) - min(ys)) / h


def tap_edges(t, taps_xy, band_frac=0.12):
    """(edges used, interior taps) of the non-core taps: a tap within band_frac x min(w,h) of an edge is an edge tap"""
    w, h = t.get("outline_um") or (0, 0)
    band = band_frac * min(w, h)
    edges = set()
    interior = 0
    for _, x, y in taps_xy:
        e = [f for f, d in (("W", x), ("E", w - x), ("S", y), ("N", h - y)) if d <= band]
        if e:
            edges.update(e)
        else:
            interior += 1
    return edges, interior


# ---------------------------------------------------------------- plan adapters

class Ctx:
    def __init__(self, P, raw, plan_path, tools):
        self.P, self.raw, self.plan_path = P, raw, Path(plan_path)
        self.tools = tools
        self.pin_cache = {}

    def pins_of_core(self, core):
        pf = core.get("pins_file")
        if not pf:
            return None
        if pf in self.pin_cache:
            return self.pin_cache[pf]
        d = None
        for base in (self.plan_path.parent, self.plan_path.parent.parent, self.plan_path.parent.parent.parent):
            p = base / pf
            if p.is_file():
                try:
                    d = json.loads(p.read_text())
                except ValueError:
                    d = None
                break
        self.pin_cache[pf] = d
        return d


def pin_width(pins_doc, pin):
    if not pins_doc:
        return None
    n = 0
    for p in pins_doc.get("pins", []):
        nm = p.get("name", "")
        if nm == pin or re.fullmatch(re.escape(pin) + r"\[\d+\]", nm):
            n += 1
    return n or None


def misaim_findings(ctx, t, frac=CBC.AIM_MIN_BIT_FRAC, min_bits=CBC.AIM_MIN_BITS):
    out = []
    widths = {b.get("name"): int(b.get("width") or 0) for b in t.get("buses") or []}
    cores = {c.get("inst"): c for c in t.get("hard_cores") or []}
    for i, e in enumerate(t.get("internal_stations") or []):
        conn = e.get("conn", "")
        if not conn.startswith("bus:") or e.get("launch") != "face flop":
            continue
        bus = conn[4:]
        W = widths.get(bus) or int(e.get("bits") or 0)
        cap = e.get("capture", "")
        if W < min_bits or "." not in cap:
            continue
        inst, pin = cap.rsplit(".", 1)
        core = cores.get(inst)
        if core is None and cap in cores:
            continue                      # whole-core capture: width unknown here
        cw = pin_width(ctx.pins_of_core(core), pin) if core else None
        if cw is None:
            continue
        if cw < frac * W:
            out.append((round(cw / W, 4), f"internal_stations[{i}] bus {bus} {W} b: chain sited toward {cap} ({cw} b); "
                        f"{len(e.get('regs_um') or [])} stages, to_um {e.get('to_um')}"))
    return out


def boundary_unregistered(pins, regs, radius=BOUNDARY_UM):
    """{port base: (bits with no register within radius (Manhattan), worst distance)} -- CBC both-side boundary rule.
    pins [(name, bit, layer, x, y, face)], regs [(x, y)] planned register sites"""
    cell = max(radius, 1.0)
    grid = collections.defaultdict(list)
    for x, y in regs:
        grid[(int(x // cell), int(y // cell))].append((x, y))
    out = {}
    for name, _bit, _ln, x, y, _f in pins:
        gx, gy = int(x // cell), int(y // cell)
        best = None
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for rx, ry in grid.get((gx + i, gy + j), ()):
                    d = abs(rx - x) + abs(ry - y)
                    best = d if best is None or d < best else best
        if best is None or best > radius:
            n, w = out.get(name, (0, 0.0))
            out[name] = (n + 1, max(w, best if best is not None else 2 * cell))
    return out


def boundary_findings(ctx, tn, radius=BOUNDARY_UM):
    import gen_phys as G
    import taps as T
    pins = G.type_pins(ctx.P, tn)
    regs = [(float(x), float(y)) for x, y, _ in T.planned_sinks(ctx.P, tn)]
    miss = boundary_unregistered(pins, regs, radius)
    if not miss:
        return []
    bits = sum(n for n, _ in miss.values())
    worst = sorted(miss.items(), key=lambda kv: -kv[1][0])
    return [(bits, f"{bits} of {len(pins)} port bits on {len(miss)} ports have no planned register within {radius:.0f} um "
             f"({', '.join(f'{k} {n}b' + (f' >{d:.0f}um' if d < 2 * radius else ' none near') for k, (n, d) in worst[:5])})")]


def reset_findings(t, limit=RESET_FLOPS, leaf=RESET_LEAF):
    """raw reset nets (no relay structure over `limit` register bits) and planned reset leaves above the CBC fanout"""
    out = []
    rs = t.get("reset") or {}
    for k in ("max_fanout", "leaf_fanout", "relay_fanout"):
        v = rs.get(k)
        if isinstance(v, (int, float)) and v > leaf:
            out.append((int(v), f"reset.{k} {v} > CBC leaf fanout {leaf}"))
    bits = sum(int(b.get("width") or 0) for b in t.get("buses") or [])
    bits += sum(int(s.get("width") or 0) * max(1, int(s.get("stations", 1) or 1)) for s in t.get("ft_slots") or [])
    bits += sum(int(e.get("bits") or 1) * len(e.get("regs_um") or []) for e in t.get("internal_stations") or [])
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    relay = any(rs.get(k) for k in ("relay_um", "local_relay_tree", "relay_tree")) or any(
        t.get(k) for k in ("reset_relay_full", "reset_replicate", "reset_spine_pins")) or bool(lc.get("collector_tree"))
    if bits > limit and not relay:
        out.append((bits, f"~{bits} boundary/station register bits on the raw reset (reset {json.dumps(rs)[:120]}); no relay_um, "
                    f"reset_relay_full/replicate or collector_tree; CBC needs leaves of <= {leaf}"))
    return out


def taps_and_sinks(ctx, tn):
    import schema as S
    import taps as T
    P = ctx.P
    t = P.types[tn]
    grid = [(n, float(x), float(y)) for n, x, y in S.tap_grid(P, tn)]
    sinks = T.sink_sites(P, tn)
    return grid, sinks


def type_findings(ctx, tn, checks, opts):
    P = ctx.P
    t = P.types[tn]
    out = []

    def add(check, value, thr, detail):
        out.append(dict(type=tn, check=check, value=value, threshold=thr, family=family(tn), detail=detail))

    if "REACH" in checks:
        for v, d in reach_findings(t, opts.reach):
            add("REACH", v, opts.reach, d)
    if "MISAIM" in checks:
        for v, d in misaim_findings(ctx, t):
            add("MISAIM", v, CBC.AIM_MIN_BIT_FRAC, d)
    if "RESET-FANOUT" in checks:
        for v, d in reset_findings(t, opts.reset_flops):
            add("RESET-FANOUT", v, opts.reset_flops, d)
    ck = t.get("clock") or {}
    if {"TAP-CAP", "TAP-COVER", "TAP-EDGE"} & set(checks) and not t.get("hard"):
        try:
            grid, sinks = taps_and_sinks(ctx, tn)
        except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
            add("TAP-ERROR", 0, 0, f"{type(e).__name__}: {str(e)[:200]}")
            grid, sinks = [], []
        cap = min(int(ck.get("tap_max_sinks") or opts.tap_cap), opts.tap_cap)     # CBC r713: <= 1,000 per tap
        if "TAP-CAP" in checks and grid and sinks:
            cnt = tap_assign(grid, sinks)
            over = tap_rebalance(grid, cnt, cap, opts.tap_radius)
            if over:
                top = sorted(over.items(), key=lambda kv: -kv[1])
                need = sum(math.ceil((v + cap) / cap) - 1 for _, v in top)
                add("TAP-CAP", round(top[0][1] + cap), cap, f"{len(top)} taps over cap {cap} after the {opts.tap_radius:.0f}-um rebalance ("
                    f"{', '.join(f'{n} {round(v + cap)}' for n, v in top[:6])}); ~{need} added taps; {len(grid)} taps, "
                    f"{round(sum(cnt.values()))} planned sinks")
        # TAP-COVER only where the taps follow a sink inventory (tap_mode density): an explicit/grid type's taps are placed by
        # hand and 28 of 43 signed S81 types would flag (CALIBRATED 11-19); the KV pv root-tap class is density + stale bins
        if "TAP-COVER" in checks and grid and ck.get("tap_mode") == "density":
            rad = opts.tap_radius        # the kit's clock_taps.tcl reach (no tap with room within 200 um -> root tap)
            unc, free, cen = tap_cover(t, grid, rad)
            if free and unc / free > opts.cover_frac and unc > opts.cover_um2:
                add("TAP-COVER", round(unc / free, 3), opts.cover_frac,
                    f"{unc / 1e6:.3f} mm2 of {free / 1e6:.3f} mm2 free area > {rad:.0f} um from every tap "
                    f"(centroid {tuple(round(c) for c in cen)}); flops placed there stay on the root tap")
        # TAP-EDGE only on explicit taps (density taps follow the sinks: kv3_sys_SD signed with an edge-only density set)
        if "TAP-EDGE" in checks and len(grid) >= 3 and ck.get("tap_mode") == "explicit":
            w, h = t.get("outline_um") or (0, 0)
            if min(w, h) > 2 * float(ck.get("tap_radius_um") or opts.tap_radius):
                fx, fy = tap_span(t, grid)
                if min(fx, fy) < opts.tap_span:
                    edges, interior = tap_edges(t, grid)
                    add("TAP-EDGE", round(min(fx, fy), 3), opts.tap_span,
                        f"{len(grid)} taps span {fx:.0%} of the width and {fy:.0%} of the height (edges {''.join(sorted(edges))}, "
                        f"{interior} interior; tap_mode {ck.get('tap_mode')}); outline {w}x{h}")
    if "STALE-BINS" in checks and getattr(opts, "kit_sinks_map", None) and tn in opts.kit_sinks_map:
        r = stale_bins(bins_count(ctx, ck), opts.kit_sinks_map[tn], opts.stale_frac)
        if r:
            add("STALE-BINS", r[0], opts.stale_frac, r[1])
    if "BOUNDARY-REG" in checks and not t.get("hard"):
        for v, d in boundary_findings(ctx, tn, opts.boundary_um):
            add("BOUNDARY-REG", v, opts.boundary_um, d)
    if "FACE-BANK" in checks:
        r = face_bank_check(ctx, tn, opts.bank_density, opts.bank_gap_um)
        if r:
            add("FACE-BANK", *r)
    return out


def ns_stride(raw, tn):
    """(stride, inset) of budgets.face_flop_ns_types for this type (key = type, its landing/param base, or a family prefix)"""
    ft = ((raw.get("budgets") or {}).get("face_flop_ns_types")) or {}
    t = raw["partition_types"][tn]
    for k in (tn, t.get("landing_base_type"), t.get("param_base_type"), family(tn)):
        if k and k in ft:
            e = ft[k]
            return int(e.get("row_stride", 1)), int(e.get("inset_rows", 0))
    for k, e in ft.items():
        if tn.startswith(k):
            return int(e.get("row_stride", 1)), int(e.get("inset_rows", 0))
    return 1, 0


def face_bank_features(pins, slots, lanes_in, cores, h):
    """(max face registers + face-near stations in any 3 adjacent 2.16-um station columns over the N and S faces,
    the smallest face-to-core gap under any N/S pin column, face and x of the densest columns)"""
    n3, where, gap = 0, (None, None), None
    for face in "NS":
        col = collections.Counter()
        for name, _bit, _ln, x, _y, f in pins:
            if f != face:
                continue
            base, sfx = (name[:-2], name[-2:]) if name[-2:] in ("_i", "_o") else (name, "")
            k = int(x / FF_CPITCH_UM)
            col[k] += 1
            if (base in slots and sfx == "_o") or name in lanes_in:
                col[k] += 1
        for k in list(col):
            s3 = col[k - 1] + col[k] + col[k + 1]
            if s3 > n3:
                n3, where = s3, (face, round(k * FF_CPITCH_UM, 1))
            x = k * FF_CPITCH_UM
            for a, b, c, d in cores:
                if a <= x <= c:
                    g = b if face == "S" else h - d
                    gap = g if gap is None or g < gap else gap
    return n3, gap, where[0], where[1]


def face_bank_check(ctx, tn, density=64, gap_um=45.0):
    """CALIBRATED RISK (D8e, 75 leaf types, 19 known 'NS face bank cannot fit'): a type whose budgets.face_flop_ns_types
    stride > 1 (the NS bank search is off at stride 1), with a dense N/S face (>= density face registers + face-near
    stations in 3 station columns) over a hard core within gap_um of that face.  The full face_flops.tcl occupancy
    (explicit reservations, PG pair rows) is not modelled; see the validation note in family_summary."""
    stride, inset = ns_stride(ctx.raw, tn)
    if stride <= 1 and inset <= 0:
        return None
    import gen_phys
    P = ctx.P
    t = P.types[tn]
    w, h = t["outline_um"]
    pins = gen_phys.type_pins(P, tn)
    slots = {s["name"] for s in t.get("ft_slots") or []}
    lanes_in = {b.get("name") for b in t.get("buses") or [] if b.get("dir") == "in"}
    n3, gap, face, x = face_bank_features(pins, slots, lanes_in, core_rects(t), h)
    if n3 >= density and gap is not None and gap <= gap_um:
        return (round(gap, 1), gap_um, f"stride {stride} inset {inset}: {n3} face registers + face-near stations in 3 station columns "
                f"(densest at {face} x={x}), a hard core {gap:.1f} um from an N/S face over pin columns (27 um retention); risk of 'NS face bank cannot fit'")
    return None


# ---------------------------------------------------------------- rows

def suggested_rows(findings, raw):
    rows = []
    fams = collections.defaultdict(list)
    for f in findings:
        fams[(f["check"], f["family"])].append(f)
    for (check, fam), fs in sorted(fams.items()):
        types = sorted({f["type"] for f in fs})
        if check == "FACE-BANK":
            rows.append(dict(check=check, family=fam, types=types, path=f"budgets.face_flop_ns_types.{fam}.row_stride", set=1,
                             why="NS face bank cannot fit inside the 27 um retention at stride > 1"))
        elif check == "TAP-CAP":
            for f in fs:
                rows.append(dict(check=check, family=fam, types=[f["type"]], path=f"partition_types.{f['type']}.clock",
                                 action="split the over-cap taps (added taps near each over-cap cluster)", detail=f["detail"]))
        elif check == "TAP-COVER":
            for f in fs:
                rows.append(dict(check=check, family=fam, types=[f["type"]], path=f"partition_types.{f['type']}.clock",
                                 action="add taps over the uncovered free area or refresh clock.sink_bins_file from the current netlist",
                                 detail=f["detail"]))
        elif check == "BOUNDARY-REG":
            for f in fs:
                rows.append(dict(check=check, family=fam, types=[f["type"]], path=f"partition_types.{f['type']}.buses",
                                 action=f"register every port within {BOUNDARY_UM:.0f} um of its pin (CBC both-side boundary)",
                                 detail=f["detail"]))
        elif check == "STALE-BINS":
            rows.append(dict(check=check, family=fam, types=types, path="partition_types.<type>.clock.sink_bins_file",
                             action="regenerate the sink bins from the newest placed kit (all_registers -clock clk), then re-run taps",
                             detail=fs[0]["detail"]))
        elif check == "TAP-EDGE":
            rows.append(dict(check=check, family=fam, types=types, path="partition_types.<type>.clock.tap_mode", set="grid+explicit",
                             why="taps on one or two edges only; use the family's grid+explicit form"))
        elif check == "RESET-FANOUT":
            for f in fs:
                rows.append(dict(check=check, family=fam, types=[f["type"]], path=f"partition_types.{f['type']}.reset",
                                 set={"local_relay_tree": True, "relay_um": 405, "max_fanout": 32}, detail=f["detail"]))
        elif check == "MISAIM":
            for f in fs:
                rows.append(dict(check=check, family=fam, types=[f["type"]], path=f"partition_types.{f['type']}.internal_stations",
                                 action="re-site the receiver chain toward the bit-weighted sink centroid (0 cycles)", detail=f["detail"]))
    return rows


def write_outputs(out, die, plan, findings, errors, nt, dt, raw):
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "findings.tsv", "w") as fh:
        fh.write("type\tcheck\tvalue\tthreshold\tfamily\tdetail\n")
        for f in findings:
            fh.write("\t".join(str(f[k]).replace("\t", " ") for k in ("type", "check", "value", "threshold", "family", "detail")) + "\n")
    rows = suggested_rows(findings, raw)
    (out / "suggested_rows.json").write_text(json.dumps(rows, indent=1))
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for f in findings:
        by[f["check"]][f["family"]].append(f)
    fam_types = collections.Counter(family(t) for t in raw["partition_types"])
    L = [f"# PRECHECK {die}", "", f"plan `{plan}`; {nt} types checked in {dt:.0f} s; {len(findings)} findings; {len(errors)} type errors.",
         "Estimator only (owner r703/r704): nothing here blocks a build.", ""]
    for check in [c for c in CHECKS if c in by] + [c for c in by if c not in CHECKS]:
        L.append(f"## {check}")
        L.append("| family | types flagged / family | worst | example |")
        L.append("|---|---|---|---|")
        for fam, fs in sorted(by[check].items(), key=lambda kv: -len(kv[1])):
            worst = max(fs, key=lambda f: f["value"] if check != "MISAIM" else -f["value"])
            n = len({f["type"] for f in fs})
            L.append(f"| {fam} | {n} / {fam_types.get(fam, '?')} | {worst['value']} | {worst['type']}: {worst['detail'][:220]} |")
        L.append("")
    if errors:
        L.append("## errors")
        L += [f"- {t}: {e}" for t, e in errors[:40]]
    (out / "family_summary.md").write_text("\n".join(L) + "\n")
    (out / "precheck.json").write_text(json.dumps(dict(die=die, plan=str(plan), types=nt, seconds=round(dt, 1),
                                                       findings=len(findings), errors=errors[:200]), indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--die", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--types", default="*", help="glob over type names (comma-separated globs allowed)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tools", default=str(HERE.parent / "die_plan"), help="die_plan tools dir (schema, taps, gen_phys)")
    ap.add_argument("--checks", default=",".join(CHECKS))
    ap.add_argument("--reach", type=float, default=REACH_UM)
    ap.add_argument("--tap-cap", type=int, default=TAP_CAP)
    ap.add_argument("--tap-radius", type=float, default=TAP_RADIUS_UM)
    ap.add_argument("--cover-frac", type=float, default=0.10)
    ap.add_argument("--cover-um2", type=float, default=40000.0)
    ap.add_argument("--tap-span", type=float, default=0.35)
    ap.add_argument("--bank-density", type=int, default=64, help="face registers + face-near stations per 3 station columns")
    ap.add_argument("--bank-gap-um", type=float, default=45.0, help="face-to-hard-core gap under the dense columns")
    ap.add_argument("--reset-flops", type=int, default=RESET_FLOPS)
    ap.add_argument("--boundary-um", type=float, default=BOUNDARY_UM)
    ap.add_argument("--kit-sinks", default="", help="kit_sinks.py JSON file(s), comma-separated (STALE-BINS)")
    ap.add_argument("--stale-frac", type=float, default=STALE_FRAC)
    a = ap.parse_args(argv)
    a.kit_sinks_map = {}
    for f in [x for x in a.kit_sinks.split(",") if x]:
        try:
            for k, v in json.loads(Path(f).read_text()).items():
                if k not in a.kit_sinks_map or v.get("mtime", 0) > a.kit_sinks_map[k].get("mtime", 0):
                    a.kit_sinks_map[k] = v
        except (OSError, ValueError) as e:
            print(f"PRECHECK kit-sinks {f}: {e}")
    sys.path.insert(0, a.tools)
    import schema as S
    t0 = time.time()
    raw = json.loads(Path(a.plan).read_text())
    P = S.Plan(raw, a.plan)
    ctx = Ctx(P, raw, a.plan, a.tools)
    globs = [g.strip() for g in a.types.split(",") if g.strip()]
    types = sorted(t for t in P.types if any(fnmatch.fnmatchcase(t, g) for g in globs))
    if not any(p.get("type") for p in raw.get("partitions") or []):
        pass
    placed = {p["type"] for p in raw.get("partitions") or []}
    checks = {c.strip().upper() for c in a.checks.split(",")} - DIE_SKIP.get(a.die, set())
    findings, errors = [], []
    for tn in types:
        if tn not in placed:
            continue
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                findings += type_findings(ctx, tn, checks, a)
        except Exception as e:  # noqa: BLE001
            errors.append((tn, f"{type(e).__name__}: {str(e)[:200]}"))
            if len(errors) < 3:
                traceback.print_exc()
    write_outputs(Path(a.out), a.die, a.plan, findings, errors, len(types), time.time() - t0, raw)
    c = collections.Counter(f["check"] for f in findings)
    print(f"PRECHECK {a.die}: {len(types)} types, {len(findings)} findings {dict(c)}, {len(errors)} errors, {time.time() - t0:.0f} s -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

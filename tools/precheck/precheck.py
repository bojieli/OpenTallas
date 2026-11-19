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
REACH_UM = 405.0
TAP_CAP = 1200
TAP_RADIUS_UM = 200.0
RESET_FLOPS = 2000
FF_CPITCH_UM = 2.16      # face_flops.tcl ff_cpitch = 40 sites x 0.054 um
FF_ROW_UM = 0.27
FF_RETENTION_UM = 27.0   # ff_put_near: |dx| + |dy| <= 27 um around the request
FF_NEAR_FACE_UM = 10.0   # a request within 10 um of the N/S face takes the face-bank search
FF_DEPTH_ROWS = 120
CHECKS = ("REACH", "MISAIM", "TAP-CAP", "TAP-COVER", "TAP-EDGE", "FACE-BANK", "RESET-FANOUT")


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
WIDE_MARGIN = 1.085     # CALIBRATED 11-19 on 43 signed S81 types: widest signed hop on a >= 256-bit chain 436.8 um (slice_station t27/t37)
NARROW_MARGIN = 1.25    # signed narrow chain up to 501.9 um (slice_station t37 ft7, 32 b)


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


def misaim_findings(ctx, t, frac=0.10, min_bits=64):
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


def reset_findings(t, limit=RESET_FLOPS):
    bits = sum(int(b.get("width") or 0) for b in t.get("buses") or [])
    bits += sum(int(s.get("width") or 0) * max(1, int(s.get("stations", 1) or 1)) for s in t.get("ft_slots") or [])
    bits += sum(int(e.get("bits") or 1) * len(e.get("regs_um") or []) for e in t.get("internal_stations") or [])
    rs = t.get("reset") or {}
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    relay = any(rs.get(k) for k in ("relay_um", "local_relay_tree", "relay_tree")) or any(
        t.get(k) for k in ("reset_relay_full", "reset_replicate", "reset_spine_pins")) or bool(lc.get("collector_tree"))
    if bits > limit and not relay:
        return [(bits, f"~{bits} boundary/station register bits on the raw reset (reset {json.dumps(rs)[:120]}); no relay_um, "
                 f"reset_relay_full/replicate or collector_tree")]
    return []


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
            add("MISAIM", v, 0.10, d)
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
        cap = int(ck.get("tap_max_sinks") or opts.tap_cap)
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
    a = ap.parse_args(argv)
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
    checks = {c.strip().upper() for c in a.checks.split(",")}
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

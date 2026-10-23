"""G0 die-plan check (TOPDOWN-PLAN): seconds, read-only, no EDA tools.

    python3 tools/die_plan/check.py PLAN.json [--out DIR] [--png] [--json-only] [--strict]

Checks (each finding is ERROR or WARN; G0 PASS = no ERROR):
  schema      structure + references (schema.validate): buses bound exactly once, no tie-offs, lane continuity
  geometry    partitions inside the die, on die.grid_um, pairwise non-overlapping; uncovered die area not in
              die.channels (WARN); partition larger than one hop without extra stations (WARN)
  abutment    every port's src face and dst face coincide (same line, window inside both edges, or on the die edge
              for @die); the pins (schema.pin_positions) land on tracks in BOTH partition frames; ports sharing a
              face + layer do not overlap; ft slot buses sit on the slot's in/out face; every instance of a
              replicated type yields the IDENTICAL pin table (bus, bit, layer, type-frame face and coordinate)
  layers      port and ft layers <= die.layer_budget.partition_signal_max
  faces       per partition face: pins / um <= face_pins_per_um averaged over every face_window_um window (all
              layers together, at most face_pin_layers layers per port); per port + layer pins / tracks <= pin_track_max
  cuts        cut sweep every cut_step_um, vertical and horizontal lines: the bits of every lane route crossing the
              line against the tracks (partition ft layers M4-M7 x ft_track_frac + die layers x cut_avail); full
              line and per partition segment <= cut_ratio_max; M8/M9-only ratio reported (research sweep form)
  hops        every register-to-register hop of every lane <= reach (lane.reach_um or die.reach_um)
  types       type count, instances per type, near-duplicate types (same outline + interface, other offsets: merge
              them; replicated types should declare type-frame pin windows)
  latency     the latency table lists every lane and equals Plan.lane_latency() (only source for RTL + compiler)
  clock/reset every non-hard type has a clock tap inside its outline on a die layer and a reset synchronizer;
              data_reset false, epoch bit true (schema)
Outputs in --out (default: next to the plan): g0_report.json and, with --png, die_plan.png (the G1 render).
"""
import argparse
import bisect
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402
from schema import DIE_PART, OPP  # noqa: E402

EPS = 1e-6
PART_FT_LAYERS = dict(H=("M4", "M6"), V=("M5", "M7"))   # in-partition ft layers (M2/M3 are cell-local)
FT_TRACK_FRAC = 0.25                                       # default share of those tracks a partition gives to ft


def lnum(name):
    return int(name[1:])


class Report:
    def __init__(self):
        self.items = []

    def err(self, check, msg, **kw):
        self.items.append(dict(level="ERROR", check=check, msg=msg, **kw))

    def warn(self, check, msg, **kw):
        self.items.append(dict(level="WARN", check=check, msg=msg, **kw))

    def errors(self):
        return [i for i in self.items if i["level"] == "ERROR"]


def on_grid(v, g):
    k = v / g
    return abs(k - round(k)) < 1e-6


def face_line(rect, face):
    """(axis coordinate of the face line, lo, hi along the face)."""
    x0, y0, x1, y1 = rect
    return {"E": (x1, y0, y1), "W": (x0, y0, y1), "N": (y1, x0, x1), "S": (y0, x0, x1)}[face]


def on_track(c, L):
    k = (c - L["offset_um"]) / L["pitch_um"]
    return abs(k - round(k)) < 1e-4


# --------------------------------------------------------------------------------------------------- geometry
def check_geometry(P, R):
    g = P.grid
    for nm, base in [("ORFS base lattice", S.BASE_LATTICE_UM)] + \
            [(f"{L} pitch", P.layers[L]["pitch_um"]) for L in sorted(P.layers) if int(L[1:]) >= 4]:
        k = g / base
        if abs(k - round(k)) > 1e-6:
            R.err("geometry", f"die.grid_um {g:g} is not a multiple of the {nm} {base:g} um")
    W, H = P.W, P.H
    rects = {n: P.rect(n) for n in P.parts}
    for n, (x0, y0, x1, y1) in rects.items():
        if x0 < -EPS or y0 < -EPS or x1 > W + EPS or y1 > H + EPS:
            R.err("geometry", f"partition {n} {fmt_rect((x0, y0, x1, y1))} outside the die {W}x{H}", part=n)
        for v in (x0, y0):
            if not on_grid(v, P.grid):
                R.err("geometry", f"partition {n} origin {x0},{y0} not on the {P.grid}-um grid", part=n)
                break
    for tn, t in P.types.items():
        for v in t["outline_um"]:
            if not on_grid(v, P.grid):
                R.err("geometry", f"type {tn} outline {t['outline_um']} not on the {P.grid}-um grid", type=tn)
                break
    names = sorted(rects, key=lambda n: rects[n][0])
    xs = [rects[n][0] for n in names]
    for i, a in enumerate(names):
        ax0, ay0, ax1, ay1 = rects[a]
        j = i + 1
        while j < len(names) and xs[j] < ax1 - EPS:
            b = names[j]
            bx0, by0, bx1, by1 = rects[b]
            if min(ax1, bx1) - max(ax0, bx0) > EPS and min(ay1, by1) - max(ay0, by0) > EPS:
                R.err("geometry", f"partitions {a} and {b} overlap", part=a, other=b)
            j += 1
    area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in rects.values())
    chan = 0.0
    chans = []
    for c in P.die.get("channels", []):
        r = P.channel_rect(c)
        chan += max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])
        if "ports" in c:
            vert = (r[2] - r[0]) < (r[3] - r[1])            # vertical channel: wires cross it horizontally
            along, wdir = ((r[3] - r[1]), "H") if vert else ((r[2] - r[0]), "V")
            tr = sum(along / P.layers[L]["pitch_um"] for L in c["layers"] if P.layers[L]["dir"] == wdir)
            bits = sum(S.port_pins_count(P.ports[q]) for q in c["ports"])
            ratio = bits / tr if tr else math.inf
            if abs((r[2] - r[0] if vert else r[3] - r[1]) - c["width_um"]) > 1e-3:
                R.err("geometry", f"channel {c.get('name', '?')}: gap between {c['between']} is "
                      f"{(r[2] - r[0] if vert else r[3] - r[1]):g} um, width_um {c['width_um']:g}")
            if ratio > P.budgets["cut_ratio_max"] + EPS:
                R.err("cuts", f"channel {c.get('name', '?')}: {bits} pins on {tr:.0f} {wdir} tracks = {ratio:.2f} > "
                      f"{P.budgets['cut_ratio_max']}")
            chans.append(dict(name=c.get("name"), between=c["between"], rect_um=[round(v, 4) for v in r],
                              width_um=c["width_um"], area_mm2=round((r[2] - r[0]) * (r[3] - r[1]) / 1e6, 5),
                              bits=bits, tracks=round(tr), ratio=round(ratio, 4)))
    gap = W * H - area - chan
    if gap > 0.001 * W * H:
        R.warn("geometry", f"{gap / 1e6:.3f} mm2 ({100 * gap / (W * H):.1f}% of the die) is neither partition nor a "
               "die.channels entry with a reason")
    for tn, t in P.types.items():
        w, h = t["outline_um"]
        for sl in t.get("ft_slots", []):
            fs = {sl["in_face"], sl["out_face"]}
            span = w if fs == {"E", "W"} else h if fs == {"N", "S"} else (w + h) / 2.0
            if span > P.reach * sl.get("stations", 1) + EPS:
                R.warn("geometry", f"type {tn} slot {sl['name']}: crossing ~{span:.0f} um > {sl.get('stations', 1)} "
                       f"station(s) x reach {P.reach:.0f} (see hops)", type=tn)
    return dict(partition_area_mm2=area / 1e6, channel_area_mm2=chan / 1e6, uncovered_mm2=max(gap, 0) / 1e6,
                fill=area / (W * H), planned_channels=chans)


def fmt_rect(r):
    return "[" + ",".join(f"{v:g}" for v in r) + "]"


# --------------------------------------------------------------------------------------------------- abutment
def check_abutment(P, R):
    """returns {(part, die_face): [(coord, layer, port)]} for the face-density check."""
    face_pins = defaultdict(list)
    type_tables = defaultdict(dict)    # type -> {inst: {(bus, bit): (layer, tface, coord)}}
    smax = lnum(P.layer_budget["partition_signal_max"])
    for pid, pr in P.ports.items():
        f = pr["face"]
        for ln in pr["layers"]:
            if ln in P.layers and lnum(ln) > smax:
                R.err("layers", f"port {pid}: pin layer {ln} above partition_signal_max "
                      f"{P.layer_budget['partition_signal_max']}", port=pid)
        try:
            pins = P.port_pins(pid)
        except (ValueError, KeyError) as e:
            R.err("abutment", f"port {pid}: {e}", port=pid)
            continue
        ends = []
        if pr["src"]["part"] != DIE_PART:
            ends.append(("src", pr["src"], f))
        if pr["dst"]["part"] != DIE_PART:
            ends.append(("dst", pr["dst"], OPP[f] if pr["src"]["part"] != DIE_PART else f))
        lo, hi = sorted(pr["window_um"])
        lines = []
        for side, e, df in ends:
            line, a, b = face_line(P.rect(e["part"]), df)
            lines.append((side, e["part"], df, line))
            if lo < a - EPS or hi > b + EPS:
                R.err("abutment", f"port {pid}: window [{lo:g},{hi:g}] outside the {df} face [{a:g},{b:g}] of "
                      f"{e['part']}", port=pid)
        ch = P.channel_of(pid)
        if ch and len(lines) == 2:
            if {pr["src"]["part"], pr["dst"]["part"]} != set(ch["between"]):
                R.err("abutment", f"port {pid}: in channel {ch.get('name', '?')} but its ends are not "
                      f"{ch['between']}", port=pid)
            elif abs(abs(lines[0][3] - lines[1][3]) - ch["width_um"]) > 1e-3:
                R.err("abutment", f"port {pid}: faces {lines[0][3]:g} / {lines[1][3]:g} are not one channel width "
                      f"({ch['width_um']:g}) apart", port=pid)
            for ln in pr["layers"]:
                if ln not in ch["layers"]:
                    R.err("abutment", f"port {pid}: pin layer {ln} not a layer of channel {ch.get('name', '?')} "
                          f"{ch['layers']}", port=pid)
        elif len(lines) == 2 and abs(lines[0][3] - lines[1][3]) > EPS:
            R.err("abutment", f"port {pid}: {lines[0][1]}.{lines[0][2]} at {lines[0][3]:g} and {lines[1][1]}."
                  f"{lines[1][2]} at {lines[1][3]:g} do not abut", port=pid)
        if DIE_PART in (pr["src"]["part"], pr["dst"]["part"]) and lines:
            side, part, df, line = lines[0]
            edge = {"E": P.W, "W": 0.0, "N": P.H, "S": 0.0}[df]
            if abs(line - edge) > EPS:
                R.err("abutment", f"port {pid}: die IO on {part}.{df} at {line:g}, not on the die edge {edge:g}",
                      port=pid)
        for side, e, df in ends:
            part = e["part"]
            tf = P.type_face(part, df)
            b = P.buses(part).get(e["bus"], {})
            if b.get("slot") and b.get("face") != tf:
                R.err("abutment", f"port {pid}: {part}.{e['bus']} is on type face {tf}, slot face is {b['face']}",
                      port=pid)
            tab = type_tables[P.parts[part]["type"]].setdefault(part, {})
            o = P.orient(part)
            w, h = P.ptype(part)["outline_um"]
            ox, oy = P.parts[part]["origin_um"]
            if df in "EW":     # 1-D transform of the along-face coordinate into the type frame
                flip, base, ext = o in ("MX", "R180"), oy, h
            else:
                flip, base, ext = o in ("MY", "R180"), ox, w
            for bit, ln, c in pins:
                tc = (ext - (c - base)) if flip else (c - base)
                if not on_track(tc, P.layers[ln]):
                    R.err("abutment", f"port {pid}: bit {bit} {ln} at die {c:.3f} is off-track in {part}'s frame "
                          f"({P.orient(part)}, type coord {tc:.4f})", port=pid, part=part)
                    break
                tab[(e["bus"], bit)] = (ln, tf, round(tc, 4))
            for bit, ln, c in pins:
                face_pins[(part, df)].append((c, ln, pid))
    # overlapping ports on one face + layer
    for (part, df), pins in face_pins.items():
        by = defaultdict(list)
        for c, ln, pid in pins:
            by[ln].append((c, pid))
        for ln, lst in by.items():
            lst.sort()
            for (c0, p0), (c1, p1) in zip(lst, lst[1:]):
                if p0 != p1 and abs(c1 - c0) < P.layers[ln]["pitch_um"] - EPS:
                    R.err("abutment", f"{part}.{df} {ln}: ports {p0} and {p1} share track {c0:.3f}", part=part)
                    break
    # replicated types: identical pin tables
    for tn, insts in type_tables.items():
        ref_name, ref = None, None
        for inst, tab in sorted(insts.items()):
            if ref is None:
                ref_name, ref = inst, tab
                continue
            if tab != ref:
                diff = set(tab.items()) ^ set(ref.items())
                k = sorted(diff)[0]
                R.err("abutment", f"type {tn}: instance {inst} pin table differs from {ref_name} ({len(diff)} "
                      f"entries, e.g. {k[0][0]}[{k[0][1]}] {k[1]}) -- a replicated type must have identical pins",
                      type=tn)
    return face_pins


# ------------------------------------------------------------------------------------------------------ faces
def check_faces(P, R, face_pins):
    B = P.budgets
    win = B["face_window_um"]
    # allowance of 2 pins per pin layer, so a window spread at exactly the budget passes (PLAN-HBM 10-23):
    # 1 pin for whole-track quantisation;
    # 1 pin for pins pushed out of the partition PG bands (schema.spread, coordinate-uniform, nearest usable track).
    lim = B["face_pins_per_um"] * win + 2 * B["face_pin_layers"]
    worst = []
    for (part, df), pins in face_pins.items():
        cs = sorted(c for c, _, _ in pins)
        mx, at = 0, None
        for i, c in enumerate(cs):
            j = bisect.bisect_right(cs, c + win - EPS)
            if j - i > mx:
                mx, at = j - i, c
        worst.append((mx / win, part, df))
        if mx > lim + EPS:
            R.err("faces", f"{part}.{df}: {mx} pins in the {win:g}-um window at {at:.2f} "
                  f"({mx / win:.2f}/um > {B['face_pins_per_um']:g})", part=part)
    for pid, pr in P.ports.items():
        if len(pr["layers"]) > B["face_pin_layers"]:
            R.err("faces", f"port {pid}: {len(pr['layers'])} pin layers > {B['face_pin_layers']}", port=pid)
        lo, hi = sorted(pr["window_um"])
        nl = len(pr["layers"])
        for li, ln in enumerate(pr["layers"]):
            if ln not in P.layers:
                continue
            nb = len(range(li, S.port_pins_count(pr), nl))
            tr = max(1, int((hi - lo) / P.layers[ln]["pitch_um"]) + 1)
            if nb / tr > B["pin_track_max"] + EPS:
                R.err("faces", f"port {pid}: {nb} pins on {tr} {ln} tracks = {nb / tr:.2f} > {B['pin_track_max']}",
                      port=pid)
    worst.sort(reverse=True)
    return [dict(part=p, face=f, pins_per_um=round(v, 3)) for v, p, f in worst[:10]]


# ---------------------------------------------------------------------------------------------- lane routes
def zroute(a, b, face_in):
    """rectilinear route from a to b inside a partition entered on face_in: Z through the midpoint."""
    if abs(a[0] - b[0]) < EPS or abs(a[1] - b[1]) < EPS:
        return [a, b]
    if face_in in "EW":
        xm = (a[0] + b[0]) / 2.0
        return [a, (xm, a[1]), (xm, b[1]), b]
    ym = (a[1] + b[1]) / 2.0
    return [a, (a[0], ym), (b[0], ym), b]


def plen(pts):
    return sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:]))


def point_at(pts, t):
    for p, q in zip(pts, pts[1:]):
        d = abs(p[0] - q[0]) + abs(p[1] - q[1])
        if t <= d + EPS:
            f = 0.0 if d == 0 else t / d
            return (p[0] + f * (q[0] - p[0]), p[1] + f * (q[1] - p[1]))
        t -= d
    return pts[-1]


def lane_geometry(P, lid):
    """route polyline (die frame), register points in order, and per-crossing info."""
    ln = P.lanes[lid]
    pts = [P.port_point(ln["ports"][0])]
    regs = [pts[0]]
    xs = []
    for part, slot, a, b in P.lane_crossings(lid):
        pa, pb = P.port_point(a), P.port_point(b)
        s = P.slot(part, slot) or {}
        fin = P.die_face(part, s.get("in_face", "W"))
        seg = zroute(pa, pb, fin)
        L = plen(seg)
        k = int(s.get("stations", 1))
        if s.get("regs_um"):
            st = [P.to_die(part, tuple(r)) for r in s["regs_um"]]
        else:
            st = [point_at(seg, L * j / k) for j in range(k)]
        regs.extend(st)
        xs.append(dict(part=part, slot=slot, len_um=round(L, 1), stations=k))
        pts.extend(seg[1:])
    regs.append(P.port_point(ln["ports"][-1]))
    return pts, regs, xs


def check_hops(P, R, geo):
    worst = []
    for lid, (pts, regs, xs) in geo.items():
        reach = float(P.lanes[lid].get("reach_um", P.reach))
        hops = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(regs, regs[1:])]
        h = max(hops) if hops else 0.0
        worst.append((h / reach, lid, h, reach))
        if h > reach + EPS:
            i = hops.index(h)
            R.err("hops", f"lane {lid}: hop {i} is {h:.0f} um > reach {reach:.0f} (add stations to the crossed "
                  "partition's slot or shorten it)", lane=lid)
    worst.sort(reverse=True)
    return [dict(lane=l, hop_um=round(h, 1), reach_um=r) for _, l, h, r in worst[:10]]


# ------------------------------------------------------------------------------------------------------- cuts
def track_density(P, names, frac):
    return sum(frac / P.layers[n]["pitch_um"] for n in names if n in P.layers)


def check_cuts(P, R, geo):
    B = P.budgets
    step = B["cut_step_um"]
    lim = B["cut_ratio_max"]
    avail = P.layer_budget.get("cut_avail", {})
    die_l = [n for n in P.layer_budget["die_layers"] if n in P.layers]
    out = dict(vertical=[], horizontal=[])
    # segment list: (x0, y0, x1, y1, bits)
    segs = []
    for lid, (pts, _, _) in geo.items():
        w = P.ports[P.lanes[lid]["ports"][0]]["width"]
        for p, q in zip(pts, pts[1:]):
            segs.append((p, q, w))
    rects = {n: P.rect(n) for n in P.parts}
    worst_full, worst_loc = (0, None), (0, None)
    for orient, D, along in (("vertical", P.W, P.H), ("horizontal", P.H, P.W)):
        wire_dir = "H" if orient == "vertical" else "V"     # wires crossing a vertical line run horizontally
        dl = [n for n in die_l if P.layers[n]["dir"] == wire_dir]
        die_den = sum(avail.get(n, 0.0) / P.layers[n]["pitch_um"] for n in dl)
        die_den_raw = sum(1.0 / P.layers[n]["pitch_um"] for n in dl)
        n = int(D // step)
        for k in range(1, n + 1):
            c = k * step
            if c >= D - EPS:
                break
            hits = []
            for p, q, w in segs:
                a, b = (p[0], q[0]) if orient == "vertical" else (p[1], q[1])
                if min(a, b) < c - EPS and max(a, b) > c + EPS:
                    hits.append(((p[1] if orient == "vertical" else p[0]), w))
            bits = sum(w for _, w in hits)
            cap = along * die_den
            parts_cap = 0.0
            loc = []
            for pn, r in rects.items():
                lo, hi, a0, a1 = (r[1], r[3], r[0], r[2]) if orient == "vertical" else (r[0], r[2], r[1], r[3])
                if not (a0 < c - EPS and a1 > c + EPS):
                    continue
                t = P.ptype(pn)
                frac = t.get("ft_track_frac", FT_TRACK_FRAC)
                pden = track_density(P, PART_FT_LAYERS[wire_dir], frac)
                seg_cap = (hi - lo) * (pden + die_den)
                parts_cap += (hi - lo) * pden
                sb = sum(w for y, w in hits if lo - EPS <= y <= hi + EPS)
                if sb:
                    loc.append((sb / seg_cap if seg_cap else math.inf, pn, sb, seg_cap))
            for ch in P.die.get("channels", []):          # planned channels: their own layers are die-route tracks
                if "ports" not in ch:
                    continue
                r = P.channel_rect(ch)
                lo, hi, a0, a1 = (r[1], r[3], r[0], r[2]) if orient == "vertical" else (r[0], r[2], r[1], r[3])
                if not (a0 < c - EPS and a1 > c + EPS):
                    continue
                cden = sum(1.0 / P.layers[L]["pitch_um"] for L in ch["layers"] if P.layers[L]["dir"] == wire_dir
                           and L not in dl)
                seg_cap = (hi - lo) * (cden + die_den)
                parts_cap += (hi - lo) * cden
                sb = sum(w for y, w in hits if lo - EPS <= y <= hi + EPS)
                if sb:
                    loc.append((sb / seg_cap if seg_cap else math.inf, f"channel:{ch.get('name', '?')}", sb, seg_cap))
            cap += parts_cap
            ratio = bits / cap if cap else (math.inf if bits else 0.0)
            m89 = bits / (along * die_den_raw) if die_den_raw else 0.0
            rec = dict(at_um=c, bits=bits, tracks=round(cap), ratio=round(ratio, 4), m89_only_ratio=round(m89, 4))
            if loc:
                lr, lp, lb, lc = max(loc)
                rec.update(worst_part=lp, worst_part_ratio=round(lr, 4), worst_part_bits=lb)
                if lr > lim + EPS:
                    R.err("cuts", f"{orient} cut at {c:g}: {lp} segment carries {lb} bits on {lc:.0f} tracks "
                          f"= {lr:.2f} > {lim}", part=lp)
                if lr > worst_loc[0]:
                    worst_loc = (lr, f"{orient}@{c:g}:{lp}")
            if ratio > lim + EPS:
                R.err("cuts", f"{orient} cut at {c:g}: {bits} bits on {cap:.0f} tracks = {ratio:.2f} > {lim}")
            if ratio > worst_full[0]:
                worst_full = (ratio, f"{orient}@{c:g}")
            out[orient].append(rec)
    out["worst_full"] = dict(ratio=round(worst_full[0], 4), at=worst_full[1])
    out["worst_partition_segment"] = dict(ratio=round(worst_loc[0], 4), at=worst_loc[1])
    out["model"] = dict(partition_ft_layers=PART_FT_LAYERS, ft_track_frac_default=FT_TRACK_FRAC,
                        die_layers=die_l, cut_avail=avail, step_um=step)
    return out


# ---------------------------------------------------------------------------------------------- latency etc.
def check_latency(P, R):
    tab = P.raw.get("latency", {}).get("lanes")
    if tab is None:
        R.err("latency", "no latency table (generate it: python3 tools/die_plan/gen.py latency PLAN.json --inplace)")
        return {}
    for lid in P.lanes:
        want = P.lane_latency(lid)
        got = tab.get(lid)
        if got is None:
            R.err("latency", f"lane {lid}: missing from the latency table", lane=lid)
        elif got["cycles"] != want["cycles"]:
            R.err("latency", f"lane {lid}: table says {got['cycles']} cycles, plan gives {want['cycles']}", lane=lid)
    return {lid: P.lane_latency(lid)["cycles"] for lid in P.lanes}


def check_clock_reset(P, R):
    die_l = set(P.layer_budget["die_layers"])
    for tn, t in P.types.items():
        if t.get("hard"):
            continue
        ck = t.get("clock")
        if not ck or "tap_um" not in ck:
            R.err("clock", f"type {tn}: no clock tap (one root per partition)", type=tn)
        else:
            w, h = t["outline_um"]
            x, y = ck["tap_um"]
            if not (0 <= x <= w and 0 <= y <= h):
                R.err("clock", f"type {tn}: clock tap {x},{y} outside the outline", type=tn)
            if ck.get("layer") and ck["layer"] not in die_l:
                R.err("clock", f"type {tn}: clock tap layer {ck['layer']} is not a die layer {sorted(die_l)}", type=tn)
            far = max(abs(x - a) + abs(y - b) for a in (0, w) for b in (0, h))
            if far > 2 * P.reach:
                R.warn("clock", f"type {tn}: farthest boundary point {far:.0f} um from the tap (> 2 hops)", type=tn)
        if "reset" not in t:
            R.err("reset", f"type {tn}: no reset synchronizer entry (one per partition)", type=tn)
        insts = {c["inst"] for c in t.get("contents", [])}
        for b in t.get("buses", []):
            lf = b.get("leaf")
            if lf is None:
                R.warn("schema", f"type {tn}: bus {b['name']} has no leaf binding", type=tn)
            elif lf.split(".")[0] not in insts:
                R.err("schema", f"type {tn}: bus {b['name']} binds to unknown instance {lf}", type=tn)
        smax = lnum(P.layer_budget["partition_signal_max"])
        for s in t.get("ft_slots", []):
            if s.get("layer") and lnum(s["layer"]) > smax:
                R.err("layers", f"type {tn} slot {s['name']}: ft layer {s['layer']} above partition_signal_max",
                      type=tn)


# ------------------------------------------------------------------------------------------------------ types
def check_seams(P, R):
    """Seam-net invariant (COORD 10-23, OpenROAD abutment semantics): every inter-partition port bit is ONE 2-pin net,
    boundary flop to boundary flop -- one out bus (src boundary flop or ft station) to one in bus (dst boundary flop or
    station), same layer and coordinate on both sides, no fan-out, no die-port tap, no clock / reset kind.  Abutted
    seams must be pin-to-pin same-layer overlaps (dbNet::isConnectedByAbutment); planned-channel seams are the die
    route's only signal nets.  Returns per partition pair {abutted, channel} pin counts = the audit's expected nets."""
    seen = defaultdict(list)
    pairs = defaultdict(lambda: dict(abutted=0, channel=0))
    for pid, pr in P.ports.items():
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if DIE_PART in (a, b):
            continue
        for side in ("src", "dst"):
            e = pr[side]
            seen[(e["part"], e["bus"])].append(pid)
            bus = P.buses(e["part"]).get(e["bus"], {})
            if bus.get("kind", "data") not in ("data", "ctl"):
                R.err("seams", f"port {pid}: {e['part']}.{e['bus']} is kind {bus.get('kind')}; a seam carries only "
                      "registered data / ctl (clock and reset come from the die spine taps)", port=pid)
        n = S.port_pins_count(pr)
        key = "|".join(sorted((a, b)))
        pairs[key]["channel" if P.channel_of(pid) else "abutted"] += n
    for (part, bus), pids in seen.items():
        if len(pids) > 1:
            R.err("seams", f"{part}.{bus} is an end of {len(pids)} seam ports {pids}: fan-out on a seam", part=part)
    tot = dict(abutted=sum(v["abutted"] for v in pairs.values()), channel=sum(v["channel"] for v in pairs.values()))
    return dict(nets=tot, pairs=dict(pairs))


def check_types(P, R):
    """type count, instances per type, and near-duplicate types: same outline + same bus interface (name, dir, width,
    kind) + same ft slots (faces, width, stations), differing only in pin offsets / contents.  Such types should be
    ONE type placed with orient / lattice shifts and pins declared on the type (type-frame windows)."""
    inst = defaultdict(int)
    for p in P.parts.values():
        inst[p["type"]] += 1
    sig = defaultdict(list)
    for tn, t in P.types.items():
        k = (tuple(t["outline_um"]),
             tuple(sorted((b["name"], b["dir"], b["width"], b.get("kind", "data")) for b in t.get("buses", []))),
             tuple(sorted((s["in_face"], s["out_face"], s["width"], s.get("stations", 1))
                          for s in t.get("ft_slots", []))))
        sig[k].append(tn)
    groups = [sorted(v) for v in sig.values() if len(v) > 1]
    for g in groups:
        R.warn("types", f"near-duplicate types {g[:8]}{'...' if len(g) > 8 else ''} ({len(g)}): same outline, buses and "
               "slots -- merge into one type (orient MX/MY/R180 + lattice origin, pins declared on the type)")
    no_geo = [tn for tn, t in P.types.items() if inst[tn] > 1 and any(
        "window_um" not in b for b in t.get("buses", []))]
    if no_geo:
        R.warn("types", f"{len(no_geo)} replicated types without type-frame pin windows on their buses (e.g. "
               f"{no_geo[:5]}): declare face/window_um/layers on the type so every instance shares one pin table")
    return dict(types=len(P.types), partitions=len(P.parts), singleton_types=sum(1 for v in inst.values() if v == 1),
                max_instances=max(inst.values()) if inst else 0, near_duplicate_groups=len(groups),
                near_duplicate_types=sum(len(g) for g in groups), mergeable_saving=sum(len(g) - 1 for g in groups))


# ------------------------------------------------------------------------------------------------------- run
def run(raw, png=None):
    R = Report()
    errs = S.validate(raw)
    for e in errs:
        R.err("schema", e)
    if errs:
        return R, dict()
    P = S.Plan(raw)
    summ = dict(die=P.name, partitions=len(P.parts), types=len(P.types), ports=len(P.ports), lanes=len(P.lanes),
                bits=sum(p["width"] for p in P.ports.values()))
    summ["types"] = check_types(P, R)
    summ["geometry"] = check_geometry(P, R)
    fp = check_abutment(P, R)
    summ["worst_faces"] = check_faces(P, R, fp)
    geo = {lid: lane_geometry(P, lid) for lid in P.lanes}
    summ["worst_hops"] = check_hops(P, R, geo)
    summ["cuts"] = check_cuts(P, R, geo)
    summ["latency"] = check_latency(P, R)
    check_clock_reset(P, R)
    summ["seams"] = check_seams(P, R)
    if png:
        import render
        render.render(P, geo, R, png)
        summ["png"] = str(png)
    return R, summ


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--png", action="store_true")
    ap.add_argument("--strict", action="store_true", help="WARN counts as failure")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    raw = S.load(a.plan)
    out = Path(a.out) if a.out else Path(a.plan).resolve().parent
    out.mkdir(parents=True, exist_ok=True)
    R, summ = run(raw, png=(out / "die_plan.png") if a.png else None)
    ne = len(R.errors())
    nw = len(R.items) - ne
    ok = ne == 0 and not (a.strict and nw)
    rep = dict(schema="opentallas.die_plan.g0.v1", plan=str(Path(a.plan).resolve()), verdict="PASS" if ok else "FAIL",
               errors=ne, warnings=nw, summary=summ, findings=R.items)
    (out / "g0_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    if not a.quiet:
        for i in R.items[:200]:
            print(f"{i['level']:5s} [{i['check']}] {i['msg']}")
        if len(R.items) > 200:
            print(f"... {len(R.items) - 200} more in g0_report.json")
    c = summ.get("cuts", {})
    ty = summ.get("types", {})
    print(f"G0 {rep['verdict']}: {ne} errors, {nw} warnings; {ty.get('types')} types / {ty.get('partitions')} "
          f"partitions ({ty.get('near_duplicate_types')} in near-duplicate groups); worst cut {c.get('worst_full')}, worst partition "
          f"segment {c.get('worst_partition_segment')}; report {out / 'g0_report.json'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

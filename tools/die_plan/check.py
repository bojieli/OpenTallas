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
  r8          COORD R8 bus-coherent latency on BINDER2's as-built bus groups (--groups bus_groups.json, else
              PLANDIR/{r8,bind}/bus_groups.json): one added delay per as-built bus, equal across replicated consumers, no
              as-built order inversion, one landing pad per site of a replicated type (r8.py); depth = the R8 landing
              table (--landing, else PLANDIR/**/<die>_r8_landing.json from gen.py latency --groups) or the bound top
  clock/reset every non-hard type has a clock tap inside its outline on a die layer and a reset synchronizer;
              data_reset false, epoch bit true (schema)
  G0C (--completeness): hard_cores, core_faces, complete; PLAN-TOOL5 cross-die rules die_io_plan (die_io.py),
              cut_lines / reach / face_tracks / ft_budget (xdie.py, per-layer reach table reach.py)
Outputs in --out (default: next to the plan): g0_report.json and, with --png, die_plan.png (the G1 render).
"""
import argparse
import bisect
import json
import math
import re
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


# G0C (COORD 10-23 ~20:10): the plan-completeness / hard-core rules are ERRORs only under `check.py --completeness`;
# plain G0 reports them as WARN "[G0C] ..." so a plan that passed G0 keeps passing while it is completed.
G0C_CHECKS = ("hard_cores", "core_faces", "complete",
              # PLAN-TOOL5 (COORD die-plan visual review 10-23, cross-die items (a)-(e)): die_io.py / xdie.py
              "die_io_plan", "cut_lines", "reach", "face_tracks", "ft_budget")


class Report:
    def __init__(self, completeness=False):
        self.items = []
        self.completeness = completeness

    def err(self, check, msg, **kw):
        if check in G0C_CHECKS:
            kw["g0c"] = True
            if not self.completeness:
                self.items.append(dict(level="WARN", check=check, msg="[G0C] " + msg, **kw))
                return
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
        # per-face layer sets (COORD 10-23): a type may list face_layers[type face]; then every pin layer on that
        # face must be in the set, and a layer above partition_signal_max (M8 on S81 svc fold / rail faces) is
        # allowed only when EVERY partition end lists it for its face
        pend = []
        if pr["src"]["part"] != DIE_PART:
            pend.append((pr["src"]["part"], f))
        if pr["dst"]["part"] != DIE_PART:
            pend.append((pr["dst"]["part"], OPP[f] if pr["src"]["part"] != DIE_PART else f))
        fl = [(pt, P.type_face(pt, df), P.ptype(pt).get("face_layers", {}).get(P.type_face(pt, df)))
              for pt, df in pend]
        for ln in pr["layers"]:
            for pt, tf, allowed in fl:
                if allowed is not None and ln not in allowed:
                    R.err("layers", f"port {pid}: pin layer {ln} not in {pt}'s face_layers[{tf}] {allowed}",
                          port=pid)
            if ln in P.layers and lnum(ln) > smax and not (fl and all(a and ln in a for _, _, a in fl)):
                R.err("layers", f"port {pid}: pin layer {ln} above partition_signal_max "
                      f"{P.layer_budget['partition_signal_max']} (allowed only via the type's face_layers)",
                      port=pid)
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
    # spare slots (COORD 10-23): reserved type-face windows with NO pins
    for tn, t in P.types.items():
        sp = t.get("spare_slots", [])
        if not sp:
            continue
        w, h = t["outline_um"]
        for s_ in sp:
            lo, hi = sorted(s_["window_um"])
            ext = h if s_["face"] in "EW" else w
            if lo < -EPS or hi > ext + EPS:
                R.err("abutment", f"type {tn} spare slot {s_['name']}: window [{lo:g},{hi:g}] outside face "
                      f"{s_['face']} [0,{ext:g}]", type=tn)
            for fs in t.get("ft_slots", []):
                for fk, wk in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
                    if fs.get(fk) == s_["face"] and fs.get(wk):
                        a, b = sorted(fs[wk])
                        if a < hi and lo < b and set(fs.get("layers") or s_["layers"]) & set(s_["layers"]):
                            R.err("abutment", f"type {tn} spare slot {s_['name']} overlaps ft slot {fs['name']} "
                                  f"{wk} [{a:g},{b:g}]", type=tn)
        for part, tab in type_tables.get(tn, {}).items():
            for (bus, bit), (ln, tf, tc) in tab.items():
                for s_ in sp:
                    lo, hi = sorted(s_["window_um"])
                    if s_["face"] == tf and ln in s_["layers"] and lo - EPS <= tc <= hi + EPS:
                        R.err("abutment", f"{part}.{bus}[{bit}] {ln} at type {tf} {tc:g} lies in spare slot "
                              f"{s_['name']} [{lo:g},{hi:g}] (a spare slot carries no pins)", part=part)
                        break
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
    worst = []
    for (part, df), pins in face_pins.items():
        # a type face whose face_layers lists n > face_pin_layers layers (S81 svc fold: M7/M5 + M8 from the die
        # budget, COORD 10-23 07:43) gets the per-layer budget on each layer: face_pins_per_um * n / face_pin_layers
        fl = P.ptype(part).get("face_layers", {}).get(P.type_face(part, df))
        nl = max(B["face_pin_layers"], len(fl) if fl else 0)
        lim = B["face_pins_per_um"] * nl / B["face_pin_layers"] * win + 2 * nl
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
            ends = [(pr[k]["part"], pr["face"] if k == "src" else OPP[pr["face"]]) for k in ("src", "dst")
                    if pr[k]["part"] != DIE_PART]
            if not ends or not all(set(pr["layers"]) <= set(P.ptype(pt).get("face_layers", {}).get(
                    P.type_face(pt, df), [])) for pt, df in ends):
                R.err("faces", f"port {pid}: {len(pr['layers'])} pin layers > {B['face_pin_layers']} "
                      "(more only on a face_layers face listed by both ends)", port=pid)
        lo, hi = sorted(pr["window_um"])
        nl = len(pr["layers"])
        for li, ln in enumerate(pr["layers"]):
            if ln not in P.layers:
                continue
            nb = len(range(li, S.port_pins_count(pr), nl))
            tr = max(1, S.usable_tracks(P.layers[ln], ln, lo, hi))     # tracks off the PG stripes (M5-M8)
            if nb / tr > B["pin_track_max"] + EPS:
                R.err("faces", f"port {pid}: {nb} pins on {tr} {ln} tracks = {nb / tr:.2f} > {B['pin_track_max']}",
                      port=pid)
    worst.sort(reverse=True)
    return [dict(part=p, face=f, pins_per_um=round(v, 3)) for v, p, f in worst[:10]]


# ---------------------------------------------------------------------------------------------- lane routes
def zroute(a, b, face_in, face_out=None):
    """rectilinear route from a to b inside a partition entered on face_in: an L for a turning slot (out face
    perpendicular to the in face: along the in face's normal, then along the out face's normal), else a Z through the
    midpoint (straight-through slot with a jog)."""
    if abs(a[0] - b[0]) < EPS or abs(a[1] - b[1]) < EPS:
        return [a, b]
    if face_out and (face_in in "EW") != (face_out in "EW"):
        return [a, (b[0], a[1]), b] if face_in in "EW" else [a, (a[0], b[1]), b]
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
        fout = P.die_face(part, s.get("out_face", "E"))
        seg = zroute(pa, pb, fin, fout)
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
    # COORD 10-23 R3: ft stations at most budgets.ft_station_max_um (750) apart inside every crossed partition
    smax = float(P.budgets.get("ft_station_max_um", 750.0))
    seen = set()
    for lid, (pts, regs, xs) in geo.items():
        for x in xs:
            key = (P.parts[x["part"]]["type"], x["slot"])
            if key in seen:
                continue
            seen.add(key)
            sp = x["len_um"] / max(1, x["stations"])
            if sp > smax + EPS:
                R.err("stations", f"type {key[0]} slot {key[1]}: {x['len_um']:.0f} um route / {x['stations']} "
                      f"station(s) = {sp:.0f} um > ft_station_max_um {smax:.0f} (R3: add stations)", type=key[0])
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
    # R8: one cycle per latency group (bus groups from BINDER2 + replicated consumers), checked on the TABLE (what the
    # binder / compiler read), and pads realisable per type
    for name, kind, lids in P.latency_groups():
        got = {l: tab.get(l, {}).get("cycles") for l in lids if l in P.lanes}
        if len(set(got.values())) > 1:
            R.err("latency", f"{kind} group {name}: unequal delays {got} (regenerate: gen.py latency --inplace pads "
                  "every member to the slowest)")
    _, bad = P.bus_pads()
    for m in bad + P.landed_skew():
        R.err("latency", m)
    return {lid: P.lane_latency(lid)["cycles"] for lid in P.lanes}


def check_clock_reset(P, R):
    die_l = set(P.layer_budget["die_layers"])
    for tn, t in P.types.items():
        if t.get("hard"):
            continue
        ck = t.get("clock")
        if ck and "tap_um" in ck:
            w, h = t["outline_um"]
            x, y = ck["tap_um"]
            if not (0 <= x <= w and 0 <= y <= h):
                R.err("clock", f"type {tn}: clock tap {x},{y} outside the outline", type=tn)
            if ck.get("layer") and ck["layer"] not in die_l:
                R.err("clock", f"type {tn}: clock tap layer {ck['layer']} is not a die layer {sorted(die_l)}", type=tn)
            far = max(abs(x - a) + abs(y - b) for a in (0, w) for b in (0, h))
            if far > 2 * P.reach:
                R.warn("clock", f"type {tn}: farthest boundary point {far:.0f} um from the tap (> 2 hops)", type=tn)
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


# ------------------------------------------------------------------------------------------- taps, hard cores
def _orient_pt(o, w, h, x, y):
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]


CORE_CELLS_MAX = 400_000      # COORD 10-23 (CORE-KS): above this a partition type must be built from hard cores
MIRROR_SKIP = ("M2", "M3")    # platform cell-access tracks: not the plan lattice in a mirrored instance's die frame


def type_cells(t):
    """estimated std cells of one instance: type.cells, else the sum of contents[].cells (None when unknown)."""
    if "cells" in t:
        return int(t["cells"])
    cs = [c["cells"] for c in t.get("contents", []) if "cells" in c]
    return sum(cs) if cs else None


_PIN_CACHE = {}


def core_pins(hc, plan_dir=None):
    """[(name, layer, x, y)] of one hard core in its own frame (R0, origin 0): pins[] + pins_file (cached)."""
    pins = [(p_["name"], p_["layer"], *p_["xy"]) for p_ in hc.get("pins", [])]
    if hc.get("pins_file"):
        key = str(Path(plan_dir or ".") / hc["pins_file"])
        if key not in _PIN_CACHE:
            js = json.loads(Path(key).read_text())
            js = js.get("pins", js) if isinstance(js, dict) else js
            _PIN_CACHE[key] = [(q.get("name") or f"{q['bus']}[{q.get('bit', 0)}]", q["layer"], q["x"], q["y"])
                               for q in js]
        pins += _PIN_CACHE[key]
    return pins


def check_taps_cores(P, R, plan_dir=None, evidence=None):
    """clock.taps[] inside the type outline, unique names; hard_cores[]: pins land on the plan tracks after
    origin + track_offset and the core orient, in the type frame AND in every placed instance's die frame (MX/MY)."""
    out = dict(taps=0, hard_cores=0, core_pins=0, core_pins_off_track=0, types_no_cells=0, over_cap_no_cores=0)
    import cells as CE
    est, out["cell_sources"] = CE.estimate(P.raw, plan_dir, evidence or ())
    no_cells = []
    for tn, t in P.types.items():
        w, h = t["outline_um"]
        nc, basis = est.get(tn, (None, None))
        if nc is None:
            out["types_no_cells"] += 1
            no_cells.append(tn)
        elif nc > CORE_CELLS_MAX and not t.get("hard_cores"):
            out["over_cap_no_cores"] += 1
            R.err("hard_cores", f"type {tn}: {nc} cells ({basis}) > {CORE_CELLS_MAX} and no hard_cores[] (outline, "
                  "pins, track_offset): a type this large is built from hardened cores (COORD 10-23 CORE-KS)",
                  type=tn)
        ck = t.get("clock", {})
        names = set()
        for tp in ck.get("taps", []):
            out["taps"] += 1
            x, y = tp["xy"]
            if not (-EPS <= x <= w + EPS and -EPS <= y <= h + EPS):
                R.err("clock", f"type {tn}: clock tap {tp['name']} at ({x:g},{y:g}) outside the outline", type=tn)
            if tp["name"] in names:
                R.err("clock", f"type {tn}: duplicate clock tap {tp['name']}", type=tn)
            names.add(tp["name"])
        for hc in t.get("hard_cores", []):
            out["hard_cores"] += 1
            cw, chh = hc["outline_um"]
            o = hc.get("orient", "R0")
            ox, oy = hc["origin_um"]
            dx, dy = hc.get("track_offset_um", [0.0, 0.0])
            if abs(ox / P.grid - round(ox / P.grid)) > 1e-6 or abs(oy / P.grid - round(oy / P.grid)) > 1e-6:
                R.err("hard_cores", f"type {tn} core {hc['inst']}: origin {hc['origin_um']} not on the "
                      f"{P.grid:g}-um lattice (put the sub-lattice shift in track_offset_um)", type=tn)
            if max(abs(dx), abs(dy)) >= S.BASE_LATTICE_UM:
                R.err("hard_cores", f"type {tn} core {hc['inst']}: track_offset {hc.get('track_offset_um')} is not a "
                      "sub-lattice shift", type=tn)
            X0, Y0 = ox + dx, oy + dy
            if X0 < -EPS or Y0 < -EPS or X0 + cw > w + EPS or Y0 + chh > h + EPS:
                R.err("hard_cores", f"type {tn} core {hc['inst']}: placed box outside the type outline", type=tn)
            try:
                pins = core_pins(hc, plan_dir)
            except (OSError, ValueError, KeyError) as e:
                pins = [(p_["name"], p_["layer"], *p_["xy"]) for p_ in hc.get("pins", [])]
                R.err("hard_cores", f"type {tn} core {hc['inst']}: pins_file {hc['pins_file']}: {e}", type=tn)
            if not pins:
                R.err("hard_cores", f"type {tn} core {hc['inst']}: no pins listed (pins / pins_file): the core pins "
                      "must be proven on the kit tracks", type=tn)
            insts = [n for n, p_ in P.parts.items() if p_["type"] == tn]
            bad = 0
            for nm, ln, x, y in pins:
                out["core_pins"] += 1
                L = P.layers.get(ln)
                if L is None or ln == "M1":
                    continue
                tx, ty = _orient_pt(o, cw, chh, x, y)
                tx, ty = X0 + tx, Y0 + ty
                # M2/M3 keep the platform cell-access tracks: checked in the type frame and unmirrored instances
                # only (a mirrored instance's die frame is not their lattice; CORE-KS false M3 errors)
                frames = [("type", tx, ty)] + [(pi, *P.to_die(pi, (tx, ty))) for pi in insts
                                               if ln not in MIRROR_SKIP or P.parts[pi].get("orient", "R0") == "R0"]
                for fr, fx, fy in frames:
                    c = fx if L["dir"] == "V" else fy
                    if not on_track(c, L):
                        bad += 1
                        if bad <= 5:
                            R.err("hard_cores", f"type {tn} core {hc['inst']} pin {nm} {ln}: "
                                  f"{'x' if L['dir'] == 'V' else 'y'} {c:.4f} off the plan track "
                                  f"(offset {L['offset_um']:g}, pitch {L['pitch_um']:g}) in the {fr} frame", type=tn)
                        break
            out["core_pins_off_track"] += bad
            if bad > 5:
                R.err("hard_cores", f"type {tn} core {hc['inst']}: {bad} pins off the plan tracks", type=tn)
    out["no_cells"] = no_cells
    if False and out["types_no_cells"]:
        R.warn("hard_cores", f"{out['types_no_cells']} types without a cell estimate (type.cells, contents[].cells or "
               f"a cells.py evidence file): the > {CORE_CELLS_MAX}-cell hard-core rule is unchecked for them: "
               f"{', '.join(no_cells[:30])}{' ...' if len(no_cells) > 30 else ''}")
    return out


# ------------------------------------------------------------------------------------- hard-core face rule
_NORMAL = dict(N=(0.0, 1.0), S=(0.0, -1.0), E=(1.0, 0.0), W=(-1.0, 0.0))
FACE_AWAY_COS = -0.1     # a core port whose pins' mean best cos(face normal, direction to a partner) is below this
FACE_WARN_COS = 0.0      # FAILs; between the two (pins about perpendicular to the partner) it WARNs


def _core_face(o, x, y, cw, ch):
    """face of a core-frame pin, in the type frame after the core orient."""
    f = min([(x, "W"), (cw - x, "E"), (y, "S"), (ch - y, "N")])[1]
    if o in ("MX", "R180") and f in "NS":
        f = OPP[f]
    if o in ("MY", "R180") and f in "EW":
        f = OPP[f]
    return f


def _bus_targets(P, tn):
    """{bus: (x, y) type-frame point on the partition face that carries it}: the type's bus face/window when
    declared, else the first planned port of an instance of the type (die window -> type frame)."""
    t = P.types[tn]
    w, h = t["outline_um"]

    def pt(face, a, b):
        m = 0.5 * (a + b)
        return dict(N=(m, h), S=(m, 0.0), E=(w, m), W=(0.0, m))[face]
    out = {}
    for b in t.get("buses", []):
        if "face" in b and "window_um" in b:
            out[b["name"]] = (b["face"], pt(b["face"], *b["window_um"]))
    insts = {n for n, p_ in P.parts.items() if p_["type"] == tn}
    for pr in P.ports.values():
        if "face" not in pr or "window_um" not in pr:
            continue
        for side in ("src", "dst"):
            e = pr[side]
            if e["part"] not in insts or e["bus"] in out:
                continue
            df = pr["face"] if side == "src" or pr["src"]["part"] == DIE_PART else OPP[pr["face"]]
            a, b_ = pr["window_um"]
            x0, y0, x1, y1 = P.rect(e["part"])
            m = 0.5 * (a + b_)
            dpt = dict(N=(m, y1), S=(m, y0), E=(x1, m), W=(x0, m))[df]
            tf = P.type_face(e["part"], df)
            out[e["bus"]] = (tf, P.to_type(e["part"], dpt))
    return out


def best_face(dirs):
    """core face (type frame) that best faces a set of partner directions [(what, ux, uy)] (re-pin hint)."""
    return max("NSEW", key=lambda f: sum(_NORMAL[f][0] * ux + _NORMAL[f][1] * uy for _, ux, uy in dirs))


def load_core_conns(plan_dir=None, path=None):
    """optional sidecar {type: {core inst: {core port: ["bus:<type bus>" | "core:<inst>" | "leaf:<content inst>" |
    "face:<N|S|E|W>", ...]}}} (default PLANDIR/core_conns.json): core connectivity the plan JSON does not carry
    (cores nested inside a content leaf, e.g. S81 frame qbanks; KV head cores), written by the binder / plan owner."""
    f = Path(path) if path else Path(plan_dir or ".") / "core_conns.json"
    return json.loads(f.read_text()) if f.is_file() else {}


def check_core_faces(P, R, plan_dir=None, conns_file=None, max_msgs=5):
    """Connectivity-aware hard-core face rule (GEOM-REVIEW face rule; COORD 10-23 PLAN-TOOL4).

    Every hard-core pin group (core port) that connects to a partition face or to another core / placed leaf must
    sit on a core face that faces a partner.  Connectivity: type.buses[].leaf "<inst>.<port>", contents[].bind
    "bus:/epoch:<bus>" and "net:<net>" (leaf-to-leaf), and the core_conns.json sidecar.  A core matches a leaf inst
    when equal or split from it ("<leaf>_<piece>").  Score, in the type frame: per pin, the best cosine over the
    port's partners between the pin's face normal and the direction from the core centre to the partner (partition
    face: the bus window centre; core / leaf: its centre); the port FAILs when the mean over its pins is < 0
    (most pins on the far side: the route wraps the core).  Cores with no known connectivity are counted
    (unchecked) and WARNed per type."""
    out = dict(groups=0, groups_away=0, pins=0, pins_away=0, types_away=0, cores=0, cores_unchecked=0)
    side = load_core_conns(plan_dir, conns_file)
    for tn, t in P.types.items():
        hcs = t.get("hard_cores", [])
        if not hcs:
            continue
        w, h = t["outline_um"]
        bt = None
        boxes = {}
        for hc in hcs:
            cw, ch = hc["outline_um"]
            dx, dy = hc.get("track_offset_um", [0.0, 0.0])
            boxes[hc["inst"]] = (hc["origin_um"][0] + dx + cw / 2, hc["origin_um"][1] + dy + ch / 2)
        cent = dict(boxes)
        for c in t.get("contents", []):
            if c["inst"] not in cent and "origin_um" in c and "outline_um" in c:
                cent[c["inst"]] = (c["origin_um"][0] + c["outline_um"][0] / 2,
                                   c["origin_um"][1] + c["outline_um"][1] / 2)
        ist_bus = [e for e in t.get("internal_stations", [])
                   if str(e.get("conn", "")).startswith("bus:") and e.get("regs_um")]
        # Broadcast buses may have distinct final relay legs for each capture core.
        # Unscoped legacy entries retain their previous last-entry behavior.
        ist_last = {e["conn"][4:]: tuple(e["regs_um"][-1]) for e in ist_bus
                    if not e.get("capture") or str(e["capture"]).startswith("face bus ")}
        ist_capture = {(e["conn"][4:], str(e["capture"])): tuple(e["regs_um"][-1])
                       for e in ist_bus if e.get("capture") and not str(e["capture"]).startswith("face bus ")}
        conns = {}          # (leaf inst, leaf port) -> [(kind, name)]
        for b in t.get("buses", []):
            if b.get("leaf") and "." in b["leaf"]:
                li, lp = b["leaf"].split(".", 1)
                conns.setdefault((li, lp), []).append(("bus", b["name"]))
        net_ends = {}
        for c in t.get("contents", []):
            for lp, v in c.get("bind", {}).items():
                k, _, nm = v.partition(":")
                if k in ("bus", "epoch") and nm:
                    conns.setdefault((c["inst"], lp), []).append(("bus", nm))
                elif k == "net" and nm:
                    conns.setdefault((c["inst"], lp), []).append(("net", nm))
                    net_ends.setdefault(nm, set()).add(c["inst"])
        for ci, ports in side.get(tn, {}).items():
            for lp, lst in ports.items():
                for v in lst:
                    k, _, nm = v.partition(":")
                    conns.setdefault((ci, lp), []).append((k, nm))
        bad_t = unchecked = 0
        for hc in hcs:
            ci = hc["inst"]
            out["cores"] += 1
            mine = [(lp, tg) for (li, lp), tg in conns.items() if li == ci or ci.startswith(li + "_")]
            if not mine:
                unchecked += 1
                continue
            try:
                pins = core_pins(hc, plan_dir)
            except (OSError, ValueError, KeyError):
                continue
            cw, ch = hc["outline_um"]
            o = hc.get("orient", "R0")
            cx, cy = boxes[ci]
            by_base = {}
            for nm, _ln, x, y in pins:
                by_base.setdefault(re.sub(r"\[\d+\]$", "", nm), []).append(_core_face(o, x, y, cw, ch))
            ports = {}
            for lp, tg in mine:
                ports.setdefault(lp, []).extend(tg)
            for lp, tg in ports.items():
                faces = by_base.get(lp)
                if not faces:
                    continue
                pts = []
                for kind, nm in tg:
                    if kind == "bus":
                        if bt is None:
                            bt = _bus_targets(P, tn)
                        if (nm, ci + "." + lp) in ist_capture:
                            pts.append((f"station {nm} -> {ci}.{lp}", ist_capture[(nm, ci + "." + lp)]))
                        elif (nm, ci) in ist_capture:
                            pts.append((f"station {nm} -> {ci}", ist_capture[(nm, ci)]))
                        elif nm in ist_last:
                            # R3-INTERNAL: a bus with FIRM internal stations reaches the core from its last station
                            # (regs_um[-1], the register next to the core pin), not from the face window
                            pts.append((f"station {nm}", ist_last[nm]))
                        elif nm in bt:
                            pts.append((f"face {bt[nm][0]} ({nm})", bt[nm][1]))
                    elif kind == "net":
                        pts += [(f"{oi} (net {nm})", cent[oi]) for oi in sorted(net_ends.get(nm, ()))
                                if oi != ci and not ci.startswith(oi + "_") and oi in cent]
                    elif kind in ("core", "leaf") and nm in cent and nm != ci:
                        pts.append((nm, cent[nm]))
                    elif kind == "face" and nm in _NORMAL:
                        pts.append((f"face {nm}", dict(N=(cx, h), S=(cx, 0.0), E=(w, cy), W=(0.0, cy))[nm]))
                dirs = []
                for what, (tx, ty) in pts:
                    d = math.hypot(tx - cx, ty - cy)
                    if d > 1e-6:
                        dirs.append((what, (tx - cx) / d, (ty - cy) / d))
                if not dirs:
                    continue
                best = {f: max(_NORMAL[f][0] * ux + _NORMAL[f][1] * uy for _, ux, uy in dirs) for f in set(faces)}
                cs = [best[f] for f in faces]
                away = sum(1 for c_ in cs if c_ < -1e-9)
                mean = sum(cs) / len(cs)
                out["groups"] += 1
                out["pins"] += len(cs)
                out["pins_away"] += away
                if mean < FACE_WARN_COS:
                    bf = best_face(dirs)
                    part = ", ".join(sorted({wh for wh, _, _ in dirs})[:3]) + (" ..." if len(dirs) > 3 else "")
                    msg = (f"type {tn} core {ci} port {lp}: {len(cs)} pins on face {'/'.join(sorted(set(faces)))} "
                           f"face away from its partner(s) {part}: mean cos {mean:+.2f}, {away} pins on the far "
                           f"side (re-pin to face {bf})")
                    if mean >= FACE_AWAY_COS:
                        out["groups_side"] = out.get("groups_side", 0) + 1
                        if out["groups_side"] <= 50:
                            R.warn("core_faces", msg + " [about perpendicular: WARN]", type=tn)
                        continue
                    out["groups_away"] += 1
                    bad_t += 1
                    if bad_t <= max_msgs:
                        R.err("core_faces", msg, type=tn)
        if bad_t > max_msgs:
            R.err("core_faces", f"type {tn}: {bad_t} core ports face away from their partners "
                  f"({bad_t - max_msgs} more not listed)", type=tn)
        if unchecked:
            R.warn("core_faces", f"type {tn}: {unchecked}/{len(hcs)} hard cores with no known connectivity (no "
                   "buses[].leaf / contents[].bind / core_conns.json entry): face rule unchecked for them", type=tn)
        out["cores_unchecked"] += unchecked
        out["types_away"] += bool(bad_t)
    return out


# ------------------------------------------------------------------------------------- plan completeness
COMPLETE_FIELDS = ("cells", "track_offset", "clock_method", "common_latency", "insertion_target", "reset_sync",
                   "face_flop", "internal_station")


def _box_dist(pt, box):
    """Manhattan distance from a point to a box (x0, y0, x1, y1); 0 inside."""
    x, y = pt
    return max(box[0] - x, 0, x - box[2]) + max(box[1] - y, 0, y - box[3])


def _hops_ok(a, regs, b, smax):
    pts = [tuple(a)] + [tuple(r) for r in regs] + [tuple(b)]
    return max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])) <= smax + EPS


def check_completeness(P, R, no_cells=(), max_msgs=5):
    """PLAN COMPLETENESS (COORD 10-23 ~20:00): G0 is a completeness check; a missing field is an ERROR.
    Per partition type (hard IP types: cells / clock / reset / face flops not required):
      cells            a cell estimate (type.cells, contents[].cells or cells.py evidence)
      track_offset     every hard_cores[] entry declares track_offset_um (pins on tracks / > 400k: hard_cores check)
      clock_method     type.clock with tap_um, taps[] or tap_mode
      insertion_target a type clock.insertion_ps equal to the die common latency (one die-wide target, R4 b)
      reset_sync       type.reset (one async-assert / sync-deassert synchronizer)
      face_flop        every type bus is carried by a planned port with face geometry (face + window + layers), so
                       the R2 face flop is FIRM at its pin (the schema pass already refuses unbound buses and ports
                       without geometry; this re-counts them for the completeness table)
      internal_station every estimated internal reg-reg connection > ft_station_max_um (face window -> leaf / core
                       box, core <-> core net) has internal_stations[] whose hops are all <= the limit (R3-INTERNAL)
    Die: clock.common_latency_ps (R4 owner rule)."""
    miss = {f: 0 for f in COMPLETE_FIELDS}
    smax = float(P.budgets.get("ft_station_max_um", 750.0))
    n_msg = defaultdict(int)

    def bad(field, tn, msg):
        miss[field] += 1
        n_msg[field] += 1
        if True:
            R.err("complete", f"[{field}] " + (f"type {tn}: " if tn else "") + msg, type=tn, field=field)
    raw_ck = P.raw.get("clock", {})
    common = raw_ck.get("common_latency_ps")
    if common is None:
        bad("common_latency", None, "die clock.common_latency_ps missing (R4: one die-wide common latency target "
            "every partition balances its face-flop insertion to; vclk latency of the IO SDC)")
    no_cells = set(no_cells)
    ends = defaultdict(set)              # type -> buses used by a port
    for pr in P.ports.values():
        for side in ("src", "dst"):
            e = pr[side]
            if e["part"] != DIE_PART and e["part"] in P.parts:
                ends[P.parts[e["part"]]["type"]].add((e["bus"], pr["id"], "face" in pr and "window_um" in pr
                                                      and "layers" in pr))
    for tn, t in P.types.items():
        hard = bool(t.get("hard"))
        if tn in no_cells and not hard:
            bad("cells", tn, "no cell estimate (type.cells, contents[].cells or a cells.py evidence file)")
        for hc in t.get("hard_cores", []):
            if "track_offset_um" not in hc:
                bad("track_offset", tn, f"hard core {hc['inst']}: no track_offset_um (state [0, 0] if on the plan "
                    "tracks)")
        if hard:
            continue
        ck = t.get("clock") or {}
        if not ({"tap_um", "taps", "tap_mode"} & set(ck)):
            bad("clock_method", tn, "no clock method (clock.tap_um, clock.taps[] or clock.tap_mode)")
        if common is not None and "insertion_ps" in ck and abs(float(ck["insertion_ps"]) - float(common)) > EPS:
            bad("insertion_target", tn, f"clock.insertion_ps {ck['insertion_ps']:g} != die common latency "
                f"{float(common):g} (R4: one die-wide target)")
        if "reset" not in t:
            bad("reset_sync", tn, "no reset synchronizer entry (one per partition)")
        used = {bus for bus, _pid, _ok in ends.get(tn, ())}
        nf = [pid for bus, pid, ok in ends.get(tn, ()) if not ok] + \
             [b["name"] for b in t.get("buses", []) if b["name"] not in used]
        if nf:
            bad("face_flop", tn, f"{len(nf)} bus(es) with no planned port / face geometry, e.g. {nf[0]}: the R2 "
                "face flop has no FIRM pin site")
        # internal reg-reg length estimate (lower bound: point to box / box to box, Manhattan)
        boxes = {}
        for hc in t.get("hard_cores", []):
            dx, dy = hc.get("track_offset_um", [0.0, 0.0])
            x0, y0 = hc["origin_um"][0] + dx, hc["origin_um"][1] + dy
            boxes[hc["inst"]] = (x0, y0, x0 + hc["outline_um"][0], y0 + hc["outline_um"][1])
        for c in t.get("contents", []):
            if c["inst"] not in boxes and "origin_um" in c and "outline_um" in c:
                x0, y0 = c["origin_um"]
                boxes[c["inst"]] = (x0, y0, x0 + c["outline_um"][0], y0 + c["outline_um"][1])
        if not boxes:
            continue
        ist = t.get("internal_stations", [])
        for e in ist:
            if not _hops_ok(e["from_um"], e["regs_um"], e["to_um"], smax):
                bad("internal_station", tn, f"internal_stations {e.get('conn', e['from_um'])}: a hop > {smax:g} um")
        conns = {e.get("conn") for e in ist if e.get("conn")}

        def covered(key, a, b_box):
            if key in conns:
                return True
            return any(abs(e["from_um"][0] - a[0]) + abs(e["from_um"][1] - a[1]) <= 50.0
                       and _box_dist(e["to_um"], b_box) <= 50.0 for e in ist)
        bt = None
        nets = defaultdict(set)
        for c in t.get("contents", []):
            for lp, v in c.get("bind", {}).items():
                if v.startswith("net:"):
                    nets[v[4:]].add(c["inst"])
        todo = []
        for b in t.get("buses", []):
            lf = b.get("leaf") or ""
            li = lf.split(".")[0]
            cand = [ci for ci in boxes if ci == li or ci.startswith(li + "_")] if li else []
            if not cand:
                continue
            if bt is None:
                bt = _bus_targets(P, tn)
            if b["name"] not in bt:
                continue
            a = bt[b["name"]][1]
            d = min(_box_dist(a, boxes[ci]) for ci in cand)
            if d > smax and not covered(f"bus:{b['name']}", a, boxes[cand[0]]) and not covered(lf, a, boxes[cand[0]]):
                todo.append((f"bus {b['name']} (face window -> {lf})", d))
        for nm, insts in nets.items():
            ins = sorted(i for i in insts if i in boxes)
            for i, x in enumerate(ins):
                for y in ins[i + 1:]:
                    bx, by = boxes[x], boxes[y]
                    d = max(bx[0] - by[2], by[0] - bx[2], 0) + max(bx[1] - by[3], by[1] - bx[3], 0)
                    if d > smax and f"{x}|{y}" not in conns and f"{y}|{x}" not in conns:
                        todo.append((f"net {nm} ({x} <-> {y})", d))
        for what, d in todo:
            bad("internal_station", tn, f"internal {what} >= {d:.0f} um > {smax:g} um with no internal_stations[] "
                "entry (R3-INTERNAL: FIRM plan stations)")
    if any(miss.values()):
        R.warn("complete", "missing-field counts: " + ", ".join(f"{k} {v}" for k, v in miss.items() if v))
    return miss


# ------------------------------------------------------------------------------------------------------ types
def check_die_io(P, R):
    """COORD 10-23 (S81-P5): every off-die port lands in a declared pad / bump window over its host partition."""
    io = P.die.get("io")
    die_ports = {pid: pr for pid, pr in P.ports.items() if DIE_PART in (pr["src"]["part"], pr["dst"]["part"])}
    if not io:
        if die_ports:
            R.warn("die_io", f"{len(die_ports)} die IO ports ({sum(int(p['width']) for p in die_ports.values())} b) "
                   "and no die.io pad / bump windows: off-die pads (SerDes PMA, HBM PHY memory side, host) unplanned")
        return dict(windows=0, ports=len(die_ports))
    seen = {}
    for w in io:
        x0, y0, x1, y1 = w["rect_um"]
        if not (0 <= x0 < x1 <= P.W + EPS and 0 <= y0 < y1 <= P.H + EPS):
            R.err("die_io", f"io window {w['name']}: rect {w['rect_um']} outside the die")
        if w["part"] not in P.parts:
            R.err("die_io", f"io window {w['name']}: unknown host partition {w['part']}")
            continue
        px0, py0, px1, py1 = P.rect(w["part"])
        if x0 < px0 - EPS or y0 < py0 - EPS or x1 > px1 + EPS or y1 > py1 + EPS:
            R.err("die_io", f"io window {w['name']}: not inside its host partition {w['part']}")
        bits = 0
        for pid in w.get("ports", []):
            pr = P.ports.get(pid)
            if pr is None or pid not in die_ports:
                R.err("die_io", f"io window {w['name']}: {pid} is not a die IO port")
                continue
            if pid in seen:
                R.err("die_io", f"die IO port {pid} in two windows ({seen[pid]}, {w['name']})")
            seen[pid] = w["name"]
            end = pr["dst"]["part"] if pr["src"]["part"] == DIE_PART else pr["src"]["part"]
            if end != w["part"]:
                R.err("die_io", f"io window {w['name']}: port {pid} ends in {end}, not the host {w['part']}")
            bits += S.port_pins_count(pr)
        if bits > w["sites"]:
            R.err("die_io", f"io window {w['name']}: {bits} signal bits > {w['sites']} sites")
    for pid in sorted(set(die_ports) - set(seen)):
        R.err("die_io", f"die IO port {pid} ({die_ports[pid]['width']} b) has no pad / bump window (die.io)")
    return dict(windows=len(io), ports=len(die_ports), placed=len(seen))


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


def check_r8(P, R, plan_dir=None, groups=None, landing=None):
    """COORD R8 (r8.py) on BINDER2's bus groups.  No bus groups -> WARN (R8 cannot be judged without the bind)."""
    import r8
    pd = Path(plan_dir) if plan_dir else None
    if groups is None and pd is not None:
        groups = next((q for q in (pd / "bus_groups.json", pd / "r8" / "bus_groups.json", pd / "bind" / "bus_groups.json")
                       if q.exists()), None)
    if groups is None:
        if pd is None:
            return dict(checked=False)
        R.warn("r8", "R8 not checked: no as-built bus groups (BINDER2 bind.py bus_groups.json; pass --groups)")
        return dict(checked=False)
    bg = json.loads(Path(groups).read_text())
    if landing is None and pd is not None:
        hits = sorted(pd.glob(f"*/{P.name}_r8_landing.json")) + sorted(pd.glob(f"{P.name}_r8_landing.json"))
        landing = hits[0] if hits else None
    lmap = None
    if landing is not None:
        lmap, ljs = r8.load_landing(landing)
        if ljs.get("bus_groups_digest") != r8.bg_digest(bg):
            R.err("r8", f"R8 landing table {landing} was made from other bus groups (digest {ljs.get('bus_groups_digest')}"
                  f" != {r8.bg_digest(bg)}): regenerate with gen.py latency --groups")
        mode = dict(replica=ljs.get("replica", "all"), bus=ljs.get("bus", "part"))
    else:
        mode = dict(replica="all", bus="part")
    msgs, st = r8.check(bg, P.raw, lmap, **mode)
    for sev, m in msgs:
        (R.err if sev == "ERROR" else R.warn)("r8", m)
    st.update(checked=True, groups_file=str(groups), landing_file=str(landing) if landing else None)
    return st


# ------------------------------------------------------------------------------------------------------- run
def g0c_summary(P, R):
    """per partition type: G0C findings by check; types with none are G3-eligible (as far as the plan goes)."""
    by = {tn: defaultdict(int) for tn in P.types}
    die = defaultdict(int)
    for i in R.items:
        if not i.get("g0c"):
            continue
        tgt = by.get(i.get("type"), die)
        tgt[i["check"] + (f":{i['field']}" if i.get("field") else "")] += 1
    bad = {tn: dict(c) for tn, c in by.items() if c}
    return dict(types=len(P.types), clean=len(P.types) - len(bad), die_level=dict(die),
                g3_eligible=sorted(tn for tn in P.types if tn not in bad and not die), by_type=bad)


def run(raw, png=None, plan_dir=None, groups=None, landing=None, evidence=None, core_conns=None, completeness=False):
    R = Report(completeness)
    io_src = "plan" if raw.get("die", {}).get("io") else None
    sc = Path(plan_dir) / "die_io.json" if plan_dir else None
    if io_src is None and sc is not None and sc.exists():
        # PLAN-TOOL5: die IO sidecar (die_io.py plan --out PLANDIR/die_io.json) when the plan has no die.io: it survives
        # the die generators' regeneration; a die.io list in the plan always wins
        raw = dict(raw, die=dict(raw["die"], io=json.loads(sc.read_text())))
        io_src = str(sc)
    errs = S.validate(raw)
    for e in errs:
        R.err("schema", e)
    if errs:
        return R, dict()
    P = S.Plan(raw)
    summ = dict(die=P.name, partitions=len(P.parts), types=len(P.types), ports=len(P.ports), lanes=len(P.lanes),
                bits=sum(p["width"] for p in P.ports.values()))
    summ["types"] = check_types(P, R)
    summ["taps_cores"] = check_taps_cores(P, R, plan_dir, evidence)
    summ["core_faces"] = check_core_faces(P, R, plan_dir, core_conns)
    summ["complete"] = check_completeness(P, R, summ["taps_cores"].get("no_cells", ()))
    summ["g0c"] = g0c_summary(P, R)
    summ["geometry"] = check_geometry(P, R)
    fp = check_abutment(P, R)
    summ["worst_faces"] = check_faces(P, R, fp)
    geo = {lid: lane_geometry(P, lid) for lid in P.lanes}
    summ["worst_hops"] = check_hops(P, R, geo)
    summ["cuts"] = check_cuts(P, R, geo)
    summ["latency"] = check_latency(P, R)
    summ["r8"] = check_r8(P, R, plan_dir, groups, landing)
    check_clock_reset(P, R)
    summ["seams"] = check_seams(P, R)
    summ["die_io"] = check_die_io(P, R)
    # PLAN-TOOL5 cross-die G0C rules (COORD DIE-PLAN VISUAL REVIEW 10-23 (a)-(e))
    import die_io
    import xdie
    summ["die_io"]["plan"] = die_io.check(P, R)
    summ["die_io"]["pg_domains"] = die_io.check_pg_domains(P, R)
    summ["die_io"]["source"] = io_src
    summ["cut_lines"] = xdie.check_cut_lines(P, R, geo)
    summ["reach"] = xdie.check_reach(P, R, geo)
    summ["face_tracks"] = xdie.check_face_tracks(P, R, fp)
    summ["ft_budget"] = xdie.check_ft_budget(P, R, fp)
    summ["g0c"] = g0c_summary(P, R)
    summ["xdie_counts"] = {c: sum(1 for i in R.items if i["check"] == c and i.get("g0c")) for c in G0C_CHECKS}
    import census_cov
    summ["census"] = census_cov.coverage(P, plan_dir or ".", R)
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
    ap.add_argument("--groups", help="R8: BINDER2 bus_groups.json (default PLANDIR/bind/bus_groups.json)")
    ap.add_argument("--landing", help="R8: <die>_r8_landing.json (default PLANDIR/*/<die>_r8_landing.json)")
    ap.add_argument("--cells-evidence", action="append", default=[],
                    help="cells.py evidence file (type / partition / module cell table or Yosys stat); repeatable; "
                         "PLANDIR cells_est.json, plan_notes.json, l1_cores_v3*.json, cells_evidence.json are read too")
    ap.add_argument("--completeness", action="store_true",
                    help="G0C: plan-completeness + hard-core rules are ERRORs (default: WARN '[G0C]'); per-type "
                         "summary in summary.g0c (types with 0 findings = G3-eligible)")
    ap.add_argument("--core-conns", help="hard-core connectivity sidecar (default PLANDIR/core_conns.json)")
    a = ap.parse_args(argv)
    raw = S.load(a.plan)
    out = Path(a.out) if a.out else Path(a.plan).resolve().parent
    out.mkdir(parents=True, exist_ok=True)
    R, summ = run(raw, png=(out / "die_plan.png") if a.png else None, plan_dir=Path(a.plan).resolve().parent,
                  groups=a.groups, landing=a.landing, evidence=a.cells_evidence, core_conns=a.core_conns,
                  completeness=a.completeness)
    ne = len(R.errors())
    nw = len(R.items) - ne
    ok = ne == 0 and not (a.strict and nw)
    rep = dict(schema="opentallas.die_plan.g0.v1", plan=str(Path(a.plan).resolve()), verdict="PASS" if ok else "FAIL",
               mode="G0C" if a.completeness else "G0",
               errors=ne, warnings=nw, summary=summ, findings=R.items)
    (out / "g0_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    if not a.quiet:
        for i in R.items[:200]:
            print(f"{i['level']:5s} [{i['check']}] {i['msg']}")
        if len(R.items) > 200:
            print(f"... {len(R.items) - 200} more in g0_report.json")
    c = summ.get("cuts", {})
    ty = summ.get("types", {})
    g = summ.get("g0c", {})
    print(f"G0C per type: {g.get('clean')}/{g.get('types')} types clean (G3-eligible: {len(g.get('g3_eligible', []))}); "
          f"die-level {g.get('die_level')}; {'ERRORs' if a.completeness else 'reported as WARN (run --completeness)'}")
    print(f"{rep['mode']} {rep['verdict']}: {ne} errors, {nw} warnings; {ty.get('types')} types / {ty.get('partitions')} "
          f"partitions ({ty.get('near_duplicate_types')} in near-duplicate groups); worst cut {c.get('worst_full')}, worst partition "
          f"segment {c.get('worst_partition_segment')}; report {out / 'g0_report.json'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

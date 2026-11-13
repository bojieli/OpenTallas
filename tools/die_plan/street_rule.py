#!/usr/bin/env python3
"""STREET-RULE-1 (COORD 11-12): street-or-abut rule for hard cores inside a partition type, as a plan-generator pass.

    street_rule.py check PLAN [--types T1,T2|--match RE] [--die NAME] [--repo ROOT] [--ref-dirs ..] [--out JSON]
    street_rule.py legalize PLAN --out-plan NEW.json --event EVENT.json [--types ..|--match RE] [--rs-halving MODE]

RULE (per partition type; positions and type outlines only, never a core shape):
  Between two hard cores whose projections overlap (a FACING pair), and between a hard core and the type outline, the
  gap is either ABUTTED (gap < abut_um, one 4.32-um placement site of the plan lattice; core_place clusters on the same
  unit) or a STREET of width
        need = max(street_min_um, pins_facing x pin_pitch_um / (street_layers x street_fill))      snapped up to 4.32
  where pins_facing = signal pins (no clk / strap) of BOTH faces inside the facing span that do NOT go straight across
  to the facing core (a pin whose net ends on the opposite core crosses the street: it needs no track along it).
  Nothing in between: an 8-26 um slot with pins facing into it is the failure class this lane removes.
  Calibration (defaults): street_min 43.2 (VISLAYOUT3-S81-SLICE L1 canyon 21.6 -> 64.8; VISLAYOUT3-S81-LEAF
  LANE-PAIR 160+160-pin faces at 43.2), pin_pitch 0.048 (M4/M5), 3 layers along the street (M3/M5/M7 or M2/M4/M6)
  at 0.6 fill (12.7e): 1,620 facing pins fill a 43.2-um street, the lepe_nh_mus_LP 3,349-pin / 15-um slot needs 90.7.
  WALL: a face with > wall_pins (1500) signal pins never faces another pin face (>= pinface_min pins) closer than
  wall_min_um (43.2): an abutted pair with such faces is an error, only the outline or a street may face it.
  TAP STREET: every core cluster keeps one face on a gap >= tap_street_um (17.28, a tap-legal site row with the 8.64
  tap clearance on both sides) or on the outline, so a clock tap can sit beside its sinks.

LEGALIZE (compactor / expander, keeps the relative order of everything):
  1-D longest-path passes, x then y, repeated until the check is clean or `rounds` is reached.  Nodes: the core
  clusters of core_place.TypeModel (cores < 4.32 apart move rigidly) and the type's fixed non-core geometry (ft station
  registers and bit-site groups, clock / reset taps, landing bands, reserved channels).  Edges only between nodes whose
  projections on the other axis overlap (only those can collide or face each other in this pass):
      core -> core  x_j >= x_i + w_i + req_ij   (req = 0 if the pair is abutted and legal, else need(pins))
      core <-> point/rect                      clearance = the point's halo (4.32 ft, 8.65 tap, as core_place)
      outline       x_i >= need(W face pins) unless abutted to W;  W' >= x_i + w_i + need(E face pins) unless abutted.
  A sliver with no pins on either face (< pinface_min) closes to abut instead (the node may move left by the gap
  when nothing else holds it).  Every displacement and every outline growth is a multiple of 4.32 (outline growth
  of the die grid, 8.64), so lattice and track phase are kept.  Non-core geometry within anchor_um of the E/N outline
  follows the outline growth.  Stations whose ends moved are re-sited by core_place.write_type (hub_repack
  route_station, register count kept); a type is APPLIED only if: 0 overlaps, 0 points under cores, every station
  keeps its register count, no direct link / ft hop exceeds max(base, 405 um), every fixed core stays, and the
  structural EQ check (only coordinates / outline_um differ) passes.  Otherwise the row says why and the base stays.

R-STREET (RULES-STREET-1 11-13, RULEBOOK-1113; cfg face_rule=1, default on): two more ERROR kinds on the same check
and the same legalize.  K = street_layers x street_fill / pin_pitch = 37.5 tracks per um of street width.
  FACE STREET (face_street): the TYPE's own face pins (bus / ft windows, uniform in the window) behind which a macro
  sits.  Macros (hard cores and LEF contents) closer than face_depth_um (129.6) to a pin face form WALLS along that
  face: neighbours whose lateral opening is < street_min_um merge.  n = type pins of the face inside the wall span;
  ends = wall ends with a >= street_min_um opening (to the next wall, to an abutted macro, to the corner).  Every
  wall member keeps        gap >= need = min(129.6, max(floor, up4.32(n / (K x ends))))            (ends = 0: 129.6)
  off the face, floor = street_min_um (43.2) when the wall is DENSE (n / wall length >= dense_per_um = 3 pins/um; the
  failing S81 faces carry 4.0-5.4), else tap_street_um (17.28).  A wall with < pinface_min (16) pins has no demand (the
  plan edge margin stays legal).  A macro ABUTTED to the face (< 4.32) is legal only when the pins in its span go
  straight into it (pins <= its own face pins + 16); otherwise its pins move out of the span or it lifts to a street.
  1,620 shadowed pins fill 43.2 one-ended, 3,240 two-ended; the 616-um t28 S wall (2,929 pins, one end) needs 82.08.
  STATION ALLEY (station_alley): planned station registers (ft bit sites / regs, internal stations) may sit only in
  open area or in a street.  A station point whose free width (macro to macro, or macro to outline, along x or y) is
  < street_min_um stands in a SLOT; with B >= pinface_min station bits in a slot of length L (the facing overlap) it
  is an ERROR when the slot is < tap_street_um (17.28) wide, or < street_min_um (43.2) wide and dense (B / L >=
  dense_per_um).  Legalize widens that slot to a street (the pair / the outline gap becomes a street requirement).
  TRANSIT STREET (transit_street, WARN; legalize widens it only with --set transit_rule=1): a station chain that RUNS ALONG a slot uses it as a corridor.  Every planned hop
  (window -> first station, station -> station, last station -> window; internal stations from -> regs -> to) is a
  segment with the bits of its slot; a hop that runs along x (|dx| >= |dy|) loads the free width in y at its
  midpoint (macro to macro or macro to outline), a hop along y the free width in x.  T = the largest sum of hop bits
  through one 43.2-um bucket of the slot; the slot keeps  width >= up4.32(T / K).  2,208 transit bits (two 1,104-bit ft
  slots side by side, the t28 S strip) need 60.48 um, 3,400 bits 90.72.  Legalize widens the slot to that width.
  NOTCH: a wall or slot shorter than street_min_um along its length is exempt from both rules (open area is at most
  21.6 um away), unless the macro is abutted to the pin face.
  Legalize moves hard cores only (never a shape, never a LEF content macro: those stay residual with their reason).
  Types WITHOUT hard cores whose LEF content macros (SRAM / ROM) break the rule are checked too (check and G0).

OUTPUT: new plan (types changed only), event JSON + TSV rows: per type outline before/after and growth %, cores
moved, violations before/after, route_supply p99 before/after (route_supply on both plans), die-level growth estimate
(partition push model: every instance of a grown type widens, partitions to its right / above are pushed keeping
their gaps; die area growth % and reticle headroom).
"""
import argparse
import collections
import copy
import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core_place as CP  # noqa: E402
import route_supply as RS  # noqa: E402

SCHEMA = "opentallas.street_rule.v1"
G = 4.32
EPS = 1e-6
DEFAULTS = dict(street_min_um=43.2, pin_pitch_um=0.048, street_layers=3.0, street_fill=0.6, abut_um=G,
                wall_pins=1500, wall_min_um=43.2, pinface_min=16, tap_street_um=17.28, anchor_um=21.6,
                rounds=4, reach=360.0, outline_grid_um=8.64, max_growth_pct=25.0, outline_margin_um=8.64, attempts=4,
                reach_limit_um=405.0, grow_axes="xy", reticle_fit=1, rs_worse=0.1,
                add_regs=0, pin_reorder=0, x_pin_factor=1.0, band_file="", sliver_rule=0,
                face_rule=1, face_depth_um=129.6, face_passes=5, dense_per_um=3.0, transit_rule=0)
RETICLE_UM = (26000.0, 33000.0)
OPP = dict(N="S", S="N", E="W", W="E")
# ERROR kinds; sliver / outline_sliver / tap_street are WARN.  face_street / station_alley: R-STREET (11-13)
# transit_street is a WARN (measured on t28: widening the corridors to bits / K on top of the face / station rules cut
# the M4-M8 overflow only 13% more for +7.7% area); --set transit_rule=1 makes legalize widen them too
HARD = ("street", "wall", "outline_street", "face_street", "station_alley")
# SLIVER RULE (COORD 11-12, VISLAYOUT3-S81-LEAF): --set sliver_rule=1 makes "no two facing core edges closer than one
# street" a hard rule: a core-core gap in [abut_um, street) is a STREET violation even when (almost) no pins face it,
# so check counts it as an error and legalize widens it to need_um (>= street_min_um).  Default 0 keeps the WARN class.


def need_um(pins, cfg):
    w = pins * cfg["pin_pitch_um"] / (cfg["street_layers"] * cfg["street_fill"])
    return round(max(cfg["street_min_um"], math.ceil(w / G - 1e-9) * G), 4)


def up(v, q=G):
    return round(math.ceil(v / q - 1e-9) * q, 4) if v > EPS else 0.0


# ------------------------------------------------------------------------------------------------ pure geometry rule
def face_pos(core, face, lo, hi):
    """sorted along-face coordinates (type frame) of the signal pins of core on face inside [lo, hi]."""
    off = core["y"] if face in "EW" else core["x"]
    return sorted(p + off for p, _ in core["pins"].get(face, ()) if lo - EPS <= p + off <= hi + EPS)


def aligned_pairs(pa, pb, tol=0.5):
    """one-to-one pin pairs at the same along-face coordinate (+-tol) on two facing faces (two pointers)."""
    i = j = n = 0
    while i < len(pa) and j < len(pb):
        if abs(pa[i] - pb[j]) <= tol:
            n += 1
            i += 1
            j += 1
        elif pa[i] < pb[j]:
            i += 1
        else:
            j += 1
    return n


def face_count(core, face, lo, hi, other=None, windows=None):
    """signal pins of core on face whose along-face coordinate (type frame) lies in [lo, hi], minus pins that go
    STRAIGHT ACROSS the gap: core_conns names the facing core `other` for the pin's bus, or (outline) the pin sits in a
    type bus / ft window on that face."""
    n = 0
    part = core["partners"]
    star = other is not None and other in part.get("*", ())
    for pos, bus in core["pins"].get(face, ()):
        a = pos + (core["y"] if face in "EW" else core["x"])
        if lo - EPS <= a <= hi + EPS:
            if other is not None and (star or other in part.get(bus, ())):
                continue
            if windows and any(w0 - 0.5 <= a <= w1 + 0.5 for w0, w1 in windows.get(face, ())):
                continue
            n += 1
    return n


def pair_rule(a, b, cfg):
    """None if a and b do not face each other, else dict(axis, gap, pins, need, kind) with kind in
    ok | abut | wall | street."""
    gx = max(b["x"] - (a["x"] + a["w"]), a["x"] - (b["x"] + b["w"]))
    gy = max(b["y"] - (a["y"] + a["h"]), a["y"] - (b["y"] + b["h"]))
    if gy < -EPS and gx > -EPS:          # side by side in x, facing E/W
        lo, hi = max(a["y"], b["y"]), min(a["y"] + a["h"], b["y"] + b["h"])
        fa, fb = ("E", "W") if a["x"] <= b["x"] else ("W", "E")
        axis, gap = "x", gx
    elif gx < -EPS and gy > -EPS:        # stacked in y, facing N/S
        lo, hi = max(a["x"], b["x"]), min(a["x"] + a["w"], b["x"] + b["w"])
        fa, fb = ("N", "S") if a["y"] <= b["y"] else ("S", "N")
        axis, gap = "y", gy
    else:
        return None
    pa, pb = face_count(a, fa, lo, hi, b["inst"]), face_count(b, fb, lo, hi, a["inst"])
    reorder = 0
    if not a.get("has_conns") and not b.get("has_conns") and pa and pb:
        # no core_conns for either core (native split seams): one-to-one aligned pin pairs cross the gap straight
        m = aligned_pairs(face_pos(a, fa, lo, hi), face_pos(b, fb, lo, hi))
        if cfg.get("pin_reorder"):
            # lever (b), owner 11-12: the two faces carry the same nets -> pin order matched so they go straight across
            reorder = min(pa, pb) - m
            m = min(pa, pb)
        pa, pb = pa - m, pb - m
    if axis == "x" and cfg.get("x_pin_factor", 1.0) != 1.0:
        # lever (d), owner 11-12: S81 BUS-GEAR (B) 2:1 x feed halves the facing E/W pins
        pa, pb = int(-(-pa * cfg["x_pin_factor"] // 1)), int(-(-pb * cfg["x_pin_factor"] // 1))
    r = dict(axis=axis, gap=round(gap, 4), pins=[pa, pb], faces=[fa, fb], span=round(hi - lo, 2), pin_reorder=reorder)
    if gap < cfg["abut_um"] - EPS:
        big = max(pa, pb) > cfg["wall_pins"] and min(pa, pb) >= cfg["pinface_min"]
        r.update(kind="wall" if big else "abut", need=cfg["wall_min_um"] if big else 0.0)
        return r
    nd = need_um(pa + pb, cfg)
    forced = (cfg.get("_alley") or {}).get(frozenset((a["inst"], b["inst"])))
    if forced:
        nd = max(nd, forced)          # R-STREET: stations sit in / run along this slot (legalize): street of that width
    r.update(need=nd, kind="ok" if gap >= nd - EPS else "street")
    if r["kind"] == "street" and pa + pb < cfg["pinface_min"]:
        if forced:
            r["alley"] = True
        elif cfg.get("sliver_rule"):
            r["sliver"] = True        # sliver rule on: a sub-street slot between facing cores is a street violation
        else:
            r["kind"] = "sliver"      # (almost) no pins into it: WARN only (tap-illegal / wasted area), never widened
    return r


def outline_rule(c, W, H, cfg, windows=None):
    out = []
    for face, gap, lo, hi in (("W", c["x"], c["y"], c["y"] + c["h"]), ("E", W - c["x"] - c["w"], c["y"], c["y"] + c["h"]),
                              ("S", c["y"], c["x"], c["x"] + c["w"]), ("N", H - c["y"] - c["h"], c["x"], c["x"] + c["w"])):
        if gap < cfg["abut_um"] - EPS:
            continue
        p = face_count(c, face, lo, hi, windows=windows)
        if face in "WE" and cfg.get("x_pin_factor", 1.0) != 1.0:
            p = int(-(-p * cfg["x_pin_factor"] // 1))
        nd = need_um(p, cfg)
        if p < cfg["pinface_min"] and gap <= cfg["outline_margin_um"] + EPS:
            continue          # the plan's standard edge margin, no pins into it
        if gap < nd - EPS:
            out.append(dict(face=face, gap=round(gap, 4), pins=p, need=nd,
                            kind="sliver" if p < cfg["pinface_min"] else "street"))
    return out


def analyze(W, H, cores, clusters, cfg, windows=None):
    """cores: [{inst, x, y, w, h, pins{face: [(pos, bus)]}, partners{bus: set(inst)}}]; clusters: [[core idx]].
    Returns violations (list of dicts) and per-kind counts."""
    V = []
    cid = {i: k for k, g in enumerate(clusters) for i in g}
    n = len(cores)
    for i in range(n):
        for j in range(i + 1, n):
            r = pair_rule(cores[i], cores[j], cfg)
            if r and r["kind"] not in ("ok", "abut"):
                r.update(a=cores[i]["inst"], b=cores[j]["inst"], same_cluster=cid[i] == cid[j])
                V.append(r)
        for r in outline_rule(cores[i], W, H, cfg, windows):
            r.update(a=cores[i]["inst"], b="outline", kind="outline_" + r["kind"])
            V.append(r)
    # tap street: each cluster needs one face on a >= tap_street_um gap or on the outline
    for k, g in enumerate(clusters):
        x0 = min(cores[i]["x"] for i in g); y0 = min(cores[i]["y"] for i in g)
        x1 = max(cores[i]["x"] + cores[i]["w"] for i in g); y1 = max(cores[i]["y"] + cores[i]["h"] for i in g)
        best = 0.0
        for side in "WESN":
            gap = {"W": x0, "E": W - x1, "S": y0, "N": H - y1}[side]
            for k2, g2 in enumerate(clusters):
                if k2 == k:
                    continue
                X0 = min(cores[i]["x"] for i in g2); Y0 = min(cores[i]["y"] for i in g2)
                X1 = max(cores[i]["x"] + cores[i]["w"] for i in g2); Y1 = max(cores[i]["y"] + cores[i]["h"] for i in g2)
                if side in "WE" and min(Y1, y1) > max(Y0, y0):
                    d = (x0 - X1) if side == "W" else (X0 - x1)
                    if d > -EPS:
                        gap = min(gap, d)
                if side in "SN" and min(X1, x1) > max(X0, x0):
                    d = (y0 - Y1) if side == "S" else (Y0 - y1)
                    if d > -EPS:
                        gap = min(gap, d)
            # a face on the outline (abutted / edge margin) counts: the edge row takes the tap
            edge = {"W": x0, "E": W - x1, "S": y0, "N": H - y1}[side]
            if edge <= cfg["outline_margin_um"] + EPS:
                gap = max(gap, cfg["tap_street_um"])
            best = max(best, gap)
        if best < cfg["tap_street_um"] - EPS:
            V.append(dict(kind="tap_street", a=cores[g[0]]["inst"], b="", gap=round(best, 2),
                          need=cfg["tap_street_um"], pins=[0, 0]))
    if cfg.get("face_rule") and cfg.get("_fwins"):
        V += face_shadow_rule(W, H, [_core_box(c) for c in cores] + list(cfg.get("_xboxes") or ()), cfg["_fwins"], cfg)
    cnt = collections.Counter(v["kind"] for v in V)
    return V, dict(cnt)


# ------------------------------------------------------------------------------------------------ R-STREET (11-13)
def type_face_windows(t):
    """{face: [(lo, hi, pins, name)]}: the type's bus / ft pin windows with their pin counts (uniform in a window)."""
    out = collections.defaultdict(list)
    for b in t.get("buses") or []:
        if isinstance(b, dict) and b.get("face") in OPP and isinstance(b.get("window_um"), list) and b.get("width"):
            lo, hi = b["window_um"][:2]
            out[b["face"]].append((float(lo), float(hi), int(b["width"]), str(b.get("name"))))
    for f in t.get("ft_slots") or []:
        for fk, wk, sfx in (("in_face", "in_window_um", "_i"), ("out_face", "out_window_um", "_o")):
            if f.get(fk) in OPP and isinstance(f.get(wk), list) and f.get("width"):
                lo, hi = f[wk][:2]
                out[f[fk]].append((float(lo), float(hi), int(f["width"]), str(f.get("name")) + sfx))
    return dict(out)


def span_pins(wins, lo, hi):
    """pins of the windows [(lo, hi, pins, name)] inside [lo, hi] (uniform density per window)."""
    n = 0.0
    for a, b, w, _ in wins:
        o = min(b, hi) - max(a, lo)
        if o > EPS:
            n += w * min(1.0, o / max(b - a, 1e-9))
    return int(round(n))


def free_spans(wins_len, shadows, smin):
    """[(lo, hi)] spans of a face (length wins_len) outside every macro shadow, >= smin long: where pins may move."""
    out, x = [], 0.0
    for lo, hi in sorted(shadows) + [(wins_len, wins_len)]:
        if lo - x >= smin - EPS:
            out.append((round(x, 2), round(lo, 2)))
        x = max(x, hi)
    return out


def _core_box(c):
    return dict(inst=c["inst"], x=c["x"], y=c["y"], w=c["w"], h=c["h"], movable=True,
                face_pins={f: len(v) for f, v in (c.get("pins") or {}).items()})


def extra_boxes(t):
    """LEF content macros of the type that are not hard cores (SRAM / ROM / PHY parts): fixed obstacles."""
    cores = {h["inst"] for h in t.get("hard_cores") or []}
    out = []
    for c in t.get("contents") or []:
        ents = [c] if c.get("lef") else []
        ents += [dict(p, inst=p.get("physical_inst")) for p in c.get("physical_parts") or []]
        for e in ents:
            if e.get("inst") in cores or "origin_um" not in e or "outline_um" not in e:
                continue
            w, h = map(float, e["outline_um"][:2])
            if e.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
                w, h = h, w
            out.append(dict(inst=e["inst"], x=float(e["origin_um"][0]), y=float(e["origin_um"][1]), w=w, h=h,
                            movable=False, face_pins={}))
    return out


def face_shadow_rule(W, H, boxes, wins, cfg):
    """R-STREET face street: violations [dict(kind='face_street', a, b='face:F', face, gap, need, pins=[n, 0], wall,
    ends, movable, free_spans)] for macros `boxes` behind the type pin windows `wins` (type_face_windows)."""
    V = []
    smin, D, ab, pmin = cfg["street_min_um"], cfg["face_depth_um"], cfg["abut_um"], cfg["pinface_min"]
    k = cfg["street_layers"] * cfg["street_fill"] / cfg["pin_pitch_um"]
    for face in "WESN":
        fw = wins.get(face) or []
        if sum(w[2] for w in fw) < pmin:
            continue
        L = H if face in "WE" else W
        ent, blk = [], []
        for b in boxes:
            if face in "WE":
                gap, lo, hi = (b["x"] if face == "W" else W - b["x"] - b["w"]), b["y"], b["y"] + b["h"]
            else:
                gap, lo, hi = (b["y"] if face == "S" else H - b["y"] - b["h"]), b["x"], b["x"] + b["w"]
            if gap >= D - EPS:
                continue
            (blk if gap < ab - EPS else ent).append((lo, hi, gap, b))
        shadows = [(e[0], e[1]) for e in ent + blk]
        fs = free_spans(L, shadows, smin)
        for lo, hi, gap, b in blk:        # abutted to the pin face: only straight-in pins may sit in its span
            n = span_pins(fw, lo, hi) - int(b.get("face_pins", {}).get(face, 0))
            if n >= pmin:
                V.append(dict(kind="face_street", a=b["inst"], b="face:" + face, face=face, gap=round(gap, 4),
                              need=smin, pins=[n, 0], wall=[round(lo, 2), round(hi, 2)], ends=0,
                              movable=bool(b.get("movable")), abutted=True, free_spans=fs))
        ent.sort(key=lambda e: (e[0], e[1]))
        walls = []
        for e in ent:
            if walls and e[0] - walls[-1]["hi"] < smin - EPS:
                walls[-1]["hi"] = max(walls[-1]["hi"], e[1])
                walls[-1]["m"].append(e)
            else:
                walls.append(dict(lo=e[0], hi=e[1], m=[e]))
        stops = [0.0, L] + [v for b_ in blk for v in b_[:2]]
        for wl in walls:
            n = span_pins(fw, wl["lo"], wl["hi"])
            if n < pmin or wl["hi"] - wl["lo"] < smin - EPS:
                continue              # no pins behind it, or a notch shorter than one street (pins jog <= 21.6 um)
            left = max([s for s in stops if s <= wl["lo"] + EPS] or [0.0])
            right = min([s for s in stops if s >= wl["hi"] - EPS] or [L])
            ends = int(wl["lo"] - left >= smin - EPS) + int(right - wl["hi"] >= smin - EPS)
            dense = n / max(wl["hi"] - wl["lo"], 1e-9) >= cfg["dense_per_um"]
            floor = smin if dense else cfg["tap_street_um"]
            nd = D if ends == 0 else min(D, max(floor, up(n / (k * ends))))
            for lo, hi, gap, b in wl["m"]:
                if gap < nd - EPS:
                    V.append(dict(kind="face_street", a=b["inst"], b="face:" + face, face=face, gap=round(gap, 4),
                                  need=round(nd, 4), pins=[n, 0], wall=[round(wl["lo"], 2), round(wl["hi"], 2)],
                                  ends=ends, dense=dense, movable=bool(b.get("movable")), free_spans=fs))
    return V


def face_needs(W, H, cores, cfg):
    """{(inst, face): need um} of the movable cores under the face rule at the current positions (legalize)."""
    out = {}
    if cfg.get("face_rule") and cfg.get("_fwins"):
        for v in face_shadow_rule(W, H, [_core_box(c) for c in cores] + list(cfg.get("_xboxes") or ()),
                                  cfg["_fwins"], cfg):
            if v["movable"]:
                out[(v["a"], v["face"])] = max(out.get((v["a"], v["face"]), 0.0), v["need"])
    for key, nd in (cfg.get("_alley_faces") or {}).items():
        out[key] = max(out.get(key, 0.0), nd)
    return out


def station_points(t):
    """[(x, y, bits)] planned station registers of a type: ft slot stations (bit sites per 8.64 cell, else the
    station register point with the slot width) and internal stations (regs_um, bits)."""
    pts = []
    for f in t.get("ft_slots") or []:
        sites = f.get("bit_sites_um") or []
        lists = sites if (sites and isinstance(sites[0], list) and sites[0] and isinstance(sites[0][0], list)) else \
            ([sites] if sites and isinstance(sites[0], list) else [])
        if lists:
            for s_ in lists:
                cells = collections.Counter()
                for p in s_:
                    if isinstance(p, list) and len(p) >= 2:
                        cells[(int(p[0] // 8.64), int(p[1] // 8.64))] += 1
                pts += [((cx + 0.5) * 8.64, (cy + 0.5) * 8.64, n) for (cx, cy), n in cells.items()]
        else:
            pts += [(float(r[0]), float(r[1]), int(f.get("width") or 1)) for r in f.get("regs_um") or []
                    if isinstance(r, list) and len(r) >= 2]
    for st in t.get("internal_stations") or []:
        for r in st.get("regs_um") or []:
            if isinstance(r, list) and len(r) >= 2:
                pts.append((float(r[0]), float(r[1]), int(st.get("bits") or 1)))
    return pts


def station_alleys(t, cfg, boxes=None):
    """R-STREET station alley: [dict(kind='station_alley', a, b, axis, gap, need, pins=[bits, 0], stations)] for
    station bits standing in a macro-macro or macro-outline slot narrower than street_min_um."""
    if not cfg.get("face_rule"):
        return []
    W, H = map(float, t["outline_um"][:2])
    if boxes is None:
        boxes = []
        for (x0, y0, x1, y1), h in zip(_core_rects(t), t.get("hard_cores") or []):
            boxes.append(dict(inst=h["inst"], x=x0, y=y0, w=x1 - x0, h=y1 - y0, movable=True))
        boxes += extra_boxes(t)
    if not boxes:
        return []
    smin, tmin = cfg["street_min_um"], cfg["tap_street_um"]
    R = [(b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"], b["inst"]) for b in boxes]
    RN = {r[4]: r for r in R}

    def slot_len(axis, a, b):
        ra, rb = RN.get(a), RN.get(b)
        i0, i1 = (1, 3) if axis == "x" else (0, 2)
        if ra and rb:
            return max(min(ra[i1], rb[i1]) - max(ra[i0], rb[i0]), 1e-9)
        r = ra or rb
        return max(r[i1] - r[i0], 1e-9)
    acc = {}
    for x, y, bits in station_points(t):
        if any(r[0] - 0.01 < x < r[2] + 0.01 and r[1] - 0.01 < y < r[3] + 0.01 for r in R):
            continue                  # on a core (its own station bay): rides with the core
        lx, ln_, rx, rn = 0.0, "outline:W", W, "outline:E"
        by, bn, ty, tn_ = 0.0, "outline:S", H, "outline:N"
        for x0, y0, x1, y1, nm in R:
            if y0 <= y <= y1:
                if x1 <= x and x1 > lx:
                    lx, ln_ = x1, nm
                if x0 >= x and x0 < rx:
                    rx, rn = x0, nm
            if x0 <= x <= x1:
                if y1 <= y and y1 > by:
                    by, bn = y1, nm
                if y0 >= y and y0 < ty:
                    ty, tn_ = y0, nm
        for axis, lo, hi, a, b in (("x", lx, rx, ln_, rn), ("y", by, ty, bn, tn_)):
            if hi - lo < smin - EPS and not (a.startswith("outline") and b.startswith("outline")):
                d = acc.setdefault((axis, a, b), dict(gap=hi - lo, bits=0, stations=0))
                d["bits"] += bits
                d["stations"] += 1
                d["gap"] = min(d["gap"], hi - lo)
    V = []
    for (axis, a, b), d in sorted(acc.items()):
        if d["bits"] < cfg["pinface_min"]:
            continue
        L = slot_len(axis, a, b)
        if L < smin - EPS:
            continue                  # a notch shorter than one street is not an alley: open area is <= 21.6 um away
        dense = d["bits"] / L >= cfg["dense_per_um"]
        nd = smin if dense else tmin
        if d["gap"] < nd - EPS:
            V.append(dict(kind="station_alley", a=a, b=b, axis=axis, gap=round(d["gap"], 4), need=nd,
                          pins=[d["bits"], 0], stations=d["stations"], slot_um=round(L, 2), dense=dense))
    return V + transit_streets(t, cfg, boxes)


def plan_face_windows(raw, plan_path=None, names=None):
    """{type: {face: [(lo, hi, pins, name)]}} for the types whose buses carry no face / window_um (qwen_kvsys: the
    windows live on the die ports): the pins of the type's first instance from schema.Plan (the gen_phys.type_pins
    walk), one window per run of a bus on a face (runs split at gaps > 8.64 um).  {} when the plan does not load."""
    T = raw.get("partition_types") or {}
    want = [n for n in (names if names is not None else T) if n in T
            and (T[n].get("hard_cores") or extra_boxes(T[n])) and not type_face_windows(T[n])]
    if not want:
        return {}
    try:
        import schema as S
        P = S.Plan(raw, plan_path)
        first = {}
        for pn, q in P.parts.items():
            first.setdefault(q["type"], pn)
        inst = {first[n]: n for n in want if n in first}
        acc = collections.defaultdict(list)
        for pid, pr in P.ports.items():
            for side in ("src", "dst"):
                tn = inst.get(pr[side]["part"])
                if tn is None:
                    continue
                part = pr[side]["part"]
                df = pr["face"] if (side == "src" or pr["src"]["part"] == S.DIE_PART) else S.OPP[pr["face"]]
                tf = P.type_face(part, df)
                line = S.Plan.rect(P, part)
                for _bit, _ln, c in P.port_pins(pid):
                    pt = ((line[2] if df == "E" else line[0]), c) if df in "EW" else \
                        (c, (line[3] if df == "N" else line[1]))
                    x, y = P.to_type(part, pt)
                    acc[(tn, tf, pr[side]["bus"])].append(y if tf in "EW" else x)
    except Exception as ex:      # noqa: BLE001 (a plan that does not load has no face rule; the check says so)
        print("street_rule: plan pin windows unavailable (%s: %s); face_street skipped for %d types"
              % (type(ex).__name__, str(ex)[:160], len(want)), file=sys.stderr)
        return {}
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    for (tn, tf, bus), cs in acc.items():
        cs.sort()
        run = [cs[0]]
        for c in cs[1:] + [None]:
            if c is None or c - run[-1] > 8.64:
                out[tn][tf].append((run[0], max(run[-1], run[0] + 0.048), len(run), bus))
                run = [c]
            else:
                run.append(c)
    return {tn: {f: sorted(w) for f, w in d.items()} for tn, d in out.items()}


def station_hops(t):
    """[(x0, y0, x1, y1, bits)] planned register-to-register hops of a type: per ft slot the chain window -> stations
    -> window (regs_um, which starts / ends on the faces when the plan says so), per internal station from -> regs ->
    to."""
    hops = []
    for f in t.get("ft_slots") or []:
        pts = [r[:2] for r in f.get("regs_um") or [] if isinstance(r, list) and len(r) >= 2]
        b = int(f.get("width") or 1)
        hops += [(a[0], a[1], c[0], c[1], b) for a, c in zip(pts, pts[1:])]
    for st in t.get("internal_stations") or []:
        pts = [st["from_um"][:2]] if isinstance(st.get("from_um"), list) else []
        pts += [r[:2] for r in st.get("regs_um") or [] if isinstance(r, list) and len(r) >= 2]
        if isinstance(st.get("to_um"), list):
            pts.append(st["to_um"][:2])
        b = int(st.get("bits") or 1)
        hops += [(a[0], a[1], c[0], c[1], b) for a, c in zip(pts, pts[1:])]
    return hops


def transit_streets(t, cfg, boxes=None):
    """R-STREET transit street: [dict(kind='transit_street', a, b, axis, gap, need, pins=[T, 0], at_um)] for slots
    whose width is under up(T / K), T = station-chain bits running along the slot through one 43.2-um bucket."""
    if not cfg.get("face_rule"):
        return []
    W, H = map(float, t["outline_um"][:2])
    if boxes is None:
        boxes = []
        for (x0, y0, x1, y1), h in zip(_core_rects(t), t.get("hard_cores") or []):
            boxes.append(dict(inst=h["inst"], x=x0, y=y0, w=x1 - x0, h=y1 - y0, movable=True))
        boxes += extra_boxes(t)
    if not boxes:
        return []
    k = cfg["street_layers"] * cfg["street_fill"] / cfg["pin_pitch_um"]
    bk = cfg["street_min_um"]
    R = [(b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"], b["inst"]) for b in boxes]
    acc = collections.defaultdict(lambda: collections.defaultdict(int))
    gap = {}
    for x0, y0, x1, y1, bits in station_hops(t):
        along_x = abs(x1 - x0) >= abs(y1 - y0)
        if max(abs(x1 - x0), abs(y1 - y0)) < bk - EPS:
            continue                  # a hop shorter than one street loads no corridor
        lo, hi = (min(x0, x1), max(x0, x1)) if along_x else (min(y0, y1), max(y0, y1))
        q = (y0 + y1) / 2 if along_x else (x0 + x1) / 2
        nb = int((hi - lo) // bk)
        seen = set()                  # a hop loads one (slot, bucket) once
        for j in range(nb + 1):       # sample the hop every 43.2 um: each sample loads the slot it stands in
            a_ = min(lo + (j + 0.5) * bk, hi) if nb else (lo + hi) / 2
            x, y = (a_, q) if along_x else (q, a_)
            if any(r[0] - 0.01 < x < r[2] + 0.01 and r[1] - 0.01 < y < r[3] + 0.01 for r in R):
                continue              # over a core: the core carries it (its own ft / station bay)
            p0, n0, p1, n1 = 0.0, "outline:" + ("S" if along_x else "W"), (H if along_x else W), \
                "outline:" + ("N" if along_x else "E")
            for rx0, ry0, rx1, ry1, nm in R:
                c0, c1, d0, d1 = (rx0, rx1, ry0, ry1) if along_x else (ry0, ry1, rx0, rx1)
                c = x if along_x else y
                d = y if along_x else x
                if c0 <= c <= c1:
                    if d1 <= d and d1 > p0:
                        p0, n0 = d1, nm
                    if d0 >= d and d0 < p1:
                        p1, n1 = d0, nm
            if n0.startswith("outline") and n1.startswith("outline"):
                continue
            key = ("y" if along_x else "x", n0, n1)       # the slot is bounded along the other axis
            gap[key] = min(gap.get(key, 1e18), p1 - p0)
            if (key, int(a_ // bk)) not in seen:
                seen.add((key, int(a_ // bk)))
                acc[key][int(a_ // bk)] += bits
    V = []
    for key, bks in sorted(acc.items()):
        j, T = max(bks.items(), key=lambda kv: kv[1])
        nd = up(T / k)
        if T >= cfg["pinface_min"] and gap[key] < nd - EPS:
            V.append(dict(kind="transit_street", a=key[1], b=key[2], axis=key[0], gap=round(gap[key], 4), need=nd,
                          pins=[T, 0], at_um=round((j + 0.5) * bk, 1)))
    return V


def type_cfg(cfg, t, name=None):
    """per-type cfg for analyze(): the type pin windows (type buses / ft slots, else the plan port pins in
    cfg _planwins) and the fixed LEF content boxes of the face rule."""
    if not cfg.get("face_rule"):
        return cfg
    wins = type_face_windows(t) or (cfg.get("_planwins") or {}).get(name) or {}
    return dict(cfg, _fwins=wins, _xboxes=extra_boxes(t))


def content_only(t, cfg, name=None):
    """R-STREET on a type WITHOUT hard cores whose LEF content macros (SRAM / ROM / PHY parts) stand behind its pin
    faces or squeeze its stations: the same face_street / station_alley kinds (never movable by legalize)."""
    xb = extra_boxes(t)
    if not cfg.get("face_rule") or not xb:
        return []
    W, H = map(float, t["outline_um"][:2])
    c = type_cfg(cfg, t, name)
    return face_shadow_rule(W, H, xb, c.get("_fwins") or {}, cfg) + station_alleys(t, cfg, xb)


def alley_force(V, transit=False):
    """({core-core pair: need}, {(inst, face): need}) that legalize widens for the station alleys V (and, with
    transit, the transit streets)."""
    pairs, faces = {}, {}
    for v in V:
        if v["kind"] not in (("station_alley", "transit_street") if transit else ("station_alley",)):
            continue
        a, b = v["a"], v["b"]
        nd = max(float(v["need"]), 43.2)
        if a.startswith("outline") or b.startswith("outline"):
            key = (b, a[-1]) if a.startswith("outline") else (a, b[-1])
            faces[key] = max(faces.get(key, 0.0), nd)
        else:
            key = frozenset((a, b))
            pairs[key] = max(pairs.get(key, 0.0), nd)
    return pairs, faces


# ------------------------------------------------------------------------------------------------ plan -> model
def conns_partners(conns, name, t):
    """{inst: {bus: set(partner inst)}} from core_conns, made SYMMETRIC: core_conns lists a link at one end or both
    (col types list e ROM <- bs bank only at the ROM end, 'core:u_r0.u_bs0.o_x0'), so a named far port gets the
    near core as its partner too."""
    cc_key = next((k for k in (name, re.sub(r"__cl[0-9a-f]{8}.*$", "", name), re.sub(r"__.*$", "", name))
                   if conns.get(k)), None)
    cc = conns.get(cc_key) if cc_key else {}
    out = collections.defaultdict(lambda: collections.defaultdict(set))
    insts = {h["inst"] for h in t.get("hard_cores") or []}

    def split(val):
        if val in insts:
            return val, None
        a, _, port = val.rpartition(".")
        if a in insts:
            return a, port
        # a split core named by its parent (u_e0 -> u_e0.u_w / u_e0.u_e)
        kids = [i for i in insts if i.startswith(val + ".")]
        return (kids, None) if kids else (None, None)
    if cc:
        out["__conns__"]["*"] = {"__type_has_core_conns__"}
    for inst, ports in (cc or {}).items():
        if inst not in insts:
            continue
        for bus, dl in (ports or {}).items():
            for d in dl or []:
                k, _, val = str(d).partition(":")
                if k != "core":
                    continue
                b, port = split(val)
                for bb in (b if isinstance(b, list) else [b] if b else []):
                    out[inst][bus].add(bb)
                    if port:
                        out[bb][re.sub(r"\[\d+\]$", "", port)].add(inst)
                    else:
                        out[bb]["*"].add(inst)
    return out


def type_windows(t):
    """{face: [(lo, hi)]} of the type bus / ft windows (along-face um)."""
    out = collections.defaultdict(list)
    for b in t.get("buses") or []:
        if isinstance(b, dict) and b.get("face") in ("N", "S", "E", "W") and isinstance(b.get("window_um"), list):
            out[b["face"]].append(tuple(b["window_um"][:2]))
    for f in t.get("ft_slots") or []:
        for fk, wk in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
            if f.get(fk) in ("N", "S", "E", "W") and isinstance(f.get(wk), list):
                out[f[fk]].append(tuple(f[wk][:2]))
    return dict(out)


FACE_ALONG = dict(N=0, S=0, E=1, W=1)     # along-face coordinate index (x on N/S, y on E/W)


def face_anchor_cfg(fa, name):
    """validated FIXED-FACE config of one type (legalize --face-anchor FILE: {type: cfg}); None = legacy (every window
    keeps its local coordinate, the instance origin stays).  cfg keys:
      grow          {"x": "E"|"W", "y": "N"|"S"}: the side the outline grows on (default E / N: origin kept).  W / S:
                    every instance origin moves by -dW / -dH, so the E / N edge keeps its die position.
      origin_shift_um [dx, dy]: an extra die-level move of every instance of the type (e.g. a pushed neighbour); 0, 0.
      fixed_faces   faces that abut FIXED partitions: their windows (buses, ft slots, landing pins and bands of the
                    face's buses, outline link ends) keep their DIE coordinate along the face.  Every other face abuts a
                    moved (or no) partition and keeps its LOCAL windows."""
    if fa is None:
        return None
    if not isinstance(fa, dict) or set(fa) - {"grow", "origin_shift_um", "fixed_faces"}:
        raise ValueError("%s: face anchor needs only grow / origin_shift_um / fixed_faces" % name)
    g = fa.get("grow") or {}
    if not isinstance(g, dict) or g.get("x", "E") not in ("E", "W") or g.get("y", "N") not in ("N", "S") or set(g) - {"x", "y"}:
        raise ValueError("%s: face anchor grow must be {x: E|W, y: N|S}" % name)
    sh = fa.get("origin_shift_um", [0.0, 0.0])
    if not isinstance(sh, list) or len(sh) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in sh):
        raise ValueError("%s: face anchor origin_shift_um must be [dx, dy]" % name)
    ff = fa.get("fixed_faces", [])
    if not isinstance(ff, list) or any(f not in FACE_ALONG for f in ff):
        raise ValueError("%s: face anchor fixed_faces must list N/S/E/W" % name)
    return dict(grow=dict(x=g.get("x", "E"), y=g.get("y", "N")), origin_shift_um=[float(sh[0]), float(sh[1])],
                fixed_faces=sorted(set(ff)))


def _on_face(x, y, W, H, tol=8.64):
    """outline faces within tol of a point (a landing pin sits a few um inside its face)."""
    return [f for f, d in (("W", x), ("E", W - x), ("S", y), ("N", H - y)) if abs(d) <= tol]


def face_anchor(tnew, M, WH0, WH1, fa, t0=None):
    """FIXED-FACE (GEN-CLASS-1 11-12, HEAD-95 west growth): legalize grows the outline on E / N in LOCAL coordinates.
    With fa (face_anchor_cfg) the instance origin moves by shift = origin_shift_um + (-dW if grow x W) / (-dH if grow
    y S); a window on a FIXED face then moves by -shift along that face so its die coordinate (the fixed neighbour's
    pins) is unchanged, while windows on every other face keep their local coordinates (their neighbours move with
    the type).  Pins and bands on a fixed face take their BASE (t0) position + the shift (the free-space remap of
    an interior stretch does not apply to a coordinate held by a fixed neighbour).  Moved on a fixed face: buses[].window_um, ft_slots in/out_window_um, landing_contract pins on the face,
    the landing bands (rect_um / rects_um / ff_rect_um) of the face's buses, and the outline end points of M.L links on
    the face.  Returns (record, errors); errors = a moved window outside the outline (the type is then not applied)."""
    W0, H0 = WH0
    W1, H1 = WH1
    sx, sy = fa["origin_shift_um"]
    if fa["grow"]["x"] == "W":
        sx -= W1 - W0
    if fa["grow"]["y"] == "S":
        sy -= H1 - H0
    d = (-sx, -sy)
    rec = dict(origin_shift_um=[round(sx, 4), round(sy, 4)], fixed_faces=fa["fixed_faces"], moved=[])
    errs = []
    L = (W1, H1)
    for face in fa["fixed_faces"]:
        a = FACE_ALONG[face]
        da = round(d[a], 4)
        if not da:
            continue
        buses = set()
        for b in tnew.get("buses") or []:
            if b.get("face") == face and isinstance(b.get("window_um"), list):
                b["window_um"] = [round(v + da, 4) for v in b["window_um"][:2]] + b["window_um"][2:]
                buses.add(b.get("name"))
                rec["moved"].append("bus %s" % b.get("name"))
                if b["window_um"][0] < -EPS or b["window_um"][1] > L[a] + EPS:
                    errs.append("bus %s window %s outside the %s face" % (b.get("name"), b["window_um"][:2], face))
        for f in tnew.get("ft_slots") or []:
            for fk, wk, sfx in (("in_face", "in_window_um", "_i"), ("out_face", "out_window_um", "_o")):
                if f.get(fk) == face and isinstance(f.get(wk), list):
                    f[wk] = [round(v + da, 4) for v in f[wk][:2]] + f[wk][2:]
                    buses.add(f.get("name", "") + sfx)
                    rec["moved"].append("ft %s.%s" % (f.get("name"), wk))
                    if f[wk][0] < -EPS or f[wk][1] > L[a] + EPS:
                        errs.append("ft %s %s outside the %s face" % (f.get("name"), wk, face))
        lc = (tnew.get("clock") or {}).get("landing_contract") or {}
        lc0 = ((t0 or tnew).get("clock") or {}).get("landing_contract") or {}
        pins0 = lc0.get("pins") or []
        for i, pin in enumerate(lc.get("pins") or []):
            xy = pin.get("xy_um")
            b0 = pins0[i].get("xy_um") if t0 is not None and i < len(pins0) else None
            ref = b0 if isinstance(b0, list) and len(b0) == 2 else xy
            if isinstance(xy, list) and len(xy) == 2 and face in _on_face(xy[0], xy[1], W1, H1):
                xy[a] = round(ref[a] + da, 4)
        bands0 = lc0.get("bands") or {}
        for bus, band in (lc.get("bands") or {}).items():
            if bus not in buses:
                continue
            if t0 is not None and bus in bands0:
                band0 = copy.deepcopy(bands0[bus])
                for k in ("rect_um", "ff_rect_um", "rects_um"):
                    if k in band0:
                        band[k] = band0[k]
            for k in ("rect_um", "ff_rect_um"):
                if isinstance(band.get(k), list) and len(band[k]) == 4:
                    band[k][a] = round(band[k][a] + da, 4)
                    band[k][a + 2] = round(band[k][a + 2] + da, 4)
            for r in band.get("rects_um") or []:
                r[a] = round(r[a] + da, 4)
                r[a + 2] = round(r[a + 2] + da, 4)
            rec["moved"].append("band %s" % bus)
        for q, (ea, eb, wb, kind) in enumerate(M.L):
            ends = []
            for e in (ea, eb):
                if e[0] is None and face in _on_face(e[1][0], e[1][1], W1, H1, tol=1.0):
                    xy = list(e[1])
                    xy[a] += da
                    e = (None, tuple(xy))
                ends.append(e)
            M.L[q] = (ends[0], ends[1], wb, kind)
    return rec, errs


def core_models(M, partners):
    """core dicts for analyze() from a core_place.TypeModel at its current state."""
    cores = []
    for i in range(M.n):
        x0, y0 = M.core_origin(i)
        w, h = M.dim[i]
        cores.append(dict(inst=M.inst[i], x=float(x0), y=float(y0), w=float(w), h=float(h), pins=M._sr_pins[i],
                          partners=partners.get(M.inst[i], {}), has_conns=bool(partners.get("__conns__"))))
    return cores


def attach_pins(M, die_dir, repo):
    """per core: face -> [(offset along the face from the core origin, bus)] in the type frame (base orient)."""
    M._sr_pins = []
    for i, h in enumerate(M.C):
        pl = RS.core_pins(h, die_dir, repo)
        x0, y0 = M.org0[i]
        w, hh = M.dim[i]
        d = collections.defaultdict(list)
        for bus, x, y in pl:
            if "clk" in bus or bus.startswith("strap_"):
                continue
            u, v = x - x0, y - y0
            f = min([(u, "W"), (w - u, "E"), (v, "S"), (hh - v, "N")])[1]
            d[f].append((v if f in "EW" else u, bus))
        M._sr_pins.append(dict(d))


# ------------------------------------------------------------------------------------------------ non-core nodes
class Item:
    """a piece of non-core geometry that may be pushed: rect [x0, y0, x1, y1] + halo + setter."""
    __slots__ = ("rect", "halo", "kind", "dx", "dy", "apply", "chain")

    def __init__(self, rect, halo, kind, apply, chain=False):
        self.rect, self.halo, self.kind, self.apply = list(rect), halo, kind, apply
        self.dx = self.dy = 0.0
        self.chain = chain          # point-like (ft register / bit-site cell): keeps its order in its row / column


def _pt_setter(lst, idx):
    def f(dx, dy):
        p = lst[idx]
        lst[idx] = [round(p[0] + dx, 4), round(p[1] + dy, 4)] + list(p[2:])
    return f


def _sites_setter(lst, idx=None):
    def f(dx, dy):
        for k in (range(len(lst)) if idx is None else idx):
            p = lst[k]
            lst[k] = [round(p[0] + dx, 4), round(p[1] + dy, 4)] + list(p[2:])
    return f


def site_components(pts, cell=8.64):
    """index groups of points connected on a cell-um grid (8-neighbourhood): a station's bit-site field moves as
    rigid pieces, so a piece never straddles a core corner it could be pushed under."""
    occ = collections.defaultdict(list)
    for k, p in enumerate(pts):
        occ[(int(p[0] // cell), int(p[1] // cell))].append(k)
    seen, out = set(), []
    for c0 in occ:
        if c0 in seen:
            continue
        stack, comp = [c0], []
        seen.add(c0)
        while stack:
            c = stack.pop()
            comp += occ[c]
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    n = (c[0] + dx, c[1] + dy)
                    if n in occ and n not in seen:
                        seen.add(n)
                        stack.append(n)
        out.append(sorted(comp))
    return out


def _rect_setter(obj, key):
    def f(dx, dy):
        r = obj[key]
        obj[key] = [round(r[0] + dx, 4), round(r[1] + dy, 4), round(r[2] + dx, 4), round(r[3] + dy, 4)] + list(r[4:])
    return f


def _key_pt_setter(obj, key):
    def f(dx, dy):
        p = obj[key]
        obj[key] = [round(p[0] + dx, 4), round(p[1] + dy, 4)] + list(p[2:])
    return f


def collect_items(t, on_core):
    """the non-core geometry of type t (a deep copy that the setters edit). on_core(p) -> True for points on a core
    (they ride with it through core_place.write_type and are not items)."""
    items = []
    for f in t.get("ft_slots") or []:
        regs = f.get("regs_um") or []
        for k, r in enumerate(regs):
            if isinstance(r, list) and len(r) >= 2 and not on_core(r):
                items.append(Item([r[0], r[1], r[0], r[1]], G, "ft_reg", _pt_setter(regs, k), chain=True))
        sw, sh = (f.get("bit_site_cell_um") or [1.404, 0.27])[:2]
        sites = f.get("bit_sites_um") or []
        if sites and isinstance(sites[0], list) and sites[0] and isinstance(sites[0][0], list):
            lists = sites
        elif sites and isinstance(sites[0], list):
            lists = [sites]
        else:
            lists = []
        for s in lists:
            # one item per 4.32-um lattice cell of a station's site field: cells keep their order per row / column
            cells = collections.defaultdict(list)
            for k, p in enumerate(s):
                if isinstance(p, list) and len(p) >= 2 and not on_core(p):
                    cells[(int(p[0] // G), int(p[1] // G))].append(k)
            for ks in cells.values():
                xs, ys = [s[k][0] for k in ks], [s[k][1] for k in ks]
                items.append(Item([min(xs), min(ys), max(xs) + sw, max(ys) + sh], G, "ft_sites", _sites_setter(s, ks),
                                  chain=True))
    ck = t.get("clock") or {}
    if isinstance(ck.get("tap_um"), list) and len(ck["tap_um"]) >= 2 and not on_core(ck["tap_um"]):
        p = ck["tap_um"]
        items.append(Item([p[0], p[1], p[0], p[1]], 8.65, "clock_tap", _key_pt_setter(ck, "tap_um")))
    for e in ck.get("edge_clocks") or []:
        if isinstance(e, dict) and isinstance(e.get("tap_um"), list) and not on_core(e["tap_um"]):
            p = e["tap_um"]
            items.append(Item([p[0], p[1], p[0], p[1]], 8.65, "edge_clock", _key_pt_setter(e, "tap_um")))
    for tp in (ck.get("taps") or []) + (ck.get("added_taps") or []):
        if isinstance(tp, dict) and isinstance(tp.get("xy"), list) and tp.get("kind") != "core" and not on_core(tp["xy"]):
            p = tp["xy"]
            items.append(Item([p[0], p[1], p[0], p[1]], 8.65, "tap", _key_pt_setter(tp, "xy")))
    rs = t.get("reset") or {}
    if isinstance(rs.get("tap_um"), list) and not on_core(rs["tap_um"]):
        p = rs["tap_um"]
        items.append(Item([p[0], p[1], p[0], p[1]], 8.65, "reset_tap", _key_pt_setter(rs, "tap_um")))
    for c in t.get("channels") or []:
        if isinstance(c, dict) and c.get("rect_um"):
            items.append(Item(c["rect_um"][:4], 0.0, "channel", _rect_setter(c, "rect_um")))
    for bn, bd in (((ck.get("landing_contract") or {}).get("bands")) or {}).items():
        if isinstance(bd, dict) and bd.get("rect_um"):
            items.append(Item(bd["rect_um"][:4], 0.0, "band", _rect_setter(bd, "rect_um")))
    return items


# ------------------------------------------------------------------------------------------------ legalizer
def _cluster_rects(M, k, pos):
    out = []
    for i in M.CL[k]:
        ox, oy = M.moff(i, "R0")
        out.append((i, pos[0] + ox, pos[1] + oy, M.dim[i, 0], M.dim[i, 1]))
    return out


def one_pass(M, items, axis, W, H, cfg, partners, fixed_k, windows=None, fix_ft=False, grow=True):
    """1-D two-sided compaction along axis ('x' -> index 0): difference constraints from the facing pairs, ASAP from
    the W/S outline, ALAP from the E/N outline; the outline grows only by the shortfall max(ASAP - ALAP); every node
    takes its old coordinate clamped into [ASAP, ALAP].  Returns (new cluster pos, new W or H, item shifts, blocked)."""
    ax = 0 if axis == "x" else 1
    L = W if ax == 0 else H
    pos = [tuple(M.cpos[k]) for k in range(M.m)]
    cores = core_models(M, partners)
    fneed = face_needs(W, H, cores, cfg)      # R-STREET: type pin-face streets + station alleys on the outline
    # nodes: clusters 0..m-1, items m..
    start = []
    for k in range(M.m):
        start.append(pos[k][ax])
    for it in items:
        start.append(it.rect[ax])
    nN = len(start)
    edges = collections.defaultdict(list)   # u -> [(v, delta)] meaning x_v >= x_u + delta
    rects = {k: _cluster_rects(M, k, pos[k]) for k in range(M.m)}

    def ov(a0, a1, b0, b1):
        return min(a1, b1) - max(a0, b0) > EPS

    # cluster - cluster
    for k in range(M.m):
        for l_ in range(M.m):
            if k == l_:
                continue
            for (i, xi, yi, wi, hi) in rects[k]:
                for (j, xj, yj, wj, hj) in rects[l_]:
                    if ax == 0:
                        if not ov(yi, yi + hi, yj, yj + hj) or xj < xi + wi - EPS:
                            continue
                    else:
                        if not ov(xi, xi + wi, xj, xj + wj) or yj < yi + hi - EPS:
                            continue
                    r = pair_rule(cores[i], cores[j], cfg)
                    if r is None:
                        continue
                    gap = r["gap"]
                    oi = (xi - pos[k][0]) if ax == 0 else (yi - pos[k][1])
                    oj = (xj - pos[l_][0]) if ax == 0 else (yj - pos[l_][1])
                    si = wi if ax == 0 else hi
                    if r["kind"] in ("ok", "abut"):
                        req = min(gap, r["need"]) if r["kind"] == "ok" else gap
                    elif r["kind"] == "sliver":
                        req = gap          # WARN class: kept as it is (never widened, never closed here)
                    else:   # street / wall
                        req = r["need"]
                    edges[k].append([l_, oi + si + req - oj, oi + si + gap - oj])   # [to, delta, relaxed delta]
    # cluster - item (both directions), vectorised over the items
    if items:
        import numpy as np
        IR = np.array([it.rect[:4] for it in items], float)
        IH = np.array([it.halo for it in items], float)
        lo_o, hi_o = (IR[:, 1], IR[:, 3]) if ax == 0 else (IR[:, 0], IR[:, 2])   # other-axis extent
        lo_a, hi_a = (IR[:, 0], IR[:, 2]) if ax == 0 else (IR[:, 1], IR[:, 3])   # this-axis extent
        pt_o = lo_o == hi_o
        for k in range(M.m):
            for (i, xi, yi, wi, hi) in rects[k]:
                oi = (xi - pos[k][0]) if ax == 0 else (yi - pos[k][1])
                si = wi if ax == 0 else hi
                c0o, c1o = (yi, yi + hi) if ax == 0 else (xi, xi + wi)
                a0, a1 = (xi, xi + wi) if ax == 0 else (yi, yi + hi)
                facing = ((np.minimum(c1o + IH, hi_o + EPS) - np.maximum(c0o - IH, lo_o) > EPS) & ~pt_o) | \
                    (pt_o & (c0o - IH < lo_o) & (lo_o < c1o + IH))
                after = facing & (lo_a >= a1 - EPS)
                before = facing & (hi_a <= a0 + EPS)
                for q in np.nonzero(after)[0]:
                    req = min(IH[q], lo_a[q] - a1)
                    d_ = oi + si + req
                    edges[k].append([M.m + int(q), d_, d_])
                for q in np.nonzero(before)[0]:
                    req = min(IH[q], a0 - hi_a[q])
                    d_ = (hi_a[q] - lo_a[q]) + req - oi
                    edges[M.m + int(q)].append([k, d_, d_])
    # point-like items keep their order inside each lattice row (x pass) / column (y pass): never stacked on each other
    nb = 1 - ax
    rows = collections.defaultdict(list)
    for q, it in enumerate(items):
        if it.chain:
            rows[int(it.rect[nb] // G)].append(q)
    for qs in rows.values():
        qs.sort(key=lambda q: (items[q].rect[ax], q))
        for qa, qb in zip(qs, qs[1:]):
            ra, rb = items[qa].rect, items[qb].rect
            wa = ra[2 + ax] - ra[ax]
            gap = rb[ax] - ra[2 + ax]
            dd_ = wa + (gap if gap < G else G) if gap > -EPS else rb[ax] - ra[ax]
            edges[M.m + qa].append([M.m + qb, dd_, dd_])
    # outline bounds: source (W / S) lower bound and sink (E / N) tail per node (+ the base-gap relaxed values)
    src = [-1e18] * nN
    src_rx = [-1e18] * nN
    tail_rx = [0.0] * nN
    tail = [0.0] * nN
    anchored = [False] * nN
    for k in range(M.m):
        src[k] = 0.0
        for (i, xi, yi, wi, hi) in rects[k]:
            oi = (xi - pos[k][0]) if ax == 0 else (yi - pos[k][1])
            si = wi if ax == 0 else hi
            near = xi if ax == 0 else yi
            r = [v for v in outline_rule(cores[i], W, H, cfg, windows) if v["face"] == ("W" if ax == 0 else "S")]
            if r and r[0]["kind"] == "street":
                src[k] = max(src[k], r[0]["need"] - oi)
            else:
                src[k] = max(src[k], min(near, cfg["outline_margin_um"]) - oi)
            src[k] = max(src[k], fneed.get((cores[i]["inst"], "W" if ax == 0 else "S"), 0.0) - oi)
            src_rx[k] = max(src_rx[k], min(near, cfg["outline_margin_um"]) - oi)
            gap0 = L - near - si
            face = "E" if ax == 0 else "N"
            p = face_count(cores[i], face, *(((cores[i]["y"], cores[i]["y"] + cores[i]["h"]) if ax == 0
                                             else (cores[i]["x"], cores[i]["x"] + cores[i]["w"]))), windows=windows)
            if gap0 < cfg["abut_um"] - EPS:
                req = gap0
                anchored[k] = True            # abutted to the far outline: stays abutted when it grows
            elif p < cfg["pinface_min"]:
                req = min(gap0, cfg["outline_margin_um"])
            else:
                req = need_um(p, cfg)
            fn_ = fneed.get((cores[i]["inst"], face), 0.0)
            if fn_ > req:
                req = fn_
                anchored[k] = False       # R-STREET: lifted off the pin face, no longer abutted to it
            tail[k] = max(tail[k], oi + si + req)
            tail_rx[k] = max(tail_rx[k], oi + si + min(req, gap0))
            # DIE-KV-98 11-12: clock landing storage bands need a macro-free strip off the bus face across the window
            o0, o1 = (cores[i]["y"], cores[i]["y"] + cores[i]["h"]) if ax == 0 else (cores[i]["x"], cores[i]["x"] + cores[i]["w"])
            for (bf, blo, bhi, clr) in cfg.get("_bands") or ():
                if min(o1, bhi) - max(o0, blo) <= EPS:
                    continue
                if bf == ("W" if ax == 0 else "S"):
                    src[k] = max(src[k], clr - oi)
                elif bf == ("E" if ax == 0 else "N"):
                    tail[k] = max(tail[k], oi + si + clr)
    for q, it in enumerate(items):
        lo_, hi_ = it.rect[ax], it.rect[2 + ax]
        src[M.m + q] = src_rx[M.m + q] = min(lo_, it.halo)
        tail[M.m + q] = tail_rx[M.m + q] = (hi_ - lo_) + min(L - hi_, it.halo)
        if hi_ >= L - cfg["anchor_um"] - EPS:
            anchored[M.m + q] = True          # face-side geometry follows the outline growth
    fixed = [fixed_k[k] for k in range(M.m)] + [fix_ft and it.kind in ("ft_reg", "ft_sites") for it in items]
    order = sorted(range(nN), key=lambda u: (start[u], u))
    rev = collections.defaultdict(list)
    for u in range(nN):
        for e in edges[u]:
            rev[e[0]].append((u, e))

    def asap():
        a_ = [start[u] if fixed[u] else src[u] for u in range(nN)]
        why = [None] * nN
        for _ in range(8):
            ch = False
            for u in order:
                for e in edges[u]:
                    if a_[u] + e[1] > a_[e[0]] + EPS:
                        a_[e[0]] = a_[u] + e[1]
                        why[e[0]] = (u, e)
                        ch = True
            if not ch:
                break
        return a_, why

    def alap(Lc):
        b_ = [start[u] if fixed[u] else Lc - tail[u] for u in range(nN)]
        why = [None] * nN
        for _ in range(8):
            ch = False
            for v in reversed(order):
                for (u, e) in rev[v]:
                    if b_[v] - e[1] < b_[u] - EPS:
                        b_[u] = b_[v] - e[1]
                        why[u] = (v, e)
                        ch = True
            if not ch:
                break
        return b_, why
    # a FIXED node (pinned cluster) can never be pushed: relax (to the base gap) the first widened street on the
    # critical chain that pushes into it, until no fixed node is pushed; the relaxed streets stay as residuals
    relaxed = 0
    for _ in range(4 * nN + 8):
        A, wa = asap()
        bad = [v for v in range(nN) if fixed[v] and A[v] > start[v] + EPS]
        if not bad:
            break
        v, done = bad[0], False
        seen = set()
        while v not in seen:
            seen.add(v)
            if wa[v] is None:
                if not fixed[v] and src[v] > src_rx[v] + EPS:
                    src[v] = src_rx[v]          # an outline street that pushes into a pinned core
                    relaxed += 1
                    done = True
                break
            u, e = wa[v]
            if e[1] > e[2] + EPS:
                e[1] = e[2]
                relaxed += 1
                done = True
                break
            v = u
        if not done:
            break
    A, _ = asap()
    for _ in range(4 * nN + 8):
        B, wb = alap(L + 1e6)
        bad = [u for u in range(nN) if fixed[u] and B[u] < start[u] - EPS]
        if not bad:
            break
        u, done = bad[0], False
        seen = set()
        while u not in seen:
            seen.add(u)
            if wb[u] is None:
                if not fixed[u] and tail[u] > tail_rx[u] + EPS:
                    tail[u] = tail_rx[u]
                    relaxed += 1
                    done = True
                break
            v, e = wb[u]
            if e[1] > e[2] + EPS:
                e[1] = e[2]
                relaxed += 1
                done = True
                break
            u = v
        if not done:
            break
    if not grow:
        # outline locked on this axis (die at the reticle): relax the first widened street on the critical chain of
        # every node that would cross the far outline, until the chain fits; relaxed streets stay residual
        for _ in range(4 * nN + 8):
            A, wa = asap()
            bad = [u for u in range(nN) if not fixed[u] and A[u] + tail[u] > L + EPS]
            if not bad:
                break
            u0 = max(bad, key=lambda u: A[u] + tail[u])
            if tail[u0] > tail_rx[u0] + EPS and A[u0] + tail_rx[u0] <= L + EPS:
                tail[u0] = tail_rx[u0]
                relaxed += 1
                continue
            v, done, seen = u0, False, set()
            while v not in seen:
                seen.add(v)
                if wa[v] is None:
                    if src[v] > src_rx[v] + EPS:
                        src[v] = src_rx[v]
                        relaxed += 1
                        done = True
                    break
                w_, e = wa[v]
                if e[1] > e[2] + EPS:
                    e[1] = e[2]
                    relaxed += 1
                    done = True
                    break
                v = w_
            if not done:
                if tail[u0] > tail_rx[u0] + EPS:
                    tail[u0] = tail_rx[u0]
                    relaxed += 1
                    continue
                break
    A, _ = asap()
    B, _ = alap(L)
    short = max([A[u] - B[u] for u in range(nN) if not fixed[u]] + [0.0])
    gq = cfg["outline_grid_um"]
    newL = L
    if short > EPS:
        newL = round(L + math.ceil(short / gq - 1e-9) * gq, 4)
        B, _ = alap(newL)
    dL = newL - L
    # target: the old coordinate clamped into [ASAP, ALAP] (minimum displacement; anchored nodes follow the growth),
    # then one forward pass so every constraint holds after snapping displacements to the 4.32 lattice
    tgt = []
    for u in range(nN):
        o = start[u] + (dL if anchored[u] else 0.0)
        tgt.append(min(max(o, A[u]), max(A[u], B[u])))
    def snap(u, v):
        """displacement on the 4.32 lattice: the multiple inside [ASAP, ALAP] nearest v, rounding away from ALAP
        overflow (a round-up past ALAP would push a pinned core or the outline)."""
        dd = v - start[u]
        lo_ = start[u] + math.floor(dd / G + 1e-9) * G
        hi_ = start[u] + math.ceil(dd / G - 1e-9) * G
        if fixed[u]:
            return start[u]
        if hi_ <= B[u] + EPS or lo_ < A[u] - EPS:
            return round(hi_, 4)
        return round(lo_, 4)
    x = [snap(u, tgt[u]) for u in range(nN)]
    for _ in range(12):
        ch = False
        for u in order:
            v0 = x[u]
            for (p_, e) in rev[u]:
                if x[p_] + e[1] > v0 + EPS:
                    v0 = x[p_] + e[1]
            if v0 > x[u] + EPS:
                x[u] = start[u] if fixed[u] else round(start[u] + up(v0 - start[u]) if v0 > start[u] else
                                                        start[u] - math.floor((start[u] - v0) / G + 1e-9) * G, 4)
                ch = True
        if not ch:
            break
    blocked = []
    newpos = []
    for k in range(M.m):
        p = list(pos[k])
        if fixed_k[k] and abs(x[k] - start[k]) > EPS:
            blocked.append(M.inst[M.CL[k][0]])
            x[k] = start[k]
        p[ax] = x[k]
        newpos.append(tuple(p))
    shifts = [round(x[M.m + q] - start[M.m + q], 4) for q in range(len(items))]
    far = max([x[u] + tail[u] for u in range(nN)] + [L])
    newL = round(L + (math.ceil((far - L) / gq - 1e-9) * gq if far > L + EPS else 0.0), 4)
    one_pass.relaxed = relaxed
    return newpos, newL, shifts, blocked


def _over_contents(cores, xboxes):
    """(core, LEF content macro) pairs that overlap: legalize never moves a content macro, so it never lands on one."""
    out = []
    for c in cores:
        for b in xboxes or ():
            if min(c["x"] + c["w"], b["x"] + b["w"]) - max(c["x"], b["x"]) > 0.01 and \
                    min(c["y"] + c["h"], b["y"] + b["h"]) - max(c["y"], b["y"]) > 0.01:
                out.append((c["inst"], b["inst"]))
    return out


def legalize_type(name, t, die_dir, repo, conns, cfg, rs_cfg, log=print):
    """returns (row, new type or None).  R-STREET: a station re-sited by the first pass may stand in a new alley; up to
    cfg face_passes (5) more passes run on the applied result until no station_alley / face_street is left."""
    row, tn = _legalize_type(name, t, die_dir, repo, conns, cfg, rs_cfg, log)
    for _ in range(int(cfg.get("face_passes", 2)) if cfg.get("face_rule") else 0):
        kinds = ("station_alley", "face_street") + (("transit_street",) if cfg.get("transit_rule") else ())
        if tn is None or not any(k in kinds for k in row.get("violations_after") or {}):
            break
        row2, tn2 = _legalize_type(name, tn, die_dir, repo, conns, cfg, rs_cfg, log)
        if tn2 is None:
            break
        W0, H0 = row["outline_before"]
        W1, H1 = row2["outline_after"]
        keep = {k: row[k] for k in ("outline_before", "violations_before", "worst_before", "overlaps_base",
                                     "points_under_base") if k in row}
        cyc = row.get("cycles_added") or {}
        cyc2 = row2.get("cycles_added") or {}
        row2["cycles_added"] = {k: (cyc.get(k) or 0) + (cyc2.get(k) or 0) if k == "total" else
                                list(cyc.get(k) or []) + list(cyc2.get(k) or []) for k in set(cyc) | set(cyc2)}
        row2["moved_cores"] = max(row.get("moved_cores", 0), row2.get("moved_cores", 0))
        row2["growth_pct"] = dict(W=round(100.0 * (W1 / W0 - 1), 2), H=round(100.0 * (H1 / H0 - 1), 2),
                                  area=round(100.0 * (W1 * H1 / (W0 * H0) - 1), 2))
        row2["passes"] = row.get("passes", 1) + 1
        row2.update(keep)
        row, tn = row2, tn2
    return row, tn


def _legalize_type(name, t, die_dir, repo, conns, cfg, rs_cfg, log=print):
    """one legalize pass: returns (row, new type or None)."""
    ccfg = dict(gap=G, sweeps=0, topk=1, lam=1.0, reach=cfg["reach"], grid_um=21.6, grt_halving="full",
                fixed_re="", rs=rs_cfg, flips_only=False, face_clear=[])
    M = CP.TypeModel(name, t, die_dir, repo, conns, ccfg)
    attach_pins(M, die_dir, repo)
    partners = conns_partners(conns, name, t)
    W0, H0 = M.W, M.H
    windows = type_windows(t)
    cfg = type_cfg(cfg, t, name)
    V0, c0 = analyze(W0, H0, core_models(M, partners), M.CL, cfg, windows)
    SA0 = station_alleys(t, cfg)
    if SA0:
        V0 = V0 + SA0
        c0 = dict(collections.Counter(v["kind"] for v in V0))
        ap_, af_ = alley_force(SA0, bool(cfg.get("transit_rule")))
        cfg = dict(cfg, _alley=ap_, _alley_faces=af_)
    row = dict(type=name, cores=M.n, clusters=M.m, outline_before=[W0, H0], violations_before=c0,
               worst_before=sorted(V0, key=lambda v: -(v["need"] - v["gap"]))[:6])
    hard = [v for v in V0 if v["kind"] in HARD and not v.get("same_cluster")]
    cfg = dict(cfg, _bands=band_clear(cfg, name))
    if not hard and not cfg["_bands"]:
        row.update(changed=False, applied=False, reason="clean")
        return row, None
    M.init_limits()
    len0 = [M.llen(q) for q in range(len(M.L))]
    nov0 = CP.overlaps(M)
    under0 = len(points_under_cores(t)) + len(sinks_under_cores(t, repo))
    cov0 = len(_over_contents(core_models(M, partners), cfg.get("_xboxes")))
    L_base = list(M.L)
    on_core0 = lambda p: M.owner(p, tol=-0.01) is not None   # noqa: E731

    lmeta = link_meta(M, conns) if cfg["add_regs"] > 0 else {}
    fanc = face_anchor_cfg((cfg.get("_face_anchor") or {}).get(name), name)

    def attempt(fixed_k, fix_ft=False):
        grow_ax = cfg.get("grow_axes", "xy")
        M.reset_state()
        M.L[:] = list(L_base)
        M.W, M.H = W0, H0
        tnew = copy.deepcopy(t)
        on_core = on_core0
        items = collect_items(tnew, on_core)
        W, H = W0, H0
        acc = [[0.0, 0.0] for _ in items]
        blocked = []
        relaxed_n = 0
        for rnd in range(cfg["rounds"]):
            for axis in ("x", "y"):
                newpos, newL, shifts, bl = one_pass(M, items, axis, W, H, cfg, partners, fixed_k, windows, fix_ft,
                                                    grow=axis in grow_ax)
                blocked += bl
                relaxed_n += one_pass.relaxed
                ax = 0 if axis == "x" else 1
                for k in range(M.m):
                    M.cpos[k] = newpos[k]
                for q, it in enumerate(items):
                    s_ = shifts[q]
                    if s_:
                        it.rect[ax] += s_
                        it.rect[2 + ax] += s_
                        acc[q][ax] += s_
                if ax == 0:
                    W = newL
                else:
                    H = newL
                M.W, M.H = W, H
            V, c = analyze(W, H, core_models(M, partners), M.CL, cfg, windows)
            if not [v for v in V if v["kind"] in HARD and not v.get("same_cluster")]:
                break
        # ---- apply to the type copy: cores + riding coordinates + stations first (write_type resolves "on a core"
        # against the BASE core boxes), then the pushed non-core items
        M.W, M.H = W, H
        srep = CP.write_type(M, tnew, ccfg, lambda s: None)
        for q, it in enumerate(items):
            if acc[q][0] or acc[q][1]:
                it.apply(acc[q][0], acc[q][1])
        # every other off-core coordinate (sink sites / bins, die islands, keepouts, relays, landing pins, reset
        # taps, ...) follows the stretch of its row / column band; nothing is left inside a moved core (COORD 11-12)
        free_remap(t, tnew, M, (W0, H0), (W, H), cfg, repo)
        # link end points on the E / N outline (type bus windows, faces) follow the outline growth
        for q, (ea, eb, wb, kind) in enumerate(M.L):
            ends = []
            for e in (ea, eb):
                if e[0] is None:
                    x, y = e[1]
                    x = x + (W - W0) if abs(x - W0) < 1.0 else x
                    y = y + (H - H0) if abs(y - H0) < 1.0 else y
                    e = (None, (x, y))
                ends.append(e)
            M.L[q] = (ends[0], ends[1], wb, kind)
        tnew["outline_um"] = [round(W, 4), round(H, 4)]
        fa_rec, fa_err = None, []
        if fanc is not None:
            fa_rec, fa_err = face_anchor(tnew, M, (W0, H0), (W, H), fanc, t)
        added_st, added_ft = [], []
        if cfg["add_regs"] > 0:
            added_st = add_station_regs(M, tnew, srep.get("need_more_idx") or [], ccfg["reach"], int(cfg["add_regs"]))
            fixed_si = {d["station"] for d in added_st}
            srep = dict(srep, need_more_idx=[i for i in srep.get("need_more_idx") or [] if i not in fixed_si])
            srep["need_more_regs"] = len(srep["need_more_idx"])
            added_ft = add_ft_regs(M, t, tnew, cfg["reach_limit_um"], int(cfg["add_regs"]))
        V1, c1 = analyze(W, H, core_models(M, partners), M.CL, dict(cfg, _alley=None), windows)
        SA1 = station_alleys(tnew, cfg)
        if SA1:
            V1 = V1 + SA1
            c1 = dict(collections.Counter(v["kind"] for v in V1))
        nov = CP.overlaps(M)
        reach_ = cfg["reach_limit_um"]
        new_over = [q for q in range(len(M.L)) if M.L[q][3] != "station" and M.llen(q) > reach_ + 0.01 and len0[q] <= reach_ + 0.01]
        longer = [(M.llen(q) - len0[q]) for q in range(len(M.L)) if M.L[q][3] != "station" and len0[q] > reach_ + 0.01
                  and M.llen(q) > len0[q] + 0.01]
        added_ln = []
        if cfg["add_regs"] > 0 and new_over:
            added_ln = add_link_stations(M, tnew, new_over, lmeta, ccfg["reach"], int(cfg["add_regs"]))
            done_q = {d["link"] for d in added_ln}
            new_over = [q for q in new_over if q not in done_q]
        tviol = len(new_over)
        under = points_under_cores(tnew) + [("sink", p) for p in sinks_under_cores(tnew, repo)]
        fthop = ft_hop_check_added(t, tnew, cfg["reach_limit_um"]) if added_ft else ft_hop_check(t, tnew, cfg["reach_limit_um"])
        t_eq = t
        if added_st or added_ft or added_ln:
            # the added stages are the only allowed structural change: compare against the base with those lists
            t_eq = copy.deepcopy(t)
            for d in added_st:
                t_eq["internal_stations"][d["station"]]["regs_um"] = tnew["internal_stations"][d["station"]]["regs_um"]
            for k in {d["slot"] for d in added_ft}:
                for key in ("regs_um", "bit_sites_um", "stations"):
                    if key in tnew["ft_slots"][k]:
                        t_eq["ft_slots"][k][key] = tnew["ft_slots"][k][key]
        if added_ln:
            n0 = len(t.get("internal_stations") or [])
            t_eq.setdefault("internal_stations", []).extend(copy.deepcopy(tnew["internal_stations"][n0:]))
        bf1 = (tnew.get("clock") or {}).get("sink_bins_file")
        if bf1 != (t.get("clock") or {}).get("sink_bins_file"):
            # the remapped sink bins file (same sinks, moved with the cores) is an allowed change
            t_eq = copy.deepcopy(t_eq) if t_eq is t else t_eq
            t_eq["clock"]["sink_bins_file"] = bf1
        eqbad = eq_struct(t_eq, tnew)
        moved = sum(1 for i in range(M.n) if tuple(M.core_origin(i)) != tuple(M.org0[i]))
        gW, gH = 100.0 * (W / W0 - 1), 100.0 * (H / H0 - 1)
        gA = 100.0 * (W * H / (W0 * H0) - 1)
        left = [v for v in V1 if v["kind"] in HARD and not v.get("same_cluster")]
        reasons = []
        if nov > nov0:
            reasons.append("overlaps %d (base %d)" % (nov, nov0))
        if srep["need_more_regs"]:
            reasons.append("stations need more regs %d" % srep["need_more_regs"])
        if tviol:
            reasons.append("links newly over reach %d" % tviol)
        if len(under) > under0:
            reasons.append("points under cores %d (base %d)" % (len(under), under0))
        if fthop:
            reasons.append("ft hops over reach %d" % len(fthop))
        if eqbad:
            reasons.append("eq %s" % eqbad[:3])
        if blocked:
            reasons.append("fixed cores pushed %s" % sorted(set(blocked))[:4])
        cov = _over_contents(core_models(M, partners), cfg.get("_xboxes"))
        if len(cov) > cov0:
            reasons.append("cores over LEF content macros %s" % cov[:3])
        bshort = band_short(M, cfg["_bands"])
        if bshort:
            reasons.append("band clearance short %d" % len(bshort))
        if gA > cfg["max_growth_pct"]:
            reasons.append("growth %.1f%% > %.0f%%" % (gA, cfg["max_growth_pct"]))
        if fa_err:
            reasons.append("fixed-face windows %s" % fa_err[:3])
        ok = not reasons
        relaxed = relaxed_n
        return dict(ok=ok, reasons=reasons, tnew=tnew, face_anchor=fa_rec, added_st=added_st, added_ft=added_ft, added_ln=added_ln, W=W, H=H, gW=gW, gH=gH, gA=gA, c1=c1, left=left, moved=moved,
                    srep=srep, nov=nov, new_over=new_over, longer=longer, under=under, fthop=fthop, eqbad=eqbad,
                    acc=acc, items=items, blocked=blocked, relaxed=relaxed,
                    timing_over=[dict(kind=M.L[q][3], bits=M.L[q][2], len_um=round(M.llen(q), 1),
                                      base_um=round(len0[q], 1)) for q in new_over][:20])

    fixed0 = [bool(M.cfix[k]) for k in range(M.m)]
    pinned = set()
    fix_ft = False
    qmap = {si: q for (si, q, _) in M.stations}
    for att in range(cfg["attempts"]):
        fk = [fixed0[k] or k in pinned for k in range(M.m)]
        R_ = attempt(fk, fix_ft)
        if R_["ok"] or att == cfg["attempts"] - 1:
            break
        # ft station chains keep their register count: when a widened street stretched an ft hop past reach, the
        # next attempt keeps every ft station register / bit-site cell where it is (streets that would push them stay
        # residual)
        ft_new = bool(R_["fthop"]) and not fix_ft
        fix_ft = fix_ft or bool(R_["fthop"])
        add = set()
        for si in R_["srep"].get("need_more_idx") or []:
            for e in M.L[qmap[si]][:2]:
                if e[0] is not None:
                    add.add(M.cid[e[0]])
        for q in R_["new_over"]:
            for e in M.L[q][:2]:
                if e[0] is not None:
                    add.add(M.cid[e[0]])
        add -= pinned
        if not add and not ft_new:
            break
        pinned |= add
    ok, reasons, tnew, W, H = R_["ok"], R_["reasons"], R_["tnew"], R_["W"], R_["H"]
    gW, gH, gA, c1, left, moved = R_["gW"], R_["gH"], R_["gA"], R_["c1"], R_["left"], R_["moved"]
    row.update(changed=True, applied=ok, attempts=att + 1, pinned=[M.inst[M.CL[k][0]] for k in sorted(pinned)],
               band_short=band_short(M, cfg["_bands"]), bands=cfg["_bands"],
               ft_fixed=fix_ft, cycles_added=dict(stations=R_["added_st"], ft=R_["added_ft"], new_link_stations=R_["added_ln"],
                                                  total=sum(d["regs_after"] - d["regs_before"] for d in R_["added_st"])
                                                  + sum(d["added"] for d in R_["added_ft"])
                                                  + sum(d["regs"] for d in R_["added_ln"])),
               streets_relaxed_at_pins=R_["relaxed"],
               reason="; ".join(reasons) or ("clean" if not left else "residual %d" % len(left)),
               outline_after=[W, H], growth_pct=dict(W=round(gW, 2), H=round(gH, 2), area=round(gA, 2)),
               moved_cores=moved, violations_after=c1, residual=sorted(left, key=lambda v: -(v["need"] - v["gap"]))[:6],
               stations=R_["srep"], overlaps=R_["nov"], links_over_reach=len(R_["new_over"]),
               points_under_cores=R_["under"][:10], ft_hops_over=R_["fthop"][:10], timing_over=R_["timing_over"],
               overlaps_base=nov0,
               long_links_lengthened=dict(n=len(R_["longer"]), max_um=round(max(R_["longer"]), 1) if R_["longer"] else 0.0,
                                          note="direct links already > 405 um in the base (registered elsewhere)"),
               points_under_base=under0, eq_violations=R_["eqbad"],
               items_moved=sum(1 for a_ in R_["acc"] if a_[0] or a_[1]), items=len(R_["items"]))
    if R_.get("face_anchor") is not None:
        row["face_anchor"] = R_["face_anchor"]
    log("  %s: %s viol %s -> %s  outline %.2fx%.2f -> %.2fx%.2f (+%.1f%%)  moved %d  %s" % (
        name, "APPLIED" if ok else "not applied", c0, c1, W0, H0, W, H, gA, moved, row["reason"]))
    return row, (tnew if ok else None)


# ------------------------------------------------------------------------------------------ free-space remap
# keys whose *_um / xy lists are sizes or lengths, not points (never remapped)
SIZE_KEYS = {"cell_wh_um", "bit_site_cell_um", "kit_core_margins_um", "legs_um", "track_offset_um", "outline_um",
             "resized_from_um", "resited_from_um"}
SINK_BIN_UM = 10.8


def _band_map(v, lo, hi, knots, L0, L1):
    """monotone piecewise-linear old -> new coordinate along one axis from the (old, new) edges of the cores whose
    span on the other axis covers [lo, hi] (falls back to all cores) plus the outline ends 0 -> 0, L0 -> L1."""
    ks = [(o, n) for (a, b, o, n) in knots if a < hi + 1e-6 and b > lo - 1e-6] or [(o, n) for (_, _, o, n) in knots]
    pts = sorted(set([(0.0, 0.0), (float(L0), float(L1))] + ks))
    mono = []
    for o, n in pts:
        if mono and (o <= mono[-1][0] + 1e-9 or n < mono[-1][1] - 1e-9):
            continue
        mono.append((o, n))
    if v <= mono[0][0]:
        return v + (mono[0][1] - mono[0][0])
    for (o0, n0), (o1, n1) in zip(mono, mono[1:]):
        if v <= o1:
            return n0 + (v - o0) * (n1 - n0) / (o1 - o0)
    return v + (mono[-1][1] - mono[-1][0])


def _push_out(x, y, rects, W, H, margin=0.54):
    """a point strictly inside a core box moves to the nearest face of that box (+ margin), inside the outline."""
    for _ in range(4):
        hit = [r for r in rects if r[0] + 1e-6 < x < r[2] - 1e-6 and r[1] + 1e-6 < y < r[3] - 1e-6]
        if not hit:
            break
        x0, y0, x1, y1 = hit[0]
        c = sorted([(x - x0, x0 - margin, y), (x1 - x, x1 + margin, y), (y - y0, x, y0 - margin), (y1 - y, x, y1 + margin)])
        for _, nx, ny in c:
            if 0 <= nx <= W and 0 <= ny <= H:
                x, y = nx, ny
                break
    return x, y


def make_free_map(R0, R1, WH0, WH1):
    """f(x, y) -> new (x, y) for an off-core point: x by the x edges of the cores in its y band, y likewise."""
    kx = [(r0[1], r0[3], r0[0], r1[0]) for r0, r1 in zip(R0, R1)] + [(r0[1], r0[3], r0[2], r1[2]) for r0, r1 in zip(R0, R1)]
    ky = [(r0[0], r0[2], r0[1], r1[1]) for r0, r1 in zip(R0, R1)] + [(r0[0], r0[2], r0[3], r1[3]) for r0, r1 in zip(R0, R1)]
    W1, H1 = WH1

    def f(x, y):
        nx = _band_map(x, y, y, kx, WH0[0], WH1[0])
        ny = _band_map(y, x, x, ky, WH0[1], WH1[1])
        nx, ny = _push_out(nx, ny, R1, W1, H1)
        return [round(min(max(nx, 0.0), W1), 4), round(min(max(ny, 0.0), H1), 4)]
    return f


def _inside(p, rects):
    return any(r[0] + 1e-6 < p[0] < r[2] - 1e-6 and r[1] + 1e-6 < p[1] < r[3] - 1e-6 for r in rects)


def _remap_walk(x0, x1, f, R0, key=None):
    """x0: base value, x1: the legalized copy. Leaves the legalizer already moved (core-riding points, items) keep
    their value; unchanged off-core points / rects are remapped with f."""
    if isinstance(x0, dict) and isinstance(x1, dict):
        for k in x1:
            if k in CP.SKIP_KEYS or k in SIZE_KEYS or k not in x0:
                continue
            x1[k] = _remap_walk(x0[k], x1[k], f, R0, k)
        return x1
    if isinstance(x0, list) and isinstance(x1, list):
        if x1 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in x1):
            if x1 != x0 or not key:
                return x1
            if len(x1) == 4 and key not in ("xy", "root", "outs", "start_in"):   # rect (rect_um, keepouts, islands)
                # a whole box: both corners by the displacement of its centre (never one corner alone)
                c = ((x1[0] + x1[2]) / 2.0, (x1[1] + x1[3]) / 2.0)
                if _inside(c, R0):
                    return x1                   # rides with its core (core_place.walk_follow)
                q = f(*c)
                dx, dy = q[0] - c[0], q[1] - c[1]
                return [round(x1[0] + dx, 4), round(x1[1] + dy, 4), round(x1[2] + dx, 4), round(x1[3] + dy, 4)]
            if len(x1) >= 2 and (key.endswith("_um") or key in ("xy", "root", "outs", "start_in")):
                if _inside(x1, R0):
                    return x1
                return f(*x1[:2]) + list(x1[2:])
            return x1
        if len(x0) == len(x1):
            return [_remap_walk(a, b, f, R0, key) for a, b in zip(x0, x1)]
    return x1


def remap_bins(rows, fol_core, f, R0, R1, b=SINK_BIN_UM):
    """sink bins [[x, y, n]]: a bin inside an old core box rides with that core, a glue bin follows the free map
    (pushed out of a moved core), then bins sharing a b-um cell merge.  The sink total is unchanged."""
    acc = collections.OrderedDict()
    for r in rows:
        x, y = float(r[0]), float(r[1])
        n = float(r[2]) if len(r) > 2 else 1.0
        q = fol_core([x, y]) if _inside((x, y), R0) else None
        nx, ny = q if q else f(x, y)          # f pushes a glue bin out of a moved core; a riding bin stays on it
        key = (int(nx // b), int(ny // b), bool(q))
        e = acc.setdefault(key, [0.0, 0.0, 0.0])
        e[0] += nx * n
        e[1] += ny * n
        e[2] += n
    out = []
    for (i, j, ride), (sx, sy, n) in acc.items():
        cx, cy = (i + 0.5) * b, (j + 0.5) * b
        if ride or _inside((cx, cy), R1):   # a riding bin, or a glue cell centre on a core: the weighted mean
            cx, cy = sx / n, sy / n
        out.append([round(cx, 3), round(cy, 3), int(n) if float(n).is_integer() else round(n, 6)])
    return out


def free_remap(t0, tnew, M, WH0, WH1, cfg, repo):
    R0, R1 = _core_rects(t0), _core_rects(tnew)
    f = make_free_map(R0, R1, WH0, WH1)
    for k in list(tnew):
        if k in CP.SKIP_KEYS or k in SIZE_KEYS or k not in t0:
            continue
        tnew[k] = _remap_walk(t0[k], tnew[k], f, R0, k)
    ck = tnew.get("clock") or {}
    bf = ck.get("sink_bins_file")
    if bf and cfg.get("_bins_dir"):
        src = Path(repo) / bf
        js = json.loads(src.read_text())
        rows = remap_bins(js.get("bins") or [], CP.follow_fn(M), f, R0, R1, float(js.get("bin_um") or SINK_BIN_UM))
        if rows != js.get("bins"):
            nj = dict(js, bins=rows, source=bf, note="STREET-RULE-1 legalize: bins follow moved cores / stretched bands")
            txt = json.dumps(nj, separators=(",", ":")) + "\n"
            h = hashlib.sha256(txt.encode()).hexdigest()[:10]
            rel = Path(cfg["_bins_dir"]) / ("%s__%s.json" % (Path(bf).stem, h))
            (Path(repo) / rel).parent.mkdir(parents=True, exist_ok=True)
            (Path(repo) / rel).write_text(txt)
            ck["sink_bins_file"] = str(rel)


def tap_check(Q, names, plan_path):
    """{type: error} of schema.tap_grid on plan dict Q (the taps gen phys exports)."""
    import schema as SC
    try:
        PQ = SC.Plan(Q, Path(plan_path))
    except Exception as e:  # noqa: BLE001  (a plan that does not load fails every type)
        return {n: "plan load: %s" % e for n in names}
    bad = {}
    for n in names:
        try:
            SC.tap_grid(PQ, n)
        except Exception as e:  # noqa: BLE001
            import traceback
            tb = traceback.extract_tb(e.__traceback__)[-1]
            bad[n] = "%s: %s [%s:%d]" % (type(e).__name__, str(e)[:260], Path(tb.filename).name, tb.lineno)
    return bad


def _tap_legalize_table(PQ, tn, table, fixed_pts, extra_boxes=()):
    """move every illegal tap of `table` (in order) to the nearest legal site (outline - clear, halo-grown placement
    boxes, keepouts, TAP_CLEAR spacing to fixed_pts and to the taps before it).  Returns [(name, old, new)]."""
    import schema as SC
    from placement_obstacles import placement_boxes
    t = PQ.types[tn]
    w, h = map(float, t["outline_um"])
    clear = SC.TAP_CLEAR_UM
    eps = 1e-8
    boxes = list(placement_boxes(t, halo=clear).values()) + list(extra_boxes)
    taken = list(fixed_pts)

    def ok(x, y):
        return (clear - eps <= x <= w - clear + eps and clear - eps <= y <= h - clear + eps
                and not any(abs(x - a) < clear - eps and abs(y - b) < clear - eps for a, b in taken)
                and not any(a + eps < x < c - eps and b + eps < y < d - eps for a, b, c, d in boxes))
    moves = []
    for e in table:
        x, y = map(float, e["xy"])
        if not ok(x, y):
            best = None
            st = 0.54
            for r in range(1, 400):
                ring = [(x + i * st, y + (r - abs(i)) * st * sg) for i in range(-r, r + 1) for sg in (1, -1)]
                ring = [(round(a, 4), round(b, 4)) for a, b in ring if ok(a, b)]
                if ring:
                    best = min(ring, key=lambda q: (abs(q[0] - x) + abs(q[1] - y), q))
                    break
            if best is None:
                continue
            moves.append((e["name"], [x, y], list(best)))
            e["xy"] = list(best)
            x, y = best
        taken.append((x, y))
    return moves


def tap_repair(Q, names, plan_path, log=print):
    """re-derive the clock taps of legalized types that fail the export tap rule (COORD 11-12):
    grid+explicit -- renumber clock.added_taps after the (outline-dependent) R4 grid, move illegal added taps to the
    nearest legal site, then added_tap_recentre.fix_type (minimal move of a failing tap, else ONE added light tap,
    reset contract guarded); explicit -- legal-site move + fix_type; density / grid -- derived at export from the
    remapped sinks (nothing stored to fix).  Returns {type: record}."""
    import schema as SC
    import added_tap_recentre as ATR
    try:
        PQ = SC.Plan(Q, Path(plan_path))
    except Exception as e:  # noqa: BLE001
        return {n: dict(error="plan load: %s" % e) for n in names}
    out = {}
    for n in names:
        ck = (Q["partition_types"][n].get("clock") or {})
        mode = ck.get("tap_mode")
        rec = dict(mode=mode, renamed=0, legal_moves=[])
        try:
            if mode == "grid+explicit" and ck.get("added_taps"):
                grid = SC._grid_taps(PQ, n)
                for i, e in enumerate(ck["added_taps"]):
                    nm = "clk_t%d" % (len(grid) + i)
                    if e.get("name") != nm:
                        e["name"] = nm
                        rec["renamed"] += 1
                rec["legal_moves"] = _tap_legalize_table(PQ, n, ck["added_taps"], [(x, y) for _, x, y in grid])
            elif mode == "explicit" and ck.get("taps"):
                tbl = [p for p in ck["taps"] if p.get("kind") != "core"]
                clear = SC.TAP_CLEAR_UM
                ko = [(a - clear, b - clear, c + clear, d + clear) for a, b, c, d in ck.get("keepouts_um", [])]
                rec["legal_moves"] = _tap_legalize_table(PQ, n, tbl, [(x, y) for _, x, y, _ in SC.core_taps(PQ, n)], ko)
            ATR.S_reset_cache(PQ)
            if mode in ("grid+explicit", "explicit"):
                r = ATR.fix_type(PQ, Q, n, 0.054, 8, add=True)
                rec.update(moves=r.get("moves"), unfixable=r.get("unfixable"), after=r.get("after"))
            else:
                SC.tap_grid(PQ, n)
                rec["after"] = None
        except Exception as e:  # noqa: BLE001
            import traceback
            rec["after"] = "%s: %s" % (type(e).__name__, str(e)[:300])
            rec["where"] = traceback.format_exc().strip().splitlines()[-3:]
        ATR.S_reset_cache(PQ)
        out[n] = rec
    return out


def _start_relays(tr):
    st = bool(tr.get("start"))
    import reset_tree as RT
    rl = RT.start_relays(tr) if st else tr.get("relays", [])
    return [r for r in rl if not st or r.get("role") in ("raw", "boot", "bootstrap_transport")]


def _q_roles(tr):
    """{net q: relay row with its emitted role} of a solved reset tree.  START trees (reset_tree.start_relays): a
    consumer tap rst_n_t<i> of a mission type is GATED (reset AND run), its registered raw copy rr_t<i> is role raw
    (emitted whenever the plan names it, reset_tree.start_raw_requests), plain tree relays rst_rl_* are raw.  Trees
    without START: every relay is a plain registered relay (raw).  A re-select must keep the role: a gated relay where
    a raw one was named fails gen-phys's reader-START check (HEAD-94 hd_st_n3_transit.u2_i, COORD 11-12)."""
    if not tr.get("start"):
        return {r["q"]: dict(r, role="raw") for r in tr.get("relays", [])}
    import reset_tree as RT
    out = {}
    for r in RT.start_relays(tr):
        out.setdefault(r["q"], r)
        m = re.match(r"^rst_n_t(\d+)$", r["q"])
        if m and r.get("role") == "gated":
            out.setdefault("rr_t" + m.group(1), dict(r, name=r["name"] + "_r", q="rr_t" + m.group(1), role="raw"))
    return out


def reset_resel(P, Q, names, plan_path, near_um=25.0):
    """re-select the raw reset references of legalized types on their re-solved reset tree (COORD 11-12, HEAD-94
    hd_lep0N "raw reset source is not the recorded registered relay"; rule = HEAD mesh_resel.py / compose.py RAWSEL):
    every reset_start_raw_exports entry -> the new start relay of the same role + depth nearest its old xy (entries
    sharing an old instance share the new one), its landing_contract pin source follows (pin offset kept); every
    landing_{reader,writer}_start stage raw_reset and landing_local_resets raw keeps its Q if that relay survives at
    the same depth within near_um of the best, else the nearest relay of that depth.  Returns {type: record}."""
    import math
    import schema as SC
    import reset_tree as RT
    def has(t):
        ck = t.get("clock") or {}
        return bool(t.get("reset_start_raw_exports") or ck.get("landing_local_resets") or ck.get("landing_raw_branches")
                    or (ck.get("landing_contract") or {}).get("collector_tree") or any(
                        (ck.get(k) or {}).get("branches") for k in ("landing_reader_start", "landing_writer_start")))
    names = [n for n in names if has(Q["partition_types"][n])]
    if not names:
        return {}
    try:
        PA, PB = SC.Plan(P, Path(plan_path)), SC.Plan(Q, Path(plan_path))
    except Exception as e:  # noqa: BLE001
        return {n: dict(error="plan load: %s" % e) for n in names}
    out = {}
    for tn in names:
        t = Q["partition_types"][tn]
        ck = t.get("clock") or {}
        rec = dict(exports=[], raw=[], skipped=[])
        try:
            ta, tb = RT.for_type(PA, tn), RT.for_type(PB, tn)
            lc = ck.get("landing_contract") or {}
            if lc.get("collector_tree") is not None:
                # the published collector_tree = the tree the bind re-solves (added_tap_recentre.republish rule); the
                # collector sources / children are re-attached after this (collector_reattach.reattach_plan)
                new = json.loads(json.dumps(tb))
                if json.dumps(new, sort_keys=True) != json.dumps(lc["collector_tree"], sort_keys=True):
                    rec["tree_republished"] = [len(lc["collector_tree"].get("relays") or []), len(new.get("relays") or [])]
                    lc["collector_tree"] = new
            ra = {r["name"]: r for r in _start_relays(ta)}
            rb = _start_relays(tb)
            pins = {x["name"]: x for x in ((ck.get("landing_contract") or {}).get("pins") or [])}
            shared, used = {}, set()
            for e in t.get("reset_start_raw_exports") or []:
                o = ra.get(e.get("instance"))
                if o is None:
                    rec["skipped"].append(e.get("instance"))
                    continue
                if e["instance"] in shared:
                    n = shared[e["instance"]]
                else:
                    c = [r for r in rb if r.get("role") == o.get("role") and r.get("depth") == o.get("depth")
                         and r["name"] not in used] or [r for r in rb if r.get("role") == o.get("role")
                                                         and r.get("depth") == o.get("depth")]
                    if not c:
                        rec["skipped"].append("%s: no same-role relay" % e.get("instance"))
                        continue
                    n = min(c, key=lambda r: math.dist(r["xy"], e.get("xy_um") or o["xy"]))
                    used.add(n["name"])
                    shared[e["instance"]] = n
                pn = pins.get(e.get("port"))
                if pn is not None and e.get("xy_um") and pn.get("xy_um"):
                    off = [pn["xy_um"][0] - e["xy_um"][0], pn["xy_um"][1] - e["xy_um"][1]]
                    pn["source_instance"], pn["source_copy_from_net"] = n["name"], n["q"]
                    pn["xy_um"] = [round(n["xy"][0] + off[0], 4), round(n["xy"][1] + off[1], 4)]
                if (e["instance"], e.get("net")) != (n["name"], n["q"]):
                    rec["exports"].append([e.get("port"), e["instance"], n["name"]])
                e["instance"], e["net"], e["xy_um"] = n["name"], n["q"], list(n["xy"])
            ra_q = _q_roles(ta)
            rb_q = _q_roles(tb)
            rb_all = list(rb_q.values())
            # tree edges (D-chain) only over the solved plain relays
            rb_plain = tb.get("relays", [])
            refs = []
            for key in ("landing_reader_start", "landing_writer_start"):
                for bus, br in ((ck.get(key) or {}).get("branches") or {}).items():
                    for i, st in enumerate(br.get("stages", [])):
                        refs.append(("%s.%s.%d" % (key, bus, i), st, "raw_reset"))
            for i, lr in enumerate(ck.get("landing_local_resets") or []):
                refs.append(("landing_local_resets.%d" % i, lr, "raw"))
            # landing_raw_branches: base + stage originals must be a D-chain of the re-solved tree (landing_raw_branches
            # .py: "exactly one same-clk plain relay" per Q, each original's D = its parent): base -> nearest same-depth
            # relay to the old base, then each stage -> the child of the previous node nearest the stage xy
            kids = collections.defaultdict(list)
            for r in rb_plain:
                if r.get("d"):
                    kids[r["d"]].append(r)
            for bi, br in enumerate(ck.get("landing_raw_branches") or []):
                ob = ra_q.get(br.get("base"))
                if ob is None or rb_q.get(br.get("base"), {}).get("xy") == ob.get("xy"):
                    nb = rb_q.get(br.get("base"))
                else:
                    cand = [r for r in rb_plain if r.get("depth") == ob.get("depth") and r.get("clk", "clk") == "clk"
                            and (rb_q.get(r["q"]) or {}).get("role") == ob.get("role")]
                    nb = min(cand, key=lambda r: math.dist(r["xy"], ob["xy"])) if cand else None
                if nb is None:
                    rec["skipped"].append("landing_raw_branches.%d.base" % bi)
                    continue
                chain, prev, ok = [], nb, True
                for st in br.get("stages") or []:
                    c = kids.get(prev["q"]) or []
                    if not c:
                        ok = False
                        break
                    keep = [r for r in c if r["q"] == st.get("original")]
                    nxt = keep[0] if keep else min(c, key=lambda r: math.dist(r["xy"], st.get("xy_um") or r["xy"]))
                    chain.append(nxt)
                    prev = nxt
                if not ok:
                    rec["skipped"].append("landing_raw_branches.%d (%s): chain ends" % (bi, br.get("name")))
                    continue
                if br.get("base") != nb["q"] or [st.get("original") for st in br["stages"]] != [r["q"] for r in chain]:
                    rec["raw"].append(["landing_raw_branches.%d" % bi, br.get("base"), nb["q"]])
                br["base"] = nb["q"]
                for st, r in zip(br["stages"], chain):
                    st["original"] = r["q"]
            for tag, obj, fld in refs:
                q = obj.get(fld)
                o = ra_q.get(q)
                if o is None:
                    continue
                pt = obj.get("xy_um") or o["xy"]
                same = [r for r in rb_all if r.get("depth") == o.get("depth") and r.get("role") == o.get("role")]
                # same form first: a plain registered relay stays plain, a raw tap copy rr_t<i> stays a copy
                cand = [r for r in same if r["q"].startswith("rr_t") == q.startswith("rr_t")] or same
                if not cand:
                    rec["skipped"].append("%s: no same-role relay" % tag)
                    continue
                n = min(cand, key=lambda r: math.dist(r["xy"], pt))
                k = rb_q.get(q)
                if k is not None and k.get("depth") == o.get("depth") and k.get("role") == o.get("role") and \
                        math.dist(k["xy"], pt) <= math.dist(n["xy"], pt) + near_um:
                    continue
                rec["raw"].append([tag, q, n["q"]])
                obj[fld] = n["q"]
        except Exception as e:  # noqa: BLE001
            rec["error"] = "%s: %s" % (type(e).__name__, str(e)[:300])
        out[tn] = rec
    return out


def sinks_under_cores(t, repo=None):
    R = _core_rects(t)
    pts, _ = sink_points(t, repo)
    return [p[:2] for p in pts if _inside(p, R)]


def sink_points(t, repo=None):
    """(sites, total weight, bins total) of clock.sink_sites_um + clock.sink_bins_file (test / check helper)."""
    ck = t.get("clock") or {}
    sites = [list(r) for r in ck.get("sink_sites_um") or []]
    bins = []
    if ck.get("sink_bins_file") and repo:
        bins = json.loads(__import__("taps").input_path(ck["sink_bins_file"], root=repo).read_text()).get("bins") or []
    return sites + [list(r) for r in bins], sum(float(r[2]) if len(r) > 2 else 1.0 for r in sites + bins)


def _core_rects(t):
    out = []
    for h in t.get("hard_cores") or []:
        x, y = h["origin_um"]
        w, hh = h["outline_um"]
        if h.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        out.append((x, y, x + w, y + hh))
    return out


def points_under_cores(t):
    """non-core fixed points (ft regs/sites, taps) strictly inside a core after the move."""
    R = _core_rects(t)
    pts = []
    for f in t.get("ft_slots") or []:
        pts += [("ft_reg", r) for r in f.get("regs_um") or [] if isinstance(r, list)]
        for s in f.get("bit_sites_um") or []:
            if s and isinstance(s[0], list):
                pts += [("ft_site", p) for p in s]
    ck = t.get("clock") or {}
    for tp in (ck.get("taps") or []) + (ck.get("added_taps") or []):
        if isinstance(tp, dict) and tp.get("kind") != "core" and isinstance(tp.get("xy"), list):
            pts.append(("tap", tp["xy"]))
    out = []
    for kind, p in pts:
        for r in R:
            if r[0] + 0.01 < p[0] < r[2] - 0.01 and r[1] + 0.01 < p[1] < r[3] - 0.01:
                out.append((kind, p[:2]))
                break
    return out


def ft_hops(t):
    W, H = t["outline_um"]
    out = []
    for f in t.get("ft_slots") or []:
        regs = [tuple(r[:2]) for r in (f.get("regs_um") or []) if isinstance(r, list)]
        a = RS.face_point(W, H, f.get("in_face", "W"), f.get("in_window_um"))
        b = RS.face_point(W, H, f.get("out_face", "E"), f.get("out_window_um"))
        ch = [a] + regs + [b]
        out.append([abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(ch, ch[1:])])
    return out


def ft_hop_check(t0, t1, reach=405.0):
    bad = []
    for k, (h0, h1) in enumerate(zip(ft_hops(t0), ft_hops(t1))):
        for j, (a, b) in enumerate(zip(h0, h1)):
            if b > max(a, reach) + 0.01:
                bad.append(dict(slot=k, hop=j, before=round(a, 1), after=round(b, 1)))
    return bad


_BANDS = {}


def band_clear(cfg, name):
    """[(face, lo, hi, clearance um)] for a type from cfg band_file ({type: [[face, lo, hi, clearance]]})."""
    f = cfg.get("band_file") or ""
    if not f:
        return []
    if f not in _BANDS:
        _BANDS[f] = json.loads(Path(f).read_text())
    return [tuple(x) for x in _BANDS[f].get(name, [])]


def band_short(M, bands):
    """bands whose macro-free strip is not clear: some core overlapping the window is closer than the clearance."""
    bad = []
    for (bf, lo, hi, clr) in bands:
        for i in range(M.n):
            x0, y0 = M.core_origin(i)
            w, h = M.dim[i]
            if M.core_orient(i) in ("R90", "R270", "MXR90", "MYR90"):
                w, h = h, w
            o0, o1 = (y0, y0 + h) if bf in "WE" else (x0, x0 + w)
            if min(o1, hi) - max(o0, lo) <= EPS:
                continue
            d = {"W": x0, "E": M.W - x0 - w, "S": y0, "N": M.H - y0 - h}[bf]
            if d < clr - EPS:
                bad.append(dict(face=bf, lo=lo, hi=hi, need=clr, have=round(d, 2), core=M.inst[i]))
                break
    return bad


def _raster(M):
    import hub_repack as HR
    rects = [(M.core_origin(i)[0], M.core_origin(i)[1], M.core_origin(i)[0] + M.dim[i, 0],
              M.core_origin(i)[1] + M.dim[i, 1]) for i in range(M.n)]
    return HR.Raster(M.W, M.H, rects)


def add_station_regs(M, tnew, idx, reach, add_max, raster=None):
    """COORD 11-12 (cycles owner-pre-approved): a station that needs more registers after the move gets them, up to
    add_max extra per station; returns [(station idx, conn, launch, capture, regs before, regs after)].
    raster: a hub_repack.Raster of the cores instead of M (REACH-FIX-1 calls it without a TypeModel)."""
    import hub_repack as HR
    R = raster if raster is not None else _raster(M)
    st = tnew.get("internal_stations") or []
    out = []
    for si in idx:
        s = st[si]
        n0 = len(s.get("regs_um") or [])
        r = HR.route_station(R, tuple(s["from_um"]), tuple(s["to_um"]), n0, reach)
        if r is None or len(r["regs"]) <= n0 or len(r["regs"]) > n0 + add_max:
            continue
        s["regs_um"] = [list(q) for q in r["regs"]]
        s["note"] = (s.get("note", "") + " | STREET-RULE-1 street widened the path to %s um: %d -> %d regs (+%d cycle(s), "
                     "owner pre-approved)" % (r["length_um"], n0, len(r["regs"]), len(r["regs"]) - n0))
        out.append(dict(station=si, conn=s.get("conn"), launch=s.get("launch"), capture=s.get("capture"),
                        regs_before=n0, regs_after=len(r["regs"]), length_um=r["length_um"]))
    return out


def link_meta(M, conns):
    """{link index q: (inst, bus, dest, bits)} for the core_conns links of M.L (same walk as TypeModel._links)."""
    out = {}
    W, H = M.W, M.H
    cc_key = next((k for k in (M.name, re.sub(r"__cl[0-9a-f]{8}.*$", "", M.name), re.sub(r"__.*$", "", M.name))
                   if conns.get(k)), None)
    cc = conns.get(cc_key) if cc_key else None
    if not cc:
        return out
    bus_pt = {bu["name"]: 1 for bu in M.t.get("buses", []) or [] if bu.get("face")}
    q = 0
    st_pairs = set()
    for s_ in M.t.get("internal_stations", []) or []:
        la = str(s_.get("launch", ""))
        if la.startswith("core:"):
            A, _, bus_ = la[5:].rpartition(".")
            st_pairs.add((A, bus_, str(s_.get("capture", ""))))
            st_pairs.add((A, bus_, str(s_.get("capture", "")).rsplit(".", 1)[0]))
    for inst, ports in cc.items():
        if inst not in M.idx:
            continue
        i = M.idx[inst]
        for bus, dl in (ports or {}).items():
            pg = M.lpins[i].get(bus)
            if not pg or not dl:
                continue
            for d in dl:
                k, _, val = str(d).partition(":")
                if k == "core":
                    if val not in M.idx and val.rpartition(".")[0] in M.idx:
                        val = val.rpartition(".")[0]
                    if val not in M.idx or (inst, bus, val) in st_pairs:
                        continue
                elif not ((k == "bus" and val in bus_pt) or (k == "face" and val in "NSEW")):
                    continue
                out[q] = (inst, bus, str(d), int(pg[0]))
                q += 1
    del W, H
    return out


def add_link_stations(M, tnew, qs, meta, reach, add_max):
    """lever (a) for direct links: a core / bus / face link a widened street pushed past reach gets a new internal
    station with the fewest registers (<= add_max) that bring every hop under reach."""
    import hub_repack as HR
    R = _raster(M)
    out = []
    for q in qs:
        if q not in meta:
            continue
        inst, bus, dest, bits = meta[q]
        a_, b_ = M.pt(M.L[q][0]), M.pt(M.L[q][1])
        r = HR.route_station(R, tuple(a_), tuple(b_), 0, reach)
        if r is None or not r["regs"] or len(r["regs"]) > add_max:
            continue
        tnew.setdefault("internal_stations", []).append(dict(
            conn=dest, from_um=[round(a_[0], 4), round(a_[1], 4)], to_um=[round(b_[0], 4), round(b_[1], 4)],
            regs_um=[list(p) for p in r["regs"]], launch="core:%s.%s" % (inst, bus),
            capture=dest[5:] if dest.startswith("core:") else dest, bits=bits,
            note="STREET-RULE-1 pass 2: link %s um > reach after the street, +%d cycle(s) (owner pre-approved 11-12)"
                 % (r["length_um"], len(r["regs"]))))
        out.append(dict(link=q, launch="core:%s.%s" % (inst, bus), dest=dest, bits=bits, regs=len(r["regs"]),
                        length_um=r["length_um"]))
    return out


def add_ft_regs(M, t0, tnew, reach, add_max, raster=None, use_base=True, ends=None):
    """an ft hop stretched past reach by a widened street gets ceil(len / reach) - 1 (<= add_max) new register stages on
    its Manhattan path (bit-site pattern copied from the nearest stage, translated; never under a core). Returns the
    added stages; hops it cannot fix are left (the type is then not applied).
    REACH-FIX-1: raster = a hub_repack.Raster instead of M; use_base=False splits EVERY hop > reach (not only the ones a
    move stretched past their base length); ends = {slot index: (in pin xy, out pin xy)} replaces the face mid-points
    (the real bit pins of gen_phys.type_pins)."""
    R = raster if raster is not None else _raster(M)
    W, H = tnew["outline_um"]
    out = []
    for k, (f0, f) in enumerate(zip(t0.get("ft_slots") or [], tnew.get("ft_slots") or [])):
        regs = [list(r) for r in (f.get("regs_um") or [])]
        sites = f.get("bit_sites_um")
        if not regs or not isinstance(regs[0], list):
            continue
        hops0 = ft_hops(dict(t0, ft_slots=[f0]))[0]
        a = RS.face_point(W, H, f.get("in_face", "W"), f.get("in_window_um"))
        b = RS.face_point(W, H, f.get("out_face", "E"), f.get("out_window_um"))
        if ends and k in ends:
            a, b = ends[k]
        j = 0
        changed = False
        while j <= len(regs):
            ch = [a] + [tuple(r[:2]) for r in regs] + [b]
            p, q = ch[j], ch[j + 1]
            L = abs(p[0] - q[0]) + abs(p[1] - q[1])
            base = hops0[j] if (use_base and j < len(hops0)) else 0.0
            if L <= max(base, reach) + 0.01:
                j += 1
                continue
            n = int(-(-L // reach)) - 1
            if n < 1 or n > add_max:
                j += 1
                continue
            # per-bit sites: row i - off belongs to regs[i] (off = 1 when station 0 at the in pin has no row, the
            # usual form; 0 when every stage has one).  A new stage needs a site row, so the pattern source is the
            # nearest stage that has one (COORD 11-12: an added stage without its row broke taps.planned_sinks)
            off = (len(regs) - len(sites)) if isinstance(sites, list) and sites else None
            if off is not None and off not in (0, 1):
                j += 1
                continue
            ref = min(max(j, off or 0), len(regs) - 1)          # nearest existing stage with a site row
            if off is not None and j < off:
                j += 1
                continue
            new = []
            for m in range(1, n + 1):
                d = L * m / (n + 1)
                dx = min(d, abs(q[0] - p[0]))
                x = p[0] + (dx if q[0] >= p[0] else -dx)
                y = p[1] + (d - dx if q[1] >= p[1] else -(d - dx))
                x, y = round(round(x / G) * G, 4), round(round(y / G) * G, 4)
                ok = None
                for r_ in range(0, 30):
                    for ddx, ddy in ((0, 0),) if r_ == 0 else ((r_, 0), (-r_, 0), (0, r_), (0, -r_)):
                        xx, yy = x + ddx * G, y + ddy * G
                        if not (0 <= xx <= W and 0 <= yy <= H) or not R.free(xx, yy):
                            continue
                        if off is not None:
                            rx, ry = regs[ref][:2]
                            pat = [[round(sx - rx + xx, 4), round(sy - ry + yy, 4)] for sx, sy in sites[ref - off]]
                            if not all(R.free(*pp) for pp in pat):
                                continue
                        else:
                            pat = None
                        ok = (xx, yy, pat)
                        break
                    if ok:
                        break
                if not ok:
                    new = None
                    break
                new.append(ok)
            if not new:
                j += 1
                continue
            for m, (xx, yy, pat) in enumerate(new):
                regs.insert(j + m, [xx, yy] + list(regs[ref][2:]))
                if pat is not None:
                    sites.insert(j + m - off, pat)
            out.append(dict(slot=k, name=f.get("name"), hop=j, len_um=round(L, 1), added=len(new)))
            changed = True
            j += len(new) + 1
        if changed:
            f["regs_um"] = regs
            if isinstance(f.get("stations"), int):
                f["stations"] = len(regs)
    return out


def ft_hop_check_added(t0, t1, reach=405.0):
    """after added ft stages the hop lists differ in length: each new hop must be <= reach or <= the longest base hop
    of its slot."""
    bad = []
    for k, (h0, h1) in enumerate(zip(ft_hops(t0), ft_hops(t1))):
        if len(h0) == len(h1):
            for j, (a, b) in enumerate(zip(h0, h1)):
                if b > max(a, reach) + 0.01:
                    bad.append(dict(slot=k, hop=j, before=round(a, 1), after=round(b, 1)))
        else:
            lim = max([reach] + h0)
            for j, b in enumerate(h1):
                if b > lim + 0.01:
                    bad.append(dict(slot=k, hop=j, before=None, after=round(b, 1)))
    return bad


def eq_struct(t0, t1):
    """positions / outline only: same keys, list lengths, strings and non-coordinate numbers everywhere."""
    bad = []

    def rec(a, b, path):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
            return
        if type(a) is not type(b):
            bad.append(path)
            return
        if isinstance(a, dict):
            if set(a) != set(b):
                bad.append(path + "{keys}")
                return
            for k in a:
                if k in ("note", "clock_entry_access"):
                    continue
                rec(a[k], b[k], path + "/" + k)
        elif isinstance(a, list):
            if len(a) != len(b):
                bad.append(path + "[len]")
                return
            for i, (x, y) in enumerate(zip(a, b)):
                rec(x, y, path + "[%d]" % i)
        elif a != b:
            bad.append(path)
    rec(t0, t1, "")
    for i, (s0, s1) in enumerate(zip(t0.get("internal_stations") or [], t1.get("internal_stations") or [])):
        if len(s0.get("regs_um") or []) != len(s1.get("regs_um") or []) or s0.get("bits") != s1.get("bits"):
            bad.append("internal_stations[%d] regs/bits" % i)
    for i, (h0, h1) in enumerate(zip(t0.get("hard_cores") or [], t1.get("hard_cores") or [])):
        if h0.get("outline_um") != h1.get("outline_um") or h0.get("orient", "R0") != h1.get("orient", "R0"):
            bad.append("hard_cores[%d] shape/orient" % i)
    return sorted(set(bad))


# ------------------------------------------------------------------------------------------------ die estimate
def die_growth(P, grown):
    """partition push model. grown: {type: (W1, H1)} new outlines. Every instance widens (die frame, R90 swaps);
    partitions after it in x (y-overlap) / in y (x-overlap) are pushed keeping their old gaps."""
    T = P["partition_types"]
    parts = P.get("partitions") or []
    Wd, Hd = map(float, P["die"]["outline_um"])
    R = []
    for p in parts:
        t = T.get(p["type"])
        if not t:
            continue
        w, h = map(float, t["outline_um"])
        w1, h1 = grown.get(p["type"], (w, h))
        if p.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
            w, h, w1, h1 = h, w, h1, w1
        R.append(dict(name=p["name"], x=float(p["origin_um"][0]), y=float(p["origin_um"][1]), w=w, h=h, dw=w1 - w, dh=h1 - h))
    out = {}
    for ax in (0, 1):
        key, dk, ok = ("x", "w", "y") if ax == 0 else ("y", "h", "x")
        okd = "h" if ax == 0 else "w"
        dd = "dw" if ax == 0 else "dh"
        order = sorted(range(len(R)), key=lambda i: R[i][key])
        new = {i: R[i][key] for i in order}
        for a_ in order:
            ra = R[a_]
            end = new[a_] + ra[dk] + ra[dd]
            for b_ in order:
                rb = R[b_]
                if rb[key] < ra[key] + ra[dk] - 1e-3:
                    continue
                if min(ra[ok] + ra[okd], rb[ok] + rb[okd]) - max(ra[ok], rb[ok]) <= 1e-3:
                    continue
                gap = rb[key] - (ra[key] + ra[dk])
                if end + gap > new[b_] + 1e-6:
                    new[b_] = end + gap
        far0 = max(r[key] + r[dk] for r in R) if R else 0.0
        far1 = max(new[i] + R[i][dk] + R[i][dd] for i in range(len(R))) if R else 0.0
        out[ax] = max(0.0, far1 - far0)
    W1, H1 = Wd + out[0], Hd + out[1]
    lo, hi = sorted((W1, H1)), sorted(RETICLE_UM)
    return dict(die_before=[Wd, Hd], die_after=[round(W1, 2), round(H1, 2)], dW=round(out[0], 2), dH=round(out[1], 2),
                area_pct=round(100.0 * (W1 * H1 / (Wd * Hd) - 1), 3),
                reticle_fits=lo[0] <= hi[0] + 1e-6 and lo[1] <= hi[1] + 1e-6,
                reticle_headroom_um=[round(hi[0] - lo[0], 1), round(hi[1] - lo[1], 1)])


def reticle_overflow(d):
    lo, hi = sorted(d["die_after"]), sorted(RETICLE_UM)
    return max(0.0, lo[0] - hi[0]) + max(0.0, lo[1] - hi[1])


def reticle_fit(P, Q, rows, log=print):
    """greedy: while the die estimate overflows the reticle, revert the grown type whose revert cuts the overflow
    most per hard violation it fixed (x instances); reverted types keep their base form (row applied=False,
    reason 'reticle'). Returns the final die estimate and the reverted types."""
    inst = collections.Counter(p["type"] for p in P.get("partitions") or [])
    app = {r["type"]: r for r in rows if r.get("applied")}
    grown = {n: tuple(r["outline_after"]) for n, r in app.items()}
    d = die_growth(P, grown) if grown else dict(area_pct=0.0, die_after=list(P["die"]["outline_um"]))
    reverted = []
    while grown and reticle_overflow(d) > 1e-6:
        ov = reticle_overflow(d)
        best = None
        for n, wh in grown.items():
            if tuple(wh) == tuple(app[n]["outline_before"]):
                continue
            g2 = {k: v for k, v in grown.items() if k != n}
            d2 = die_growth(P, g2) if g2 else dict(die_after=list(P["die"]["outline_um"]))
            r = app[n]
            fixed = sum(v for k, v in (r.get("violations_before") or {}).items() if k in HARD) - \
                sum(v for k, v in (r.get("violations_after") or {}).items() if k in HARD)
            score = (ov - reticle_overflow(d2)) / max(1.0, fixed * inst.get(n, 1))
            key = (score, ov - reticle_overflow(d2), -fixed)
            if best is None or key > best[0]:
                best = (key, n, d2)
        if best is None:
            break
        _, n, d2 = best
        grown.pop(n)
        Q["partition_types"][n] = copy.deepcopy(P["partition_types"][n])
        app[n].update(applied=False, reason="reticle: reverted to fit the die estimate in 26x33 mm")
        reverted.append(n)
        d = d2 if grown else dict(area_pct=0.0, die_after=list(P["die"]["outline_um"]), reticle_fits=True)
        log("  reticle fit: reverted %s -> overflow %.1f um" % (n, reticle_overflow(d)))
    return d, reverted


# ------------------------------------------------------------------------------------------------ G0 hook
def g0_check(raw, R, plan_dir, mode="warn", repo=None, ref_dirs=(), max_msgs=40, cfg=None):
    """check.py --street-rule warn|error: one finding per (type, kind) with the worst pairs; street / wall /
    outline_street are the rule (ERROR under 'error'), sliver / outline_sliver / tap_street are always WARN."""
    repo = Path(repo or HERE.parents[1]).resolve()
    die = (raw.get("die") or {}).get("name") or Path(plan_dir).name
    RS.REF_DIRS[:] = [str(plan_dir)] + [str(repo / "physical" / "die_plan" / r) for r in ref_dirs]
    die_dir = repo / "physical" / "die_plan" / die
    if not die_dir.is_dir():
        die_dir = Path(plan_dir)
    rs_cfg = dict(RS.DEFAULTS, derate=dict(RS.DERATE), core_ceiling=RS.DEFAULTS["core_ceiling"], views={}, kit_views={})
    conns = RS.load_conns(die_dir, None, Path(plan_dir), RS.REF_DIRS[1:])
    cfg = dict(DEFAULTS, **(cfg or {}))
    if cfg.get("face_rule"):
        cfg["_planwins"] = plan_face_windows(raw, Path(plan_dir) / "die_plan.json")
    ccfg = dict(gap=G, sweeps=0, topk=1, lam=1.0, reach=cfg["reach"], grid_um=21.6, grt_halving="full",
                fixed_re="", rs=rs_cfg, flips_only=False, face_clear=[])
    summ = dict(types=0, types_with_errors=0, counts={})
    tot = collections.Counter()
    n = 0
    for tn, t in raw["partition_types"].items():
        if not t.get("hard_cores"):
            V = content_only(t, cfg, tn)        # R-STREET: LEF content macros only
            if not V:
                continue
        else:
            M = CP.TypeModel(tn, t, die_dir, repo, conns, ccfg)
            attach_pins(M, die_dir, repo)
            V, cnt = analyze(M.W, M.H, core_models(M, conns_partners(conns, tn, t)), M.CL, type_cfg(cfg, t, tn),
                             type_windows(t))
            V += station_alleys(t, cfg)
        summ["types"] += 1
        cnt = dict(collections.Counter(v["kind"] for v in V))
        tot.update(cnt)
        if any(k in HARD for k in cnt):
            summ["types_with_errors"] += 1
        by = collections.defaultdict(list)
        for v in V:
            by[v["kind"]].append(v)
        for kind, vs in sorted(by.items()):
            vs.sort(key=lambda v: -(v["need"] - v["gap"]))
            w = vs[0]
            msg = ("%s: %d %s (street-or-abut rule, STREET-RULE-1); worst %s|%s gap %.2f um < %.2f um, facing pins %s"
                   % (tn, len(vs), kind, w["a"], w["b"], w["gap"], w["need"], w["pins"]))
            n += 1
            if n > max_msgs and kind not in HARD:
                continue
            if kind in HARD and mode == "error":
                R.err("street_gap", msg, type=tn)
            else:
                R.warn("street_gap", msg, type=tn)
    summ["counts"] = dict(tot)
    return summ


# ------------------------------------------------------------------------------------------------ driver
def load_plan(path):
    raw = Path(path).read_bytes()
    P = json.loads(gzip.decompress(raw)) if str(path).endswith(".gz") else json.loads(raw)
    return P, hashlib.sha256(raw).hexdigest()


def setup(a):
    repo = Path(a.repo).resolve()
    plan = Path(a.plan)
    if not plan.is_absolute():
        plan = repo / plan
    P, sha = load_plan(plan)
    RS.REF_DIRS[:] = [str(plan.parent)] + [str(repo / "physical" / "die_plan" / r) for r in a.ref_dirs]
    die = a.die or (P.get("die") or {}).get("name") or plan.parent.name
    die_dir = repo / "physical" / "die_plan" / ({"s81_head": "s81_head"}.get(die, die))
    if not die_dir.is_dir():
        die_dir = plan.parent
    rs_cfg = dict(RS.DEFAULTS, derate=dict(RS.DERATE), core_ceiling=RS.DEFAULTS["core_ceiling"])
    for key, fn in (("views", "route_supply_views.json"),):
        try:
            rs_cfg[key] = json.loads((HERE / fn).read_text()).get("views", {})
        except (OSError, ValueError):
            rs_cfg[key] = {}
    try:
        rs_cfg["kit_views"] = json.loads((HERE / "route_supply_kit_views.json").read_text()).get(die, {})
    except (OSError, ValueError, AttributeError):
        rs_cfg["kit_views"] = {}
    conns = RS.load_conns(die_dir, None, plan.parent, RS.REF_DIRS[1:])
    names = [n for n, t in P["partition_types"].items() if len(t.get("hard_cores") or []) >= 1]
    if a.types:
        want = set(a.types.split(","))
        names = [n for n in names if n in want]
    if a.match:
        names = [n for n in names if re.search(a.match, n)]
    cfg = dict(DEFAULTS)
    for kv in a.set or []:
        k, _, v = kv.partition("=")
        if k in DEFAULTS and isinstance(DEFAULTS[k], str):
            cfg[k] = v
        else:
            cfg[k] = type(DEFAULTS[k])(float(v)) if k in DEFAULTS else float(v)
    if cfg.get("face_rule"):
        xn = [n for n, t in P["partition_types"].items() if not t.get("hard_cores") and extra_boxes(t)]
        if a.types:
            xn = [n for n in xn if n in set(a.types.split(","))]
        if a.match:
            xn = [n for n in xn if re.search(a.match, n)]
        cfg["_xnames"] = xn
        cfg["_planwins"] = plan_face_windows(P, plan, names + xn)
    return repo, plan, P, sha, die, die_dir, rs_cfg, conns, names, cfg


def cmd_check(a):
    repo, plan, P, sha, die, die_dir, rs_cfg, conns, names, cfg = setup(a)
    ccfg = dict(gap=G, sweeps=0, topk=1, lam=1.0, reach=cfg["reach"], grid_um=21.6, grt_halving="full",
                fixed_re="", rs=rs_cfg, flips_only=False, face_clear=[])
    rows = []
    for n in names:
        t = P["partition_types"][n]
        M = CP.TypeModel(n, t, die_dir, repo, conns, ccfg)
        attach_pins(M, die_dir, repo)
        V, c = analyze(M.W, M.H, core_models(M, conns_partners(conns, n, t)), M.CL, type_cfg(cfg, t, n), type_windows(t))
        V += station_alleys(t, cfg)
        c = dict(collections.Counter(v["kind"] for v in V))
        rows.append(dict(type=n, cores=M.n, counts=c, worst=sorted(V, key=lambda v: -(v["need"] - v["gap"]))[:8],
                         face=[v for v in V if v["kind"] in ("face_street", "station_alley", "transit_street")]))
        print("%s\t%d\t%s" % (n, M.n, json.dumps(c, sort_keys=True)), flush=True)
    for n in cfg.get("_xnames") or ():      # R-STREET: types with LEF content macros only (no hard core)
        V = content_only(P["partition_types"][n], cfg, n)
        c = dict(collections.Counter(v["kind"] for v in V))
        rows.append(dict(type=n, cores=0, counts=c, worst=sorted(V, key=lambda v: -(v["need"] - v["gap"]))[:8], face=V))
        print("%s\t%d\t%s" % (n, 0, json.dumps(c, sort_keys=True)), flush=True)
    rec = dict(schema=SCHEMA, mode="check", plan=str(plan), plan_sha256=sha, die=die,
               cfg={k: v for k, v in cfg.items() if k not in ("_planwins", "_xnames")}, rows=rows,
               types_with_violations=sum(1 for r in rows if any(k in HARD for k in r["counts"])))
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print("types %d, with street-rule violations %d" % (len(rows), rec["types_with_violations"]))
    return 0


_JOB = None


def _one(n):
    P, die_dir, repo, conns, cfg, rs_cfg = _JOB
    try:
        return legalize_type(n, P["partition_types"][n], die_dir, repo, conns, cfg, rs_cfg)
    except Exception as e:      # recorded per type, the base type stays
        print("  %s: ERROR %s" % (n, e), flush=True)
        return dict(type=n, changed=False, applied=False, reason="error %s: %s" % (type(e).__name__, e)), None


def face_anchor_origins(Q, rows):
    """FIXED-FACE: every R0 instance of an applied type with a face anchor moves by its origin_shift_um (the W / S
    growth and the declared die move); a type with a non-R0 instance and a non-zero shift is not applied (its base
    stays: rotated frames are not handled)."""
    for r in rows:
        fa = r.get("face_anchor")
        if not r.get("applied") or not fa or not any(fa["origin_shift_um"]):
            continue
        insts = [p for p in Q.get("partitions") or [] if p.get("type") == r["type"]]
        if any(p.get("orient", "R0") != "R0" for p in insts):
            r["applied"] = False
            r["reason"] = "fixed-face origin shift needs R0 instances"
            continue
        for p in insts:
            p["origin_um"] = [round(p["origin_um"][0] + fa["origin_shift_um"][0], 4),
                              round(p["origin_um"][1] + fa["origin_shift_um"][1], 4)]
        fa["instances_moved"] = [p["name"] for p in insts]


def cmd_legalize(a):
    repo, plan, P, sha, die, die_dir, rs_cfg, conns, names, cfg = setup(a)
    Q = copy.deepcopy(P)
    rows = []
    global _JOB
    # --no-bins (R-STREET classification runs): nothing is written under --repo, the types keep their base bins file
    cfg["_bins_dir"] = "" if getattr(a, "no_bins", False) else "physical/die_plan/%s/street_rule_bins" % die
    if getattr(a, "face_anchor", None):
        cfg["_face_anchor"] = json.loads(Path(a.face_anchor).read_text())
        for n in cfg["_face_anchor"]:
            face_anchor_cfg(cfg["_face_anchor"][n], n)
    _JOB = (P, die_dir, repo, conns, cfg, rs_cfg)
    if a.jobs > 1 and len(names) > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(min(a.jobs, len(names))) as pool:
            res = pool.map(_one, names, chunksize=1)
    else:
        res = [_one(n) for n in names]
    for n, (row, tn) in zip(names, res):
        rows.append(row)
        if tn is not None:
            Q["partition_types"][n] = tn
    face_anchor_origins(Q, rows)
    # export dry run of the clock taps (schema.tap_grid = what gen phys / kit_rtl derives; density taps re-derive
    # from the remapped sinks, every sink <= tap_radius_um): a type whose legalized form fails where its base passes
    # keeps its base form (COORD 11-12, HEAD-94 hd_lep0N "no legal clock tap within 200 um")
    applied = [r["type"] for r in rows if r.get("applied")]
    if applied and cfg.get("tap_check", 1):
        bad1 = tap_check(Q, applied, plan)
        if bad1:
            # re-derive the taps of the failing types, then re-check every applied type (a child type's taps can
            # fail a parent's export)
            n1 = len(bad1)
            for rnd in range(3):
                # a parent's check reads its child types: repeat until no type improves (children fixed first)
                rep = tap_repair(Q, sorted(bad1), plan)
                for r in rows:
                    if r["type"] in rep:
                        r["tap_repair"] = rep[r["type"]]
                prev = len(bad1)
                bad1 = tap_check(Q, applied, plan)
                if not bad1 or len(bad1) >= prev:
                    break
            print("tap repair: %d failing -> %d after re-derivation" % (n1, len(bad1)), flush=True)
        bad0 = tap_check(P, sorted(bad1), plan) if bad1 else {}
        for it in range(3):
            rev = [n for n in bad1 if n not in bad0]
            for r in rows:
                n = r["type"]
                if n in bad1:
                    r["tap_check"] = dict(after=bad1[n], base=bad0.get(n))
                    if n not in bad0:
                        r["applied"] = False
                        r["reason"] = "clock taps: %s" % bad1[n][:160]
                        Q["partition_types"][n] = copy.deepcopy(P["partition_types"][n])
                elif n in applied:
                    r["tap_check"] = "ok"
            if not rev:
                break
            # a reverted child can change a parent's export: re-check the types still applied
            still = [r["type"] for r in rows if r.get("applied")]
            b2 = tap_check(Q, still, plan) if still else {}
            b0 = tap_check(P, sorted(set(b2) - set(bad0)), plan) if b2 else {}
            bad1, bad0 = b2, dict(bad0, **b0)
            if not [n for n in bad1 if n not in bad0]:
                for r in rows:
                    if r.get("applied"):
                        r["tap_check"] = "ok" if r["type"] not in bad1 else dict(after=bad1[r["type"]], base=bad0.get(r["type"]))
                break
        print("tap check: %d applied, %d fail after (%d also fail in base) -> %d reverted" % (
            len(applied), len(bad1), len(bad0), len([n for n in bad1 if n not in bad0])), flush=True)
    # raw reset references follow the re-solved reset trees of every type still applied (after the tap re-derivation:
    # the taps feed the relay siting), same pass as the rect / bins / taps fix (COORD 11-12)
    still = [r["type"] for r in rows if r.get("applied")]
    if still and cfg.get("reset_resel", 1):
        rr, rep, reverted = reset_contract(P, Q, still, plan)
        for r in rows:
            n = r["type"]
            if n in rr:
                r["reset_resel"] = rr[n]
            if n in (rep.get("reattached") or {}):
                r["collector_reattach"] = rep["reattached"][n]
            if n in reverted:
                r["applied"] = False
                r["reason"] = "reset contract: %s" % reverted[n][:160]
    def write_plan():
        txt = json.dumps(Q, indent=1) + "\n"
        if a.out_plan.endswith(".gz"):
            Path(a.out_plan).write_bytes(gzip.compress(txt.encode()))
        else:
            Path(a.out_plan).write_text(txt)
        return hashlib.sha256(Path(a.out_plan).read_bytes()).hexdigest()

    out_sha = None
    rs_rev = []
    if a.out_plan:
        out_sha = write_plan()
        grown = sorted(r["type"] for r in rows if r.get("applied"))
        if a.rs_halving != "off" and grown:
            outdir = Path(a.rs_out or Path(a.out_plan).parent / "rs")
            rb = CP.rs_rows(plan, die, repo, grown, a.ref_dirs, a.rs_halving, outdir / "before")
            # the output plan usually sits outside the base plan dir: the base dir is a ref dir so route_supply reads the
            # same core_conns / pin sidecars as the "before" run (without it the "after" demand was near zero, COORD 11-12)
            ra = CP.rs_rows(Path(a.out_plan).resolve(), die, repo, grown, list(a.ref_dirs) + [str(Path(plan).resolve().parent)],
                            a.rs_halving, outdir / "after")
            for r in rows:
                if r["type"] in grown:
                    rs_ = r["route_supply"] = [CP.rs_summary(rb.get(r["type"])), CP.rs_summary(ra.get(r["type"]))]
                    p0, p1 = rs_[0].get("p99"), rs_[1].get("p99")
                    if p0 is not None and p1 is not None and p1 > p0 + cfg["rs_worse"]:
                        # the advisory route model says the legal form routes worse: keep the base type
                        Q["partition_types"][r["type"]] = copy.deepcopy(P["partition_types"][r["type"]])
                        r.update(applied=False, reason="route_supply p99 worse %.2f -> %.2f" % (p0, p1))
                        rs_rev.append(r["type"])
    reverted = []
    if cfg.get("reticle_fit", 1):
        _, reverted = reticle_fit(P, Q, rows)
    grown = {r["type"]: tuple(r["outline_after"]) for r in rows if r.get("applied")}
    die_est = die_growth(P, grown) if grown else dict(area_pct=0.0)
    die_est.update(reticle_reverted=reverted, rs_reverted=rs_rev)
    if a.out_plan and (reverted or rs_rev):
        out_sha = write_plan()
    rec = dict(schema=SCHEMA, mode="legalize", tool="tools/die_plan/street_rule.py", lane="STREET-RULE-1",
               advisory=True, base_plan=str(plan), base_plan_sha256=sha, plan_output=a.out_plan,
               plan_output_sha256=out_sha, die=die,
               cfg={k: v for k, v in cfg.items() if k not in ("_planwins", "_xnames")}, die_estimate=die_est,
               summary=dict(types=len(rows), violating=sum(1 for r in rows if r.get("changed")),
                            applied=len(grown),
                            cycles_added=sum((r.get("cycles_added") or {}).get("total", 0) for r in rows if r.get("applied")),
                            types_with_cycles_added=sorted(r["type"] for r in rows if r.get("applied")
                                                           and (r.get("cycles_added") or {}).get("total"))), rows=rows)
    if a.event:
        Path(a.event).write_text(json.dumps(rec, indent=1) + "\n")
    hdr = ["type", "applied", "W0", "H0", "W1", "H1", "growth_area_pct", "moved", "viol_before", "viol_after",
           "rs_p99_before", "rs_p99_after", "reason"]
    lines = ["\t".join(hdr)]
    for r in rows:
        if not r.get("changed"):
            continue
        rs_ = r.get("route_supply") or [{}, {}]
        lines.append("\t".join(map(str, [r["type"], r["applied"], *r["outline_before"], *r.get("outline_after", ["", ""]),
                                         (r.get("growth_pct") or {}).get("area", ""), r.get("moved_cores", ""),
                                         sum((r.get("violations_before") or {}).values()),
                                         sum((r.get("violations_after") or {}).values()),
                                         rs_[0].get("p99", ""), rs_[1].get("p99", ""), r.get("reason", "")])))
    if a.tsv:
        Path(a.tsv).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("die estimate:", json.dumps(die_est))
    return 0


def main(argv=None):
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 100000))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nm in ("check", "legalize"):
        s = sub.add_parser(nm)
        s.add_argument("plan")
        s.add_argument("--types")
        s.add_argument("--match")
        s.add_argument("--die")
        s.add_argument("--repo", default=".")
        s.add_argument("--ref-dirs", nargs="*", default=[])
        s.add_argument("--set", action="append", metavar="KEY=VALUE", help="override a DEFAULTS rule constant")
        s.add_argument("--out")
        if nm == "legalize":
            s.add_argument("--out-plan")
            s.add_argument("--event")
            s.add_argument("--tsv")
            s.add_argument("--rs-halving", choices=("full", "edge_outline", "none", "off"), default="edge_outline")
            s.add_argument("--rs-out")
            s.add_argument("--jobs", type=int, default=1)
            s.add_argument("--no-bins", action="store_true",
                           help="do not write remapped sink-bin files under --repo (read-only classification run)")
            s.add_argument("--face-anchor", help="JSON {type: {grow: {x: E|W, y: N|S}, origin_shift_um: [dx, dy], "
                           "fixed_faces: [..]}}: faces abutting FIXED partitions keep die windows, others local")
    s = sub.add_parser("sidecar", help="carry a legalized plan's republished collector trees + reattached sources into "
                       "an asbuilt clock_landing_table sidecar (the strict bind reads sources from the sidecar)")
    s.add_argument("base_plan")
    s.add_argument("new_plan")
    s.add_argument("sidecar_in")
    s.add_argument("sidecar_out")
    s = sub.add_parser("resetfix", help="run only the reset-contract step (re-select, collector_tree republish, source "
                       "re-attach, revert on failure) on an already legalized plan")
    s.add_argument("base_plan")
    s.add_argument("new_plan")
    s.add_argument("out_plan")
    s.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    if a.cmd == "resetfix":
        return cmd_resetfix(a)
    if a.cmd == "sidecar":
        return cmd_sidecar(a)
    return cmd_check(a) if a.cmd == "check" else cmd_legalize(a)


def reset_contract(P, Q, names, plan_path, rounds=4):
    """reset contract of the moved / grown types, in place on Q: raw reset refs re-selected + published collector_tree
    republished (reset_resel), collector sources / children re-attached (reattach_each).  A type whose re-select fails,
    whose raw-branch chain ends, or whose sources find no same-depth relay within 405 um is reverted to its base form;
    the reset wavefront is die-wide, so after a revert every other type restarts from its pre-step form and the step
    repeats.  -> (rr, reattach report, {type: reason})"""
    names = list(names)
    snap = {n: copy.deepcopy(Q["partition_types"][n]) for n in names}
    reverted = {}
    for _ in range(rounds):
        live = [n for n in names if n not in reverted]
        for n in live:
            Q["partition_types"][n] = copy.deepcopy(snap[n])
        rr = reset_resel(P, Q, live, plan_path)
        rep = reattach_each(P, Q)
        bad = {n: str(rep["over"][n]) for n in rep.get("over") or {} if n in live}
        for n, v in rr.items():
            if v.get("error") or any("chain ends" in str(x) or "no same-role" in str(x) for x in v.get("skipped", [])):
                bad.setdefault(n, str(v.get("error") or v.get("skipped")))
        nch = sum(len(v.get("exports", [])) + len(v.get("raw", [])) for v in rr.values())
        print("reset contract: %d types, %d refs re-selected, %d trees republished, %d collectors re-attached, "
              "%d reverted" % (len(rr), nch, sum(1 for v in rr.values() if v.get("tree_republished")),
                               len(rep.get("reattached") or {}), len(bad)), flush=True)
        if not bad:
            break
        for n, why in bad.items():
            reverted[n] = why
            Q["partition_types"][n] = copy.deepcopy(P["partition_types"][n])
    return rr, rep, reverted


def reattach_each(P, Q, reach_um=405):
    """collector_reattach.reattach_plan, one type at a time: a type whose sources find no same-depth relay within
    reach lands in over[] (with the error) instead of aborting the whole plan"""
    import collector_reattach as CRA
    rep = {"reattached": {}, "over": {}}
    for tn in sorted(Q.get("partition_types") or {}):
        if CRA._lc(Q, tn) is None:
            continue
        sub_p = {"partition_types": {tn: P["partition_types"][tn]}} if tn in P.get("partition_types", {}) else {
            "partition_types": {}}
        sub_q = {"partition_types": {tn: Q["partition_types"][tn]}}
        try:
            r = CRA.reattach_plan(sub_p, sub_q, reach_um)
        except ValueError as e:
            rep["over"][tn] = [str(e)]
            continue
        rep["reattached"].update(r["reattached"])
        rep["over"].update(r["over"])
    return rep


def cmd_resetfix(a):
    P, _ = load_plan(Path(a.base_plan))
    Q, _ = load_plan(Path(a.new_plan))
    norm = lambda o: json.dumps(o, sort_keys=True)  # noqa: E731
    moved = [n for n, t in Q["partition_types"].items()
             if n in P["partition_types"] and norm(t) != norm(P["partition_types"][n])]
    rr, rep, reverted = reset_contract(P, Q, moved, Path(a.base_plan))
    txt = json.dumps(Q, indent=1) + "\n"
    Path(a.out_plan).write_bytes(gzip.compress(txt.encode()) if a.out_plan.endswith(".gz") else txt.encode())
    print(json.dumps(dict(changed_types=len(moved), reverted=reverted,
                          sha256=hashlib.sha256(Path(a.out_plan).read_bytes()).hexdigest())))
    return 0


def cmd_sidecar(a):
    """for every type whose landing collector_tree differs between BASE and NEW: the sidecar's collector.types[tn].tree
    becomes NEW's tree (only where the sidecar copy equals BASE's, else refused), then the sources / children node/tap
    are synced (collector_reattach.sync_sidecar).  Other types / keys unchanged."""
    import collector_reattach as CRA
    B, _ = load_plan(Path(a.base_plan))
    N, _ = load_plan(Path(a.new_plan))
    raw_side = Path(a.sidecar_in).read_bytes()
    side = json.loads(gzip.decompress(raw_side) if a.sidecar_in.endswith(".gz") else raw_side)
    st = ((side.get("collector") or {}).get("types") or {})
    norm = lambda o: json.dumps(o, sort_keys=True)  # noqa: E731
    changed, refused = [], []
    for tn, t in N["partition_types"].items():
        lc = ((t.get("clock") or {}).get("landing_contract") or {})
        blc = (((B["partition_types"].get(tn) or {}).get("clock") or {}).get("landing_contract") or {})
        if lc.get("collector_tree") is None or norm(lc["collector_tree"]) == norm(blc.get("collector_tree")):
            continue
        if tn not in st:
            continue
        if norm(st[tn].get("tree")) != norm(blc.get("collector_tree")):
            refused.append(tn)
            continue
        st[tn]["tree"] = json.loads(json.dumps(lc["collector_tree"]))
        changed.append(tn)
    n = CRA.sync_sidecar(N, side, changed) if changed else {}
    txt = json.dumps(side, separators=(",", ":"))
    Path(a.sidecar_out).write_bytes(gzip.compress(txt.encode()) if a.sidecar_out.endswith(".gz") else txt.encode())
    print(json.dumps(dict(trees_replaced=changed, sources_synced=n, refused_stale_sidecar=refused)))
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())

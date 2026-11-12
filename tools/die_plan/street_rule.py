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
                add_regs=0, pin_reorder=0, x_pin_factor=1.0, band_file="")
RETICLE_UM = (26000.0, 33000.0)
OPP = dict(N="S", S="N", E="W", W="E")
HARD = ("street", "wall", "outline_street")      # ERROR kinds; sliver / outline_sliver / tap_street are WARN


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
    r.update(need=nd, kind="ok" if gap >= nd - EPS else "street")
    if r["kind"] == "street" and pa + pb < cfg["pinface_min"]:
        r["kind"] = "sliver"          # (almost) no pins into it: WARN only (tap-illegal / wasted area), never widened
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
    cnt = collections.Counter(v["kind"] for v in V)
    return V, dict(cnt)


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


def legalize_type(name, t, die_dir, repo, conns, cfg, rs_cfg, log=print):
    """returns (row, new type or None)."""
    ccfg = dict(gap=G, sweeps=0, topk=1, lam=1.0, reach=cfg["reach"], grid_um=21.6, grt_halving="full",
                fixed_re="", rs=rs_cfg, flips_only=False, face_clear=[])
    M = CP.TypeModel(name, t, die_dir, repo, conns, ccfg)
    attach_pins(M, die_dir, repo)
    partners = conns_partners(conns, name, t)
    W0, H0 = M.W, M.H
    windows = type_windows(t)
    V0, c0 = analyze(W0, H0, core_models(M, partners), M.CL, cfg, windows)
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
    under0 = len(points_under_cores(t))
    L_base = list(M.L)
    on_core0 = lambda p: M.owner(p, tol=-0.01) is not None   # noqa: E731

    lmeta = link_meta(M, conns) if cfg["add_regs"] > 0 else {}

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
        added_st, added_ft = [], []
        if cfg["add_regs"] > 0:
            added_st = add_station_regs(M, tnew, srep.get("need_more_idx") or [], ccfg["reach"], int(cfg["add_regs"]))
            fixed_si = {d["station"] for d in added_st}
            srep = dict(srep, need_more_idx=[i for i in srep.get("need_more_idx") or [] if i not in fixed_si])
            srep["need_more_regs"] = len(srep["need_more_idx"])
            added_ft = add_ft_regs(M, t, tnew, cfg["reach_limit_um"], int(cfg["add_regs"]))
        V1, c1 = analyze(W, H, core_models(M, partners), M.CL, cfg, windows)
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
        under = points_under_cores(tnew)
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
        bshort = band_short(M, cfg["_bands"])
        if bshort:
            reasons.append("band clearance short %d" % len(bshort))
        if gA > cfg["max_growth_pct"]:
            reasons.append("growth %.1f%% > %.0f%%" % (gA, cfg["max_growth_pct"]))
        ok = not reasons
        relaxed = relaxed_n
        return dict(ok=ok, reasons=reasons, tnew=tnew, added_st=added_st, added_ft=added_ft, added_ln=added_ln, W=W, H=H, gW=gW, gH=gH, gA=gA, c1=c1, left=left, moved=moved,
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
    log("  %s: %s viol %s -> %s  outline %.2fx%.2f -> %.2fx%.2f (+%.1f%%)  moved %d  %s" % (
        name, "APPLIED" if ok else "not applied", c0, c1, W0, H0, W, H, gA, moved, row["reason"]))
    return row, (tnew if ok else None)


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


def add_station_regs(M, tnew, idx, reach, add_max):
    """COORD 11-12 (cycles owner-pre-approved): a station that needs more registers after the move gets them, up to
    add_max extra per station; returns [(station idx, conn, launch, capture, regs before, regs after)]."""
    import hub_repack as HR
    R = _raster(M)
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


def add_ft_regs(M, t0, tnew, reach, add_max):
    """an ft hop stretched past reach by a widened street gets ceil(len / reach) - 1 (<= add_max) new register stages on
    its Manhattan path (bit-site pattern copied from the nearest stage, translated; never under a core). Returns the
    added stages; hops it cannot fix are left (the type is then not applied)."""
    R = _raster(M)
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
        j = 0
        changed = False
        while j <= len(regs):
            ch = [a] + [tuple(r[:2]) for r in regs] + [b]
            p, q = ch[j], ch[j + 1]
            L = abs(p[0] - q[0]) + abs(p[1] - q[1])
            base = hops0[j] if j < len(hops0) else 0.0
            if L <= max(base, reach) + 0.01:
                j += 1
                continue
            n = int(-(-L // reach)) - 1
            if n < 1 or n > add_max:
                j += 1
                continue
            ref = min(j, len(regs) - 1)          # nearest existing stage: bit-site pattern source
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
                        if isinstance(sites, list) and len(sites) == len(regs):
                            rx, ry = regs[ref][:2]
                            pat = [[round(sx - rx + xx, 4), round(sy - ry + yy, 4)] for sx, sy in sites[ref]]
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
                    sites.insert(j + m, pat)
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
    ccfg = dict(gap=G, sweeps=0, topk=1, lam=1.0, reach=cfg["reach"], grid_um=21.6, grt_halving="full",
                fixed_re="", rs=rs_cfg, flips_only=False, face_clear=[])
    summ = dict(types=0, types_with_errors=0, counts={})
    tot = collections.Counter()
    n = 0
    for tn, t in raw["partition_types"].items():
        if not t.get("hard_cores"):
            continue
        summ["types"] += 1
        M = CP.TypeModel(tn, t, die_dir, repo, conns, ccfg)
        attach_pins(M, die_dir, repo)
        V, cnt = analyze(M.W, M.H, core_models(M, conns_partners(conns, tn, t)), M.CL, cfg, type_windows(t))
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
        V, c = analyze(M.W, M.H, core_models(M, conns_partners(conns, n, t)), M.CL, cfg, type_windows(t))
        rows.append(dict(type=n, cores=M.n, counts=c, worst=sorted(V, key=lambda v: -(v["need"] - v["gap"]))[:8]))
        print("%s\t%d\t%s" % (n, M.n, json.dumps(c, sort_keys=True)), flush=True)
    rec = dict(schema=SCHEMA, mode="check", plan=str(plan), plan_sha256=sha, die=die, cfg=cfg, rows=rows,
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


def cmd_legalize(a):
    repo, plan, P, sha, die, die_dir, rs_cfg, conns, names, cfg = setup(a)
    Q = copy.deepcopy(P)
    rows = []
    global _JOB
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
            ra = CP.rs_rows(Path(a.out_plan).resolve(), die, repo, grown, a.ref_dirs, a.rs_halving, outdir / "after")
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
               plan_output_sha256=out_sha, die=die, cfg=cfg, die_estimate=die_est,
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
    a = ap.parse_args(argv)
    return cmd_check(a) if a.cmd == "check" else cmd_legalize(a)


if __name__ == "__main__":
    sys.exit(main())

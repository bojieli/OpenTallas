#!/usr/bin/env python3
"""TYPE-SAFE-2-AREA 11-08 (OWNER 11-08 (B) macro congestion budget; brief item 3): macro-edge CHANNEL REPACK plan event.

Channel model (TS1 a/ts_area.py, M4-M7 = 4 layers): for every hard-core edge facing another core (overlapping
projection, nothing between) or the outline, need = pins on the facing faces x 0.048 / (LAYERS x 0.7); deficit =
need - gap.  A die re-tile cannot grow S81 slots by the approved +349/+291 without breaking abutment (lattice
stretch needs >= +443/+357, see the queue post), so this event works INSIDE the current outline:

  per axis, the type's "free" lines are the x (y) intervals no hard core spans (plus zero-length cuts at abutted
  edges).  A deficit channel can only widen where its gap holds free lines; slack moves there from free lines whose
  every containing channel has surplus (greedy, never driving a channel below min(need, its old gap)).
  COORD 08:41 option (C) form (grid safe): every shift is a whole number of --grid steps (8.64 um = core-origin
  lattice, a multiple of every M2-M9 pitch, the 4.32 PG period and the ft site grids); a widening opens at one cut
  line, a narrowing removes one OBJECT-FREE band (no tap / site / content origin inside it), so cores move rigidly
  and no point leaves its grid.  Face points (windows, ft in/out, chain ends) stay put: abutment and die ports are
  untouched.  Then greedy core MIRROR flips (MY / MX) are kept only where the type shortfall drops: the
  track_offset is re-fit for the new orient (S81 gen_plan_v4.core_track_offset rule, no more off-track pins than
  before), and a core named anywhere else in the type (core clock taps, relays, landings) or with an orientation
  specific pins file never flips.  Per type, the clock-site rules (tap_mode sites, core clock groups) run on the
  result; an added tap the move put in a halo goes back to its base xy, else the nearest legal 4.32 site, else the
  type keeps its base form.  Outline, buses, pins_file, RTL: unchanged.  Remaining deficits are reported per core
  face (repin_asks.py).  No type grows (a type grows only on a real GRT fail: two strikes -> RE-FORM).

  python3 -I tools/die_plan/slot_channel_event.py BASE OUT EVENT --pins-root DIR [--skip-types a,b] [--only-types a,b]
                                                  [--layers 4] [--grid 8.64] [--no-flips] [--analyze]
"""
import argparse
import copy
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
EPS = 1e-6
OPP = dict(N="S", S="N", E="W", W="E")
_PC = {}


def pins_of(hc, root):
    pins = [(p["name"], *p["xy"]) for p in hc.get("pins", [])]
    pf = hc.get("pins_file")
    if pf:
        if pf not in _PC:
            f = Path(root) / pf
            js = json.loads(f.read_text()) if f.exists() else []
            js = js.get("pins", js) if isinstance(js, dict) else js
            _PC[pf] = [(q.get("name") or f"{q['bus']}[{q.get('bit', 0)}]", q["x"], q["y"]) for q in js]
        pins += _PC[pf]
    return pins


def face_counts(hc, root):
    cw, ch = hc["outline_um"]
    o = hc.get("orient", "R0")
    c = defaultdict(int)
    for nm, x, y in pins_of(hc, root):
        if "clk" in nm or nm.startswith("strap_"):
            continue
        f = min([(x, "W"), (cw - x, "E"), (y, "S"), (ch - y, "N")])[1]
        if o in ("MX", "R180") and f in "NS":
            f = OPP[f]
        if o in ("MY", "R180") and f in "EW":
            f = OPP[f]
        c[f] += 1
    return c


def boxes_of(t, root):
    out = []
    for hc in t.get("hard_cores", []):
        dx, dy = hc.get("track_offset_um", [0, 0])
        x0, y0 = hc["origin_um"][0] + dx, hc["origin_um"][1] + dy
        w, h = hc["outline_um"]
        out.append((x0, y0, x0 + w, y0 + h, face_counts(hc, root), hc["inst"]))
    return out


def channels(t, boxes, layers):
    """[(axis, lo, hi, need, core, face)] for every facing pair / core-outline edge with pins (TS1 model)"""
    W, H = t["outline_um"]
    out = []
    for i, a in enumerate(boxes):
        for f, ax in (("E", 0), ("N", 1), ("W", 0), ("S", 1)):
            best, nb = None, None
            for j, b in enumerate(boxes):
                if i == j:
                    continue
                if f == "E" and b[0] >= a[2] - EPS and min(a[3], b[3]) - max(a[1], b[1]) > 1:
                    g = b[0] - a[2]
                elif f == "N" and b[1] >= a[3] - EPS and min(a[2], b[2]) - max(a[0], b[0]) > 1:
                    g = b[1] - a[3]
                else:
                    continue
                if best is None or g < best:
                    best, nb = g, b
            if f in "WS":
                # only the outline edge for W/S (core<->core pairs are counted once from E/N)
                has = any((b[2] <= a[0] + EPS and min(a[3], b[3]) - max(a[1], b[1]) > 1) if f == "W" else
                          (b[3] <= a[1] + EPS and min(a[2], b[2]) - max(a[0], b[0]) > 1) for b in boxes if b is not a)
                if has:
                    continue
                lo, hi = (0.0, a[0]) if f == "W" else (0.0, a[1])
                pins = a[4][f]
            elif nb is None:
                lo, hi = (a[2], W) if f == "E" else (a[3], H)
                pins = a[4][f]
            else:
                lo, hi = (a[2], nb[0]) if f == "E" else (a[3], nb[1])
                pins = a[4][f] + nb[4][OPP[f]]
            if pins == 0 or hi - lo < -EPS:
                continue
            out.append((ax, lo, max(lo, hi), pins * 0.048 / (layers * 0.7), a[5], f))
    return out


def free_intervals(boxes, ax, L):
    sp = sorted((b[ax], b[ax + 2]) for b in boxes)
    out, cur = [], 0.0
    for a, b in sp:
        if a > cur + EPS:
            out.append([cur, a])
        cur = max(cur, b)
    if L > cur + EPS:
        out.append([cur, L])
    # zero-length cut lines: a core edge that no core spans strictly (abutted cores, gap 0) can still open
    have = {round(v, 4) for iv in out for v in iv}
    for e in sorted({round(v, 4) for a, b in sp for v in (a, b)}):
        if 0 < e < L and e not in have and not any(a < e - EPS and b > e + EPS for a, b in sp):
            out.append([e, e])
    return sorted(out)


def plan_axis(chs, fr, grid, caps=None):
    """greedy slack transfer in whole grid steps -> new free-interval lengths; returns (new_lengths, rows).
    caps[k]: the most interval k may give (its widest object-free band, grid-floored)."""
    L = [b - a for a, b in fr]
    n = list(L)
    caps = list(caps) if caps is not None else [math.floor(x / grid + EPS) * grid for x in L]
    mem = [[j for j, (a, b) in enumerate(fr) if a >= lo - EPS and b <= hi + EPS] for (_, lo, hi, _, _, _) in chs]
    gap = [hi - lo for (_, lo, hi, _, _, _) in chs]
    floor = [min(need, g) for (_, _, _, need, _, _), g in zip(chs, gap)]
    in_ch = defaultdict(list)
    for i, js in enumerate(mem):
        for j in js:
            in_ch[j].append(i)

    def cur(i):
        return gap[i] + sum(n[j] - L[j] for j in mem[i])
    order = sorted(range(len(chs)), key=lambda i: cur(i) - chs[i][3])
    for i in order:
        need = chs[i][3]
        if cur(i) >= need - EPS or not mem[i]:
            continue
        recv = max(mem[i], key=lambda j: L[j])
        for k in sorted(range(len(fr)), key=lambda k: -caps[k]):
            d = need - cur(i)
            if d <= EPS:
                break
            if k in mem[i] or n[k] > L[k] + EPS:
                continue                      # never take from a receiver
            cap = caps[k] - (L[k] - n[k])
            for i2 in in_ch[k]:
                if recv in mem[i2]:
                    continue          # a channel holding both donor and receiver keeps its width
                cap = min(cap, cur(i2) - floor[i2])
            amt = min(math.floor(max(0.0, cap) / grid + EPS) * grid, math.ceil(d / grid - EPS) * grid)
            if amt <= EPS:
                continue
            n[k] -= amt
            n[recv] += amt
    rows = []
    for i, (ax, lo, hi, need, core, face) in enumerate(chs):
        g1 = cur(i)
        if gap[i] < need - EPS or g1 < need - EPS:
            rows.append(dict(core=core, face=face, gap=round(gap[i], 2), need=round(need, 2), new_gap=round(g1, 2),
                             short=round(max(0.0, need - g1), 2)))
    return n, rows


def free_bands(fr, pts):
    """per free interval: the object-free sub-bands (u, v) between movable type points (sorted, widest first)"""
    out = []
    for a, b in fr:
        cs = sorted({a, b} | {p for p in pts if a + EPS < p < b - EPS})
        out.append(sorted(((u, v) for u, v in zip(cs, cs[1:])), key=lambda g: -(g[1] - g[0])) or [(a, b)])
    return out


def axis_map(fr, n, bands):
    """grid-STEP monotone map (every shift is a whole number of grid steps, so all type grids survive): a growing
    interval opens at the middle of its widest object-free band; a shrinking one removes a band from its widest
    object-free band (no point lies inside a removed band)."""
    ev = []                                   # (pos, delta, width): x > pos (+delta) / x >= pos + width (-width)
    for (a, b), nj, bd in zip(fr, n, bands):
        d = nj - (b - a)
        u, v = bd[0]
        if d > EPS:
            ev.append(("g", (u + v) / 2, d))
        elif d < -EPS:
            if v - u < -d - EPS:
                raise AssertionError(f"band {u}-{v} narrower than the removal {-d}")
            c = u + (v - u + d) / 2
            ev.append(("s", c, -d))

    def m(x):
        y = x
        for k, p, d in ev:
            if k == "g" and x > p + EPS:
                y += d
            elif k == "s":
                if x >= p + d - EPS:
                    y -= d
                elif x > p + EPS:
                    y -= x - p
        return y
    return m


def transform_type(t, mx, my, W, H):
    """apply (mx, my) to every type-local coordinate; face points of the axis-parallel faces stay"""
    def pt(p):
        x, y = p[0], p[1]
        nx = x if (abs(y) < EPS or abs(y - H) < EPS) else mx(x)
        ny = y if (abs(x) < EPS or abs(x - W) < EPS) else my(y)
        return [round(nx, 4), round(ny, 4)] + list(p[2:])

    def rect(r):
        return pt(r[:2])[:2] + pt(r[2:4])[:2] + list(r[4:])
    SIZE = {"outline_um", "track_offset_um", "bit_site_cell_um", "window_um", "in_window_um", "out_window_um",
            "width_um", "pitch_um", "keepouts_um"}

    def walk(x, key=None):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in SIZE:
                    continue
                if k == "origin_um" and "outline_um" in x and x is not t:
                    continue                  # handled by the caller (rigid move)
                x[k] = walk(v, k)
            return x
        if isinstance(x, list):
            if x and all(isinstance(v, (int, float)) for v in x):
                if key and ("rect" in key) and len(x) == 4:
                    return rect(x)
                if len(x) >= 2 and key and (key.endswith("_um") or key in ("xy", "root", "outs")):
                    return pt(x)
                return x
            return [walk(v, key) for v in x]
        return x
    for hc in t.get("hard_cores", []):          # rigid: the core span (origin + track offset) moves by the map's shift
        dx, dy = hc.get("track_offset_um", [0, 0])
        o = hc["origin_um"]
        cx, cy = o[0] + dx + 0.5 * hc["outline_um"][0], o[1] + dy + 0.5 * hc["outline_um"][1]
        sx, sy = mx(cx) - cx, my(cy) - cy        # span midpoint: slope 1 there, no edge ambiguity
        hc["origin_um"] = [round(o[0] + sx, 4), round(o[1] + sy, 4)]
    for c in t.get("contents", []):
        for cc in [c] + list(c.get("physical_parts", [])):
            if "origin_um" in cc:
                o = cc["origin_um"]
                cc["origin_um"] = [round(mx(o[0]), 4), round(my(o[1]), 4)]
    walk(t)
    return t


def movable_points(t, W, H):
    """x and y of every type-local point the map would move (everything but hard-core origins and face points)"""
    xs, ys = set(), set()

    def rx(x):
        xs.add(round(x, 4))
        return x

    def ry(y):
        ys.add(round(y, 4))
        return y
    tt = copy.deepcopy(t)
    tt["hard_cores"] = []
    transform_type(tt, rx, ry, W, H)
    return xs, ys


_LY = {}


def layer_pins(hc, root):
    """[(layer, x, y)] core-frame pin centres (pins[] + pins_file) for the track-offset proof"""
    out = [(p.get("layer"), *p["xy"]) for p in hc.get("pins", [])]
    pf = hc.get("pins_file")
    if pf:
        if pf not in _LY:
            f = Path(root) / pf
            js = json.loads(f.read_text()) if f.exists() else []
            js = js.get("pins", js) if isinstance(js, dict) else js
            _LY[pf] = [(q.get("layer"), q["x"], q["y"]) for q in js]
        out += _LY[pf]
    return out


def track_fit(hc, root, o):
    """S81 gen_plan_v4.core_track_offset for orient o: (dx, dy, off-track M2-M7 pins) on the 0.012 sub-grid"""
    import schema as S
    Ls = {x["name"]: x for x in S.ASAP7_LAYERS}
    w, h = hc["outline_um"]
    ox, oy = hc["origin_um"]

    def pt(x, y):
        return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]

    def off(c, l):
        k = (c - l["offset_um"]) / l["pitch_um"]
        return abs(k - round(k)) > 1e-4
    pins = [(ln, x, y) for ln, x, y in layer_pins(hc, root) if ln in Ls and ln != "M1"]
    V = [(pt(x, y)[0], Ls[ln]) for ln, x, y in pins if Ls[ln]["dir"] == "V"]
    Hh = [(pt(x, y)[1], Ls[ln]) for ln, x, y in pins if Ls[ln]["dir"] == "H"]
    cand = [round(0.012 * k, 3) for k in range(0, 24)]
    c0 = hc.get("track_offset_um", [0.108, 0.012])

    def best(P, c, base):
        sc = {d: sum(off(base + d + q, l) for q, l in P) for d in cand}
        m = min(sc.values())
        c = round(c, 3)
        return (c if sc.get(c) == m else min(d for d in cand if sc[d] == m)), m
    dx, bx = best(V, c0[0], ox)
    dy, by = best(Hh, c0[1], oy)
    return dx, dy, bx + by


FLIP = dict(MY={"R0": "MY", "MY": "R0", "MX": "R180", "R180": "MX"},
            MX={"R0": "MX", "MX": "R0", "MY": "R180", "R180": "MY"})
ORIENT_PINS = ("_MX", "_MY", "MX.", "MY.", "_f.", "_flip", "_mirror")


def flip_ok(t, hc):
    """a core may flip when nothing else in the type names it (core clock taps, relays, landings, access stacks)
    and its pins file is not orientation-specific"""
    pf = hc.get("pins_file") or ""
    if any(k in pf for k in ORIENT_PINS) or hc.get("clock_entry_access") or hc.get("straps") \
            or hc.get("parent_id_straps"):
        return False
    rest = json.dumps({k: v for k, v in t.items() if k != "hard_cores"})
    return f'"{hc["inst"]}' not in rest and f'{hc["inst"]}.' not in rest and f'{hc["inst"]}/' not in rest


def evaluate(t, root, layers, grid, W, H, pts):
    bx = boxes_of(t, root)
    chs = channels(t, bx, layers)
    d0 = sum(max(0.0, need - (hi - lo)) for (_, lo, hi, need, _, _) in chs)
    res = {}
    for ax, Lx in ((0, W), (1, H)):
        c = [ch for ch in chs if ch[0] == ax]
        fr = free_intervals(bx, ax, Lx)
        bands = free_bands(fr, pts[ax])
        caps = [math.floor((bd[0][1] - bd[0][0]) / grid + EPS) * grid for bd in bands]
        n, rows = plan_axis(c, fr, grid, caps)
        res[ax] = (fr, n, rows, bands)
    d1 = sum(r["short"] for ax in (0, 1) for r in res[ax][2])
    return d0, d1, chs, res


def boxes_clear(t, root, W, H):
    bx = boxes_of(t, root)
    for i, a in enumerate(bx):
        if a[0] < -EPS or a[1] < -EPS or a[2] > W + EPS or a[3] > H + EPS:
            return False
        for b in bx[i + 1:]:
            if min(a[2], b[2]) - max(a[0], b[0]) > EPS and min(a[3], b[3]) - max(a[1], b[1]) > EPS:
                return False
    return True


def mini_plan(raw, tn, t):
    m = {k: v for k, v in raw.items() if k not in ("partition_types", "partitions")}
    m["partition_types"] = {tn: t}
    m["partitions"] = [p for p in raw["partitions"] if p["type"] == tn]
    return m


def mini_errors(raw, tn, t):
    """the per-type clock-site rules schema.validate runs (tap sites by tap_mode, core clock groups) on a one-type
    plan (schema.Plan of the type and its partitions only: milliseconds, so every candidate is checked)"""
    import schema as S
    import taps as T
    import core_clock_groups as CG
    m = mini_plan(raw, tn, copy.deepcopy(t))
    out = set()
    try:
        P = S.Plan(m)
    except Exception as exc:              # noqa: BLE001  (any plan-construction error is a rule failure here)
        return {f"plan: {exc}"}
    mode = t.get("clock", {}).get("tap_mode")
    for fn in ((T.grid_explicit_sites,) if mode == "grid+explicit" else (T.explicit_tap_sites,)
               if mode == "explicit" else ()) + (CG.groups,):
        try:
            fn(P, tn)
        except (ValueError, KeyError, TypeError) as exc:
            out.add(str(exc))
    return out


_NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")


def plan_rules(raw, tn, t, plan_dir, side):
    """G0 rules a repack can break INSIDE one type, on a one-type plan: check.py internal reg-reg reach
    (internal_station: core <-> core / face -> core bundles, internal_stations hops, numbers masked) and the hard-core
    face rule (core_faces); and the ft chains (die_hop_scan.type_tables, per bit [in pin, S0..Sk-1, out pin]) as
    segment lengths.  Returns (finding keys, {(slot, bit): [segments]})."""
    import schema as S
    import check as CK
    import die_hop_scan as DH
    m = mini_plan(raw, tn, copy.deepcopy(t))
    P = S.Plan(m)
    R = CK.Report()
    CK.check_completeness(P, R, side=side, plan_dir=plan_dir)
    try:
        CK.check_core_faces(P, R, plan_dir)
    except Exception as exc:              # noqa: BLE001
        R.err("core_faces", f"core_faces raised {exc}")
    keys = {(i["check"], _NUM.sub("#", i["msg"])) for i in R.items
            if "[internal_station]" in i["msg"] or i["check"] in ("core_faces", "hard_cores")}
    segs = {}
    try:
        pins, chains = DH.type_tables(P, tn)
    except Exception as exc:              # noqa: BLE001
        return keys | {("ft", f"type_tables raised {type(exc).__name__}")}, segs
    for sn, ch in chains.items():
        pi, po = pins.get(sn + "_i", {}), pins.get(sn + "_o", {})
        for bit, st in ch.items():
            pts = ([pi[bit][:2]] if bit in pi else []) + [tuple(p[:2]) for p in st] + ([po[bit][:2]] if bit in po else [])
            segs[(sn, bit)] = [DH.md(a, b) for a, b in zip(pts, pts[1:])]
    return keys, segs


def rules_ok(base, new, reach):
    """no new finding; per ft bit: a face segment (pin <-> S0 / S(k-1) <-> pin, half of a die hop) never grows,
    an inner hop stays <= max(its base length, reach)"""
    bk, bs = base
    nk, ns = new
    why = [f"{c}: {m[:160]}" for c, m in sorted(nk - bk)]
    for key, sg in ns.items():
        b = bs.get(key)
        if b is None or len(b) != len(sg):
            why.append(f"ft {key}: chain shape changed")
            continue
        for i, (x, y) in enumerate(zip(b, sg)):
            face = i in (0, len(sg) - 1)
            if (face and y > x + 0.01) or (not face and y > max(x, reach) + 0.01):
                why.append(f"ft {key[0]} bit {key[1]} seg {i}: {x:.1f} -> {y:.1f} um")
                break
        if len(why) > 4:
            break
    return not why, why


TAP_STEP = 4.32


def legalize_type(raw, Q, tn, orig_added):
    """per-type plan rules on the repacked type (one-type plan through schema.validate, no new error vs the base type).
    An added clock tap the map put inside a moved core halo / next to a re-cleared grid tap goes back to its base xy
    when that is legal, else to the nearest legal site on the 4.32-um PG period within +-8 steps; else the type keeps
    its base form (returns ok=False)."""
    base = mini_errors(raw, tn, raw["partition_types"][tn])
    t = Q["partition_types"][tn]
    fixes = []
    orig = {p["name"]: p["xy"] for p in (orig_added or [])}
    for _ in range(64):
        new = sorted(e for e in mini_errors(raw, tn, t) if e not in base)
        if not new:
            return True, fixes, []
        m = re.search(r"added tap (clk_t\d+) violates", new[0])
        if not m:
            return False, fixes, new
        nm = m.group(1)
        tp = next((p for p in t.get("clock", {}).get("added_taps", []) if p["name"] == nm), None)
        if tp is None or any(f["tap"] == nm for f in fixes):
            return False, fixes, new
        x0, y0 = tp["xy"]
        cands = ([tuple(orig[nm])] if nm in orig else []) + sorted(
            ((round(x0 + i * TAP_STEP, 4), round(y0 + j * TAP_STEP, 4)) for i in range(-8, 9) for j in range(-8, 9)
             if i or j), key=lambda q: abs(q[0] - x0) + abs(q[1] - y0))
        done = False
        for c in cands:
            tp["xy"] = [c[0], c[1]]
            if not any(f"added tap {nm} violates" in e for e in mini_errors(raw, tn, t) if e not in base):
                fixes.append(dict(tap=nm, mapped=[x0, y0], to=[c[0], c[1]]))
                done = True
                break
        if not done:
            tp["xy"] = [x0, y0]
            return False, fixes, new
    return False, fixes, ["legalize: too many rounds"]


def evaluate_after(t, root, layers):
    """remaining channel shortfall of a type as it now stands (TS1 model, no further repack)"""
    return sum(max(0.0, nd - (hi - lo)) for (_, lo, hi, nd, _, _) in channels(t, boxes_of(t, root), layers))


def open_rows(t, root, layers):
    return sorted([dict(core=c_, face=f_, gap=round(hi - lo, 2), need=round(nd, 2), new_gap=round(hi - lo, 2),
                        short=round(nd - (hi - lo), 2)) for (_, lo, hi, nd, c_, f_) in
                   channels(t, boxes_of(t, root), layers) if hi - lo < nd - EPS], key=lambda q: -q["short"])


def build(raw, root, skip, only, layers, grid, analyze, flips=True, plan_dir=None):
    Q = copy.deepcopy(raw)
    plan_dir = plan_dir or root
    side = {}
    reach = 405.0
    if not analyze:
        import check as CK
        import schema as S
        side = CK.load_core_conns(plan_dir)
        reach = min(float(raw.get("budgets", {}).get("ft_station_max_um", S.SIGNAL_REACH_UM)), S.SIGNAL_REACH_UM)
    edits, report = [], []
    for tn in sorted(Q["partition_types"]):
        t = Q["partition_types"][tn]
        if tn in skip or (only and tn not in only) or t.get("hard") or not t.get("hard_cores"):
            continue
        W, H = t["outline_um"]
        if not any(hi - lo < need - EPS for (_, lo, hi, need, _, _) in channels(t, boxes_of(t, root), layers)):
            continue
        pts = movable_points(t, W, H)
        d0, d1, chs, res = evaluate(t, root, layers, grid, W, H, pts)
        base_d1 = d1
        flipped = []
        if flips:                              # greedy core mirror flips: keep one only if the shortfall drops
            for _ in range(2):
                better = False
                for hc in t["hard_cores"]:
                    if not flip_ok(t, hc):
                        continue
                    o0, to0 = hc.get("orient", "R0"), list(hc.get("track_offset_um", [0.108, 0.012]))
                    bad0 = track_fit(hc, root, o0)[2]
                    for kind in ("MY", "MX"):
                        o1 = FLIP[kind][o0]
                        dx, dy, bad1 = track_fit(hc, root, o1)
                        if bad1 > bad0:
                            continue
                        hc["orient"], hc["track_offset_um"] = o1, [dx, dy]
                        e = evaluate(t, root, layers, grid, W, H, pts) if boxes_clear(t, root, W, H) else None
                        if e is not None and e[1] < d1 - 0.5:
                            d1, res = e[1], e[3]
                            flipped.append(dict(core=hc["inst"], module=hc.get("module"), orient=[o0, o1],
                                                track_offset_um=[to0, [dx, dy]], off_track_pins=bad1))
                            o0, to0, bad0, better = o1, [dx, dy], bad1, True
                        else:
                            hc["orient"], hc["track_offset_um"] = o0, to0
                if not better:
                    break
        moved = any(abs(a - b) > EPS for ax in (0, 1) for a, b in zip(res[ax][1], [r[1] - r[0] for r in res[ax][0]]))
        row = dict(type=tn, channels=len(chs), deficit_um=round(d0, 1), remaining_um=round(d1, 1),
                   resolved_um=round(d0 - d1, 1), repack_only_remaining_um=round(base_d1, 1), moved=moved,
                   flips=flipped,
                   open=sorted([r for ax in (0, 1) for r in res[ax][2] if r["short"] > 0], key=lambda r: -r["short"]))
        report.append(row)
        if (moved or flipped) and not analyze and d1 < d0 - EPS:
            orig_added = copy.deepcopy(t.get("clock", {}).get("added_taps"))
            flipped_t = copy.deepcopy(t)              # orients / offsets after the flip pass, before the map
            base_rules = plan_rules(raw, tn, raw["partition_types"][tn], plan_dir, side)
            ok, why, variant = False, [], None
            # variants, best first: full map; one axis only; without the flips (repack only, each axis)
            vlist = [("xy", True), ("x", True), ("y", True)] + ([("xy", False), ("x", False), ("y", False)]
                                                                if flipped else [])
            for axes, keep_flips in vlist:
                tv = copy.deepcopy(flipped_t) if keep_flips else copy.deepcopy(raw["partition_types"][tn])
                e = evaluate(tv, root, layers, grid, W, H, pts)
                if e[1] >= d0 - EPS:
                    continue
                rv = e[3]
                ident = lambda v: v                   # noqa: E731
                mx = axis_map(rv[0][0], rv[0][1], rv[0][3]) if "x" in axes else ident
                my = axis_map(rv[1][0], rv[1][1], rv[1][3]) if "y" in axes else ident
                transform_type(tv, mx, my, W, H)
                Q["partition_types"][tn] = tv
                ok, fixes, why = legalize_type(raw, Q, tn, orig_added)
                if ok:
                    ok, why2 = rules_ok(base_rules, plan_rules(raw, tn, Q["partition_types"][tn], plan_dir, side),
                                        reach)
                    why = why2
                if ok:
                    t = Q["partition_types"][tn]
                    d1v = evaluate_after(t, root, layers)
                    row.update(variant=f"{axes}{'+flips' if keep_flips and flipped else ''}",
                               remaining_um=round(d1v, 1), resolved_um=round(d0 - d1v, 1),
                               flips=flipped if keep_flips else [], tap_moves=fixes,
                               open=open_rows(t, root, layers))
                    break
                row.setdefault("rejected", []).append(dict(variant=axes + ("+flips" if keep_flips else ""),
                                                           why=why[:3]))
            if ok and row["resolved_um"] > EPS:
                edits.append({k: v for k, v in row.items() if k != "open"})
            else:
                row.pop("variant", None)
                row.pop("tap_moves", None)
                Q["partition_types"][tn] = copy.deepcopy(raw["partition_types"][tn])
                op = [dict(core=c_, face=f_, gap=round(hi - lo, 2), need=round(nd, 2), new_gap=round(hi - lo, 2),
                           short=round(nd - (hi - lo), 2)) for (_, lo, hi, nd, c_, f_) in
                      channels(Q["partition_types"][tn], boxes_of(Q["partition_types"][tn], root), layers)
                      if hi - lo < nd - EPS]
                row.update(reverted=True, remaining_um=row["deficit_um"], resolved_um=0.0, flips=[],
                           open=sorted(op, key=lambda q: -q["short"]))
        elif not analyze:
            Q["partition_types"][tn] = copy.deepcopy(raw["partition_types"][tn])
    return Q, edits, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("event")
    ap.add_argument("--pins-root", required=True)
    ap.add_argument("--skip-types", default="")
    ap.add_argument("--only-types", default="")
    ap.add_argument("--layers", type=float, default=4.0)
    ap.add_argument("--grid", type=float, default=8.64, help="every shift is a whole number of these (um): 8.64 = the core-origin lattice, a multiple of every track pitch, the PG period and the ft site grids")
    ap.add_argument("--no-flips", action="store_true")
    ap.add_argument("--plan-dir", help="the plan directory check.py reads (core_conns.json, core pins); default --pins-root")
    ap.add_argument("--analyze", action="store_true")
    a = ap.parse_args(argv)
    raw_b = Path(a.base).read_bytes()
    P0 = json.loads(raw_b)
    skip = {s for s in a.skip_types.split(",") if s}
    only = {s for s in a.only_types.split(",") if s} or None
    Q, edits, report = build(P0, a.pins_root, skip, only, a.layers, a.grid, a.analyze, not a.no_flips, a.plan_dir)
    touched = {e["type"] for e in edits}
    for k in P0:
        if k != "partition_types" and json.dumps(P0[k], sort_keys=True) != json.dumps(Q[k], sort_keys=True):
            raise AssertionError(f"top-level key {k} changed")
    for tn, v in P0["partition_types"].items():
        v1 = Q["partition_types"][tn]
        if tn not in touched and json.dumps(v, sort_keys=True) != json.dumps(v1, sort_keys=True):
            raise AssertionError(f"type {tn} changed but is not listed")
        for k in ("outline_um", "buses", "params", "module", "rtl", "contents"):
            if k == "contents":
                strip = lambda cs: [{kk: vv for kk, vv in c.items() if kk not in ("origin_um", "physical_parts")}
                                    for c in (cs or [])]
                if json.dumps(strip(v.get(k)), sort_keys=True) != json.dumps(strip(v1.get(k)), sort_keys=True):
                    raise AssertionError(f"type {tn}: contents changed beyond origins")
                continue
            if json.dumps(v.get(k), sort_keys=True) != json.dumps(v1.get(k), sort_keys=True):
                raise AssertionError(f"type {tn}: {k} changed")
    if not a.analyze:
        import schema as S
        base_errs = set(map(str, S.validate(copy.deepcopy(P0))))
        reverted = []
        for _ in range(8):           # a type whose repack breaks a plan rule (tap halo/spacing, ...) keeps its base form
            errs = [e for e in map(str, S.validate(copy.deepcopy(Q))) if e not in base_errs]
            if not errs:
                break
            names = {e_["type"] for e_ in edits}
            bad = {tn for tn in names if any(re.search(r"(?<![\w.])" + re.escape(tn) + r"(?![\w])", e) for e in errs)}
            if not bad:
                raise SystemExit("slot_channel_event: output fails schema validation: " + "; ".join(errs[:5]))
            for tn in sorted(bad):
                Q["partition_types"][tn] = copy.deepcopy(P0["partition_types"][tn])
                why = [e for e in errs if tn in e][:2]
                reverted.append(dict(type=tn, why=why))
                print(f"revert {tn}: {why[0][:200]}", file=sys.stderr)
            edits[:] = [e_ for e_ in edits if e_["type"] not in bad]
            for r in report:
                if r["type"] in bad:
                    t0 = P0["partition_types"][r["type"]]
                    op = [dict(core=c_, face=f_, gap=round(hi - lo, 2), need=round(nd, 2), new_gap=round(hi - lo, 2),
                               short=round(nd - (hi - lo), 2))
                          for (_, lo, hi, nd, c_, f_) in channels(t0, boxes_of(t0, a.pins_root), a.layers)
                          if hi - lo < nd - EPS]
                    r.update(reverted=True, remaining_um=r["deficit_um"], resolved_um=0.0, flips=[],
                             open=sorted(op, key=lambda q: -q["short"]))
        else:
            raise SystemExit("slot_channel_event: schema still failing after 8 revert rounds")
        Path(a.out).write_text(json.dumps(Q, indent=1) + "\n")
    data = Path(a.out).read_bytes() if not a.analyze else b""
    rec = dict(schema="opentallas.slot_channel_event.v1", tool="tools/die_plan/slot_channel_event.py",
               owner="OWNER 2026-11-08 (B) macro congestion budget; lane TYPE-SAFE-2-AREA",
               base_plan=str(a.base), base_plan_sha256=hashlib.sha256(raw_b).hexdigest(),
               plan_output=None if a.analyze else str(a.out),
               plan_output_sha256=hashlib.sha256(data).hexdigest() if data else None,
               layers=a.layers, grid_um=a.grid, skipped_types=sorted(skip), edits=edits, report=report,
               reverted=[] if a.analyze else reverted,
               totals=dict(types_with_deficit=len(report), types_moved=len(edits),
                           deficit_um=round(sum(r["deficit_um"] for r in report), 1),
                           resolved_um=round(sum(r["resolved_um"] for r in report), 1),
                           remaining_um=round(sum(r["remaining_um"] for r in report), 1),
                           fully_resolved=sum(1 for r in report if r["remaining_um"] <= EPS),
                           flips=sum(len(r["flips"]) for r in report),
                           repack_only_remaining_um=round(sum(r["repack_only_remaining_um"] for r in report), 1)))
    Path(a.event).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec["totals"]))


if __name__ == "__main__":
    main()

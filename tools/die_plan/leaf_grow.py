#!/usr/bin/env python3
"""leaf_grow.py -- LEAF-GROW (FP-CONVERGE-S81, COORD ruling 11-25): grow one ot_s81sl_leaf / kv_leaf type row on the W side.

  leaf_grow.py grow PLAN --types REGEX --dx UM [--dy UM --ycut UM] [--xcut UM] --out PLAN2
  leaf_grow.py check PLAN0 PLAN1 --types REGEX     # structural invariants old -> new (exit 1 on a break)
  leaf_grow.py retap PLAN --types REGEX --out PLAN2 # rename grid+explicit added taps for the re-derived grid count
  leaf_grow.py retap-check PLAN --types REGEX       # taps.grid_explicit_sites per type (exit 1 on a refusal)
  leaf_grow.py widen PLAN --types REGEX --out PLAN2 # ANY type: widen each plan-core gap <9 um carrying a bus lane (ADV-MACRO-GAP) to bits/(tracks x 0.5)
  (--any-type on grow/retap/retap-check/check lifts the leaf-name filter)

Grid clock taps are derived from the outline (schema._grid_taps), so growth can change their count; grid+explicit added
taps must then be clk_t<n_grid+i>.  grow re-derives n_grid with schema._grid_taps on the grown plan and renames added taps
plus every exact reference in the row (--no-retap skips); re-record reset anchors (reset_anchor --repick) afterwards.

grow(): outline_um W += dx.  Every type-local point with x >= XCUT (default: the smallest hard-core origin x of the
row, i.e. the column the cores start at) moves by +dx; the strip x < XCUT is the pin / street side and stays.  PIN-ANCHORED
items never move in x (they sit on the N/S faces at fixed absolute x so the neighbouring tile still abuts): ft_slots
(regs, bit sites, windows) except the points ON the E face (x >= W - 0.01, they follow the face to W + dx), buses windows,
clock landing_contract pins / bands / collector_local_sources, band_fixed_um, landing_reader/writer_start,
edge_clocks, landing_local_resets, landing_reader_start.  W-face windows stay at x = 0.
With --dy/--ycut every y >= ycut moves by +dy (H += dy); pin-anchored items on the N face (y >= H - 0.01) follow to H + dy.
No die-level fix-ups: the caller re-runs core_place (--slot-clear --ft-resite) on the grown plan, which re-derives
stations / taps of the cores it moves; the gate is plan_gate_pre INOUTLINE + leaf_template check.
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

FT_XCUT = [0.0]           # --ft-xcut: in-band ft points with x < this never shift (default 0 = all follow)
FT_MODE = [True]          # True: ft slots pin-anchored; "ft": in-band ft points shift with the cores (--ft-interior)
LEAF_RE = re.compile(r"^ot_s81sl_(kv_)?leaf__")
ANY_TYPE = [False]        # --any-type: the growth / retap / check commands accept any partition type (non-leaf: dsdv_slice_*_C ...)
LATTICE = 4.32            # placement lattice (hub_repack.G); widened gaps are rounded UP to a multiple


def type_ok(tn):
    return ANY_TYPE[0] or bool(LEAF_RE.match(tn))
EPS = 0.01
# subtrees that are pin-anchored (never x-shifted; E / N face points follow the face)
PIN_KEYS = {"ft_slots", "buses"}
PIN_CLOCK = {"landing_contract", "band_fixed_um", "landing_reader_start", "landing_writer_start", "edge_clocks",
             "landing_local_resets"}
# x-coordinate point lists that shift (key -> kind)  ("pt" = [x, y, ...]; "pts" = list of pt)


def isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_pt(v):
    return isinstance(v, list) and 2 <= len(v) <= 4 and isnum(v[0]) and isnum(v[1])


def xform(pt, W, H, dx, dy, xcut, ycut, pinned):
    """new point for one [x, y, ...]"""
    x, y = float(pt[0]), float(pt[1])
    nx, ny = x, y
    if pinned == "ft" and EPS < x < W - EPS and EPS < y < H - EPS:
        if x < FT_XCUT[0]:                               # in-band ft point west of the ft cut stays (the kept street)
            return [round(x, 4), round(y + (dy if dy and y >= ycut else 0.0), 4)] + list(pt[2:])
        pinned = False                                   # --ft-interior: an in-band ft reg / bit site follows the cores
    if pinned:
        if x >= W - EPS:
            nx = x + dx
        if dy and y >= H - EPS:
            ny = y + dy
    else:
        if x >= xcut:
            nx = x + dx
        if dy and y >= ycut:
            ny = y + dy
    return [pt[0] if nx == x else round(nx, 4), pt[1] if ny == y else round(ny, 4)] + list(pt[2:])


def walk(o, f, pinned):
    """rebuild o with every [x, y] point mapped by f(pt, pinned); subtrees named in PIN_* switch pinned on"""
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if k.endswith("window_um") or k in ("window", "in_window_um", "out_window_um"):
                out[k] = v                                  # 1-D along a face: never an (x, y) point
            elif k in ("outline_um", "bit_site_cell_um", "track_offset_um", "legs_um", "cell_wh_um", "bits", "relay_depth"):
                out[k] = v
            else:
                out[k] = walk(v, f, pinned or (FT_MODE[0] if k == "ft_slots" else None) or k in PIN_KEYS or k in PIN_CLOCK)
        return out
    if isinstance(o, list):
        if is_pt(o):
            return f(o, pinned)
        return [walk(v, f, pinned) for v in o]
    return o


def ft_slot_interior(sl, f, W, H, dx):
    """--ft-interior on one ft slot: a bit-site group moves as ONE unit (by its centroid against --ft-xcut), so a group
    never splits across the cut; registers follow xform (face points stay on their face, E-face points follow W)."""
    sl = copy.deepcopy(sl)
    sl["regs_um"] = [f(r, "ft") for r in sl.get("regs_um") or []]
    groups = []
    for g in sl.get("bit_sites_um") or []:
        if not g or not is_pt(g[0]):
            groups.append(g)
            continue
        cx = sum(q[0] for q in g) / len(g)
        cy = sum(q[1] for q in g) / len(g)
        on_face = cx <= EPS or cx >= W - EPS or cy <= EPS or cy >= H - EPS
        if on_face:
            groups.append([f(q, True) for q in g])
        elif cx >= FT_XCUT[0]:
            groups.append([[round(q[0] + dx, 4), round(q[1], 4)] + list(q[2:]) for q in g])
        else:
            groups.append([list(q) for q in g])
        # (dy growth of interior ft groups is not supported here: grow y in a separate call without --ft-interior)
    if "bit_sites_um" in sl:
        sl["bit_sites_um"] = groups
    return sl


def rename_added_taps(row, n_grid):
    """grid+explicit (taps.grid_explicit_sites): added taps must be named clk_t<n_grid+i> in table order, n_grid =
    len(schema._grid_taps) of the CURRENT outline.  -> (row2, {old: new}); every other exact string reference in the row
    (collector_tree taps, landing pins source_clock_port, ...) is renamed in the same single pass, so overlapping old/new
    ranges never chain.  Idempotent."""
    row = copy.deepcopy(row)
    table = (row.get("clock") or {}).get("added_taps") or []
    old = [q.get("name") for q in table]
    new = ["clk_t%d" % (n_grid + i) for i in range(len(table))]
    mp = {o: n for o, n in zip(old, new) if o != n}
    if not mp:
        return row, {}

    def rn(o):
        if isinstance(o, dict):
            return {k: rn(v) for k, v in o.items()}
        if isinstance(o, list):
            return [rn(v) for v in o]
        return mp.get(o, o) if isinstance(o, str) else o
    for q, n in zip(table, new):
        q["name"] = n
    for k in list(row):
        if k == "clock":
            for ck in list(row["clock"]):
                if ck != "added_taps":
                    row["clock"][ck] = rn(row["clock"][ck])
        else:
            row[k] = rn(row[k])
    return row, mp


def _schema():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import schema as S
    return S


def retap_plan(raw, path, tns):
    """re-derive the grid tap count with the plan generator's own schema._grid_taps and rename added taps"""
    S = _schema()
    P = S.Plan(raw, path)
    out = {}
    for tn in tns:
        if ((raw["partition_types"][tn].get("clock") or {}).get("tap_mode")) != "grid+explicit":
            continue
        n = len(S._grid_taps(P, tn))
        raw["partition_types"][tn], mp = rename_added_taps(raw["partition_types"][tn], n)
        out[tn] = (n, mp)
    return out


def grow_row(t, dx, dy=0.0, ycut=None, xcut=None):
    t = copy.deepcopy(t)
    W, H = t["outline_um"]
    hc = t.get("hard_cores") or []
    if xcut is None:
        xcut = min(h["origin_um"][0] for h in hc) if hc else 0.0
    if ycut is None:
        ycut = 0.0 if not dy else H
    f = lambda pt, pinned: xform(pt, W, H, dx, dy, xcut, ycut, pinned)  # noqa: E731
    for k in list(t):
        if k == "outline_um":
            continue
        if k == "hard_cores":
            for h in t[k]:
                h["origin_um"] = f(h["origin_um"], False)
            continue
        if k == "ft_slots" and FT_MODE[0] == "ft":
            t[k] = [ft_slot_interior(sl, f, W, H, dx) for sl in t[k]]
            continue
        t[k] = walk(t[k], f, (FT_MODE[0] if k == "ft_slots" else None) or k in PIN_KEYS)
    t["outline_um"] = [round(W + dx, 4), round(H + dy, 4)]
    t["note"] = (t.get("note", "") + " | LEAF-GROW 11-25: outline +%.2f x +%.2f (xcut %.2f)" % (dx, dy, xcut)).strip(" |")
    return t


def pts(t):
    """every (path, x, y) point of a row (for the invariants)"""
    out = []

    def rec(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                if k.endswith("window_um") or k in ("outline_um", "bit_site_cell_um", "track_offset_um"):
                    continue
                rec(v, p + "." + k)
        elif isinstance(o, list):
            if is_pt(o):
                out.append((p, float(o[0]), float(o[1])))
            else:
                for i, v in enumerate(o):
                    rec(v, p + "[%d]" % i)
    rec(t, "")
    return out


def check_rows(a, b, name="", cuts=1):
    """-> [problem]: invariants of a grown row b against its source a"""
    bad = []
    Wa, Ha = a["outline_um"]
    Wb, Hb = b["outline_um"]
    if Wb < Wa - EPS or Hb < Ha - EPS:
        bad.append("outline shrank")
    for v, nm in ((Wb, "W"), (Hb, "H")):
        q = v / 4.32
        if raster_bad(v):
            # hub_repack.Raster sizes its lattice with int(W / G) + 1: a width whose float quotient lands just under the
            # integer drops the face column, so every E/N face point reads blocked (ft_failed on the face register)
            bad.append("RASTER %s %.4f / 4.32 = %.12f truncates; pick dx/dy one lattice step off" % (nm, v, q))
    pa, pb = pts(a), pts(b)
    if [p for p, _, _ in pa] != [p for p, _, _ in pb]:
        bad.append("point set / order changed")
        return bad
    out = [p for p, x, y in pb if x < -EPS or y < -EPS or x > Wb + EPS or y > Hb + EPS]
    out0 = {p for p, x, y in pa if x < -EPS or y < -EPS or x > Wa + EPS or y > Ha + EPS}
    new = [p for p in out if p not in out0]       # points the source already had outside stay the source's defect
    if new:
        bad.append("INOUTLINE %d NEW points outside (first %s)" % (len(new), new[0]))
    for (p, x0, y0), (_, x1, y1) in zip(pa, pb):
        if y0 != y1 and Hb == Ha:
            bad.append("y moved without --dy: " + p)
            break
    for fa, fb in zip(a.get("ft_slots") or [], b.get("ft_slots") or []):
        if len(fa.get("regs_um") or []) != len(fb.get("regs_um") or []):
            bad.append("ft %s register count changed" % fa.get("name"))
        if fa.get("in_window_um") != fb.get("in_window_um") or fa.get("out_window_um") != fb.get("out_window_um"):
            bad.append("ft %s window changed" % fa.get("name"))
    if len(a.get("hard_cores") or []) != len(b.get("hard_cores") or []):
        bad.append("core count changed")
    # relative geometry of the cores that moved together is untouched: every core either kept or moved by exactly dx
    dxs = {round(hb["origin_um"][0] - ha["origin_um"][0], 3) for ha, hb in zip(a["hard_cores"], b["hard_cores"])}
    if len(dxs) > cuts + 1:
        bad.append("cores moved by %s (expected {0, dx} per cut, %d cut(s))" % (sorted(dxs), cuts))
    return bad


def _lattice_up(v):
    """smallest multiple of the 4.32 lattice >= v (epsilon-safe)"""
    return round(-(-round(v / LATTICE, 6) // 1) * LATTICE, 4)


def blocked_plan_gaps(t):
    """-> ([(axis, gap, need_gap, lo_rect, hi_rect, bits)], [kit_internal (gap, a, b, bits)]).  A gap is the one
    ADV-MACRO-GAP flags (a sub-9 um facing pair that carries a bus lane); need_gap = bits / (tracks/um x SUPPLY_FRAC), the
    ADV-CHANNEL-WIDTH width.  Only pairs whose BOTH macros are plan hard_cores can be moved by the outline; a pair of macros
    with no plan origin_um is returned as kit_internal (contents macros with an origin_um move like cores)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))      # python3 -I does not put the script dir on sys.path
    import adv_seatgap as SG
    import adv_slot_gap as SL
    inst = {h["inst"] for h in t.get("hard_cores") or []}
    # `contents` macros (lef + absolute origin_um: the C-band memory / eg macro sites) are plan-positioned too: grow_row shifts them
    inst |= {c["inst"] for c in t.get("contents") or [] if isinstance(c, dict) and c.get("origin_um") and c.get("outline_um") and c.get("inst")}
    rects = {r[4]: r for r in SG.G.hard_rects(t)}
    _n, blk = SG.macro_gap(t)
    plan, kit = [], []
    for g, a, b, _run, bits in blk:
        ra, rb = rects.get(a), rects.get(b)
        if a not in inst or b not in inst or ra is None or rb is None:
            kit.append((g, a, b, bits))
            continue
        lo, hi = (ra, rb) if rb[0] >= ra[2] - 1e-6 and rb[0] > ra[0] else (rb, ra)
        gx = hi[0] - lo[2]
        ax = "x" if 0 < gx < SG.GAP_UM + 1e-6 else "y"
        if ax == "y":
            lo, hi = (ra, rb) if rb[1] > ra[1] else (rb, ra)
        need = bits / (SL.tracks_per_um(ax) * SL.RD.SUPPLY_FRAC)
        plan.append((ax, g, need, lo, hi, bits))
    return plan, kit


def raster_bad(v):
    """hub_repack.Raster sizes its lattice with int(W / 4.32) + 1: a lattice-multiple width whose float quotient lands just
    under the integer drops the face column"""
    q = v / 4.32
    return abs(q - round(q)) < 1e-6 and int(q) != round(q)


def widen_row(t):
    """grow the outline so every plan-core gap that carries a bus lane becomes >= its ADV-CHANNEL-WIDTH width: one cut per
    gap (x gaps ascending, then y gaps), every point at or beyond the facing core's edge shifts by the added width
    (grow_row semantics: pin-anchored items stay, E / N face points follow).  -> (row2, [report])"""
    plan, kit = blocked_plan_gaps(t)
    rep = [("kit-internal", g, a, b, bits) for g, a, b, bits in kit]
    t2, off = t, {"x": 0.0, "y": 0.0}
    for ax in ("x", "y"):
        k = 0 if ax == "x" else 1
        cuts = [[p, _lattice_up(max(0.0, p[2] - p[1]))] for p in sorted((p for p in plan if p[0] == ax), key=lambda p: p[4][k])]
        cuts = [c for c in cuts if c[1] > 0]
        while cuts and raster_bad(round(t["outline_um"][k] + sum(c[1] for c in cuts), 4)):
            cuts[-1][1] = round(cuts[-1][1] + LATTICE, 4)  # RASTER guard: step the last cut one lattice pitch wider
        for (_ax, g, need, lo, hi, bits), add in cuts:
            cut = hi[k] + off[ax]
            t2 = grow_row(t2, add, 0.0, None, cut) if ax == "x" else grow_row(t2, 0.0, add, cut, None)
            off[ax] += add
            rep.append((ax, round(g, 2), lo[4], hi[4], bits, round(need, 1), add))
        face = 0.0
        while not cuts and raster_bad(round(t["outline_um"][k] + face, 4)):
            face = round(face + LATTICE, 4)  # an inherited truncating width on an uncut axis: grow the face only (no core moves)
        if face:
            e = t2["outline_um"][k]
            t2 = grow_row(t2, face, 0.0, None, e) if ax == "x" else grow_row(t2, 0.0, face, e, None)
            rep.append((ax, "raster-face", t["outline_um"][k], t2["outline_um"][k], 0, 0.0, face))
    return t2, rep, sum(1 for p in plan if p[0] and _lattice_up(max(0.0, p[2] - p[1])) > 0)


def cmd_widen(a):
    ANY_TYPE[0] = True
    P = json.loads(Path(a.plan).read_text())
    rc, n = 0, 0
    for tn, t in P["partition_types"].items():
        if not re.search(a.types, tn) or not t.get("hard_cores"):
            continue
        g, rep, ncut = widen_row(t)
        if not ncut:
            print("%s nothing to widen%s" % (tn, "".join("; kit-internal %s | %s %.2f um %d bits (not plan-movable)" % (r[2][-34:], r[3][-34:], r[1], r[4]) for r in rep if r[0] == "kit-internal")))
            continue
        bad = check_rows(t, g, tn, cuts=ncut)
        print("%s outline %s -> %s %s" % (tn, t["outline_um"], g["outline_um"], "BAD " + "; ".join(bad) if bad else "ok"))
        for r in rep:
            print("   ", r)
        if bad:
            rc = 1
            continue
        P["partition_types"][tn] = g
        n += 1
    if rc or not n:
        return rc or 2
    if not a.no_retap:
        for tn, (ng, mp) in retap_plan(P, a.plan, [tn for tn in P["partition_types"] if re.search(a.types, tn)]).items():
            print("%s grid taps %d: %d added taps renamed" % (tn, ng, len(mp)))
    Path(a.out).write_text(json.dumps(P, separators=(",", ":")))
    return 0


def cmd_grow(a):
    P = json.loads(Path(a.plan).read_text())
    n = []
    for tn, t in P["partition_types"].items():
        if type_ok(tn) and re.search(a.types, tn) and t.get("hard_cores"):
            FT_MODE[0] = "ft" if a.ft_interior else True
            FT_XCUT[0] = a.ft_xcut
            g = grow_row(t, a.dx, a.dy, a.ycut, a.xcut)
            bad = check_rows(t, g, tn)
            print("%s outline %s -> %s %s" % (tn, t["outline_um"], g["outline_um"], "BAD " + "; ".join(bad) if bad else "ok"))
            if bad:
                return 1
            P["partition_types"][tn] = g
            n.append(tn)
    if not n:
        print("no type matched", file=sys.stderr)
        return 2
    if not a.no_retap:
        for tn, (ng, mp) in retap_plan(P, a.plan, n).items():
            print("%s grid taps %d: %d added taps renamed" % (tn, ng, len(mp)))
    Path(a.out).write_text(json.dumps(P, separators=(",", ":")))
    return 0


def cmd_check(a):
    A = json.loads(Path(a.plan0).read_text())["partition_types"]
    B = json.loads(Path(a.plan1).read_text())["partition_types"]
    rc = 0
    for tn in sorted(B):
        if type_ok(tn) and re.search(a.types, tn) and tn in A:
            bad = check_rows(A[tn], B[tn], tn)
            print(tn, "BAD " + "; ".join(bad) if bad else "ok")
            rc |= bool(bad)
    return rc


def cmd_retap(a):
    """already-grown plan: rename added taps of the matched grid+explicit leaf types to the re-derived grid count"""
    P = json.loads(Path(a.plan).read_text())
    tns = [tn for tn in P["partition_types"] if type_ok(tn) and re.search(a.types, tn)]
    for tn, (ng, mp) in retap_plan(P, a.plan, tns).items():
        print("%s grid taps %d: %d added taps renamed" % (tn, ng, len(mp)))
    Path(a.out).write_text(json.dumps(P, separators=(",", ":")))
    return 0


def cmd_retap_check(a):
    """the bind's own check: taps.grid_explicit_sites refuses wrong added-tap names / order / legality"""
    S = _schema()
    import taps as TP
    raw = S.load(a.plan)
    P = S.Plan(raw, a.plan)
    rc = 0
    for tn in sorted(raw["partition_types"]):
        t = raw["partition_types"][tn]
        if type_ok(tn) and re.search(a.types, tn) and (t.get("clock") or {}).get("tap_mode") == "grid+explicit":
            try:
                TP.grid_explicit_sites(P, tn)
                print(tn, "ok")
            except Exception as e:  # noqa: BLE001 -- report every refusal
                print(tn, "BAD", e)
                rc = 1
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("grow")
    g.add_argument("plan")
    g.add_argument("--types", required=True)
    g.add_argument("--dx", type=float, default=0.0)
    g.add_argument("--dy", type=float, default=0.0)
    g.add_argument("--xcut", type=float, default=None)
    g.add_argument("--ycut", type=float, default=None)
    g.add_argument("--ft-interior", action="store_true",
                   help="in-band ft regs / bit sites (not on a face) with x >= xcut shift with the cores")
    g.add_argument("--ft-xcut", type=float, default=0.0,
                   help="with --ft-interior: in-band ft points with x < this stay (e.g. the street a slot keeps)")
    g.add_argument("--no-retap", action="store_true", help="do not rename grid+explicit added taps after the grow")
    g.add_argument("--any-type", action="store_true", help="any partition type, not only ot_s81sl_(kv_)leaf__*")
    g.add_argument("--out", required=True)
    w = sp.add_parser("widen", help="widen every plan-core gap < 9 um that carries a bus lane to the ADV-CHANNEL-WIDTH width (any type)")
    w.add_argument("plan")
    w.add_argument("--types", required=True)
    w.add_argument("--no-retap", action="store_true")
    w.add_argument("--out", required=True)
    r = sp.add_parser("retap")
    r.add_argument("plan")
    r.add_argument("--types", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--any-type", action="store_true")
    rk = sp.add_parser("retap-check")
    rk.add_argument("plan")
    rk.add_argument("--types", default=".")
    rk.add_argument("--any-type", action="store_true")
    c = sp.add_parser("check")
    c.add_argument("plan0")
    c.add_argument("plan1")
    c.add_argument("--types", default=".")
    c.add_argument("--any-type", action="store_true")
    a = ap.parse_args(argv)
    ANY_TYPE[0] = bool(getattr(a, "any_type", False))
    return {"grow": cmd_grow, "check": cmd_check, "retap": cmd_retap, "retap-check": cmd_retap_check, "widen": cmd_widen}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

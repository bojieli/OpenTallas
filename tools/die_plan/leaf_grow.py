#!/usr/bin/env python3
"""leaf_grow.py -- LEAF-GROW (FP-CONVERGE-S81, COORD ruling 11-25): grow one ot_s81sl_leaf / kv_leaf type row on the W side.

  leaf_grow.py grow PLAN --types REGEX --dx UM [--dy UM --ycut UM] [--xcut UM] --out PLAN2
  leaf_grow.py check PLAN0 PLAN1 --types REGEX     # structural invariants old -> new (exit 1 on a break)
  leaf_grow.py retap PLAN --types REGEX --out PLAN2 # rename grid+explicit added taps for the re-derived grid count
  leaf_grow.py retap-check PLAN --types REGEX       # taps.grid_explicit_sites per type (exit 1 on a refusal)

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


def check_rows(a, b, name=""):
    """-> [problem]: invariants of a grown row b against its source a"""
    bad = []
    Wa, Ha = a["outline_um"]
    Wb, Hb = b["outline_um"]
    if Wb < Wa - EPS or Hb < Ha - EPS:
        bad.append("outline shrank")
    for v, nm in ((Wb, "W"), (Hb, "H")):
        q = v / 4.32
        if abs(q - round(q)) < 1e-6 and int(q) != round(q):
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
    if len(dxs) > 2:
        bad.append("cores moved by %s (expected {0, dx})" % sorted(dxs))
    return bad


def cmd_grow(a):
    P = json.loads(Path(a.plan).read_text())
    n = []
    for tn, t in P["partition_types"].items():
        if LEAF_RE.match(tn) and re.search(a.types, tn) and t.get("hard_cores"):
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
        if LEAF_RE.match(tn) and re.search(a.types, tn) and tn in A:
            bad = check_rows(A[tn], B[tn], tn)
            print(tn, "BAD " + "; ".join(bad) if bad else "ok")
            rc |= bool(bad)
    return rc


def cmd_retap(a):
    """already-grown plan: rename added taps of the matched grid+explicit leaf types to the re-derived grid count"""
    P = json.loads(Path(a.plan).read_text())
    tns = [tn for tn in P["partition_types"] if LEAF_RE.match(tn) and re.search(a.types, tn)]
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
        if LEAF_RE.match(tn) and re.search(a.types, tn) and (t.get("clock") or {}).get("tap_mode") == "grid+explicit":
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
    g.add_argument("--out", required=True)
    r = sp.add_parser("retap")
    r.add_argument("plan")
    r.add_argument("--types", required=True)
    r.add_argument("--out", required=True)
    rk = sp.add_parser("retap-check")
    rk.add_argument("plan")
    rk.add_argument("--types", default=".")
    c = sp.add_parser("check")
    c.add_argument("plan0")
    c.add_argument("plan1")
    c.add_argument("--types", default=".")
    a = ap.parse_args(argv)
    return {"grow": cmd_grow, "check": cmd_check, "retap": cmd_retap, "retap-check": cmd_retap_check}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

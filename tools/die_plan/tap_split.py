#!/usr/bin/env python3
"""tap_split.py: structural clock-tap splitter on the PLAN (die-agnostic).  TAP-GRID-R5 11-21.

COORD lever 6.1 (FABLE-CLOSURE-STRATEGY lever 6 fix 2) and FABLE-CLOSURE-0910 lever 8: every clock tap of a type,
explicit and added ones included, carries at most the type's sink cap (gen_phys._tap_cap = clock.tap_max_sinks) under
the kit's NEAREST-tap split, and every sink is within --radius-um (default 300, Manhattan) of its nearest tap.

Why nearest and not the kit's capacitated split: the plan G0 finding tap_sink_cap (check.tap_sink_loads) counts the
nearest-tap load, and the kit's cap pass (clock_taps.tcl) only re-homes the excess onto a neighbour up to
tap_radius_um further away, which is the insertion spread the hold repair pays for (TAP-GRID-R4 J8: FF hold tracks the
tap insertion spread, r = -0.64).  A tap whose nearest load is under the cap needs no re-homing.

What it changes (append only, so no existing tap name, site, reset relay, landing or inst_taps reference moves):
  tap_mode density / grid+explicit -> clock.added_taps (names continue: clk_t<len(current taps) + i>)
  tap_mode explicit                -> clock.taps (appended after the table; core entries are ignored by the name rule)
Other modes (grid, grid+sinks, bare hard macros) are reported UNSUPPORTED and left alone.

Inputs are G0's: taps = schema.tap_grid(P, tn), sinks = taps.sink_sites(P, tn) (weighted bins / planned sinks
+ control sinks) -- except that a type given a PLACED register inventory (--sinks TYPE=FILE / --sinks-dir DIR) is split
on that inventory instead.  TAP-SOFTFLOP (TAP-GRID-R5 11-22, COORD; FAM-S81-MISC-R4 kv_leaf t5): a type with no
clock.sink_bins_file is modelled from its planned face / ft / core sinks only, so its soft-logic flops are not counted
(t5: planned max load 1,099 vs 63,448 placed registers, clk_t24 ~8,000).  Every report row says its sink_basis
(placed / bins / planned); a planned-only type is flagged SINK-MODEL-PLANNED-ONLY, and --require-placed turns it into
status NO_PLACED (no rows) so a split never rests on the undercount.  A placed file is taps.py bins JSON ({"bins"}),
an odb geometry dump ({"cells"}), a [[x, y(, n)], ...] list, or a .reg dump ("R x y" register centres, "D x0 y0 x1 y1"
die box whose origin is subtracted).  Each new site is legalised by schema.tap_clear(strict) on the PG-safe clock axes (as the density
taps are) and must pass the added-tap validator rules (outline, hard-core / placed macro / keepout halo, spacing to
every tap and early core tap).

Solver: while a tap is over the cap or over the radius, the worst one is split: its nearest-sink set is cut at the
weighted median (both axes) and at the radius; a new tap goes to the weighted median of a part, legalised; the
candidate that lowers the total excess (sum of load over the cap + sink weight beyond the radius) most is kept.  A tap
with no improving candidate is blocked until the geometry changes.  Added taps then relax to the weighted medians of
their nearest sinks while the excess does not rise.

Usage (heavy plans: run through ot-run):
  python3 -I tap_split.py PLAN [--types A,B | --over] [--radius-um 300] [--max-add 200] --rows ROWS.json
                          [--out-plan PLAN2.json] [--tools DIR]
--over: only types with a tap over the cap or the radius.  --out-plan writes PLAN with the rows appended and re-checks
every touched type on the written plan with G0's own functions (schema.tap_grid + taps.sink_sites + taps.tap_loads).
"""
import argparse, json, math, sys
from pathlib import Path

MODES = ("density", "grid+explicit", "explicit")
EPS = 1e-8


def _np():
    import numpy as np
    return np


PLACED = {}          # type -> [(x, y, w)] placed register inventory (TAP-SOFTFLOP); set by main / tests


def load_placed(path):
    """[(x, y, w)] type-frame clocked registers of a placed netlist from one of the formats in the module doc."""
    path = Path(path)
    txt = path.read_text()
    if path.suffix == ".reg" or txt.startswith(("R ", "D ")):
        ox = oy = 0.0
        out = []
        for ln in txt.splitlines():
            f = ln.split()
            if f and f[0] == "D":
                ox, oy = float(f[1]), float(f[2])
            elif f and f[0] == "R":
                out.append((float(f[1]), float(f[2]), 1.0))
        return [(x - ox, y - oy, w) for x, y, w in out]
    d = json.loads(txt)
    if isinstance(d, dict) and "cells" in d:
        import taps as TP
        d = TP.bins_from_dump(d)
    if isinstance(d, dict):
        d = d["bins"]
    return [(float(r[0]), float(r[1]), float(r[2]) if len(r) > 2 else 1.0) for r in d]


def sink_basis(P, tn):
    if tn in PLACED:
        return "placed"
    return "bins" if (P.types[tn].get("clock") or {}).get("sink_bins_file") else "planned"


def type_sinks(P, tn):
    import taps as TP
    return list(PLACED[tn]) if tn in PLACED else TP.sink_sites(P, tn)


def nearest(TX, TY, X, Y):
    """index (ties -> lower tap index, as taps.tap_loads) and L1 distance of every sink's nearest tap."""
    np = _np()
    n = len(X)
    idx = np.empty(n, dtype=np.int64)
    dist = np.empty(n)
    blk = max(1, (1 << 20) // max(1, len(TX)))
    for i in range(0, n, blk):
        D = np.abs(X[i:i + blk, None] - TX[None, :]) + np.abs(Y[i:i + blk, None] - TY[None, :])
        j = D.argmin(axis=1)
        idx[i:i + blk] = j
        dist[i:i + blk] = D[np.arange(len(j)), j]
    return idx, dist


def stats(idx, dist, W, ntaps, radius):
    np = _np()
    load = np.bincount(idx, weights=W, minlength=ntaps)
    far = np.zeros(ntaps)
    np.maximum.at(far, idx, dist)
    beyond = np.bincount(idx, weights=W * (dist > radius + 1e-6), minlength=ntaps)
    return load, far, beyond


def excess(load, beyond, cap):
    np = _np()
    return float(np.maximum(0.0, np.round(load) - cap).sum() + beyond.sum())


def wmedian(v, w):
    np = _np()
    o = np.argsort(v, kind="stable")
    c = np.cumsum(w[o])
    k = int(np.searchsorted(c, 0.5 * c[-1]))
    return float(v[o][min(k, len(o) - 1)])


class Site:
    """legal new-tap sites of one type: schema.tap_clear(strict) on the PG-safe axes, then the added-tap validator."""

    def __init__(self, P, tn, fixed):
        import schema, taps as TP
        self.S, self.TP = schema, TP
        self.t = t = P.types[tn]
        ck = t.get("clock", {}) or {}
        self.w, self.h = map(float, t["outline_um"])
        self.clear = schema.type_tap_clear(t)
        from placement_obstacles import placement_boxes
        c = self.clear
        self.boxes = list(placement_boxes(t, halo=c).values())
        self.boxes += [(a - c, b - c, cc + c, d + c) for a, b, cc, d in ck.get("keepouts_um", [])]
        self.core = [(x, y) for _, x, y, _ in schema.core_taps(P, tn)]
        self.fixed = list(fixed)
        if ck.get("tap_model") == "frozen_anchor":
            self.pin_snap = self.axes = None
        else:
            import gen_phys
            self.axes = gen_phys.clock_legal_axes(P, tn)
            snap = gen_phys._snap_tap
            hard = bool(t.get("hard"))
            memo = {}

            def pin_snap(x, y):
                k = (x, y)
                if k not in memo:
                    memo[k] = snap(P, x, y, pg_legal=not hard)
                return memo[k]
            self.pin_snap = pin_snap

    def ok(self, x, y, taken):
        c, e = self.clear, EPS
        return (c - e <= x <= self.w - c + e and c - e <= y <= self.h - c + e
                and not any(abs(x - a) < c - e and abs(y - b) < c - e for a, b in taken)
                and not any(a + e < x < cc - e and b + e < y < d - e for a, b, cc, d in self.boxes))

    def place(self, x, y, added):
        m = self.TP.TAP_MARGIN_UM
        x = min(max(x, m), self.w - m)
        y = min(max(y, m), self.h - m)
        taken = self.core + self.fixed + list(added)
        try:
            x, y = self.S.tap_clear(self.t, x, y, taken, strict=True, pin_snap=self.pin_snap, legal_axes=self.axes)
        except Exception:
            return None
        x, y = round(x, 4), round(y, 4)
        return (x, y) if self.ok(x, y, taken) else None


def split_type(P, tn, radius, max_add, cap=None, require_placed=False):
    import schema, taps as TP, gen_phys
    np = _np()
    t = P.types[tn]
    ck = t.get("clock", {}) or {}
    mode = ck.get("tap_mode", "grid")
    rep = dict(type=tn, mode=mode)
    if mode not in MODES or schema.bare_hard_single_tap(t) or ck.get("child_root_taps") is not None:
        rep["status"] = "UNSUPPORTED"      # no table to append to; not counted (grid+sinks taps cost minutes to solve)
        return rep, []
    tp = schema.tap_grid(P, tn)
    rep["sink_basis"] = basis = sink_basis(P, tn)
    if basis == "planned":
        rep["why"] = "SINK-MODEL-PLANNED-ONLY (no sink_bins_file, no --sinks): soft-logic flops not counted"
        if require_placed:
            rep["status"] = "NO_PLACED"
            return rep, []
    sinks = type_sinks(P, tn)
    cap = int(min(cap, gen_phys._tap_cap(t)) if cap else gen_phys._tap_cap(t))   # --cap only tightens the plan cap
    rep["cap"], rep["radius_um"], rep["taps_before"] = cap, radius, len(tp)
    if not sinks:
        rep["status"] = "NO_SINKS"
        return rep, []
    S_ = np.array(sinks, dtype=float)
    X, Y, W = S_[:, 0], S_[:, 1], S_[:, 2]
    TX = np.array([p[1] for p in tp], dtype=float)
    TY = np.array([p[2] for p in tp], dtype=float)
    idx, dist = nearest(TX, TY, X, Y)
    load, far, beyond = stats(idx, dist, W, len(tp), radius)
    rep["before"] = dict(max_load=int(round(load.max())), over_cap=int((np.round(load) > cap).sum()),
                         max_radius=round(float(far.max()), 3), over_radius=int((far > radius + 1e-6).sum()),
                         excess=excess(load, beyond, cap))
    if rep["before"]["excess"] <= 0:
        rep["status"] = "OK"
        return rep, []
    site = Site(P, tn, [(p[1], p[2]) for p in tp])
    added = []
    n0 = len(tp)

    def full(ax, ay):
        tx = np.concatenate([TX, np.array(ax, dtype=float)]) if ax else TX
        ty = np.concatenate([TY, np.array(ay, dtype=float)]) if ay else TY
        return nearest(tx, ty, X, Y)

    blocked = set()
    while len(added) < max_add:
        nt = n0 + len(added)
        load, far, beyond = stats(idx, dist, W, nt, radius)
        before = excess(load, beyond, cap)
        if before <= 0:
            break
        score = np.maximum(np.round(load) / cap, far / radius)
        order = [int(k) for k in np.argsort(-score, kind="stable") if score[k] > 1.0 + 1e-9 and int(k) not in blocked]
        if not order:
            break
        k = order[0]
        mem = np.nonzero(idx == k)[0]
        kx = TX[k] if k < n0 else added[k - n0][0]
        ky = TY[k] if k < n0 else added[k - n0][1]
        parts = []
        if far[k] > radius + 1e-6:
            parts.append(mem[dist[mem] > radius + 1e-6])
        mx, my = X[mem], Y[mem]
        first = 0 if (mx.max() - mx.min()) >= (my.max() - my.min()) else 1
        for ax in (first, 1 - first):
            v = mx if ax == 0 else my
            cut = wmedian(v, W[mem])
            lo, hi = mem[v <= cut], mem[v > cut]
            if len(lo) == 0 or len(hi) == 0:
                cut = 0.5 * (v.max() + v.min())
                lo, hi = mem[v <= cut], mem[v > cut]
            if len(lo) and len(hi):
                own = kx if ax == 0 else ky
                far_hi = abs(own - (v.max())) >= abs(own - v.min())
                parts += [hi, lo] if far_hi else [lo, hi]
        cands = []
        for part in parts:
            if len(part) == 0 or len(part) == len(mem) and far[k] <= radius:
                continue
            cands.append((wmedian(X[part], W[part]), wmedian(Y[part], W[part])))
        # sliding quantile sites along both axes: a dense line or a few heavy bins (coll_ft station columns, cb ring
        # bins of ~220 sinks) need an uneven cut, the half medians alone over-load the new tap
        for ax in (first, 1 - first):
            v = mx if ax == 0 else my
            u = my if ax == 0 else mx
            o = np.argsort(v, kind="stable")
            c = np.cumsum(W[mem][o])
            for q in (0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9):
                j = o[min(int(np.searchsorted(c, q * c[-1])), len(o) - 1)]
                sl = np.abs(v - v[j]) <= 0.25 * max(1e-9, v.max() - v.min()) + 1e-9
                uu = wmedian(u[sl], W[mem][sl])
                cands.append((float(v[j]), uu) if ax == 0 else (uu, float(v[j])))
        best = None
        seen = set()
        for cx, cy in cands:
            s = site.place(cx, cy, added)
            if s is None or s in added or s in seen:
                continue
            seen.add(s)
            dn = np.abs(X - s[0]) + np.abs(Y - s[1])
            ch = dn < dist
            if not ch.any():
                continue
            i2 = np.where(ch, nt, idx)
            d2 = np.where(ch, dn, dist)
            l2, _f2, b2 = stats(i2, d2, W, nt + 1, radius)
            e2 = excess(l2, b2, cap)
            if e2 < before - 1e-9 and (best is None or e2 < best[0]):
                best = (e2, s, i2, d2)
        if best is None:
            blocked.add(k)
            continue
        added.append(best[1])
        idx, dist = best[2], best[3]
        blocked.clear()
    # relax added taps to the weighted medians of their nearest sinks while the excess does not rise
    for _ in range(3):
        moved = False
        for j in range(len(added)):
            nt = n0 + len(added)
            load, far, beyond = stats(idx, dist, W, nt, radius)
            e0 = excess(load, beyond, cap)
            mem = np.nonzero(idx == n0 + j)[0]
            if len(mem) == 0:
                continue
            others = added[:j] + added[j + 1:]
            s = site.place(wmedian(X[mem], W[mem]), wmedian(Y[mem], W[mem]), others)
            if s is None or s == added[j] or s in others:
                continue
            trial = added[:j] + [s] + added[j + 1:]
            i2, d2 = full([a for a, _ in trial], [b for _, b in trial])
            l2, _f2, b2 = stats(i2, d2, W, nt, radius)
            if excess(l2, b2, cap) <= e0 and (l2[n0:] > 0).all():
                added, idx, dist, moved = trial, i2, d2, True
        if not moved:
            break
    # drop added taps left without sinks (an empty tap is a TAP-LIMIT finding); recompute
    if added:
        load, _, _ = stats(idx, dist, W, n0 + len(added), radius)
        added = [a for j, a in enumerate(added) if load[n0 + j] > 0]
        idx, dist = full([a for a, _ in added], [b for _, b in added])
    nt = n0 + len(added)
    load, far, beyond = stats(idx, dist, W, nt, radius)
    rep["after"] = dict(max_load=int(round(load.max())), over_cap=int((np.round(load) > cap).sum()),
                        max_radius=round(float(far.max()), 3), over_radius=int((far > radius + 1e-6).sum()),
                        excess=excess(load, beyond, cap), added=len(added),
                        min_added_load=int(round(load[n0:].min())) if added else None)
    rep["status"] = "SPLIT" if rep["after"]["excess"] <= 0 else ("PARTIAL" if added else "BLOCKED")
    if rep["status"] != "SPLIT":
        rep["residual"] = [dict(tap=(tp[k][0] if k < n0 else f"clk_t{k}"), load=int(round(load[k])),
                                radius=round(float(far[k]), 3))
                           for k in range(nt) if round(load[k]) > cap or far[k] > radius + 1e-6][:40]
    key = "taps" if mode == "explicit" else "added_taps"
    rows = [{"name": f"clk_t{n0 + i}", "xy": [round(x, 3), round(y, 3)]} for i, (x, y) in enumerate(added)]
    rep["key"] = key
    return rep, rows


def apply_rows(raw, rows_by_type):
    for tn, (key, rows) in rows_by_type.items():
        ck = raw["partition_types"][tn].setdefault("clock", {})
        ck.setdefault(key, [])
        ck[key] = list(ck[key]) + rows


def recheck(P, types, radius, cap_max=None):
    """G0's own count (check.tap_sink_loads rule) on the written plan."""
    import schema, taps as TP, gen_phys
    out = {}
    for tn in types:
        tp = schema.tap_grid(P, tn)
        loads = TP.tap_loads([(x, y) for _, x, y in tp], type_sinks(P, tn))
        cap = gen_phys._tap_cap(P.types[tn])
        cap = min(cap, cap_max) if cap_max else cap
        out[tn] = dict(taps=len(tp), sink_basis=sink_basis(P, tn), max_load=int(round(max(n for n, _ in loads))),
                       over_cap=sum(1 for n, _ in loads if round(n) > cap),
                       max_radius=round(max(f for _, f in loads), 3),
                       over_radius=sum(1 for _, f in loads if f > radius + 1e-6))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--types", default="")
    ap.add_argument("--over", action="store_true", help="all types with a tap over the cap or radius (default: all)")
    ap.add_argument("--radius-um", type=float, default=300.0)
    ap.add_argument("--max-add", type=int, default=200)
    ap.add_argument("--cap", type=int, default=0, help="split to min(plan cap, CAP) sinks/tap (Fable lever 8: 1650); default = plan cap")
    ap.add_argument("--sinks", action="append", default=[], metavar="TYPE=FILE",
                    help="placed register inventory of TYPE (TAP-SOFTFLOP): .reg / bins JSON / geometry dump / [[x,y]] list")
    ap.add_argument("--sinks-dir", help="DIR/<type>.reg or DIR/<type>.json for every type that has one")
    ap.add_argument("--require-placed", action="store_true",
                    help="a type without sink_bins_file or placed sinks is NO_PLACED (no rows) instead of split on planned sinks")
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out-plan")
    ap.add_argument("--tools", help="tools/die_plan of the tree to plan with (default: next to this file)")
    a = ap.parse_args(argv)
    if a.radius_um <= 0 or a.radius_um > 300:
        ap.error("--radius-um must be in (0, 300] (COORD: tap sink radius <= 300 um)")
    sys.path.insert(0, str(Path(a.tools).resolve() if a.tools else Path(__file__).resolve().parent))
    import schema as S
    import taps as TP
    raw = json.loads(Path(a.plan).read_text())
    TP.PLAN_DIR = str(Path(a.plan).resolve().parent)
    P = S.Plan(raw, a.plan)
    types = [x for x in a.types.split(",") if x] or sorted(P.types)
    PLACED.clear()
    for kv in a.sinks:
        tn, f = kv.split("=", 1)
        PLACED[tn] = load_placed(f)
    if a.sinks_dir:
        for tn in types:
            for ext in (".reg", ".json"):
                f = Path(a.sinks_dir) / f"{tn}{ext}"
                if tn not in PLACED and f.is_file():
                    PLACED[tn] = load_placed(f)
    reps, rows_by_type = [], {}
    for tn in types:
        try:
            rep, rows = split_type(P, tn, a.radius_um, a.max_add, cap=a.cap or None, require_placed=a.require_placed)
        except Exception as ex:
            rep, rows = dict(type=tn, status="ERROR", why=f"{type(ex).__name__}: {str(ex)[:200]}"), []
        if rows:
            rows_by_type[tn] = (rep["key"], rows)
        reps.append(rep)
        b, f = rep.get("before", {}), rep.get("after", {})
        print(f"TAP_SPLIT {tn} {rep['status']} [{rep.get('sink_basis', '?')}]: taps {rep.get('taps_before')} +{len(rows)}; max load "
              f"{b.get('max_load')}->{f.get('max_load', b.get('max_load'))}/{rep.get('cap')}, over cap {b.get('over_cap')}->"
              f"{f.get('over_cap', b.get('over_cap'))}, max radius {b.get('max_radius')}->{f.get('max_radius', b.get('max_radius'))}"
              f"{' ' + rep['why'] if rep.get('why') else ''}", flush=True)
    out = dict(tool="tap_split.py", plan=str(a.plan), radius_um=a.radius_um, cap=a.cap or None,
               rows={tn: {"key": k, "rows": r} for tn, (k, r) in rows_by_type.items()}, report=reps)
    if a.out_plan:
        apply_rows(raw, rows_by_type)
        Path(a.out_plan).write_text(json.dumps(raw, indent=1, sort_keys=False) + "\n")
        P2 = S.Plan(json.loads(Path(a.out_plan).read_text()), a.out_plan)
        out["recheck"] = recheck(P2, sorted(rows_by_type), a.radius_um, a.cap or None)
        bad = {k: v for k, v in out["recheck"].items() if v["over_cap"] or v["over_radius"]}
        print(f"TAP_SPLIT RECHECK {len(out['recheck'])} types on {a.out_plan}: {len(bad)} still over cap/radius", flush=True)
    Path(a.rows).write_text(json.dumps(out, indent=1) + "\n")
    tot = {s: sum(1 for r in reps if r.get("status") == s) for s in ("OK", "SPLIT", "PARTIAL", "BLOCKED", "UNSUPPORTED", "ERROR", "NO_SINKS", "NO_PLACED")}
    print("TAP_SPLIT SUMMARY " + " ".join(f"{k}={v}" for k, v in tot.items()) +
          f"; taps added {sum(len(r) for _, r in rows_by_type.values())}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

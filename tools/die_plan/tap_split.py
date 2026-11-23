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

SINK-EST (TAP-GRID-R5 11-23, COORD class item: QC q00 plan 976 vs CTS 1,531 on clk_t60, cbx_q10 ~955 vs 3,265 placed).
Cause: the planned basis (taps.sink_sites without clock.sink_bins_file) is the face / ft / station / control registers
only; the soft-logic flops (datapath pipelines, FIFOs, FSMs, banks) are not in the plan at all, and a sink_bins_file
from an older netlist can lag the placed one (KV pv_v4 126k vs 200k).  Calibration vs the kit's per-tap CTS load (PRECHECK
cache placed per-tap max) on types whose plan tap count is within 10 % of the kit's: S81 J9 v2 (33 types, 8 families)
planned max x3.44 median (p90 5.34) under CTS, placed registers on the plan taps (nearest tap) 0.89 x it (p90 1.12);
KV D29 r5 (17 types, 16 families) placed-nearest 0.52 x CTS median (p90 0.93; max 1.65 kv3_hg_v3), planned/bins up to x11
under (hub_Eo 1,148 vs 12,903).  Placed regs = 1.52 x netlist flops (median of 398 kits: ICG / latch / split multibit).
So every type without a --sinks file or sink_bins_file
now takes, in order: (1) the shared PRECHECK flops cache placed_bins of its exact type, else of its base type
(__cl / __pv / _h suffix stripped) with the same outline (+-2 um) -> basis "cache"; (2) else, with a netlist flop count
in the cache, the planned sinks plus the residual REG_PER_FLOP x flops - planned spread uniformly over the outline on a
20 um grid -> basis "planned+flops"; (3) else planned (SINK-MODEL-PLANNED-ONLY as before).  --flops-cache PATH
(default $OT_FLOPS_CACHE, else the PRECHECK cache path when it exists); --flops-cache none = the old behaviour.

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

MULTI-TAP (TAP-GRID-R5 11-23, COORD): a tap over the cap that serves a DENSE sink cluster cannot be split one tap at a
time -- by nearest-tap assignment any single new tap next to the cluster takes nearly all of it (S81 leaf t47 clk_t29:
2759 sinks in a 98x28 um box, every one-tap add left a new tap of 3073-3160), so the greedy loop found no improving
candidate and stopped with free legal sites all around (257 of the 261 J9 residual over-cap taps).  When no single tap
improves, the splitter now adds k = ceil(load / (cap * 0.9)) taps together: weighted k-medians (L1, the metric of the
assignment) on that tap's sink coordinates, each centre legalised to the nearest legal site (Site.place, same rules
as a single add), all sinks re-assigned, and the group kept when the excess drops (k, k+1, k+2 tried).
--multi-margin sets the 0.9; --multi-margin 0 turns the mode off.
NEIGHBOURHOOD (TAP-GRID-R5 11-23, S81 J9 residual 36): an over-cap tap whose sinks are a thin strip inside a dense
region shared with its neighbours (col_h9_r0_p3 clk_t46: 1719 sinks in an 11 x 101 um strip; lepe_mu_C clk_t48) cannot be
split from its own sinks: the k-medians centre nearest the neighbour pulls thousands of the neighbour's sinks (new tap
4188-5418).  When the own-sink group does not help, the splitter re-solves the region: sinks of the tap and its
--multi-nbhd nearest taps (default 8), the existing taps FIXED as centres, kf free centres (kf = ceil(region load /
(cap * margin)) - fixed, at least 1, +3 tried) by constrained weighted k-medians (assign to all, move only the free
ones), each legalised, all sinks re-assigned, kept when the excess drops.

TAPOFF (TAP-GRID-R5 11-23, COORD class ruling): a type with a plan clock.tap_offset.per_port_ps row gets a row for every
appended / fresh tap in the same step (tap_offset_fill.fill: the nearest listed tap's row): written into --out-plan and
listed in the rows JSON as "tap_offset" {type: {port: row}} for row scripts that apply the taps themselves.

FRESH (TAP-GRID-R5 11-23, rc66 SPARSE-TAP-1 serdes): --fresh TYPES rebuilds the WHOLE tap table of those types from their
sinks instead of appending (serdes__t2: a uniform grid over 2886 x 1227 vs a sink median at (1550, 255), 8 taps over
cap, 7 under 30 sinks, 37 % of sinks > 200 um from a tap).  k = ceil(load / (cap x margin)) weighted L1 k-medians,
legalised; then while a tap is over cap or radius its group is split by 2-medians (far part own centre); taps
under --fresh-min-sinks are dropped and their sinks re-assigned; centres relaxed to their group medians.  Written as
clock.tap_mode explicit, clock.taps = [clk, clk_t1, ...], clock.added_taps removed (row key "replace_taps"); the
landing references are re-anchored by the REMAP-ALWAYS pass like any row.  No tap over empty area: every kept tap
serves >= min sinks.

PROTECT-RINGS (TAP-GRID-R5 11-23, rc117 KV kv3_sys_c): a landing ring copies the raw reset of the tap NEAREST its
receive window (clock_landings: bus face / window_um midpoint, ft_slot in_face / in_window_um, landing_contract pin
fclk_in_<bus>) and the plan's
landing_raw_branches name that original node; an added tap nearer a window renames it (sys_c D29: the bind took
rst_n_t71, the plan names rst_n_t31 -> EMIT 'origin reset phase/equation differs').  --protect-rings: a new tap site
is illegal when it is strictly nearer (L1) any receive window than that window's nearest existing tap.  An optional
REGEX limits it to the named rings (sys_c: only fclk_in_ft1_i feeds the 'origin' raw-branch role; protecting all 23
rings left 3 taps over cap).

GLOBAL (TAP-GRID-R5 11-23, FABLE-RC-S81 rc32 / rc7): the greedy, MULTI-TAP and NEIGHBOURHOOD passes only add taps and
never move an added tap once later taps exist, so a type can stall in a local optimum (dry run 3: 22 leaf + 3 slice C
types over cap).  --global-rounds R (default 0 = off): after the relax step, every round takes the over-cap taps plus
their --multi-nbhd nearest taps as one region; the plan taps there stay FIXED, every ADDED tap there is MOVABLE, and
ceil(load / (cap x margin)) - 1 extra seeds go into each over-cap tap (k-medians of its sinks).  Weighted L1 k-medians
over the region's sinks (fixed + free centres), legalise the free ones, re-assign every sink; kept only when the
cap / radius excess drops.  Plan taps never move (FIXCHK prefix rule).

SPAN (TAP-GRID-R5 11-23, FABLE-RC-S81 RC-GAP 3/3): --span-um S bounds each tap's sink box (W + H of the bounding box of
the sinks it serves, the kit's OT_TAP_SPAN rule; the L1 radius alone allows up to 4x radius).  After the cap / radius
split, a tap with span > S is split by k-medians seeded farthest-point (one far flop gets its own centre: col_h9_r2
clk_t13, 184 sinks, span 514 um, the far flop padded all 184 to 606 ps), k = 2..4, legalised, all sinks re-assigned, kept
when the summed span excess (um) drops and the cap / radius excess does not rise.  A type is SPLIT only with no tap over
the span either.

REMAP-ALWAYS (TAP-GRID-R5 11-23, COORD: third tap row in one night that broke its reset anchors -- S81 J8, HEAD Row B,
KV D29 14 EMIT): new taps renumber the reset tree, so every --out-plan run ALWAYS follows the rows with
landing_remap.remap_plan(resets="anchor", --bound-rtl when given) over every touched type, then plan_gate_pre's own
check_landremap against the input plan.  A type the remap refuses (RemapError) or whose landing reset references stay
stale (any FAIL LANDREMAP*) is restored to the input plan, its rows are dropped, its report status is REMAP_FAIL, and
the run exits 3.  The rows file then holds only rows whose written plan has no stale landing reference.
"""
import argparse, json, math, sys
from pathlib import Path

MODES = ("density", "grid+explicit", "explicit")
EPS = 1e-8


def _np():
    import numpy as np
    return np


PLACED = {}          # type -> [(x, y, w)] placed register inventory (TAP-SOFTFLOP); set by main / tests
BASIS = {}           # type -> sink basis label of a PLACED entry that did not come from a --sinks file (SINK-EST)
FLOPS_CACHE_DEFAULT = "/srv/opentallas-scratch2/claude/precheck-cache/flops_cache.json"
STALE_BINS = 1.2     # SINK-EST: KV pv_v4 sink_bins_file 126k sinks vs 200k placed registers (plan max 1,699 vs CTS 10,042)
REG_PER_FLOP = 1.52  # SINK-EST: median placed clock sinks per netlist flop over 398 kits (p10 1.07, p90 2.99)
FILL_UM = 20.0


def _base_names(tn):
    import re
    out, cur = [tn], tn
    for pat in (r"_h$", r"__pv[0-9a-f]+$", r"__cl[0-9a-f]+$"):
        nxt = re.sub(pat, "", cur)
        if nxt != cur:
            out.append(nxt)
            cur = nxt
    return out


def estimate_sinks(P, tn, cache, planned=None):
    """SINK-EST: ([(x, y, w)], basis) for a type without a placed file / sink_bins_file (see the module doc), or (None, None)."""
    t = P.types[tn]
    W_, H_ = (float(v) for v in t["outline_um"][:2])
    bins = cache.get("placed_bins") or {}
    for n in _base_names(tn):
        b = bins.get(n)
        if b and b.get("die_um") and abs(float(b["die_um"][0]) - W_) <= 2.0 and abs(float(b["die_um"][1]) - H_) <= 2.0:
            return [(float(r[0]), float(r[1]), float(r[2])) for r in b["bins"]], "cache" if n == tn else f"cache:{n}"
    FL = cache.get("flops") or {}
    fl = next((FL[n]["flops"] for n in _base_names(tn) if (FL.get(n) or {}).get("flops")), None)
    if not fl:
        return None, None
    if planned is None:
        import taps as TP
        planned = TP.sink_sites(P, tn)
    rest = REG_PER_FLOP * fl - sum(w for *_, w in planned)
    if rest <= 0:
        return None, None
    nx, ny = max(1, int(W_ // FILL_UM)), max(1, int(H_ // FILL_UM))
    w = rest / (nx * ny)
    return list(planned) + [((i + 0.5) * W_ / nx, (j + 0.5) * H_ / ny, w) for i in range(nx) for j in range(ny)], "planned+flops"


def load_cache(path):
    import os
    if path is None:
        path = os.environ.get("OT_FLOPS_CACHE") or (FLOPS_CACHE_DEFAULT if Path(FLOPS_CACHE_DEFAULT).is_file() else None)
    if not path or path == "none":
        return {}
    return json.loads(Path(path).read_text())


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
        return BASIS.get(tn, "placed")
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
        self.protect = []
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

    def protect_rings(self, pat=".*"):
        """PROTECT-RINGS: [(x, y, d)] receive-window points (bus / ft_slot / fclk_in_ pin name matching `pat`) and the L1
        distance to their nearest existing tap."""
        import re
        rx = re.compile(pat)
        pts = []
        for b in self.t.get("buses", []) or []:
            if "face" in b and "window_um" in b and rx.search(f"fclk_in_{b.get('name', '')}"):
                pts.append((b["face"], sum(b["window_um"]) / 2))
        for sl in self.t.get("ft_slots", []) or []:
            if "in_face" in sl and "in_window_um" in sl and rx.search(f"fclk_in_{sl.get('name', '')}_i"):
                pts.append((sl["in_face"], sum(sl["in_window_um"]) / 2))
        ex = self.fixed + self.core
        xy = [(0.0 if face == "W" else self.w, at) if face in "EW" else (at, 0.0 if face == "S" else self.h)
              for face, at in pts]
        # the ring receive pins themselves (clock.landing_contract.pins fclk_in_<bus>): KV buses carry no face /
        # window, the bind takes them from the collector sidecar; the pin sits on that window
        lc = (self.t.get("clock") or {}).get("landing_contract") or {}
        xy += [tuple(map(float, q["xy_um"])) for q in lc.get("pins") or []
               if q.get("dir") == "in" and q.get("kind") == "clock" and str(q.get("name", "")).startswith("fclk_in_")
               and rx.search(str(q["name"]))
               and isinstance(q.get("xy_um"), list) and len(q["xy_um"]) == 2]
        for x, y in xy:
            if ex:
                self.protect.append((x, y, min(abs(x - a) + abs(y - b) for a, b in ex)))
        return len(self.protect)

    def ok(self, x, y, taken):
        c, e = self.clear, EPS
        if any(abs(x - px) + abs(y - py) < d - e for px, py, d in self.protect):
            return False
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


def kmedians(X, Y, W, k, iters=25):
    """weighted k-medians (L1) of points (X, Y, W); seeds = weighted quantiles along the longer axis.  -> [(x, y)]."""
    np = _np()
    if k <= 1 or len(X) <= 1:
        return [(wmedian(X, W), wmedian(Y, W))]
    k = min(k, len(X))
    ax, ou = (X, Y) if (X.max() - X.min()) >= (Y.max() - Y.min()) else (Y, X)
    o = np.argsort(ax, kind="stable")
    c = np.cumsum(W[o])
    C = []
    for q in ((i + 0.5) / k for i in range(k)):
        j = o[min(int(np.searchsorted(c, q * c[-1])), len(o) - 1)]
        C.append((float(X[j]), float(Y[j])))
    C = np.array(C, dtype=float)
    lab = None
    for _ in range(iters):
        D = np.abs(X[:, None] - C[None, :, 0]) + np.abs(Y[:, None] - C[None, :, 1])
        nl = D.argmin(axis=1)
        if lab is not None and (nl == lab).all():
            break
        lab = nl
        for j in range(len(C)):
            m = lab == j
            if m.any():
                C[j] = (wmedian(X[m], W[m]), wmedian(Y[m], W[m]))
    return [(float(a), float(b)) for a, b in C]


def fixed_kmedians(X, Y, W, fixed, seeds, iters=30):
    """weighted L1 k-medians with FIXED centres: points go to the nearest of fixed + free centres, only the free ones
    move to the weighted median of their points.  -> [(x, y)] free centres (a free centre left without points stays)."""
    np = _np()
    F = np.array(fixed, dtype=float).reshape(-1, 2)
    C = np.array(seeds, dtype=float).reshape(-1, 2)
    nf, lab = len(F), None
    for _ in range(iters):
        A = np.vstack([F, C])
        D = np.abs(X[:, None] - A[None, :, 0]) + np.abs(Y[:, None] - A[None, :, 1])
        nl = D.argmin(axis=1)
        if lab is not None and (nl == lab).all():
            break
        lab = nl
        for j in range(len(C)):
            m = lab == nf + j
            if m.any():
                C[j] = (wmedian(X[m], W[m]), wmedian(Y[m], W[m]))
    return [(float(a), float(b)) for a, b in C]


def nbhd_add(site, added, k, idx, TA, X, Y, W, load, cap, margin, before, full, radius, n0, nbhd=8, tries=4):
    """NEIGHBOURHOOD: re-solve tap k and its `nbhd` nearest taps with the existing taps fixed; -> best or None."""
    import math
    np = _np()
    if margin <= 0 or nbhd <= 0:
        return None
    d = np.abs(TA[:, 0] - TA[k, 0]) + np.abs(TA[:, 1] - TA[k, 1])
    nb = [int(j) for j in np.argsort(d, kind="stable")[:nbhd + 1]]
    reg = np.nonzero(np.isin(idx, nb))[0]
    if len(reg) < 2:
        return None
    rl = float(W[reg].sum())
    need = max(1, int(math.ceil(rl / (cap * margin))) - len(nb))
    mem = np.nonzero(idx == k)[0]
    best = None
    for kf in range(need, need + tries):
        seeds = kmedians(X[mem], Y[mem], W[mem], kf) if kf > 1 else [(wmedian(X[mem], W[mem]), wmedian(Y[mem], W[mem]))]
        C = fixed_kmedians(X[reg], Y[reg], W[reg], TA[nb], seeds)
        new = []
        for cx, cy in C:
            s_ = site.place(cx, cy, added + new)
            if s_ is not None and s_ not in added and s_ not in new:
                new.append(s_)
        if not new:
            continue
        tr = added + new
        i2, d2 = full([a for a, _ in tr], [b for _, b in tr])
        l2, _f2, b2 = stats(i2, d2, W, n0 + len(tr), radius)
        e2 = excess(l2, b2, cap)
        if e2 < before - 1e-9 and (best is None or e2 < best[0]):
            best = (e2, new, i2, d2)
        if best is not None and best[0] <= 0:
            break
    return best


def multi_add(site, added, mem, X, Y, W, load_k, cap, margin, before, full, radius, n0, tries=3):
    """MULTI-TAP: k = ceil(load_k / (cap * margin)) taps at the k-medians of the tap's sinks, legalised one by one,
    all sinks re-assigned; -> (excess, new sites, idx, dist) of the best k that lowers the excess, else None."""
    import math
    np = _np()
    if margin <= 0 or len(mem) < 2:
        return None
    k0 = max(2, int(math.ceil(load_k / (cap * margin))))
    best = None
    for k in range(k0, k0 + tries):
        new = []
        for cx, cy in kmedians(X[mem], Y[mem], W[mem], k):
            s_ = site.place(cx, cy, added + new)
            if s_ is not None and s_ not in added and s_ not in new:
                new.append(s_)
        if len(new) < 2:
            continue
        tr = added + new
        i2, d2 = full([a for a, _ in tr], [b for _, b in tr])
        l2, _f2, b2 = stats(i2, d2, W, n0 + len(tr), radius)
        e2 = excess(l2, b2, cap)
        if e2 < before - 1e-9 and (best is None or e2 < best[0]):
            best = (e2, new, i2, d2)
        if best is not None and best[0] <= 0:
            break
    return best


def global_pass(site, added, idx, dist, X, Y, W, TX, TY, cap, margin, radius, n0, full, max_add, rep, rounds=2, nbhd=8):
    """GLOBAL: re-solve each over-cap region with all added taps there movable; -> (added, idx, dist)."""
    import math
    np = _np()
    if margin <= 0:
        return added, idx, dist
    for _ in range(rounds):
        nt = n0 + len(added)
        load, _far, beyond = stats(idx, dist, W, nt, radius)
        e0 = excess(load, beyond, cap)
        over = [int(k) for k in np.nonzero(np.round(load) > cap)[0]]
        if e0 <= 0 or not over:
            break
        TA = np.column_stack([np.concatenate([TX, np.array([a for a, _ in added], dtype=float)]),
                              np.concatenate([TY, np.array([b for _, b in added], dtype=float)])])
        nb = set()
        for k in over:
            d = np.abs(TA[:, 0] - TA[k, 0]) + np.abs(TA[:, 1] - TA[k, 1])
            nb.update(int(j) for j in np.argsort(d, kind="stable")[:nbhd + 1])
        nb = sorted(nb)
        fixed = [j for j in nb if j < n0]
        free = [j for j in nb if j >= n0]
        seeds = [tuple(TA[j]) for j in free]
        for k in over:
            kk = int(math.ceil(float(load[k]) / (cap * margin)))
            if kk <= 1:
                continue
            mem = np.nonzero(idx == k)[0]
            C = kmedians(X[mem], Y[mem], W[mem], kk)
            C.sort(key=lambda c: abs(c[0] - TA[k, 0]) + abs(c[1] - TA[k, 1]))
            seeds += C[1:]                         # the centre nearest the tap stays with the tap itself
        keep = [added[j - n0] for j in range(n0, nt) if j not in set(free)]
        if len(keep) + len(seeds) > max_add:
            seeds = seeds[:max(0, max_add - len(keep))]
        if not seeds:
            break
        reg = np.nonzero(np.isin(idx, nb))[0]
        C = fixed_kmedians(X[reg], Y[reg], W[reg], TA[fixed] if fixed else np.zeros((0, 2)), seeds)
        new = []
        for cx, cy in C:
            s_ = site.place(float(cx), float(cy), keep + new)
            if s_ is not None and s_ not in keep and s_ not in new:
                new.append(s_)
        tr = keep + new
        i2, d2 = full([a for a, _ in tr], [b for _, b in tr])
        l2, _f2, b2 = stats(i2, d2, W, n0 + len(tr), radius)
        e2 = excess(l2, b2, cap)
        if e2 >= e0 - 1e-9:
            break
        added, idx, dist = tr, i2, d2
        rep["global"] = rep.get("global", 0) + 1
    return added, idx, dist


def fresh_type(P, tn, radius, cap=None, margin=0.9, min_sinks=30, max_taps=400, require_placed=False):
    """FRESH: a new explicit tap table for type tn from its sinks; -> (rep, rows) with rep["key"] = "replace_taps"."""
    import math
    import gen_phys
    import schema
    np = _np()
    t = P.types[tn]
    cap = min(gen_phys._tap_cap(t), cap) if cap else gen_phys._tap_cap(t)
    rep = dict(type=tn, mode="fresh", cap=cap, radius_um=radius, sink_basis=sink_basis(P, tn), min_sinks=min_sinks)
    if require_placed and not rep["sink_basis"].startswith(("placed", "cache")):
        rep["status"] = "NO_PLACED"
        return rep, []
    sinks = type_sinks(P, tn)
    if not sinks:
        rep["status"] = "NO_SINKS"
        return rep, []
    S_ = np.array(sinks, dtype=float)
    X, Y, W = S_[:, 0], S_[:, 1], S_[:, 2]
    tp = schema.tap_grid(P, tn)
    rep["taps_before"] = len(tp)
    if tp:
        i0, d0 = nearest(np.array([q[1] for q in tp], float), np.array([q[2] for q in tp], float), X, Y)
        l0, f0, b0 = stats(i0, d0, W, len(tp), radius)
        rep["before"] = dict(max_load=int(round(l0.max())), over_cap=int((np.round(l0) > cap).sum()),
                             under_min=int((l0 < min_sinks).sum()), max_radius=round(float(f0.max()), 3),
                             over_radius=int((f0 > radius + 1e-6).sum()), excess=excess(l0, b0, cap))
    site = Site(P, tn, [])

    def legal(C):
        out = []
        for cx, cy in C:
            s_ = site.place(float(cx), float(cy), out)
            if s_ is not None and s_ not in out:
                out.append(s_)
        return out

    def assign(C):
        return nearest(np.array([a for a, _ in C], float), np.array([b for _, b in C], float), X, Y)

    k0 = max(1, int(math.ceil(float(W.sum()) / (cap * margin))))
    C = legal(kmedians(X, Y, W, k0))
    if not C:
        rep["status"] = "BLOCKED"
        rep["why"] = "no legal tap site"
        return rep, []
    blocked = set()
    for _ in range(4 * max_taps):
        idx, dist = assign(C)
        load, far, _b = stats(idx, dist, W, len(C), radius)
        bad = [int(k) for k in np.argsort(-np.maximum(np.round(load) / cap, far / radius), kind="stable")
               if (round(load[k]) > cap or far[k] > radius + 1e-6) and tuple(C[k]) not in blocked]
        if not bad or len(C) >= max_taps:
            break
        k = bad[0]
        mem = np.nonzero(idx == k)[0]
        e0 = excess(load, _b, cap)
        best = None
        for kk in (2, 3):
            if len(mem) < kk:
                break
            new = legal(kmedians(X[mem], Y[mem], W[mem], kk))
            tr = C[:k] + C[k + 1:]
            tr = tr + [q for q in new if q not in tr]
            i2, d2 = assign(tr)
            l2, _f2, b2 = stats(i2, d2, W, len(tr), radius)
            e2 = excess(l2, b2, cap)
            if e2 < e0 - 1e-9 and (best is None or e2 < best[0]):
                best = (e2, tr)
        if best is None:
            blocked.add(tuple(C[k]))
            continue
        C = best[1]
    for _ in range(5):                               # drop taps under min_sinks, relax centres to their medians
        idx, dist = assign(C)
        load, far, _b = stats(idx, dist, W, len(C), radius)
        keep = [C[j] for j in range(len(C)) if load[j] >= min_sinks]
        if keep and len(keep) < len(C):
            C = keep
            idx, dist = assign(C)
            load, far, _b = stats(idx, dist, W, len(C), radius)
        e0 = excess(load, _b, cap)
        R_ = []
        for j in range(len(C)):
            m = idx == j
            R_.append((wmedian(X[m], W[m]), wmedian(Y[m], W[m])) if m.any() else C[j])
        R_ = legal(R_)
        if len(R_) != len(C):
            break
        i2, d2 = assign(R_)
        l2, _f2, b2 = stats(i2, d2, W, len(R_), radius)
        if excess(l2, b2, cap) > e0 + 1e-9 or (l2 < min_sinks).any() or R_ == C:
            break
        C = R_
    idx, dist = assign(C)
    load, far, beyond = stats(idx, dist, W, len(C), radius)
    rep["after"] = dict(max_load=int(round(load.max())), over_cap=int((np.round(load) > cap).sum()),
                        under_min=int((load < min_sinks).sum()), max_radius=round(float(far.max()), 3),
                        over_radius=int((far > radius + 1e-6).sum()), excess=excess(load, beyond, cap),
                        taps=len(C), beyond_radius_share=round(float(W[dist > radius + 1e-6].sum() / W.sum()), 4))
    ok = rep["after"]["excess"] <= 0 and not rep["after"]["under_min"]
    rep["status"] = "SPLIT" if ok else "PARTIAL"
    rep["key"] = "replace_taps"
    rows = [{"name": "clk" if i == 0 else f"clk_t{i}", "xy": [round(x, 3), round(y, 3)]} for i, (x, y) in enumerate(C)]
    return rep, rows


def spans(idx, X, Y, nt):
    """W + H of the bounding box of each tap's sinks (0 for an empty tap)."""
    np = _np()
    lo_x = np.full(nt, np.inf); hi_x = np.full(nt, -np.inf); lo_y = np.full(nt, np.inf); hi_y = np.full(nt, -np.inf)
    np.minimum.at(lo_x, idx, X); np.maximum.at(hi_x, idx, X); np.minimum.at(lo_y, idx, Y); np.maximum.at(hi_y, idx, Y)
    sp = (hi_x - lo_x) + (hi_y - lo_y)
    sp[~np.isfinite(sp)] = 0.0
    return sp


def fp_seeds(X, Y, W, k):
    """k seeds: the weighted median, then repeatedly the point farthest (L1) from every seed so far."""
    np = _np()
    S = [(wmedian(X, W), wmedian(Y, W))]
    d = np.abs(X - S[0][0]) + np.abs(Y - S[0][1])
    for _ in range(1, k):
        j = int(d.argmax())
        S.append((float(X[j]), float(Y[j])))
        d = np.minimum(d, np.abs(X - X[j]) + np.abs(Y - Y[j]))
    return S


def span_excess(sp, span_um):
    np = _np()
    return float(np.maximum(0.0, sp - span_um).sum())


def span_pass(site, added, idx, dist, X, Y, W, cap, radius, n0, span_um, max_add, full, rep, iters=25):
    """SPAN: split taps whose sink box W + H exceeds span_um; -> (added, idx, dist)."""
    np = _np()
    blocked = set()
    while len(added) < max_add:
        nt = n0 + len(added)
        sp = spans(idx, X, Y, nt)
        sx = span_excess(sp, span_um)
        order = [int(k) for k in np.argsort(-sp, kind="stable") if sp[k] > span_um + 1e-6 and int(k) not in blocked]
        if not order:
            break
        k = order[0]
        load, _far, beyond = stats(idx, dist, W, nt, radius)
        e0 = excess(load, beyond, cap)
        mem = np.nonzero(idx == k)[0]
        best = None
        for kk in (2, 3, 4):
            if len(mem) < kk:
                break
            C = fp_seeds(X[mem], Y[mem], W[mem], kk)
            lab = None
            C = np.array(C, dtype=float)
            for _ in range(iters):                 # weighted L1 k-medians from the farthest-point seeds
                D = np.abs(X[mem][:, None] - C[None, :, 0]) + np.abs(Y[mem][:, None] - C[None, :, 1])
                nl = D.argmin(axis=1)
                if lab is not None and (nl == lab).all():
                    break
                lab = nl
                for j in range(kk):
                    m = lab == j
                    if m.any():
                        C[j] = (wmedian(X[mem][m], W[mem][m]), wmedian(Y[mem][m], W[mem][m]))
            new = []
            for cx, cy in C[1:]:                   # the tap itself keeps the first (median) group
                s_ = site.place(float(cx), float(cy), added + new)
                if s_ is not None and s_ not in added and s_ not in new:
                    new.append(s_)
            if not new or len(added) + len(new) > max_add:
                continue
            tr = added + new
            i2, d2 = full([a for a, _ in tr], [b for _, b in tr])
            l2, _f2, b2 = stats(i2, d2, W, n0 + len(tr), radius)
            sx2 = span_excess(spans(i2, X, Y, n0 + len(tr)), span_um)
            if sx2 < sx - 1e-6 and excess(l2, b2, cap) <= e0 + 1e-9 and (best is None or sx2 < best[0]):
                best = (sx2, new, i2, d2)
        if best is None:
            blocked.add(k)
            continue
        added = added + best[1]
        idx, dist = best[2], best[3]
        rep["span_adds"] = rep.get("span_adds", 0) + len(best[1])
        blocked.clear()
    return added, idx, dist


def split_type(P, tn, radius, max_add, cap=None, require_placed=False, multi_margin=0.9, multi_nbhd=8, span_um=None,
               global_rounds=0, protect_rings=None):
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
    if basis == "planned+flops":
        rep["why"] = "SINK-EST planned + netlist flop residual spread uniformly (no placed kit of this outline)"
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
    if span_um:
        sp0 = spans(idx, X, Y, len(tp))
        rep["before"].update(max_span=round(float(sp0.max()), 3), over_span=int((sp0 > span_um + 1e-6).sum()), span_um=span_um)
    if rep["before"]["excess"] <= 0 and not (span_um and rep["before"]["over_span"]):
        rep["status"] = "OK"
        return rep, []
    site = Site(P, tn, [(p[1], p[2]) for p in tp])
    if protect_rings:
        rep["protected_windows"] = site.protect_rings(protect_rings if isinstance(protect_rings, str) else ".*")
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
            mb = multi_add(site, added, mem, X, Y, W, float(load[k]), cap, multi_margin, before, full, radius, n0)
            if mb is None:
                TA = np.column_stack([np.concatenate([TX, np.array([a for a, _ in added], dtype=float)]),
                                      np.concatenate([TY, np.array([b for _, b in added], dtype=float)])])
                mb = nbhd_add(site, added, k, idx, TA, X, Y, W, load, cap, multi_margin, before, full, radius, n0,
                              nbhd=multi_nbhd)
                if mb is not None:
                    rep["nbhd"] = rep.get("nbhd", 0) + 1
            if mb is None or len(added) + len(mb[1]) > max_add:
                blocked.add(k)
                continue
            added.extend(mb[1])
            idx, dist = mb[2], mb[3]
            rep["multi"] = rep.get("multi", 0) + 1
            blocked.clear()
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
    if global_rounds and added:
        added, idx, dist = global_pass(site, added, idx, dist, X, Y, W, TX, TY, cap, multi_margin, radius, n0, full,
                                       max_add, rep, rounds=global_rounds, nbhd=multi_nbhd or 8)
    # drop added taps left without sinks (an empty tap is a TAP-LIMIT finding); recompute
    if added:
        load, _, _ = stats(idx, dist, W, n0 + len(added), radius)
        added = [a for j, a in enumerate(added) if load[n0 + j] > 0]
        idx, dist = full([a for a, _ in added], [b for _, b in added])
    if span_um:
        added, idx, dist = span_pass(site, added, idx, dist, X, Y, W, cap, radius, n0, span_um, max_add, full, rep)
        if added:                                  # a span split can leave an earlier added tap empty
            load, _, _ = stats(idx, dist, W, n0 + len(added), radius)
            added = [a for j, a in enumerate(added) if load[n0 + j] > 0]
            idx, dist = full([a for a, _ in added], [b for _, b in added])
    nt = n0 + len(added)
    load, far, beyond = stats(idx, dist, W, nt, radius)
    rep["after"] = dict(max_load=int(round(load.max())), over_cap=int((np.round(load) > cap).sum()),
                        max_radius=round(float(far.max()), 3), over_radius=int((far > radius + 1e-6).sum()),
                        excess=excess(load, beyond, cap), added=len(added),
                        min_added_load=int(round(load[n0:].min())) if added else None)
    span_bad = 0
    if span_um:
        sp = spans(idx, X, Y, nt)
        span_bad = int((sp > span_um + 1e-6).sum())
        rep["after"].update(max_span=round(float(sp.max()), 3), over_span=span_bad, span_um=span_um)
    rep["status"] = "SPLIT" if rep["after"]["excess"] <= 0 and not span_bad else ("PARTIAL" if added else "BLOCKED")
    if rep["status"] != "SPLIT":
        rep["residual"] = [dict(tap=(tp[k][0] if k < n0 else f"clk_t{k}"), load=int(round(load[k])),
                                radius=round(float(far[k]), 3))
                           for k in range(nt) if round(load[k]) > cap or far[k] > radius + 1e-6][:40]
    key = "taps" if mode == "explicit" else "added_taps"
    rows = [{"name": f"clk_t{n0 + i}", "xy": [round(x, 3), round(y, 3)]} for i, (x, y) in enumerate(added)]
    rep["key"] = key
    return rep, rows


def remap_rows(orig_raw, raw, plan_path, out_plan, types, root, bound_rtl=None, remap_fn=None, check_fn=None, resets="anchor"):
    """REMAP-ALWAYS: landing_remap (anchor mode) over `types` on raw (rows applied), write out_plan, then the PRE
    LANDREMAP check vs plan_path.  Failing types are restored from orig_raw.  -> (receipt, {type: why})."""
    import copy
    import re
    if remap_fn is None or check_fn is None:
        import landing_remap as LR
        import plan_gate_pre as PG

        def remap_fn(old, new, names):
            try:
                return LR.remap_plan(old, new, root, Path(out_plan).parent, set(names), resets=resets, bound_rtl=bound_rtl)
            except TypeError:                       # older tool trees: no bound_rtl keyword
                return LR.remap_plan(old, new, root, Path(out_plan).parent, set(names), resets=resets)
        check_fn = check_fn or (lambda new_path, old_path: PG.check_landremap(new_path, old_path))
        err_cls = LR.RemapError
    else:
        err_cls = ValueError
    failed, todo, rec = {}, set(types), None

    def restore(tn):
        raw["partition_types"][tn] = copy.deepcopy(orig_raw["partition_types"][tn])
    while todo:
        trial = copy.deepcopy(raw)
        try:
            rec = remap_fn(orig_raw, trial, sorted(todo))
            raw.clear(); raw.update(trial)
            break
        except Exception as e:                      # RemapError, reset_anchor.AnchorError (serdes fresh tables), ...
            tn = str(e).split(":", 1)[0].strip()
            if tn not in todo:
                # the error names no type (reset_anchor.record: 'referenced relay(s) not in the tree'): find the
                # failing types one by one; nothing isolated -> re-raise
                bad = {}
                for t1 in sorted(todo):
                    try:
                        remap_fn(orig_raw, copy.deepcopy(raw), [t1])
                    except Exception as e1:
                        bad[t1] = e1
                if not bad or len(todo) == 1:
                    raise
                for t1, e1 in bad.items():
                    failed[t1] = f"REMAP_FAIL landing_remap: {str(e1)[:240]}"
                    todo.discard(t1); restore(t1)
                continue
            failed[tn] = f"REMAP_FAIL landing_remap: {str(e)[:240]}"
            todo.discard(tn); restore(tn)
    for _ in range(3):
        Path(out_plan).write_text(json.dumps(raw, indent=1, sort_keys=False) + "\n")
        new = {}
        for ln in check_fn(str(out_plan), str(plan_path)):
            m = re.match(r"FAIL (LANDREMAP\S*) (\S+?):", ln)
            if m and m.group(2) in types and m.group(2) not in failed:
                new[m.group(2)] = f"REMAP_FAIL {ln[:300]}"
        if not new:
            break
        for tn, why in new.items():
            failed[tn] = why; restore(tn)
    return rec, failed


def apply_rows(raw, rows_by_type):
    for tn, (key, rows) in rows_by_type.items():
        ck = raw["partition_types"][tn].setdefault("clock", {})
        if key == "replace_taps":                   # FRESH: the whole table, explicit
            ck["tap_mode"] = "explicit"
            ck["taps"] = list(rows)
            ck.pop("added_taps", None)
            continue
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
    ap.add_argument("--flops-cache", default=None,
                    help="SINK-EST: PRECHECK flops cache (placed_bins / flops) for types without --sinks or sink_bins_file; "
                         "default $OT_FLOPS_CACHE else the shared cache when present; 'none' = planned sinks only")
    ap.add_argument("--require-placed", action="store_true",
                    help="a type without sink_bins_file or placed sinks is NO_PLACED (no rows) instead of split on planned sinks")
    ap.add_argument("--multi-margin", type=float, default=0.9,
                    help="MULTI-TAP: k = ceil(load / (cap * M)) taps at the k-medians of a dense cluster when no single tap helps; 0 = off")
    ap.add_argument("--fresh", default="", metavar="TYPES",
                    help="FRESH: comma list of types whose tap table is rebuilt from their sinks (explicit, replaces taps)")
    ap.add_argument("--fresh-min-sinks", type=int, default=30, help="FRESH: drop taps serving fewer sinks")
    ap.add_argument("--protect-rings", nargs="?", const=".*", default=None, metavar="REGEX",
                    help="PROTECT-RINGS: no new tap nearer a landing receive window (fclk_in_<bus> name matching REGEX, "
                         "default all) than its current nearest tap; e.g. only the ring feeding a raw-branch role")
    ap.add_argument("--global-rounds", type=int, default=0,
                    help="GLOBAL: rounds of over-cap region re-solve with added taps movable (0 = off)")
    ap.add_argument("--span-um", type=float, default=0.0,
                    help="SPAN: also bound each tap's sink box W + H to this (kit OT_TAP_SPAN rule, e.g. 300); 0 = off")
    ap.add_argument("--multi-nbhd", type=int, default=8,
                    help="NEIGHBOURHOOD: re-solve an over-cap tap with its N nearest taps fixed when its own group does not help; 0 = off")
    ap.add_argument("--rows", required=True)
    ap.add_argument("--out-plan")
    ap.add_argument("--tools", help="tools/die_plan of the tree to plan with (default: next to this file)")
    ap.add_argument("--root", help="tree root for landing_remap (default: the --tools tree root)")
    ap.add_argument("--remap-resets", default="anchor", choices=("anchor", "resel"),
                    help="landing_remap reset mode (default anchor); resel = fresh relay selection by role + depth (a "
                         "FRESH table re-solves the reset tree: anchor finds no same-depth relay within tolerance)")
    ap.add_argument("--bound-rtl", help="rtl/ of the bind of record of PLAN: landing_remap anchor mode reads OLD relay identities there")
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
    BASIS.clear()
    cache = load_cache(a.flops_cache)
    if cache:
        for tn in types:
            if tn in PLACED or tn not in P.types:
                continue
            binned = bool((P.types[tn].get("clock") or {}).get("sink_bins_file"))
            try:
                est, basis = estimate_sinks(P, tn, cache)
                if binned:                            # a sink_bins_file stays unless a placed kit holds > STALE_BINS x its sinks
                    nb = sum(w for *_, w in TP.sink_sites(P, tn))
                    if not (basis or "").startswith("cache") or sum(w for *_, w in est) <= STALE_BINS * nb:
                        continue
                    basis = basis.replace("cache", "cache>bins", 1)
            except Exception as e:                    # an estimate never blocks the split; the type keeps its planned basis
                print(f"TAP_SPLIT SINK-EST {tn}: skipped ({type(e).__name__}: {str(e)[:120]})", flush=True)
                continue
            if est:
                PLACED[tn], BASIS[tn] = est, basis
        print(f"TAP_SPLIT SINK-EST " + " ".join(f"{b}={sum(1 for v in BASIS.values() if v.split(':')[0] == b)}"
                                                 for b in ("cache", "cache>bins", "planned+flops")), flush=True)
    reps, rows_by_type = [], {}
    for tn in types:
        try:
            if tn in set(x for x in a.fresh.split(",") if x):
                rep, rows = fresh_type(P, tn, a.radius_um, cap=a.cap or None, margin=a.multi_margin or 0.9,
                                       min_sinks=a.fresh_min_sinks, require_placed=a.require_placed)
            else:
                rep, rows = split_type(P, tn, a.radius_um, a.max_add, cap=a.cap or None, require_placed=a.require_placed,
                                    multi_margin=a.multi_margin, multi_nbhd=a.multi_nbhd, span_um=a.span_um or None,
                                    global_rounds=a.global_rounds, protect_rings=a.protect_rings)
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
    rc = 0
    import tap_offset_fill as TF
    if rows_by_type and ((raw.get("clock") or {}).get("tap_offset") or {}).get("per_port_ps"):
        import copy
        tr = copy.deepcopy(raw)
        apply_rows(tr, rows_by_type)
        out["tap_offset"] = TF.fill(tr, S.Plan(tr, a.plan), types=set(rows_by_type))
    if a.out_plan:
        orig = json.loads(Path(a.plan).read_text())
        apply_rows(raw, rows_by_type)
        root = a.root or str((Path(a.tools).resolve() if a.tools else Path(__file__).resolve().parent).parents[1])
        rec, failed = remap_rows(orig, raw, a.plan, a.out_plan, sorted(rows_by_type), root, a.bound_rtl,
                                 resets=a.remap_resets)
        for tn, why in failed.items():
            rows_by_type.pop(tn, None)
            for r in reps:
                if r.get("type") == tn:
                    r["status"], r["why"] = "REMAP_FAIL", why
            print(f"TAP_SPLIT {tn} REMAP_FAIL: rows dropped, type restored ({why[:200]})", flush=True)
        out["rows"] = {tn: {"key": k, "rows": r} for tn, (k, r) in rows_by_type.items()}
        if out.get("tap_offset"):                   # TAPOFF: rows of the types that kept their taps, into the written plan
            out["tap_offset"] = {tn: v for tn, v in out["tap_offset"].items() if tn in rows_by_type}
            w = json.loads(Path(a.out_plan).read_text())
            tab = w["clock"]["tap_offset"]["per_port_ps"]
            for tn, v in out["tap_offset"].items():
                for n, r in v.items():
                    tab.setdefault(tn, {})[n] = {k: r[k] for k in ("TT", "FF", "tol")}
            Path(a.out_plan).write_text(json.dumps(w, indent=1, sort_keys=False) + "\n")
            print(f"TAP_SPLIT TAPOFF {sum(len(v) for v in out['tap_offset'].values())} tap_offset rows written "
                  f"({len(out['tap_offset'])} types)", flush=True)
        out["remap"] = dict(mode=a.remap_resets, failed=failed, receipt=rec)
        print(f"TAP_SPLIT REMAP {a.remap_resets}: {len(rows_by_type)} types remapped clean, {len(failed)} REMAP_FAIL", flush=True)
        rc = 3 if failed else 0
        P2 = S.Plan(json.loads(Path(a.out_plan).read_text()), a.out_plan)
        out["recheck"] = recheck(P2, sorted(rows_by_type), a.radius_um, a.cap or None)
        bad = {k: v for k, v in out["recheck"].items() if v["over_cap"] or v["over_radius"]}
        print(f"TAP_SPLIT RECHECK {len(out['recheck'])} types on {a.out_plan}: {len(bad)} still over cap/radius", flush=True)
    Path(a.rows).write_text(json.dumps(out, indent=1) + "\n")
    tot = {s: sum(1 for r in reps if r.get("status") == s) for s in ("OK", "SPLIT", "PARTIAL", "BLOCKED", "UNSUPPORTED", "ERROR", "NO_SINKS", "NO_PLACED", "REMAP_FAIL")}
    print("TAP_SPLIT SUMMARY " + " ".join(f"{k}={v}" for k, v in tot.items()) +
          f"; taps added {sum(len(r) for _, r in rows_by_type.values())}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())

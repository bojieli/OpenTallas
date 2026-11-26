#!/usr/bin/env python3
"""tap_reach_fix.py -- C-TAP-REACH: every FIRM clock seat inside tap_radius_um of a clock tap.

CLASS C-TAP-REACH (merges TAP-SPAN).  The taps of an explicit / grid+explicit / grid type are a stored table, and the
planner inventory (taps.sink_sites) omits the flops the kit places beyond the face / ft registers: reset relays,
landing rings, ring local-read flops.  When those seats move (a row, a reset-tree re-solve) the table is stale and CTS
has to drive a long arm from the nearest tap (QC coll_ft cA4: 40 clock flops over 220 um from the nearest tap, 5 over
300; max 338 um at the x=655 relay column).  The static check is reach_fix class 1 (plan_geom.type_sites on the
exported taps, nearest-tap split as AUTO-GEOM measures it) split by seat kind and by the thresholds that matter:

    over radius   seat farther than tap_radius_um (default 200) from its nearest tap
    over 220      the CTS own-driver check of QC-INT-R2 (clk flops > 220 um from the nearest tap)
    over 300      the AUTO-GEOM tap-span class (and a tap whose assigned-sink box W + H exceeds 300)

CHECK (report only, never a gate):   ADV-TAP-REACH   tap_reach_fix.findings (plan_advisory TAP-REACH) / `tap_reach_fix.py check`

GENERATOR (default OFF; plan flag at the top level of the plan dict):

    "tap_reach": {"enable": 1, "radius_um": 200, "rounds": 4, "types": "<regex>", "jobs": 1,
     "span_um": 300}      (opt-in TAP-SPAN stage; absent = reach only)

`derive(raw, plan_path, tree)` is the per-cut step beside tap_derive.derive (row_gate runs it after --tap-manifest,
before normalize_plan).  Without the flag it returns ([], {}) and touches nothing.  With it, every non-hard type whose
exported taps leave a seat beyond the radius gets sink taps appended to its OWN tap table (never moving a tap that is
already there):

    explicit            clock.taps += {name clk_t<n>, xy}
    grid+explicit/grid  clock.added_taps += ...   (grid / grid+sinks / sinks become grid+explicit, as reach_fix)
    density             the far non-plan seats join clock.sink_sites_um (+ reach_fix_sinks); the density generator then
                        places the taps; far 'plan' (inventory) seats are the density generator's own business.

Sites: one tap per radius-bounded group of far seats (farthest-first greedy k-centre at the weighted L1 median of the
group), legal by schema.tap_clear(strict) off hard cores / keepouts / the other taps, pin-snapped like gen_phys.  The
far non-plan seats join clock.sink_sites_um / reach_fix_sinks (reach_fix's own mechanism) so the planner's no-empty-tap
validation sees what the new tap is for.  The BASE taps are frozen as type.reset.consumer_sites_um first (reach_fix
RESET-KEY 11-19) so the reset relays, their indices and sites do not move and the bound reset RTL stays valid.  A type is
kept only when the exported taps load, the over-radius seat count strictly falls and no seat got farther than before.

Row form for row_gate: `script:tools/die_plan/tap_reach_fix.py::--row {in} {out} {report} --types REGEX` sets the flag (derive runs in step 3).

Relation to tools/die_plan/tap_reach.py (QC-INT-R2-TOOLS, PRE class TAPREACH, report-only): that check is the fast plan-seat
PRE rule (relay_sites / station regs / collector relays against the stored taps).  This module is the generator side it
names and its check reads the plan geometry the kit really places (plan_geom.type_sites: it adds the reset-tree relays and
the landing / ring local-read flops, on the exported taps of every tap mode) plus the tap sink-box span; the flag is `tap_reach`.

Composition with C-TAP-LOAD (--tap-manifest, tap_derive): tap_derive first (load / span of the placed sink bins, adds
taps by its own solver); tap_reach second on the result, so its radius check sees the load-split taps and only adds taps
for seats still out of reach.  Both only append to clock.taps / clock.added_taps; both are followed by the stock
tap_offset_cover fill (new taps need tap_offset rows).
"""
import argparse
import copy
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

CHECK = "ADV-TAP-REACH"
FLAG = "tap_reach"
RADIUS_UM = 200.0       # METHODOLOGY 12.8b entry-to-sink; the kit clock_taps.tcl reach
OWN_DRIVER_UM = 220.0   # QC-INT-R2 CTS own-driver check
SPAN_UM = 300.0         # AUTO-GEOM tap span limit (also OT_TAP_SPAN_UM)
ROUNDS = 4
BANDS = (RADIUS_UM, OWN_DRIVER_UM, 250.0, SPAN_UM)
EXPLICIT_MODES = ("explicit", "grid+explicit", "grid", "grid+sinks", "sinks")


def enabled(raw):
    cfg = raw.get(FLAG) if isinstance(raw, dict) else None
    return isinstance(cfg, dict) and bool(cfg.get("enable"))


def _d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _setup(tree=None):
    import reach_fix as RF
    if tree:
        os.environ.setdefault("OT_REPO_ROOT", str(Path(tree).resolve()))
        RF.set_repo(tree)
    return RF


def type_radius(t, default=RADIUS_UM):
    return float((t.get("clock") or {}).get("tap_radius_um") or default)


def measure(P, tn, radius=None, RF=None, span=None):
    """-> (row, A).  row: seats, per-band counts (all / by kind), max, worst tap, tap spans > 300.  A: assignment detail
    (grid, sinks, own, dist, kinds) or None when the type has no taps or no sinks."""
    RF = RF or _setup()
    radius = radius or RADIUS_UM
    row, A = RF.tap_metrics(P, tn, None, 10 ** 9, radius)
    out = dict(type=tn, mode=(P.types[tn].get("clock") or {}).get("tap_mode", "grid"), taps=row.get("taps"),
               seats=row.get("sinks"), c1_max_um=row.get("c1_max_um"), c1_worst=row.get("c1_worst"))
    if A is None:
        out.update(over=0, over220=0, over250=0, over300=0, kinds={}, span_taps_over_300=0, span_max_um=0.0)
        return out, None
    dist, kinds = A["dist"], [re.split(r"[:(]", k)[0] for k in A["kinds"]]
    out["over"] = sum(1 for v in dist if v > radius + 1e-6)
    out["over220"] = sum(1 for v in dist if v > OWN_DRIVER_UM + 1e-6)
    out["over250"] = sum(1 for v in dist if v > 250.0 + 1e-6)
    out["over300"] = sum(1 for v in dist if v > SPAN_UM + 1e-6)
    kd = defaultdict(int)
    for v, k in zip(dist, kinds):
        if v > radius + 1e-6:
            kd[k] += 1
    out["kinds"] = dict(kd)
    box = {}
    for (x, y, _w), j in zip(A["sinks"], A["own"]):
        b = box.setdefault(j, [x, x, y, y])
        b[0], b[1], b[2], b[3] = min(b[0], x), max(b[1], x), min(b[2], y), max(b[3], y)
    spans = {A["grid"][j][0]: (b[1] - b[0]) + (b[3] - b[2]) for j, b in box.items()}
    span = span or SPAN_UM
    out["span_taps_over_300"] = sum(1 for v in spans.values() if v > span + 1e-6)
    out["span_max_um"] = round(max(spans.values() or [0.0]), 1)
    out["span_taps"] = len(spans)
    return out, A


def _far_groups(A, radius, firm_only):
    """far seats grouped by their nearest tap -> [(tap index, [(x, y, w, kind)])]"""
    by = defaultdict(list)
    for (x, y, w), j, d, k in zip(A["sinks"], A["own"], A["dist"], A["kinds"]):
        kind = re.split(r"[:(]", k)[0]
        if d > radius + 1e-6 and not (firm_only and kind == "plan"):
            by[j].append((x, y, w, kind))
    return sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0]))


def new_sites(PQ, tn, A, radius, RF):
    """legal tap sites for the far seats of one measurement (reach_fix.fix_taps radius branch, minimal)"""
    import schema as S
    import taps as TP
    import gen_phys
    t = PQ.types[tn]
    grid = A["grid"]
    all_xy = [(x, y) for _, x, y in grid]
    core = [(x, y) for _, x, y, _ in S.core_taps(PQ, tn)]
    try:
        axes = gen_phys.clock_legal_axes(PQ, tn)
    except Exception:  # noqa: BLE001
        axes = None
    snap = lambda x, y: gen_phys._snap_tap(PQ, x, y, pg_legal=True)  # noqa: E731
    new, blocked = [], []
    far = [s for s, d in zip(A["sinks"], A["dist"]) if d > radius + 1e-6]
    rem = sorted(far, key=lambda p: (-min(_d(p, (gx, gy)) for _, gx, gy in grid), p[0], p[1]))
    while rem:
        seed = rem[0]
        grp = [p for p in rem if _d(p, seed) <= radius] or [seed]
        gp = [p if p[2] > 0 else (p[0], p[1], 1.0) for p in grp]
        cx, cy = TP._wmedian(gp, 0), TP._wmedian(gp, 1)
        try:
            q = S.tap_clear(t, cx, cy, core + all_xy + new, strict=True, pin_snap=snap, legal_axes=axes)
        except Exception:  # noqa: BLE001
            q = None
        if q is not None:
            q = (round(q[0], 4), round(q[1], 4))
        # a legal site displaced so far that it no longer reaches the seed is no fix (blocked strip: the nearest legal
        # site was 430 um away on HEAD hd_lep0N_w x=851): those seats stay reported, not "covered" by a distant tap
        if q is None or _d(q, seed) > radius or q in all_xy or q in new:
            blocked.append(seed)
            rem = [p for p in rem if p is not seed]
            continue
        new.append(q)
        rem = [p for p in rem if _d(p, q) > radius]
    new_sites.blocked = blocked
    return new


def span_sites(PQ, tn, A, span, radius, RF):
    """TAP-SPAN stage (opt-in span_um): a tap whose assigned-sink box W + H exceeds `span` is split: the sinks go to
    ceil(span_j / span) weighted L1 medians, the group nearest the tap keeps it, every other group gets a tap at its median
    (legal site, within radius / 2 of that median, else the group stays on the old tap)."""
    import schema as S
    import gen_phys
    t = PQ.types[tn]
    grid = A["grid"]
    all_xy = [(x, y) for _, x, y in grid]
    core = [(x, y) for _, x, y, _ in S.core_taps(PQ, tn)]
    try:
        axes = gen_phys.clock_legal_axes(PQ, tn)
    except Exception:  # noqa: BLE001
        axes = None
    snap = lambda x, y: gen_phys._snap_tap(PQ, x, y, pg_legal=True)  # noqa: E731
    by = defaultdict(list)
    for sk, j in zip(A["sinks"], A["own"]):
        by[j].append(sk)
    new = []
    for j in sorted(by):
        pts = by[j]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        sp = (max(xs) - min(xs)) + (max(ys) - min(ys))
        if sp <= span + 1e-6 or len(pts) < 2:
            continue
        k = max(2, int(math.ceil(sp / span)))
        cen, groups = RF._wkmedians(pts, k)
        keep = min(range(len(cen)), key=lambda c: (_d(cen[c], (grid[j][1], grid[j][2])), c))
        for c, (x, y) in enumerate(cen):
            if c == keep or not groups[c]:
                continue
            try:
                q = S.tap_clear(t, x, y, core + all_xy + new, strict=True, pin_snap=snap, legal_axes=axes)
            except Exception:  # noqa: BLE001
                continue
            q = (round(q[0], 4), round(q[1], 4))
            if _d(q, (x, y)) > 0.5 * radius or q in all_xy or q in new:
                continue
            new.append(q)
    return new


def _reset_sig(P, tn):
    """the type's generated reset tree as (relay name, x, y) rows + root: a tap change that moves a relay renumbers the
    raw reset pointers (landing / START rst_rl_<k> refs: DERIVEDNAME / RSTREACH on HEAD hd_host_n when density taps changed).
    None = no generated tree to compare."""
    try:
        import reset_tree as RT
        if not (RT.pipelined(P) or RT.wavefront(P)):
            return None            # interim kit_rsync plans carry no raw relay pointers
        T = RT.for_type(P, tn)
    except Exception:  # noqa: BLE001
        return None
    rows = sorted((str(r.get("name")), round(float(r["xy"][0]), 3), round(float(r["xy"][1]), 3)) for r in T.get("relays", []))
    root = T.get("root")
    return rows, (tuple(round(float(v), 3) for v in root) if root else None)


def _table(ck, mode):
    return ck.get("taps") if mode == "explicit" else ck.get("added_taps")


def _count_own(ck, mode):
    """rows already in the table before this tool appends (explicit: non-core rows)"""
    return sum(1 for p in _table(ck, mode) or [] if p.get("kind") != "core")


def _drop_illegal(raw, plan_path, tn, ck, mode, orig_n, RF, rec):
    """the export validator (taps.explicit_taps / grid_explicit_taps) is stricter than tap_clear on some sites (outline /
    halo / spacing to the taps before it in table order): a tap THIS tool appended that it names is dropped and the
    appended names re-packed; anything else (a stored tap, another error) is left to the caller's revert."""
    import schema as S
    for _ in range(64):
        PQ = RF.plan_obj(raw, plan_path)
        RF._reset_caches(PQ)
        try:
            S.tap_grid(PQ, tn)
            return None
        except Exception as e:  # noqa: BLE001
            msg = "%s: %s" % (type(e).__name__, str(e)[:200])
            m = re.search(r"tap (clk_t\d+) violates", msg)
            tbl = _table(ck, mode) or []
            idx = next((i for i, r in enumerate(tbl) if m and r.get("name") == m.group(1) and r.get("kind") != "core"), None)
            first_new = next((i for i, r in enumerate([r for r in tbl]) if r.get("kind") != "core"), 0)
            own_rows = [i for i, r in enumerate(tbl) if r.get("kind") != "core"]
            if idx is None or own_rows.index(idx) < orig_n:
                return msg
            tbl.pop(idx)
            n = 0
            for r in tbl:
                if r.get("kind") == "core":
                    continue
                if mode == "explicit":
                    r["name"] = "clk" if n == 0 else "clk_t%d" % n
                n += 1
            if mode != "explicit":
                n0 = len(S._grid_taps(PQ, tn))
                for i, r in enumerate(tbl):
                    r["name"] = "clk_t%d" % (n0 + i)
            rec.setdefault("dropped_illegal", []).append(m.group(1))
    return "too many illegal taps"


def _append_taps(ck, mode, new, PQ, tn):
    import schema as S
    if mode == "explicit":
        tbl = ck.setdefault("taps", [])
        n = sum(1 for p in tbl if p.get("kind") != "core")
        for q in new:
            tbl.append(dict(name="clk_t%d" % n, xy=list(q)))
            n += 1
    else:
        tbl = ck.setdefault("added_taps", [])
        n0 = len(S._grid_taps(PQ, tn))
        for q in new:
            tbl.append(dict(name="clk_t%d" % (n0 + len(tbl)), xy=list(q)))


def solve_type(raw, plan_path, tn, radius=None, rounds=ROUNDS, RF=None, span=None):
    """_solve_type with a restore on any error: a type that raises is put back and reported, never half-edited"""
    saved = copy.deepcopy(raw["partition_types"][tn])
    try:
        return _solve_type(raw, plan_path, tn, radius, rounds, RF, span)
    except Exception as e:  # noqa: BLE001
        raw["partition_types"][tn] = saved
        return dict(type=tn, mode=(saved.get("clock") or {}).get("tap_mode", "grid"), added=[], changes=[],
                    status="reverted: error %s: %s" % (type(e).__name__, str(e)[:200]))


def _solve_type(raw, plan_path, tn, radius=None, rounds=ROUNDS, RF=None, span=None):
    """append sink taps to type tn of plan dict `raw` (in place) until no seat is beyond the radius or no site helps.
    With span (opt-in span_um) taps whose sink box W + H exceeds it are split as well (TAP-SPAN stage).
    Returns a record; the type is restored when the result is not strictly better."""
    RF = RF or _setup()
    import schema as S
    t = raw["partition_types"][tn]
    ck = t.get("clock") or {}
    rec = dict(type=tn, mode=ck.get("tap_mode", "grid"), added=[], changes=[], status="unchanged")
    if t.get("hard") or not ck:
        rec["status"] = "hard or no clock"
        return rec
    if ck.get("native_domains") is not None or ck.get("child_root_taps") is not None:
        rec["status"] = "native domains / child-root taps own their taps"
        return rec
    radius = radius or type_radius(t)
    before_raw = copy.deepcopy(t)
    P0 = RF.plan_obj(raw, plan_path)
    RF._reset_caches(P0)
    base, A = measure(P0, tn, radius, RF, span)
    KEYS = ("over", "over220", "over300", "c1_max_um", "kinds", "span_taps_over_300", "span_taps")
    rec["before"] = {k: base[k] for k in KEYS}
    if A is None or not (base["over"] or (span and base["span_taps_over_300"])):
        rec["status"] = "within reach"
        return rec
    sig0 = _reset_sig(P0, tn)
    mode = ck.get("tap_mode", "grid")
    if mode == "density":
        if not base["over"]:
            rec["status"] = "density: span stage not supported (taps follow the sink inventory)"
            return rec
        if ck.get("added_taps"):
            # stored added_taps are named after the density count (clk_t<base>..): growing the sink inventory would renumber
            # them (TAP-NAMEDRIFT, KV kv3_hgi "density added tap names/order must be clk_t59..clk_t69"); a different fix
            rec["status"] = "density with stored added_taps: names follow the density count, not derived (report only)"
            return rec
        far = [(x, y, w) for x, y, w, k in _far_groups_flat(A, radius) if k != "plan"]
        if not far:
            rec["status"] = "density: far seats are inventory sinks (the density generator places those taps)"
            return rec
        add = [[round(x, 4), round(y, 4), max(1.0, round(w, 3))] for x, y, w in far]
        rec["added_sinks"] = len(RF._add_reach_sinks(ck, add))
    else:
        if mode not in EXPLICIT_MODES:
            rec["status"] = "tap_mode %s not handled" % mode
            return rec
        if mode != "explicit":
            ck["tap_mode"] = "grid+explicit"
            ck.setdefault("added_taps", [])
        mode = ck["tap_mode"]
        own_lim = {k: ck.get(k) for k in ("tap_radius_um", "tap_max_sinks")}
        RF._freeze_reset_consumers(P0, tn, t, rec)
        orig_n = _count_own(ck, mode)
        for rnd in range(rounds):
            PQ = RF.plan_obj(raw, plan_path)
            RF._reset_caches(PQ)
            m, A = measure(PQ, tn, radius, RF, span)
            if A is None or not m["over"]:
                break
            new = new_sites(PQ, tn, A, radius, RF)
            rec["blocked_seats"] = [[round(p[0], 1), round(p[1], 1)] for p in getattr(new_sites, "blocked", [])][:12]
            if not new:
                rec["unfixed"] = "no legal tap site within reach of %d far seats" % m["over"]
                break
            farx = [s for s, d, k in zip(A["sinks"], A["dist"], A["kinds"])
                    if d > radius + 1e-6 and re.split(r"[:(]", k)[0] != "plan"]
            if farx:
                RF._add_reach_sinks(ck, [[round(x, 4), round(y, 4), max(1.0, round(w, 3))] for x, y, w in farx])
            _append_taps(ck, mode, new, PQ, tn)
            rec["added"].extend([list(q) for q in new])
            err = _drop_illegal(raw, plan_path, tn, ck, mode, orig_n, RF, rec)
            if err:
                rec["unfixed"] = err
                break
        for rnd in range(rounds if span else 0):
            PQ = RF.plan_obj(raw, plan_path)
            RF._reset_caches(PQ)
            m, A = measure(PQ, tn, radius, RF, span)
            if A is None or not m["span_taps_over_300"]:
                break
            new = span_sites(PQ, tn, A, span, radius, RF)
            if not new:
                rec["span_unfixed"] = "no legal split site for %d taps over the span" % m["span_taps_over_300"]
                break
            _append_taps(ck, mode, new, PQ, tn)
            rec["added"].extend([list(q) for q in new])
            err = _drop_illegal(raw, plan_path, tn, ck, mode, orig_n, RF, rec)
            if err:
                rec["span_unfixed"] = err
                break
    if mode != "density":
        own_rows = [r for r in _table(ck, mode) or [] if r.get("kind") != "core"]
        rec["added"] = [list(r["xy"]) for r in own_rows[orig_n:]]
    PA = RF.plan_obj(raw, plan_path)
    RF._reset_caches(PA)
    try:
        S.tap_grid(PA, tn)
        after, A2 = measure(PA, tn, radius, RF, span)
    except Exception as e:  # noqa: BLE001
        raw["partition_types"][tn] = before_raw
        rec.update(status="reverted: export fails %s: %s" % (type(e).__name__, str(e)[:160]), added=[])
        return rec
    sig1 = _reset_sig(PA, tn)
    if sig0 is not None and sig1 != sig0:
        raw["partition_types"][tn] = before_raw
        rec.update(status="reverted: the new taps move the type's reset relays (raw reset pointers would go stale; "
                          "needs the START re-derive of the row that moves taps)", added=[])
        return rec
    better = A2 is not None and (after["over"] < base["over"] or (
        span and after["over"] <= base["over"] and after["span_taps_over_300"] < base["span_taps_over_300"]))
    if not better or (after["c1_max_um"] or 0) > (base["c1_max_um"] or 0) + 1e-6:
        raw["partition_types"][tn] = before_raw
        rec.update(status="reverted: over-radius seats %s -> %s, max %s -> %s, span taps %s -> %s" % (
            base["over"], after["over"], base["c1_max_um"], after["c1_max_um"], base["span_taps_over_300"],
            after["span_taps_over_300"]), added=[])
        return rec
    rec["after"] = {k: after[k] for k in KEYS}
    rec["status"] = "derive"
    return rec


def _far_groups_flat(A, radius):
    out = []
    for (x, y, w), d, k in zip(A["sinks"], A["dist"], A["kinds"]):
        if d > radius + 1e-6:
            out.append((x, y, w, re.split(r"[:(]", k)[0]))
    return out


def derive(raw, plan_path, tree, *, types=None):
    """Per-cut generator step.  No flag -> ([], {}), raw untouched.  Returns (changed types, per-type report)."""
    if not enabled(raw):
        return [], {}
    cfg = raw[FLAG]
    radius = float(cfg["radius_um"]) if cfg.get("radius_um") else None
    rounds = int(cfg.get("rounds") or ROUNDS)
    span = float(cfg["span_um"]) if cfg.get("span_um") else None
    rx = re.compile(types or cfg.get("types") or ".")
    RF = _setup(tree)
    import row_normalize
    plan_path = Path(plan_path)
    selected, report = [], {}
    jobs = int(cfg.get("jobs") or 1)
    with row_normalize.in_tree(Path(tree).resolve()):
        P = RF.plan_obj(raw, plan_path)
        todo = [tn for tn in sorted({p["type"] for p in P.parts.values()})
                if rx.search(tn) and not raw["partition_types"][tn].get("hard") and raw["partition_types"][tn].get("clock")]
        if jobs > 1 and len(todo) > 1:
            import multiprocessing as mp
            _SOLVE.update(raw=raw, plan_path=plan_path, radius=radius, rounds=rounds, RF=RF, span=span)
            with mp.get_context("fork").Pool(min(jobs, len(todo))) as pool:
                results = pool.map(_solve_job, todo, chunksize=1)
            for tn, rec, tdict in results:
                if tdict is not None:
                    raw["partition_types"][tn] = tdict
                report[tn] = rec
        else:
            for tn in todo:
                report[tn] = solve_type(raw, plan_path, tn, radius, rounds, RF, span)
    selected = [tn for tn in sorted(report) if report[tn]["status"] == "derive"]
    return selected, report


_SOLVE = {}


def _solve_job(tn):
    g = _SOLVE
    rec = solve_type(g["raw"], g["plan_path"], tn, g["radius"], g["rounds"], g["RF"], g["span"])
    return tn, rec, (g["raw"]["partition_types"][tn] if rec["status"] == "derive" else None)


# ----------------------------------------------------------------------------------------------- ADV check
def findings(raw, plan_path, tree=None, max_lines=20, deadline_s=100.0, types=None, **_kw):
    """plan_advisory-style lines (WARN ADV-TAP-REACH ...), report only"""
    import time
    t0 = time.time()
    try:
        RF = _setup(tree)
        P = RF.plan_obj(raw, plan_path)
        used = sorted({p["type"] for p in P.parts.values()})
        rx = re.compile(types or ".")
        rows, late = [], 0
        for tn in used:
            t = P.types[tn]
            if t.get("hard") or not t.get("clock") or not rx.search(tn):
                continue
            if time.time() - t0 > deadline_s:
                late += 1
                continue
            try:
                r, _ = measure(P, tn, type_radius(t), RF)
            except Exception as e:  # noqa: BLE001
                rows.append(dict(type=tn, error="%s: %s" % (type(e).__name__, str(e)[:80])))
                continue
            rows.append(r)
    except Exception as e:  # noqa: BLE001
        return ["WARN %s not checked: %s: %s" % (CHECK, type(e).__name__, str(e)[:160])]
    bad = sorted((r for r in rows if r.get("over")), key=lambda r: (-r["over300"], -r["over220"], -r["over"], r["type"]))
    lines = ["WARN %s %s: %d seat(s) beyond tap_radius (%d > 220 um, %d > 300 um; max %.0f um at %s; %s); %d/%d taps with sink-box span > 300; "
             "fix = plan flag tap_reach (sink taps per relay column / seat cluster)" % (
                 CHECK, r["type"], r["over"], r["over220"], r["over300"], r["c1_max_um"] or 0, r["c1_worst"],
                 ", ".join("%s %d" % kv for kv in sorted(r["kinds"].items())), r["span_taps_over_300"], r["span_taps"])
             for r in bad[:max_lines]]
    if len(bad) > max_lines:
        lines.append("WARN %s ... %d more type(s)" % (CHECK, len(bad) - max_lines))
    if late:
        lines.append("WARN %s deadline: %d type(s) not checked" % (CHECK, late))
    if bad or late:
        lines.append("WARN %s summary: %d of %d types over radius, %d over 220, %d over 300" % (
            CHECK, len(bad), len(rows), sum(1 for r in bad if r["over220"]), sum(1 for r in bad if r["over300"])))
    return lines


# ------------------------------------------------------------------------------------------------ CLI
_G = {}


def _check_job(tn):
    P, RF = _G["P"], _G["RF"]
    try:
        r, _ = measure(P, tn, type_radius(P.types[tn]), RF)
        return r
    except Exception as e:  # noqa: BLE001
        return dict(type=tn, error="%s: %s" % (type(e).__name__, str(e)[:160]))


def row_main(argv):
    """row_gate.py script row: tap_reach_fix.py --row IN OUT REPORT [--types RE] [--radius U] [--span U] [--jobs N] [--rounds N].
    Only SETS the plan flag (the row IS the intent); row_gate step 3 then derives the taps from the applied plan (it needs the
    tree: the sink bins and the reset tree resolve there).  Idempotent: an existing flag keeps its other keys."""
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("report")
    ap.add_argument("--types")
    ap.add_argument("--radius", type=float)
    ap.add_argument("--span", type=float)
    ap.add_argument("--jobs", type=int)
    ap.add_argument("--rounds", type=int)
    A = ap.parse_args(argv)
    plan = json.loads(Path(A.inp).read_text())
    cfg = dict(plan.get(FLAG) or {})
    cfg["enable"] = 1
    for key, val in (("types", A.types), ("radius_um", A.radius), ("span_um", A.span), ("jobs", A.jobs), ("rounds", A.rounds)):
        if val is not None:
            cfg[key] = val
    plan[FLAG] = cfg
    Path(A.out).write_text(json.dumps(plan, separators=(",", ":")) + "\n")
    Path(A.report).write_text(json.dumps({"config": cfg}, indent=1) + "\n")
    print("tap_reach row: flag set %s" % json.dumps(cfg, sort_keys=True))
    return 0


def main(argv=None):
    if (argv if argv is not None else sys.argv[1:])[:1] == ["--row"]:
        return row_main((argv if argv is not None else sys.argv[1:])[1:])
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("plan")
    c.add_argument("--tree")
    c.add_argument("--types")
    c.add_argument("-j", type=int, default=4)
    c.add_argument("--json")
    f = sub.add_parser("fix")
    f.add_argument("plan")
    f.add_argument("--tree", required=True)
    f.add_argument("--out", required=True)
    f.add_argument("--types")
    f.add_argument("--radius", type=float)
    f.add_argument("-j", type=int, default=1)
    f.add_argument("--span", type=float)
    a = ap.parse_args(argv)
    if a.cmd == "check":
        RF = _setup(a.tree)
        raw = json.loads(Path(a.plan).read_text())
        P = RF.plan_obj(raw, a.plan)
        rx = re.compile(a.types or ".")
        used = [tn for tn in sorted({p["type"] for p in P.parts.values()})
                if rx.search(tn) and not P.types[tn].get("hard") and P.types[tn].get("clock")]
        _G.update(P=P, RF=RF)
        if a.j > 1:
            import multiprocessing as mp
            with mp.get_context("fork").Pool(a.j) as pool:
                rows = pool.map(_check_job, used, chunksize=1)
        else:
            rows = [_check_job(tn) for tn in used]
        tot = dict(types=len(rows), over=sum(1 for r in rows if r.get("over")),
                   over220=sum(1 for r in rows if r.get("over220")), over300=sum(1 for r in rows if r.get("over300")),
                   span_types=sum(1 for r in rows if r.get("span_taps_over_300")), errors=sum(1 for r in rows if r.get("error")))
        doc = dict(check=CHECK, plan=str(a.plan), summary=tot, rows=rows)
        if a.json:
            Path(a.json).write_text(json.dumps(doc, indent=1) + "\n")
        print(json.dumps(tot))
        return 0
    raw = json.loads(Path(a.plan).read_text())
    raw[FLAG] = dict(enable=1, **({"radius_um": a.radius} if a.radius else {}), **({"types": a.types} if a.types else {}),
                    **({"jobs": a.j} if a.j > 1 else {}), **({"span_um": a.span} if a.span else {}))
    selected, report = derive(raw, a.plan, a.tree)
    import row_normalize
    row_normalize.dump(raw, Path(a.out))
    print(json.dumps(dict(changed=selected, report={k: dict(status=v["status"], before=v.get("before"), after=v.get("after"),
                                                           added=len(v.get("added") or []), added_sinks=v.get("added_sinks"),
                                                           blocked=v.get("blocked_seats")) for k, v in report.items()
                                                    if v["status"] != "within reach"}), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

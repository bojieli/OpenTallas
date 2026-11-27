#!/usr/bin/env python3
"""NORMALIZE (COMPOSE-FAST 11-25, OWNER via COORD): rows carry intent only; this pass derives the consequences after ALL rows are
applied, so no lane hand-runs (or forgets) a repair step and no compose breaks on a consequence one row could not see.

Tonight's binds failed on consequences, each found only at the bind (1-3 h a loop): stations changed depth -> fixed_cycles not
re-priced (ISTCYC) and R8 tables stale (R8STALE / R8_STALE, 31 on KV pvw_1: table depth 30, bind 32); moved sinks / cores ->
density added-tap names off the new base count (TAPNAME, then LANDREMAP-UNCHECKED); moved station registers -> their bank sites
left behind, in a core or off the site grid (ADV-SITE-IN-MACRO / SITEGRID).  The standard repairs, in this order:

  plan phase (plan json only, seconds to minutes; `row_normalize.py plan`):
    1 REPRICE  stn_reprice.reprice_raw: every lane whose end-bus station depth moved vs BASE and whose BASE fixed_cycles followed
               source + destination takes the new depth (fixed_cycles + latency fixed / cycles / natural by the same delta).
    2 LEGAL    core_place.resite_station_banks on every type whose internal_stations or hard_cores differ from BASE: a bank whose
               registers moved follows them (unless the row moved the bank itself), then every bank site that is in a core + halo,
               off the CORE_AREA or off the site/row grid goes to the nearest free legal site (the core_place legaliser).
    3 TAPNAME  every clock.tap_mode "density" type the rows touched with clock.added_taps: the added taps are renamed to continue
               from the density base count of the NEW plan (clk_t<nb>..), in order, and an added tap that the moved sinks / cores
               made illegal (outline / halo / tap spacing, the taps.density_taps predicate) moves to the nearest legal 0.054 um site
               (the kv-pv-estrip tapname_fix.py form, for every die and type).
    4 LANDREMAP landing_remap.remap_plan(BASE, plan, resets="anchor") on the types whose tap set changed, while the references still
               carry the OLD tap names (KV-SINKBINS 11-25); the sections it rewrote (landing raw branches / reader / writer starts / local
               resets, landing pin source taps) are kept and restored after RETAP, so no name is mapped twice.
    5 RETAP    retap.repoint(BASE, plan): every type whose tap set (names, sites) changed vs BASE gets its tap-named references
               (landing contract source taps, consumer new_reset, per-port tap offsets / windows) re-pointed to the nearest new tap
               and its own published collector tree re-solved.
  tables phase (needs bus_groups.json from `bind.py r8-prepass`, the bind head; `row_normalize.py tables`):
    6 R8       r8_refresh.py: the as-built land_r8 table and every land_r8_extra table re-derived from this plan's bind head, ALWAYS
               before the bind (R8 drift is reported as fixed, never left for the strict bind to find as R8_STALE).

Each step only touches what differs from BASE; a plan equal to BASE is returned byte-equal (no step fires).  Every step writes
a report row; nothing is silently dropped.  --skip STEP leaves one out (reprice, legal, tapname, landremap, retap).

  row_normalize.py plan --base BASE --in PLAN --out OUT --tree TREE [--report R.json] [--skip STEP ...]
  row_normalize.py tables --plan PLAN --tree TREE --asbuilt AB --bus-groups OUT/bus_groups.json [--report R.json]
TREE = the tree the plan's repository-relative inputs resolve in (the gate's launch tree)."""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import math
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

STEPS = ("reprice", "legal", "tapname", "landremap", "retap")
TAP_STEP_UM = 0.054


def _pt(raw):
    return raw.get("partition_types") or {}


def touched_types(raw, braw):
    """types whose partition_types entry differs from BASE (new types included), in plan order"""
    b = _pt(braw)
    return [tn for tn, t in _pt(raw).items() if b.get(tn) != t]


# ------------------------------------------------------------------ 1 REPRICE
def step_reprice(raw, braw):
    import stn_reprice as SR
    return {k: list(v) for k, v in SR.reprice_raw(raw, braw).items()}


# ------------------------------------------------------------------ 2 LEGAL
_BANK_KEYS = ("bit_sites_um", "face_bit_sites_um")


def _bank_base(b, t):
    """the BASE type as the legaliser should see it: a station row whose bank sites the row moved itself takes its own regs / to
    as base (no follow shift: the row already placed the bank); other rows keep the BASE regs (the bank follows the move)"""
    bb = copy.deepcopy(b)
    bst, nst = bb.get("internal_stations") or [], t.get("internal_stations") or []
    for i, s in enumerate(nst):
        if i < len(bst) and bst[i].get("conn") == s.get("conn") and any(bst[i].get(k) != s.get(k) for k in _BANK_KEYS):
            for k in ("regs_um", "to_um"):
                if k in s:
                    bst[i][k] = copy.deepcopy(s[k])
    return bb


def step_legal(raw, braw, types, resite=None):
    """core_place legaliser on the touched types whose stations or cores moved -> {type: report}"""
    if resite is None:
        import core_place as CP
        resite = CP.resite_station_banks
    out = {}
    for tn in types:
        t, b = _pt(raw).get(tn), _pt(braw).get(tn) or {}
        if not isinstance(t, dict) or not t.get("outline_um"):
            continue
        if t.get("internal_stations") == b.get("internal_stations") and t.get("hard_cores") == b.get("hard_cores"):
            continue
        if not any(s.get(k) for s in t.get("internal_stations") or [] for k in _BANK_KEYS):
            continue
        t_new, r = copy.deepcopy(t), {}
        resite(_bank_base(b, t), t_new, r)
        if t_new != t:
            raw["partition_types"][tn] = t_new
            out[tn] = dict(r, changed=True)
        elif r.get("bank_failed"):
            out[tn] = dict(r, changed=False)
    return out


# ------------------------------------------------------------------ 3 TAPNAME
@contextlib.contextmanager
def in_tree(tree):
    """cwd + $OT_REPO_ROOT = TREE while the tap / reset solvers read the plan's repository-relative inputs"""
    here, old = os.getcwd(), os.environ.get("OT_REPO_ROOT")
    if tree:
        os.chdir(tree)
        os.environ["OT_REPO_ROOT"] = str(Path(tree).resolve())
    try:
        yield
    finally:
        os.chdir(here)
        if old is None:
            os.environ.pop("OT_REPO_ROOT", None)
        else:
            os.environ["OT_REPO_ROOT"] = old


def _density_types(raw, types):
    return [tn for tn in types if isinstance(_pt(raw).get(tn), dict)
            and ((_pt(raw)[tn].get("clock") or {}).get("tap_mode") == "density") and (_pt(raw)[tn]["clock"].get("added_taps"))]


def _real_tap_fns(raw, plan_path):
    """(base_count(tn), legal_factory(tn) -> legal(x, y), taken list) on the real taps / schema solvers"""
    import schema
    import taps as TP
    from placement_obstacles import placement_boxes
    P = schema.Plan(json.loads(json.dumps(raw)), Path(plan_path).absolute())
    cache = {}

    def base(tn):
        if tn not in cache:
            cache[tn] = TP._density_base(P, tn)
        return cache[tn]

    def legal_for(tn):
        tt = P.types[tn]
        w, h = tt["outline_um"]
        clear, eps = schema.type_tap_clear(tt), 1e-8
        boxes = list(placement_boxes(tt, halo=clear).values())
        boxes += [(a - clear, b - clear, c + clear, d + clear) for a, b, c, d in (tt.get("clock") or {}).get("keepouts_um", [])]
        taken = [(x, y) for _, x, y, _ in schema.core_taps(P, tn)] + [(q[1], q[2]) for q in base(tn)]

        def legal(x, y):
            return (clear - eps <= x <= w - clear + eps and clear - eps <= y <= h - clear + eps
                    and not any(abs(x - a) < clear - eps and abs(y - b) < clear - eps for a, b in taken)
                    and not any(a + eps < x < c - eps and b + eps < y < d - eps for a, b, c, d in boxes))
        return legal, taken
    return (lambda tn: len(base(tn))), legal_for


def _nearest_legal(x, y, legal, rmax=1200):
    for r in range(1, rmax):
        cand = [(x + i * TAP_STEP_UM, y + j * TAP_STEP_UM) for i in range(-r, r + 1) for j in (-r, r)]
        cand += [(x + i * TAP_STEP_UM, y + j * TAP_STEP_UM) for j in range(-r + 1, r) for i in (-r, r)]
        cand = [c for c in cand if legal(*c)]
        if cand:
            return min(cand, key=lambda c: abs(c[0] - x) + abs(c[1] - y))
    return None


def step_tapname(raw, types, plan_path=None, base_count=None, legal_for=None):
    """rename density added taps from the new base count; move illegal ones to the nearest legal site -> {type: report}"""
    dts = _density_types(raw, types)
    if not dts:
        return {}
    if base_count is None or legal_for is None:
        bc, lf = _real_tap_fns(raw, plan_path)
        base_count, legal_for = base_count or bc, legal_for or lf
    out = {}
    for tn in dts:
        added = raw["partition_types"][tn]["clock"]["added_taps"]
        nb = base_count(tn)
        exp = [f"clk_t{nb + i}" for i in range(len(added))]
        old = [str(a.get("name")) for a in added]
        rec = {}
        if old != exp:
            for a, e in zip(added, exp):
                a["name"] = e
            rec.update(base=nb, renamed=sum(1 for o, e in zip(old, exp) if o != e), first=[old[0], exp[0]])
        legal, taken = legal_for(tn)
        moved = []
        for a in added:
            x, y = map(float, a["xy"])
            if not legal(x, y):
                best = _nearest_legal(x, y, legal)
                if best is None:
                    rec["failed"] = f"{a['name']}: no legal site within {1200 * TAP_STEP_UM:.0f} um of {x},{y}"
                    taken.append((x, y))
                    continue
                a["xy"] = [round(best[0], 4), round(best[1], 4)]
                moved.append([a["name"], [x, y], a["xy"]])
                x, y = best
            taken.append((x, y))
        if moved:
            rec.update(relegalised=len(moved), moved=moved[:6])
        if rec:
            out[tn] = rec
    return out


# ------------------------------------------------------------------ 4 LANDREMAP + 5 RETAP
LANDREMAP_KEYS = ("landing_raw_branches", "landing_reader_start", "landing_writer_start", "landing_local_resets")


def _init_tap_readers(readers):
    global _tap_readers
    _tap_readers = readers


def _solve_tap_row(task):
    side, tn = task
    try:
        return side, tn, _tap_readers[side](tn)
    except Exception:  # Let the original call raise in canonical row order.
        return side, tn, None


def tap_readers(braw, raw, base_path, plan_path, types):
    import retap as RT
    from functools import cache

    stock = (RT._plan_taps(braw, str(base_path)), RT._plan_taps(raw, str(plan_path)))
    maps = [{}, {}]
    if os.environ.get("OT_NORMALIZE_POOL") == "1" and len(types) > 1:
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor
        from threading import active_count
        from bind_emit_par import allocated_cpus
        import reset_tree

        # These modes can start a common wavefront solve from a tap read.
        # Leave them on the stock shared Plan readers instead of duplicating it.
        def local(typ):
            clock = (typ or {}).get("clock") or {}
            return not clock.get("control_sinks") and clock.get("tap_mode") not in ("grid+explicit", "grid+sinks", "sinks")

        names = [tn for tn in types if tn in _pt(braw)
                 and local(_pt(braw)[tn]) and local(_pt(raw)[tn])]
        jobs = min(allocated_cpus(), reset_tree.pool_size(len(names) * 2))
        if (jobs > 1 and "fork" in multiprocessing.get_all_start_methods()
                and multiprocessing.parent_process() is None and active_count() == 1):
            try:
                tasks = [(side, tn) for side in range(2) for tn in names]
                with ProcessPoolExecutor(max_workers=jobs, mp_context=multiprocessing.get_context("fork"),
                                         initializer=_init_tap_readers, initargs=(stock,)) as pool:
                    for side, tn, result in pool.map(_solve_tap_row, tasks):
                        if result is not None:
                            maps[side][tn] = result
            except (OSError, RuntimeError):
                pass

    def reader(side):
        @cache
        def read(tn):
            return maps[side][tn] if tn in maps[side] else stock[side](tn)
        return read
    return reader(0), reader(1)


def tapset_changed(braw, raw, base_path, plan_path, types, *, readers=None):
    """the touched types whose tap set (names, sites) differs from BASE (the retap rule)"""
    to, tn_ = readers or tap_readers(braw, raw, base_path, plan_path, types)
    key = lambda ts: [(n, round(x, 6), round(y, 6)) for n, x, y in ts]  # noqa: E731
    out = []
    for tn in types:
        if tn in _pt(braw) and key(to(tn)) != key(tn_(tn)):
            out.append(tn)
    return out


def _protect(t):
    ck = t.get("clock") or {}
    lc = ck.get("landing_contract") or {}
    keep = {"pins": [(q.get("source_clock_port"), q.get("source_clock_tap")) for q in lc.get("pins") or []]}
    keep.update({k: copy.deepcopy(ck[k]) for k in LANDREMAP_KEYS if k in ck})
    return keep


def _restore(t, keep):
    ck = t.setdefault("clock", {})
    for q, (sp, st) in zip((ck.get("landing_contract") or {}).get("pins") or [], keep["pins"]):
        if sp is not None:
            q["source_clock_port"] = sp
        if st is not None:
            q["source_clock_tap"] = st
    for k, v in keep.items():
        if k != "pins":
            ck[k] = v


def step_landremap(braw, raw, tree, plan_path, types):
    """landing_remap.remap_plan (anchor resets) on the types whose tap set changed, BEFORE retap, while every tap reference still
    carries the OLD names (KV-SINKBINS 11-25: retap first left 23 DERIVEDNAME stale rst_rl_<k>; anchor mode refuses renamed refs)
    -> ({type: n records} or {type: {failed}}, protected sections to restore after retap)"""
    if not types:
        return {}, {}
    import landing_remap as LM
    # LANDREMAP-ISOLATE-1125: remap_plan raises on the first bad type and may have rewritten earlier types already.  Restore
    # the plan, drop the type the error names ("<type>: ..."), re-run the rest; an error naming no type fails them all.
    failed, todo = {}, list(types)
    snap = copy.deepcopy(raw)
    while todo:
        try:
            rec = LM.remap_plan(braw, raw, str(tree or os.getcwd()), Path(plan_path).parent, set(todo), resets="anchor", bound_old=True)
            break
        except Exception as e:  # noqa: BLE001 - named, fails the gate (fail closed)
            raw.clear()
            raw.update(copy.deepcopy(snap))
            msg = f"landing_remap {type(e).__name__}: {str(e)[:300]}"
            bad = [tn for tn in todo if str(e).startswith(f"{tn}:")]
            for tn in bad or todo:
                failed[tn] = {"failed": msg}
            todo = [tn for tn in todo if tn not in failed]
    if not todo:
        return failed, {}
    prot = {tn: _protect(_pt(raw)[tn]) for tn in todo}
    n = {tn: sum(1 for k in ("resets", "taps", "anchors") for x in rec.get(k) or [] if tn in json.dumps(x)) for tn in todo}
    return {**n, **failed}, prot


def _init_base_reset_worker(raw, path):
    global _base_reset_context
    _base_reset_context = raw, path


def _solve_base_reset_trees(types):
    import retap as RT
    read = RT._plan_tree(*_base_reset_context)
    return {tn: read(tn) for tn in types}


def _prepare_base_reset_trees(stack, braw, raw, base_path, changed):
    """Start the immutable BASE trees while LANDREMAP solves the new geometry."""
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor
    from bind_emit_par import allocated_cpus
    import landing_remap as LM
    import reset_anchor as RA
    import reset_tree
    import retap as RT

    if not changed or "fork" not in multiprocessing.get_all_start_methods():
        return {}
    # These LANDREMAP paths have all OLD anchor information in the existing
    # receipt and compute a new tree. RETAP later needs the canonical OLD solve
    # to determine ownership of its published collector tree.
    try:
        if min(allocated_cpus(), reset_tree.pool_size(2)) < 2:
            return {}
        if any(not RA.refs(_pt(raw)[tn]) or (_pt(raw)[tn].get("clock") or {}).get("landing_raw_branches")
               or not LM.bound_old_tree(tn, _pt(braw)[tn]) for tn in changed):
            return {}
        eligible = [tn for tn in changed if RT._published(_pt(braw)[tn]) is not None]
    except (AttributeError, KeyError, TypeError, ValueError):
        # The canonical steps still diagnose malformed input in their usual order.
        return {}
    if not eligible:
        return {}
    try:
        pool = stack.enter_context(ProcessPoolExecutor(
            max_workers=1, mp_context=multiprocessing.get_context("fork"),
            initializer=_init_base_reset_worker, initargs=(braw, str(base_path)),
        ))
        future = pool.submit(_solve_base_reset_trees, eligible)
    except (OSError, RuntimeError):
        return {}
    return dict.fromkeys(eligible, future)


def step_retap(braw, raw, base_path, plan_path, types, protect=None, *, base_trees=None, old_taps=None, close_base=None):
    """Repoint taps while preserving landing-remapped refs for the final START reach pass."""
    from functools import cache
    import retap as RT

    parallel = os.environ.get("OT_NORMALIZE_POOL") == "1"

    def plan_tree(context, path, names):
        return RT._plan_tree(context, path, names) if names else RT._plan_tree(context, path)

    def tree_factory(context, path, names=()):
        if context is not braw:
            # All old ownership reads are complete before REPUBLISH builds
            # the candidate tree, so its pool need not coexist with ours.
            if close_base is not None:
                close_base()
            return plan_tree(context, path, names)
        fallback = cache(lambda: plan_tree(context, path, [tn for tn in names if tn not in base_trees]))

        def read(tn):
            if tn in base_trees:
                try:
                    return base_trees[tn].result()[tn]
                except Exception:
                    # Preserve the original solver/verdict if the worker could
                    # not prepare the BASE result under its current lease.
                    pass
            return fallback()(tn)
        return read

    def tap_factory(context, path):
        return old_taps if context is braw else RT._plan_taps(context, path)

    def restore_landing_refs():
        for tn, keep in protect.items():
            _restore(_pt(raw)[tn], keep)
        return protect.keys()

    base_trees = base_trees or {}
    kwargs = {"prepare_tree_fn": tree_factory} if parallel else {"tree_fn": tree_factory if base_trees else None}
    if old_taps:
        kwargs.update(taps_fn=tap_factory, ctaps_fn=RT._plan_consumer_taps)
    if protect:
        kwargs["before_repick"] = restore_landing_refs
    rep = RT.repoint(braw, raw, str(base_path), str(plan_path), types=set(types), **kwargs)
    return {tn: len(ch) for tn, ch in rep.items()}


def normalize_plan(braw, raw, tree=None, base_path=None, plan_path=None, skip=(), hooks=None):
    """all plan-phase steps on raw (in place) -> report"""
    hooks = hooks or {}
    skip = {s.lower() for s in skip}
    rep = dict(steps={}, seconds={})
    types = touched_types(raw, braw)
    rep["touched_types"] = types
    prot = {}
    base_trees = {}
    old_taps = None
    with in_tree(tree), contextlib.ExitStack() as workers:
        # Scope the solver policy to normalized plans. Standalone readers keep
        # their existing behavior, and zero is the serial control for this path.
        if "OT_NORMALIZE_POOL" not in os.environ:
            os.environ["OT_NORMALIZE_POOL"] = "1"
            workers.callback(os.environ.pop, "OT_NORMALIZE_POOL", None)
        base_workers = workers.enter_context(contextlib.ExitStack())
        if isinstance(raw.get("land_reach"), dict) and raw["land_reach"].get("enable") and "landreach" not in skip:
            # C-LAND-REACH (default off, plan flag land_reach.enable): re-seat flagged hard cland cores before the steps that read seats
            import land_reach as LR
            t0 = time.time()
            lr = LR.apply(raw, tree)
            rep["steps"]["landreach"] = {f"{m['type']}/{m['landing']}": m["shift_um"] for m in lr["moved"]}
            rep["landreach"] = lr
            rep["seconds"]["landreach"] = round(time.time() - t0, 1)
            if lr["moved"]:           # the re-seated types are changed types now: legal / tapname / landremap / retap must see them
                types = touched_types(raw, braw)
                rep["touched_types"] = types
        for name in STEPS:
            t0 = time.time()
            if name in skip:
                rep["steps"][name] = "skipped"
                continue
            if name == "reprice":
                r = step_reprice(raw, braw)
            elif name == "legal":
                r = step_legal(raw, braw, types, resite=hooks.get("resite"))
            elif name == "tapname":
                r = step_tapname(raw, types, plan_path, hooks.get("base_count"), hooks.get("legal_for"))
            elif name == "landremap":
                if "landremap" in hooks:
                    r, prot = hooks["landremap"](braw, raw, types)
                else:
                    readers = None
                    if types and os.environ.get("OT_NORMALIZE_POOL") == "1":
                        readers = tap_readers(braw, raw, base_path, plan_path, types)
                        old_taps = readers[0]
                    ch = tapset_changed(braw, raw, base_path, plan_path, types, readers=readers) if types else []
                    if "retap" not in skip and "retap" not in hooks:
                        base_trees = _prepare_base_reset_trees(base_workers, braw, raw, base_path, ch)
                    r, prot = step_landremap(braw, raw, tree, plan_path, ch)
            else:
                if "retap" in hooks:
                    r = hooks["retap"](braw, raw, types)
                    for tn, keep in prot.items():
                        _restore(_pt(raw)[tn], keep)
                else:
                    r = (step_retap(braw, raw, base_path, plan_path, types, prot,
                                    base_trees=base_trees, old_taps=old_taps,
                                    close_base=base_workers.close if old_taps else None) if types else {})
            rep["steps"][name] = r
            rep["seconds"][name] = round(time.time() - t0, 1)
    rep["changed"] = {k: len(v) for k, v in rep["steps"].items() if isinstance(v, dict) and v}
    return rep


# ------------------------------------------------------------------ 5 R8 (tables)
def _sha(p):
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]
    except OSError:
        return None


def r8_tables(tree, asbuilt):
    ab = json.loads((Path(tree) / asbuilt if not Path(asbuilt).is_absolute() else Path(asbuilt)).read_text())
    if not ab.get("land_r8"):
        return None, []
    rel = lambda p: Path(p) if Path(p).is_absolute() else Path(tree) / p  # noqa: E731
    return rel(ab["land_r8"]), [rel(x) for x in ab.get("land_r8_extra") or []]


def normalize_tables(plan, tree, asbuilt, bus_groups, *, pin_pre=None, pin_extra=0):
    """Refresh the as-built R8 tables, preserving an explicitly supplied pin policy."""
    import r8_refresh as RR
    table, extras = r8_tables(tree, asbuilt)
    if table is None:
        return dict(r8="no land_r8 in the as-built", rc=0, fixed={})
    before = {str(p): _sha(p) for p in [table] + extras}
    abp = Path(asbuilt) if Path(asbuilt).is_absolute() else Path(tree) / asbuilt
    buf = io.StringIO()
    argv = [str(plan), str(bus_groups), str(table), "--asbuilt", str(abp), "--root", str(tree)]
    if pin_pre is not None:
        argv += ["--pin-pre", str(pin_pre), "--pin-extra", str(pin_extra)]
    with contextlib.redirect_stdout(buf):
        rc = RR.main(argv)
    after = {p: _sha(p) for p in before}
    fixed = {os.path.relpath(p, tree): [before[p], after[p]] for p in before if before[p] != after[p]}
    return dict(rc=rc, fixed=fixed, tables=len(before), log=buf.getvalue()[-1500:],
                r8=(f"R8 drift fixed in {len(fixed)} of {len(before)} table(s)" if fixed else f"R8 tables current ({len(before)})")
                if rc == 0 else f"R8 refresh FAILED rc {rc}")


def dump(raw, path):
    tmp = Path(str(path) + ".norm.tmp")
    tmp.write_text(json.dumps(raw, indent=1, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--base", required=True)
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--tree")
    p.add_argument("--report")
    p.add_argument("--skip", action="append", default=[], choices=STEPS)
    t = sub.add_parser("tables")
    t.add_argument("--plan", required=True)
    t.add_argument("--tree", required=True)
    t.add_argument("--asbuilt", required=True)
    t.add_argument("--bus-groups", required=True)
    t.add_argument("--report")
    a = ap.parse_args(argv)
    if a.cmd == "plan":
        braw = json.loads(Path(a.base).read_text())
        text = Path(a.inp).read_text()
        raw = json.loads(text)
        rep = normalize_plan(braw, raw, a.tree, Path(a.base).absolute(), Path(a.out).absolute(), a.skip)
        if rep["changed"]:
            dump(raw, a.out)
        elif os.path.abspath(a.inp) != os.path.abspath(a.out):
            Path(a.out).write_text(text)
        print(f"NORMALIZE plan: {len(rep['touched_types'])} touched type(s); changed {rep['changed'] or 'nothing'}; "
              f"seconds {rep['seconds']}")
        rc = 3 if any(isinstance(v, dict) and any(isinstance(x, dict) and (x.get("failed") or x.get("bank_failed")) for x in v.values())
                      for v in rep["steps"].values()) else 0
    else:
        rep = normalize_tables(a.plan, a.tree, a.asbuilt, a.bus_groups)
        print(f"NORMALIZE tables: {rep['r8']}" + "".join(f"\n  {k}: {v[0]} -> {v[1]}" for k, v in rep["fixed"].items()))
        rc = rep["rc"]
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1, default=str) + "\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())

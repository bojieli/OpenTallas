#!/usr/bin/env python3
"""RETAP (QC-PLAN-R3, COORD 11-20): re-point tap-named plan references after a type's clock taps are re-derived.

clock.tap_mode "density" (and the other derived modes) solve the taps from clock.sink_bins_file, so new sink bins
(e.g. sink_bins_from_place.py from a placed kit) renumber and move the taps clk_t<i>.  Two kinds of plan rows name taps
literally and go stale in the same step: N46V0 bind EMIT 'forwarded clock source clk_t134 is not a planned physical
tap input' (clock.landing_contract out clock pins source_clock_port / source_clock_tap) on 3 QC types, and EMIT
'rst_n_t0: emitted/published reset edge mismatch' (reset.consumer_localization new_reset rst_n_t<i>, the terminal
reset relay of tap i) on sle_sc_v2 / sle_sc_v3.  The second one is also a stale PUBLISHED reset tree:
clock.landing_contract.collector_tree is a snapshot of reset_tree.for_type taken on the old taps, while the bind
emits the relays of the tree it re-solves on the new taps (tap 0 and its edges included), so reset_consumers.localize
finds the emitted relay d != the published d.

repoint(old_raw, new_raw, old_plan_path, new_plan_path) maps every tap of the OLD tap set to the NEW tap nearest its old
site (Manhattan, ties by name: the rule of type_split._remap_clock_sources) and rewrites both kinds of reference in
new_raw in place.  Types whose tap set (names and sites) is unchanged are not touched, so an unchanged plan is
byte-identical.  In the same step every type whose tap set changed and that publishes a (soft) collector_tree gets
it re-solved on the new plan (reset_tree.for_type, the tree the bind emits) and republished, the rule of
type_split._reset_trees / added_tap_recentre.republish: only where the published tree IS reset_tree.for_type of the old
plan (a tree built another way, e.g. the cb landing collector form with entry / core_resets, or an already stale
snapshot, is left as is and reported as tree_not_own, never overwritten).  Reset relay names rst_rl_<k> that other plan rows name are
re-picked at bind by reset_anchor.py; not here.

TAPOFF-RETAP (QC-CB-SPREAD-R2 11-24, COORD: C1m PRE TAPOFF-MISSING x28 after CB-TAPBINS): the die per-port clock rows
(clock.tap_offset.per_port_ps / clock.tap_window.per_port_ps, keyed type -> tap name) name taps too.  In the same step, every type
whose tap set changed gets its row rebuilt on the new taps (tapoff=True, the default): a new tap at an unchanged site keeps its row;
a moved / new tap takes the row of the OLD tap nearest its site (the tap_map rule; a row kept by NAME would time a renumbered tap
at another tap's offset), offsets form tol = max(that row's tol, the old table's leave-one-out p95 of the nearest-other-tap
estimate, ceil 0.1 ps), window form = the largest window of the 3 nearest old taps; rows of names that are no longer taps go
(core clk_c* rows are never touched).  Then tap_offset_cover.fill closes whatever is still missing, so PRE TAPOFF-MISSING reads 0.
The rows are estimates until die_sta_related --kit-offset-out / tap_window_measure re-measure.  --no-tapoff keeps the old behaviour.

RRDRV-FAR (COORD 11-25; QC-RRDRV-FIX b6140412608d, QC-STB-SPLIT stb_rrfar.py, KV-OWN-HG-R2 hgi_v6): the tap map above
numbers START raw resets on the clock tap census (taps_fn), but the bind numbers rr_t<i> / rst_n_t<i> on the reset tree's
consumer taps (reset_tree.consumer_taps: clock taps + reset.local_taps_um).  A shift by the tap count (or a landing_remap
restore of the old names) then leaves a raw past the tree (no wavefront driver: PRE RSTREACH RRDRV) or 700-1167 um away.
repick_start_raws() runs last in repoint() on every re-tapped type whose tree is its own, and callers that restore START
sections after repoint (landing_remap anchor restore) call it again after the restore: every clock.landing_{reader,writer}_start
stage raw_reset and clock.landing_local_resets raw named rr_t<N> / rst_n_t<N> with N past the consumer taps or more than
far_um (300) from its stage site is re-picked to the consumer tap nearest the stage (Manhattan, ties lower index), prefix kept.
landing_raw_branches role stages are skipped (the bind re-derives them); rst_rl_<k> relay names are reset_anchor's.  All consumer
taps release at the same wavefront depth, so the re-pick adds 0 cycles.  --no-repick-far turns it off.

  retap.py OLD_PLAN NEW_PLAN OUT [--report R.json] [--types a,b] [--no-tapoff]
  sink_bins_from_place.py apply PLAN OUT --bins TYPE=FILE ... calls repoint in the same step.
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAPQ = re.compile(r"^rst_n_t(\d+)$")
RAWQ = re.compile(r"^rr_t(\d+)$")
START_KEYS = ("landing_writer_start", "landing_reader_start", "landing_local_resets")
FWD_KEYS = ("source_clock_port", "source_clock_tap")
FAR_UM = 300.0


class RetapError(ValueError):
    pass


def tap_index(name):
    """'clk' -> 0, 'clk_t<i>' -> i (the reset tree names its terminal relay of tap i rst_n_t<i>)."""
    if name == "clk":
        return 0
    m = re.fullmatch(r"clk_t(\d+)", name)
    return int(m.group(1)) if m else None


def tap_map(old, new):
    """{old tap name: new tap name}, nearest new site to each old site (Manhattan, ties by name).  old/new: [(n, x, y)]."""
    if not new:
        raise RetapError("new tap set is empty")
    return {n: min(new, key=lambda s: (abs(s[1] - x) + abs(s[2] - y), s[0]))[0] for n, x, y in old}


def repoint_type(t, old, new, reset=True):
    """Rewrite the tap references of type dict t (in place) from tap set old to new: forwarded clock sources always,
    tap-indexed reset names when reset (see below).  -> [[where, key, was, now, um]]"""
    key = lambda ts: [(n, round(x, 6), round(y, 6)) for n, x, y in ts]  # noqa: E731
    if key(old) == key(new):
        return []
    m, site, nsite = tap_map(old, new), {n: (x, y) for n, x, y in old}, {n: (x, y) for n, x, y in new}
    names = set(nsite)
    um = lambda a, b: round(abs(site[a][0] - nsite[b][0]) + abs(site[a][1] - nsite[b][1]), 3)  # noqa: E731
    out = []
    for q in t.get("clock", {}).get("landing_contract", {}).get("pins", []) or []:
        if q.get("kind") != "clock" or q.get("dir") != "out":
            continue
        for k in FWD_KEYS:
            s = q.get(k)
            if not s or s == "clk" or (s in names and s in site and m[s] == s):
                continue
            if s not in site:
                if s in names:
                    continue
                raise RetapError(f"pin {q.get('name')} {k} {s} is neither an old nor a new tap")
            out.append([f"landing_contract.{q.get('name')}", k, s, m[s], um(s, m[s])])
            q[k] = m[s]
    if not reset:
        return out
    # Tap-indexed RESET names: rst_n_t<i> (terminal relay of tap i: reset.consumer_localization new_reset,
    # landing_contract collector_children / collector_local_sources node, ...) and rr_t<i> (its raw copy: START
    # transport stages raw_reset, local resets raw).  They name nodes of the type's reset tree, so they move with the
    # taps ONLY when that tree is re-solved on the new taps (reset=True: no published tree, or an own tree that
    # repoint() republishes).  A type that keeps a foreign / stale published tree keeps its names (they name that tree;
    # N46V0G bind: re-pointing them gave 'writer START raw reset rr_t125 has no registered wavefront driver').
    # The published collector_tree itself is replaced whole, never walked; rst_rl_<k> stays with reset_anchor at bind.
    by_idx = {tap_index(n): n for n in site}
    nidx = {n: tap_index(n) for n in nsite}

    def walk(o, where):
        items = list(o.items()) if isinstance(o, dict) else list(enumerate(o)) if isinstance(o, list) else ()
        for k, v in items:
            if isinstance(o, dict) and k == "collector_tree":
                continue
            w = f"{where}.{k}" if isinstance(o, dict) else where
            if isinstance(v, str):
                g = TAPQ.match(v) or RAWQ.match(v)
                if not g:
                    continue
                i = int(g.group(1))
                oi = by_idx.get(i)
                if oi is not None:
                    ni, d_um = nidx[m[oi]], um(oi, m[oi])
                elif i >= len(old) and not w.startswith("reset."):
                    # reset-tree outputs (rst_o seams) follow the consumer taps: index n_taps + j (sle_sc_v3
                    # collector_children node rst_n_t69 with 69 taps); they shift with the tap count.  A localized
                    # consumer (reset.*) lands on a tap, so an unknown index there fails closed.
                    ni, d_um = i - len(old) + len(new), 0.0
                else:
                    raise RetapError(f"{w}: {v}: no tap {i} in the old tap set")
                now = ("rst_n_t" if v.startswith("rst_n_t") else "rr_t") + str(ni)
                if now != v:
                    out.append([w.lstrip("."), k if isinstance(o, dict) else "item", v, now, d_um])
                    o[k] = now
                    if isinstance(o, dict) and o.get("tap") == i:
                        o["tap"] = ni
            elif isinstance(v, (dict, list)):
                walk(v, w)
    for sec in ("clock", "reset"):
        if sec in t:
            walk(t[sec], sec)
    return out


def tap_rename_map(old, new):
    """explicit old -> new tap rename map of one type (KV-SINKBINS 11-25): the tool's own rule (tap_map: nearest NEW site to each OLD
    site, Manhattan, ties by name) for every OLD tap whose name is not a NEW tap; names that are in both grids map to themselves and
    are left out.  old/new: [(name, x, y)].  Consumers rename with apply_rename and never guess: a clk_t name in neither grid is an error."""
    live = {n for n, _, _ in new}
    return {o: n for o, n in tap_map(old, new).items() if o not in live}


def apply_rename(names, rename, live, where=""):
    """rename every name of `names` (a list, in place) through `rename`; a clk_t<i> name that is neither renamed nor live raises
    RetapError naming `where` and the name (never guessed)"""
    for i, v in enumerate(names):
        if isinstance(v, str) and re.match(r"^clk_t\d+$", v) and v not in live:
            if v not in rename:
                raise RetapError(f"{where}: tap {v} is in neither the old nor the new tap grid (no rename)")
            names[i] = rename[v]
    return names


def _plan_taps(raw, path):
    sys.path.insert(0, str(HERE))
    import schema
    P = schema.Plan(json.loads(json.dumps(raw)), path)
    return lambda tn: [(n, float(x), float(y)) for n, x, y in schema.tap_grid(P, tn)]


def _plan_tree(raw, path):
    sys.path.insert(0, str(HERE))
    import schema
    import reset_tree as RT
    P = schema.Plan(json.loads(json.dumps(raw)), path)
    return lambda tn: json.loads(json.dumps(RT.for_type(P, tn)))


def _norm(o):
    return json.dumps(o, sort_keys=True)


def _published(t):
    lc = t.get("clock", {}).get("landing_contract") or {}
    tree = lc.get("collector_tree")
    if tree is None or t.get("hard") or (isinstance(tree, dict) and tree.get("hard")):
        return None
    return tree


def republish_tree(t, new_tree):
    """set t's landing collector_tree to new_tree (in place) -> [[where, key, was, now, n]] (empty when equal)"""
    old = t["clock"]["landing_contract"]["collector_tree"]
    if _norm(old) == _norm(new_tree):
        return []
    key = lambda r: (r.get("q"), r.get("d"))  # noqa: E731
    ko = {key(r) for r in old.get("relays", [])}
    kn = {key(r) for r in new_tree.get("relays", [])}
    t["clock"]["landing_contract"]["collector_tree"] = new_tree
    return [["landing_contract.collector_tree", "relays", len(old.get("relays", [])), len(new_tree.get("relays", [])),
             len(kn - ko)]]


def _reset_inputs(t):
    """the parts of a type the reset tree is solved from, minus the published tree itself (clock without landing_contract.collector_tree, reset)"""
    ck = json.loads(json.dumps(t.get("clock") or {}))
    (ck.get("landing_contract") or {}).pop("collector_tree", None)
    return _norm({"clock": ck, "reset": t.get("reset")})


CORE_RE = re.compile(r"^clk_c")


def _tapoff_tables(raw):
    ck = raw.get("clock") or {}
    off = (ck.get("tap_offset") or {}).get("per_port_ps") or {}
    win = (ck.get("tap_window") or {}).get("per_port_ps") or {}
    return off, win


def _ceil1(v):
    import math
    return math.ceil(v * 10 - 1e-9) / 10.0


def _near(xy, pts, k=1):
    return sorted(pts, key=lambda q: (abs(q[1] - xy[0]) + abs(q[2] - xy[1]), q[0]))[:k]


def carry_tapoff(old_raw, new_raw, tn, old, new):
    """Rebuild new_raw's per-port clock row of type tn on the new tap set (see TAPOFF-RETAP) -> [report row] or []."""
    off_o, win_o = _tapoff_tables(old_raw)
    off_n, win_n = _tapoff_tables(new_raw)
    form = "offset" if off_o.get(tn) else ("window" if win_o.get(tn) else None)
    if form is None:
        return []
    src = (off_o if form == "offset" else win_o)[tn]
    dst = (off_n if form == "offset" else win_n).setdefault(tn, {})
    osite = {n: (x, y) for n, x, y in old}
    listed = [(n, x, y) for n, x, y in old if n in src]
    if not listed:
        return []
    p95 = 0.0
    if form == "offset" and len(listed) > 1:
        err = []
        for i, (n, x, y) in enumerate(listed):
            m = _near((x, y), listed[:i] + listed[i + 1:])[0][0]
            for c in ("TT", "FF"):
                err.append(abs(float(src[m][c]) - float(src[n][c])))
        err.sort()
        p95 = err[min(len(err) - 1, int(0.95 * len(err)))]
    names = {n for n, _, _ in new}
    kept = carried = removed = 0
    for n, x, y in new:
        if n in src and osite.get(n) == (x, y):
            dst[n] = copy.deepcopy(src[n])
            kept += 1
            continue
        if form == "offset":
            m = _near((x, y), listed)[0][0]
            row = dict(src[m])
            row["tol"] = _ceil1(max(float(row.get("tol", 0.0)), p95))
        else:
            row = max((src[m] for m, _, _ in _near((x, y), listed, 3)), key=lambda v: float(v if not isinstance(v, dict) else max(v.values())))
            row = copy.deepcopy(row)
        dst[n] = row
        carried += 1
    for n in list(dst):
        if n not in names and not CORE_RE.match(n):
            del dst[n]
            removed += 1
    return [[f"clock.tap_{form}.per_port_ps", "rows", kept, carried, removed]]


def _plan_consumer_taps(raw, path):
    sys.path.insert(0, str(HERE))
    import schema
    import reset_tree as RT
    P = schema.Plan(json.loads(json.dumps(raw)), path)
    return lambda tn: [(str(n), float(x), float(y)) for n, x, y in RT.consumer_taps(P, tn)]


def _raw_branch_roles(ck):
    return {str(x) for b in ck.get("landing_raw_branches") or [] if isinstance(b, dict) for x in b.get("consumers") or []}


def repick_type(t, ctaps, far_um=FAR_UM):
    """RRDRV-FAR on one type dict (in place).  ctaps: the reset tree's consumer taps [(n, x, y)] in index order.
    -> [[where, key, was, now, hop_um]] (hop from the stage site to the new tap)."""
    ck = t.get("clock") or {}
    if not ctaps:
        return []
    D = lambda a, b: abs(float(a[0]) - b[0]) + abs(float(a[1]) - b[1])  # noqa: E731
    roles = _raw_branch_roles(ck)
    out = []

    def pick(o, key, where, xy):
        v = o.get(key)
        g = TAPQ.match(str(v or "")) or RAWQ.match(str(v or ""))
        if not g or xy is None:
            return
        n = int(g.group(1))
        if n < len(ctaps) and D(xy, ctaps[n][1:]) <= far_um:
            return
        k = min(range(len(ctaps)), key=lambda j: (D(xy, ctaps[j][1:]), j))
        now = ("rst_n_t" if str(v).startswith("rst_n_t") else "rr_t") + str(k)
        if now != v:
            o[key] = now
            out.append([where, key, v, now, round(D(xy, ctaps[k][1:]), 3)])

    for key, side in (("landing_reader_start", "reader"), ("landing_writer_start", "writer")):
        for bus, br in sorted(((ck.get(key) or {}).get("branches") or {}).items()):
            for i, st in enumerate((br.get("stages") or []) if isinstance(br, dict) else []):
                if not isinstance(st, dict) or f"{side}:{bus}:{i}" in roles:
                    continue
                pick(st, "raw_reset", f"clock.{key}.branches.{bus}.stages[{i}]", st.get("xy_um"))
    for j, lr in enumerate(ck.get("landing_local_resets") or []):
        if isinstance(lr, dict):
            pick(lr, "raw", f"clock.landing_local_resets[{j}]", lr.get("xy_um"))
    return out


def repick_start_raws(raw, path=None, types=None, far_um=FAR_UM, ctaps_fn=None):
    """RRDRV-FAR on raw (in place) for types (default: all).  ctaps_fn(raw, path) -> (tn -> consumer taps); default
    reset_tree.consumer_taps on the plan.  A type whose consumer taps cannot be solved is reported, never raised.
    -> {type: [[where, key, was, now, hop_um]]}"""
    fn = None      # the plan is built only when a selected type has START raws
    rep = {}
    for tn, t in raw["partition_types"].items():
        if types is not None and tn not in types:
            continue
        ck = t.get("clock") or {}
        if not (ck.get("landing_reader_start") or ck.get("landing_writer_start") or ck.get("landing_local_resets")):
            continue
        try:
            fn = fn or (ctaps_fn or _plan_consumer_taps)(raw, path)
            ct = fn(tn)
        except Exception as e:  # noqa: BLE001
            rep[tn] = [["clock", "repick_far", "SKIP", f"{type(e).__name__}: {e}"[:160], 0]]
            continue
        ch = repick_type(t, ct, far_um)
        if ch:
            rep[tn] = ch
    return rep


def repoint(old_raw, new_raw, old_path=None, new_path=None, types=None, taps_fn=None, tree_fn=None, republish_reset=False,
            tapoff=True, far_um=FAR_UM, ctaps_fn=None):
    """Re-point new_raw (in place) against old_raw, then re-solve and republish the collector_tree of every type whose
    tap set changed.  taps_fn(raw, path) -> (tn -> [(n, x, y)]) (default schema.tap_grid); tree_fn(raw, path) ->
    (tn -> tree) (default reset_tree.for_type on the re-pointed plan).
    RESETPUB-1122 (COORD: TAP-GRID-R5 clock keys changed the reset tree, the tap set did not, so nothing was republished and the QC V3
    binds died at EMIT): a type whose tap set is unchanged but whose clock / reset inputs changed is re-solved too, and republished
    when its old published tree was its own (reset_tree.for_type of the old plan).  republish_reset=True republishes every selected
    type that publishes a tree (also an already stale one) with the tree the tools solve now.
    -> {type: [[where, key, was, now, um_or_n]]} for the types that changed."""
    tf = taps_fn or _plan_taps
    to, tn_ = tf(old_raw, old_path), tf(new_raw, new_path)
    rep, moved = {}, []
    key = lambda ts: [(n, round(x, 6), round(y, 6)) for n, x, y in ts]  # noqa: E731
    todo, own_todo = [], []
    for tn, t in new_raw["partition_types"].items():
        if types and tn not in types:
            continue
        if tn not in old_raw["partition_types"]:
            continue
        a, b = to(tn), tn_(tn)
        if key(a) == key(b):
            continue
        todo.append((tn, a, b))
    tr_old = tr = None
    if any(_published(new_raw["partition_types"][tn]) is not None for tn, _, _ in todo):
        tr_old = (tree_fn or _plan_tree)(old_raw, old_path)
    for tn, a, b in todo:
        t = new_raw["partition_types"][tn]
        pub = _published(old_raw["partition_types"][tn])
        own = pub is None or _norm(pub) == _norm(tr_old(tn))
        if own:
            own_todo.append(tn)
        ch = repoint_type(t, a, b, reset=own)
        if tapoff:
            ch = (ch or []) + carry_tapoff(old_raw, new_raw, tn, a, b)
        if ch:
            rep[tn] = ch
        if pub is not None:
            if own:
                moved.append(tn)
            else:
                rep.setdefault(tn, []).append(["landing_contract.collector_tree", "tree_not_own", 0, 0, 0])
    done = {tn for tn, _, _ in todo}
    extra, forced = [], []
    for tn, t in new_raw["partition_types"].items():
        if tn in done or (types and tn not in types) or tn not in old_raw["partition_types"] or _published(t) is None:
            continue
        if republish_reset:
            forced.append(tn)
        elif _reset_inputs(t) != _reset_inputs(old_raw["partition_types"][tn]):
            extra.append(tn)
    if extra:
        tr_old = tr_old or (tree_fn or _plan_tree)(old_raw, old_path)
        for tn in extra:
            pub = _published(old_raw["partition_types"][tn])
            if _norm(pub) == _norm(tr_old(tn)):
                moved.append(tn)
            else:
                rep.setdefault(tn, []).append(["landing_contract.collector_tree", "tree_not_own", 0, 0, 0])
    moved += forced
    if moved:
        tr = (tree_fn or _plan_tree)(new_raw, new_path)
        for tn in moved:
            ch = republish_tree(new_raw["partition_types"][tn], tr(tn))
            if ch:
                rep.setdefault(tn, []).extend(ch)
    if tapoff and todo:
        rep.update(_tapoff_close(new_raw, new_path, [tn for tn, _, _ in todo]))
    if far_um is not None and own_todo:
        # RRDRV-FAR: number START raws on the reset tree's consumer taps (what the bind emits), not the clock tap census.
        # Injected taps_fn (tests) doubles as the consumer census when no ctaps_fn is given (no reset.local_taps_um there).
        cf = ctaps_fn or ((lambda raw, path: taps_fn(raw, path)) if taps_fn else None)
        for tn, ch in repick_start_raws(new_raw, new_path, set(own_todo), far_um, cf).items():
            rep.setdefault(tn, []).extend(ch)
    return rep


def _tapoff_close(raw, path, tns):
    """tap_offset_cover.fill on the re-tapped types (whatever carry_tapoff left missing, e.g. a type the old tap grid named
    only in part) -> {type: [report row]} for the types it touched; a type it must skip is reported, never raised."""
    off, win = _tapoff_tables(raw)
    tns = [tn for tn in tns if off.get(tn) or win.get(tn)]
    if not tns:
        return {}
    import tap_offset_cover as TC
    out = {}
    rows = TC.fill(raw, path, types="^(" + "|".join(re.escape(t) for t in tns) + ")$")
    for r in rows:
        if r.get("added") or r.get("stale_removed") or str(r.get("status", "")).startswith("SKIP"):
            out[r["type"]] = [[f"clock.tap_{r['form']}.per_port_ps", "cover_fill", r.get("added", 0), r.get("stale_removed", 0),
                               r.get("status", "")]]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old"); ap.add_argument("new"); ap.add_argument("out")
    ap.add_argument("--report"); ap.add_argument("--types", default="")
    ap.add_argument("--republish-reset", action="store_true",
                    help="RESETPUB-1122: republish the collector_tree of every selected type with the tree the tools solve now (also a stale one)")
    ap.add_argument("--no-tapoff", action="store_true", help="TAPOFF-RETAP: leave clock.tap_offset / tap_window per_port_ps rows as they are")
    ap.add_argument("--no-repick-far", action="store_true", help="RRDRV-FAR: leave START raw resets past the tree / over 300 um as mapped")
    ap.add_argument("--repick-only", action="store_true",
                    help="RRDRV-FAR only, on NEW (e.g. after a landing_remap restore of START sections): OLD is not read")
    a = ap.parse_args(argv)
    new = json.loads(Path(a.new).read_text())
    sel = [x for x in a.types.split(",") if x] or None
    if a.repick_only:
        rep = repick_start_raws(new, a.new, set(sel) if sel else None)
    else:
        old = json.loads(Path(a.old).read_text())
        rep = repoint(old, new, a.old, a.new, sel, republish_reset=a.republish_reset, tapoff=not a.no_tapoff,
                      far_um=None if a.no_repick_far else FAR_UM)
    Path(a.out).write_text(json.dumps(new, indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    for tn, ch in sorted(rep.items()):
        tof = [c for c in ch if str(c[0]).startswith("clock.tap_")]
        ch = [c for c in ch if not str(c[0]).startswith("clock.tap_")]
        if tof:
            print("RETAP", tn, "tapoff", " ".join(f"{c[1]}={c[2]}/{c[3]}/{c[4]}" for c in tof))
        if not ch:
            continue
        refs = [c for c in ch if c[0] != "landing_contract.collector_tree"]
        tree = [c for c in ch if c[0] == "landing_contract.collector_tree"]
        print("RETAP", tn, "refs", len(refs), "max_um", max([c[4] for c in refs] or [0]),
              "tree", ("NOT OWN (left as published)" if tree and tree[0][1] == "tree_not_own" else
                       f"{tree[0][2]}->{tree[0][3]} relays, {tree[0][4]} new edges" if tree else "unchanged"))
    print("RETAP types", len(rep), "refs", sum(len(c) for c in rep.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

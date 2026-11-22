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

  retap.py OLD_PLAN NEW_PLAN OUT [--report R.json] [--types a,b]
  sink_bins_from_place.py apply PLAN OUT --bins TYPE=FILE ... calls repoint in the same step.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAPQ = re.compile(r"^rst_n_t(\d+)$")
RAWQ = re.compile(r"^rr_t(\d+)$")
START_KEYS = ("landing_writer_start", "landing_reader_start", "landing_local_resets")
FWD_KEYS = ("source_clock_port", "source_clock_tap")


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


def repoint(old_raw, new_raw, old_path=None, new_path=None, types=None, taps_fn=None, tree_fn=None, republish_reset=False):
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
    todo = []
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
        ch = repoint_type(t, a, b, reset=own)
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
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old"); ap.add_argument("new"); ap.add_argument("out")
    ap.add_argument("--report"); ap.add_argument("--types", default="")
    ap.add_argument("--republish-reset", action="store_true",
                    help="RESETPUB-1122: republish the collector_tree of every selected type with the tree the tools solve now (also a stale one)")
    a = ap.parse_args(argv)
    old, new = json.loads(Path(a.old).read_text()), json.loads(Path(a.new).read_text())
    rep = repoint(old, new, a.old, a.new, [x for x in a.types.split(",") if x] or None, republish_reset=a.republish_reset)
    Path(a.out).write_text(json.dumps(new, indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    for tn, ch in sorted(rep.items()):
        refs = [c for c in ch if c[0] != "landing_contract.collector_tree"]
        tree = [c for c in ch if c[0] == "landing_contract.collector_tree"]
        print("RETAP", tn, "refs", len(refs), "max_um", max([c[4] for c in refs] or [0]),
              "tree", ("NOT OWN (left as published)" if tree and tree[0][1] == "tree_not_own" else
                       f"{tree[0][2]}->{tree[0][3]} relays, {tree[0][4]} new edges" if tree else "unchanged"))
    print("RETAP types", len(rep), "refs", sum(len(c) for c in rep.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

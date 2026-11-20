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


def repoint_type(t, old, new):
    """Rewrite the tap references of type dict t (in place) from tap set old to new.  -> [[where, key, was, now, um]]"""
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
    by_idx = {tap_index(n): n for n in site}
    nidx = {n: tap_index(n) for n in nsite}
    for r in t.get("reset", {}).get("consumer_localization", []) or []:
        g = TAPQ.match(str(r.get("new_reset", "")))
        if not g:
            continue
        o = by_idx.get(int(g.group(1)))
        if o is None:
            raise RetapError(f"consumer {r.get('instance')}.{r.get('pin')} {r['new_reset']}: no tap {g.group(1)} in the old tap set")
        now = f"rst_n_t{nidx[m[o]]}"
        if now != r["new_reset"]:
            out.append([f"consumer_localization.{r.get('instance')}.{r.get('pin')}", "new_reset", r["new_reset"], now, um(o, m[o])])
            r["new_reset"] = now
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


def repoint(old_raw, new_raw, old_path=None, new_path=None, types=None, taps_fn=None, tree_fn=None):
    """Re-point new_raw (in place) against old_raw, then re-solve and republish the collector_tree of every type whose
    tap set changed.  taps_fn(raw, path) -> (tn -> [(n, x, y)]) (default schema.tap_grid); tree_fn(raw, path) ->
    (tn -> tree) (default reset_tree.for_type on the re-pointed plan).
    -> {type: [[where, key, was, now, um_or_n]]} for the types that changed."""
    tf = taps_fn or _plan_taps
    to, tn_ = tf(old_raw, old_path), tf(new_raw, new_path)
    rep, moved = {}, []
    key = lambda ts: [(n, round(x, 6), round(y, 6)) for n, x, y in ts]  # noqa: E731
    for tn, t in new_raw["partition_types"].items():
        if types and tn not in types:
            continue
        if tn not in old_raw["partition_types"]:
            continue
        has_fwd = any(q.get("kind") == "clock" and q.get("dir") == "out" and any(q.get(k) for k in FWD_KEYS)
                      for q in t.get("clock", {}).get("landing_contract", {}).get("pins", []) or [])
        has_rst = any(TAPQ.match(str(r.get("new_reset", ""))) for r in t.get("reset", {}).get("consumer_localization", []) or [])
        has_tree = _published(t) is not None
        if not (has_fwd or has_rst or has_tree):
            continue
        a, b = to(tn), tn_(tn)
        if key(a) == key(b):
            continue
        ch = repoint_type(t, a, b)
        if ch:
            rep[tn] = ch
        if has_tree:
            moved.append(tn)
    if moved:
        tr_old = (tree_fn or _plan_tree)(old_raw, old_path)
        tr = (tree_fn or _plan_tree)(new_raw, new_path)
        for tn in moved:
            pub = old_raw["partition_types"][tn]["clock"]["landing_contract"]["collector_tree"]
            if _norm(pub) != _norm(tr_old(tn)):
                rep.setdefault(tn, []).append(["landing_contract.collector_tree", "tree_not_own", 0, 0, 0])
                continue
            ch = republish_tree(new_raw["partition_types"][tn], tr(tn))
            if ch:
                rep.setdefault(tn, []).extend(ch)
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old"); ap.add_argument("new"); ap.add_argument("out")
    ap.add_argument("--report"); ap.add_argument("--types", default="")
    a = ap.parse_args(argv)
    old, new = json.loads(Path(a.old).read_text()), json.loads(Path(a.new).read_text())
    rep = repoint(old, new, a.old, a.new, [x for x in a.types.split(",") if x] or None)
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

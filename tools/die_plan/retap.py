#!/usr/bin/env python3
"""RETAP (QC-PLAN-R3, COORD 11-20): re-point tap-named plan references after a type's clock taps are re-derived.

clock.tap_mode "density" (and the other derived modes) solve the taps from clock.sink_bins_file, so new sink bins
(e.g. sink_bins_from_place.py from a placed kit) renumber and move the taps clk_t<i>.  Two kinds of plan rows name taps
literally and go stale in the same step: N46V0 bind EMIT 'forwarded clock source clk_t134 is not a planned physical
tap input' (clock.landing_contract out clock pins source_clock_port / source_clock_tap) on 3 QC types, and EMIT
'rst_n_t0: emitted/published reset edge mismatch' (reset.consumer_localization new_reset rst_n_t<i>, the terminal
reset relay of tap i) on sle_sc_v2.

repoint(old_raw, new_raw, old_plan_path, new_plan_path) maps every tap of the OLD tap set to the NEW tap nearest its old
site (Manhattan, ties by name: the rule of type_split._remap_clock_sources) and rewrites both kinds of reference in
new_raw in place.  Types whose tap set (names and sites) is unchanged are not touched, so an unchanged plan is
byte-identical.  Reset relay names rst_rl_<k> are re-picked at bind by reset_anchor.py; not here.

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


def repoint(old_raw, new_raw, old_path=None, new_path=None, types=None, taps_fn=None):
    """Re-point new_raw (in place) against old_raw.  taps_fn(raw, path) -> (tn -> [(n, x, y)]) (default schema.tap_grid).
    -> {type: [[where, key, was, now, um]]} for the types that changed."""
    tf = taps_fn or _plan_taps
    to, tn_ = tf(old_raw, old_path), tf(new_raw, new_path)
    rep = {}
    for tn, t in new_raw["partition_types"].items():
        if types and tn not in types:
            continue
        if tn not in old_raw["partition_types"]:
            continue
        has_fwd = any(q.get("kind") == "clock" and q.get("dir") == "out" and any(q.get(k) for k in FWD_KEYS)
                      for q in t.get("clock", {}).get("landing_contract", {}).get("pins", []) or [])
        has_rst = any(TAPQ.match(str(r.get("new_reset", ""))) for r in t.get("reset", {}).get("consumer_localization", []) or [])
        if not (has_fwd or has_rst):
            continue
        ch = repoint_type(t, to(tn), tn_(tn))
        if ch:
            rep[tn] = ch
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
        print("RETAP", tn, len(ch), "max_um", max(c[4] for c in ch))
    print("RETAP types", len(rep), "refs", sum(len(c) for c in rep.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

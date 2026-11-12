#!/usr/bin/env python3
"""DIE-S81-87 11-12: apply a FROZEN param-class split (tools/die_plan/param_class_split.py report, key "splits") to a plan.

usage: apply_psplit_1112.py IN OUT REPORT --splits SPLIT_REPORT.json [--types T,..] [--sidecar IN --sidecar-out OUT]
                            [--asbuilt IN --asbuilt-out OUT --sidecar-ref REL]
Runs with cwd = repo root (tools/die_plan importable).  NOT a composer stage: it adds/removes plan types, and the composer
stage contract keeps the type set, so it is the LAST step of an event, on the composer's final plan (after the
dead-input stage).  Fail closed: every split type is in the plan and its partitions are exactly the union of its clones'
partitions (the split report was computed on a bind of the same type definitions); a clone name already in the plan
fails.  Idempotent: types already replaced by their clones are skipped.  Output = param_class_split.apply_plan on the
same input, i.e. byte-identical to running the tool with --bind-out on the bind of record."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "tools/die_plan"))
import param_class_split as P  # noqa: E402


def prune_stale(raw, todo):
    """param_class_split.apply_plan keeps the base type T as a dict key / list entry next to its clones (the form
    clock_landing_plan leaves).  Three plan readers reject a name that is no longer a plan type (G0:
    reset_tree.ResetError 'reset.relay_lockup names unknown types'), so the stale base entries are removed where the
    clones already carry their own copy: clock.tap_window.per_type_ps / per_port_ps, reset.in_sites,
    reset.relay_lockup.types.  Returns the removals."""
    out = []
    for s in todo:
        t = s["type"]
        for path in (("clock", "tap_window", "per_type_ps"), ("clock", "tap_window", "per_port_ps"), ("reset", "in_sites")):
            d = raw
            for k in path:
                d = d.get(k) if isinstance(d, dict) else None
            if isinstance(d, dict) and t in d:
                del d[t]
                out.append(dict(path="/".join(path), key=t))
        lst = ((raw.get("reset") or {}).get("relay_lockup") or {}).get("types")
        if isinstance(lst, list) and t in lst:
            lst.remove(t)
            out.append(dict(path="reset/relay_lockup/types", item=t))
    return out


def prune_side(obj, nm, todo):
    """The same stale-base rule for the bind inputs.  The bind (clock_landings.expand_station_types) requires every name in
    asbuilt.internal_stations_types to be an actual plan type or the base of one ('native station families have no actual
    cohort'): the split base name left in the list next to its clones fails the bind.  The sidecar keeps one collector.types
    entry per clone (apply_side copies it), so the stale base entry goes too."""
    out = []
    for s in todo:
        t = s["type"]
        if nm == "asbuilt" and isinstance(obj.get("internal_stations_types"), list) and t in obj["internal_stations_types"]:
            obj["internal_stations_types"].remove(t)
            out.append(dict(path="internal_stations_types", item=t))
        if nm == "sidecar":
            d = (obj.get("collector") or {}).get("types")
            if isinstance(d, dict) and t in d:
                del d[t]
                out.append(dict(path="collector/types", key=t))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("report")
    ap.add_argument("--splits", required=True)
    ap.add_argument("--types")
    ap.add_argument("--sidecar")
    ap.add_argument("--sidecar-out")
    ap.add_argument("--asbuilt")
    ap.add_argument("--asbuilt-out")
    ap.add_argument("--sidecar-ref")
    a = ap.parse_args(argv)
    text = Path(a.inp).read_text()
    raw = json.loads(text)
    spl = json.loads(Path(a.splits).read_text())["splits"]
    if a.types:
        want = set(a.types.split(","))
        spl = [s for s in spl if s["type"] in want]
        if {s["type"] for s in spl} != want:
            print("apply_psplit: ERROR types not in the split report", file=sys.stderr)
            return 2
    parts = {}
    for p in raw["partitions"]:
        parts.setdefault(p["type"], set()).add(p["name"])
    todo, done = [], []
    for s in spl:
        tn, names = s["type"], [c["name"] for c in s["clones"]]
        if tn not in raw["partition_types"]:
            if all(n in raw["partition_types"] for n in names):
                done.append(tn)
                continue
            print(f"apply_psplit: ERROR {tn} neither split nor present", file=sys.stderr)
            return 2
        want_p = set().union(*[set(c["partitions"]) for c in s["clones"]])
        if parts.get(tn, set()) != want_p:
            print(f"apply_psplit: ERROR {tn}: plan partitions differ from the split report "
                  f"({len(parts.get(tn, ()))} vs {len(want_p)})", file=sys.stderr)
            return 2
        if any(n in raw["partition_types"] for n in names):
            print(f"apply_psplit: ERROR {tn}: clone name already in plan", file=sys.stderr)
            return 2
        todo.append(s)
    refs = P.apply_plan(raw, todo) if todo else []
    pruned = prune_stale(raw, todo)
    out = P._dump_like(raw, text) if todo else text
    Path(a.out).write_text(out)
    rep = dict(schema="opentallas.die_plan.apply_psplit_1112.v1", already_split=done,
               splits=[dict(type=s["type"], clones=[c["name"] for c in s["clones"]]) for s in todo],
               in_sha256=hashlib.sha256(text.encode()).hexdigest(), out_sha256=hashlib.sha256(out.encode()).hexdigest(),
               plan_refs=refs, pruned_stale_base_refs=pruned)
    for nm, src, dst in (("sidecar", a.sidecar, a.sidecar_out), ("asbuilt", a.asbuilt, a.asbuilt_out)):
        if not src:
            continue
        st = Path(src).read_text()
        obj = json.loads(st)
        rep[nm + "_refs"] = P.apply_side(obj, todo, nm)
        rep[nm + "_pruned_stale_base_refs"] = prune_side(obj, nm, todo)
        if nm == "asbuilt" and a.sidecar_ref and obj.get("clock_landing_table"):
            obj["clock_landing_table"] = a.sidecar_ref
        Path(dst).write_text(P._dump_like(obj, st))
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"apply_psplit: {len(todo)} type(s) split into {sum(len(s['clones']) for s in todo)} clones; {len(done)} already split")
    return 0


if __name__ == "__main__":
    sys.exit(main())

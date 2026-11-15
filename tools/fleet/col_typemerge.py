#!/usr/bin/env python3
"""S81-TYPEMERGE-IMPL (FABLE-S81-TYPEMERGE R1 / R2 / R4 / R3a analysis): make the S81 col sign-off key the layout, not the type name.

  groups  PLAN [--by layout]            sibling groups and layout hashes per col family (counts before the delta)
  depth   PLAN TABLE OUT                R2: ring DEPTH (hence the strap_ca_k_* width, strap_kw = log2(DEPTH) + 4) = the maximum over
                                        a sibling group, per bus.  TABLE = count-aligned bind table (regions_ca_strap.json); OUT =
                                        the same table with count_aligned.ports[*].depth raised.  K values, sched_lat and every
                                        region are untouched; a deeper ring only widens the count window (guard, timeout default to
                                        DEPTH), so a crossing that closed at depth 4 closes at depth 8.
  taps    PLAN OUT                      R4: core clock taps of one sibling group take the group's modal xy (tap sites derived from
                                        the current core origin; the hard-core signature of a group is one origin per core)
  sites   LANDED_PLAN                   R3a analysis: per family the monitor entry sites (collector_children xy + bands monitor_*) per
                                        type, the union and the number of types after the union

A sibling group = family + geometry key + hard-core signature (module/lef/lib/origin/orient) + outline: exactly the part of a col type
that is physical; the ROM image parameters (P_*_INSTANCE), the type name inside notes / collector_tree.type and the pv label are not.
"""
import argparse
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import col_inherit as CI   # noqa: E402

FAM_RE = re.compile(r"^(col_h(?:9|10)_r[012](?:_p\d+)?)__")
LABEL_RE = re.compile(r"__(?:cl[0-9a-f]{6,}|pv[0-9a-f]{6,})")
SKIP_KEYS = {"module", "note", "param_set", "param_base_type", "budget_owner", "notes", "landing_base_type"}


def family(name):
    m = FAM_RE.match(name)
    return m and m.group(1)


def col_types(plan):
    pt = CI.plan_types(plan)
    return {n: t for n, t in pt.items() if family(n)}


def sibling_key(name, t):
    """physical identity before CA/clock landing: family, geometry, hard cores without ROM image params, outline"""
    return CI.jsha([family(name), CI.geometry_key(t), CI.hard_core_signature(t), t.get("outline_um")])


def sibling_groups(plan):
    """{key: [type names]}"""
    out = collections.defaultdict(list)
    for n, t in sorted(col_types(plan).items()):
        out[sibling_key(n, t)].append(n)
    return dict(out)


def _norm(o, name):
    if isinstance(o, dict):
        return {k: _norm(v, name) for k, v in o.items() if k not in SKIP_KEYS}
    if isinstance(o, list):
        return [_norm(v, name) for v in o]
    if isinstance(o, str):
        return LABEL_RE.sub("", o.replace(name, "@T"))
    return o


def layout_hash(name, t):
    """R1 key: the whole type with names, notes, ROM image params and the cl/pv labels removed"""
    return CI.jsha(_norm(t, name))


def layout_groups(plan):
    out = collections.defaultdict(list)
    for n, t in sorted(col_types(plan).items()):
        out[layout_hash(n, t)].append(n)
    return dict(out)


# ------------------------------------------------------------------ R2
def depth_unify(plan, table):
    """-> (table copy, report).  Per sibling group and per landed bus name: depth := group max."""
    pt = CI.plan_types(plan)
    ptype = {p["name"]: p["type"] for p in plan["partitions"]}
    ports = {p["id"]: p for p in plan["ports"]}
    gkey = {}
    for k, names in sibling_groups(plan).items():
        for n in names:
            gkey[n] = k
    ca = json.loads(json.dumps(table))["count_aligned"]
    depth = collections.defaultdict(int)       # (group, bus) -> max
    rows = []
    for pid, c in ca["ports"].items():
        p = ports.get(pid)
        if p is None:
            continue
        tn = ptype[p["dst"]["part"]]
        if tn not in gkey:
            continue
        key = (gkey[tn], p["dst"]["bus"])
        depth[key] = max(depth[key], int(c["depth"]))
        rows.append((pid, key, tn))
    changed = collections.Counter()
    for pid, key, tn in rows:
        c = ca["ports"][pid]
        if int(c["depth"]) < depth[key]:
            changed[tn] += 1
            c["depth"] = depth[key]
    new = json.loads(json.dumps(table))
    new["count_aligned"] = ca
    ca["depth_unify"] = dict(rule="S81-TYPEMERGE R2: ring depth = max over the sibling group per bus", ports_raised=sum(changed.values()))
    rep = dict(ports_raised=sum(changed.values()), types_touched=len(changed),
               by_family=dict(collections.Counter(family(t) for t in changed)))
    return new, rep


# ------------------------------------------------------------------ R4
def retap(plan):
    """-> (plan copy, report).  Within one sibling group each core tap takes the modal xy of its name (the sites that every
    core origin in the group agrees on); a tap is moved only when the core origin and orientation are equal across the group."""
    new = json.loads(json.dumps(plan))
    pt = CI.plan_types(new)
    moved = 0
    maxd = 0.0
    per_type = collections.Counter()
    for k, names in sibling_groups(new).items():
        for key in ("taps", "added_taps"):
            votes = collections.defaultdict(collections.Counter)
            for n in names:
                for x in pt[n].get("clock", {}).get(key, []):
                    if x.get("kind") == "core":
                        votes[x["name"]][tuple(x["xy"])] += 1
            for n in names:
                for x in pt[n].get("clock", {}).get(key, []):
                    if x.get("kind") != "core":
                        continue
                    (best, _), = votes[x["name"]].most_common(1)
                    if tuple(x["xy"]) != best:
                        d = abs(x["xy"][0] - best[0]) + abs(x["xy"][1] - best[1])
                        maxd = max(maxd, d)
                        x["xy"] = list(best)
                        moved += 1
                        per_type[n] += 1
    return new, dict(taps_moved=moved, types_touched=len(per_type), max_move_um=round(maxd, 3))


# ------------------------------------------------------------------ R3a analysis
def entry_sites(t):
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    sites = set()
    for c in lc.get("collector_children", []) or []:
        sites.add(("child", tuple(c.get("xy_um") or ()), bool(c.get("seam"))))
    for b, v in (lc.get("bands") or {}).items():
        if b.startswith("monitor_"):
            sites.add(("band", tuple(v.get("rect_um") or ())))
    for p in lc.get("pins", []) or []:
        if p.get("name", "").startswith(("cland_dn_", "fclk_in_cland_dn")):
            sites.add(("pin", p["name"], tuple(p.get("xy_um") or ())))
    return frozenset(sites)


def sites_report(plan):
    rep = {}
    for k, names in sibling_groups(plan).items():
        fam = family(names[0])
        sets = {n: entry_sites(CI.plan_types(plan)[n]) for n in names}
        union = frozenset().union(*sets.values())
        d = rep.setdefault(fam, dict(groups=0, distinct_site_sets=0, max_union_children=0, types=0))
        d["groups"] += 1
        d["types"] += len(names)
        d["distinct_site_sets"] += len(set(sets.values()))
        d["max_union_children"] = max(d["max_union_children"], sum(1 for s in union if s[0] == "child"))
    return rep


def cmd_groups(a):
    plan = json.load(open(a.plan))
    sg, lg = sibling_groups(plan), layout_groups(plan)
    fam = collections.defaultdict(lambda: [0, set(), set()])
    for k, names in sg.items():
        for n in names:
            fam[family(n)][0] += 1
            fam[family(n)][1].add(k)
    for h, names in lg.items():
        fam[family(names[0])][2].add(h)
    tot = [0, 0, 0]
    for f, (n, g, l) in sorted(fam.items()):
        print("%-16s types %3d sibling_groups %3d layout_hashes %3d" % (f, n, len(g), len(l)))
        tot = [tot[0] + n, tot[1] + len(g), tot[2] + len(l)]
    print("%-16s types %3d sibling_groups %3d layout_hashes %3d" % ("TOTAL", *tot))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("groups"); g.add_argument("plan"); g.set_defaults(fn=cmd_groups)
    d = sp.add_parser("depth"); d.add_argument("plan"); d.add_argument("table"); d.add_argument("out")
    t = sp.add_parser("taps"); t.add_argument("plan"); t.add_argument("out")
    s = sp.add_parser("sites"); s.add_argument("plan")
    a = ap.parse_args(argv)
    if a.cmd == "groups":
        return cmd_groups(a)
    plan = json.load(open(a.plan))
    if a.cmd == "depth":
        new, rep = depth_unify(plan, json.load(open(a.table)))
        json.dump(new, open(a.out, "w"))
    elif a.cmd == "taps":
        new, rep = retap(plan)
        open(a.out, "w").write(json.dumps(new, indent=1) + "\n")
    else:
        rep = sites_report(plan)
    print(json.dumps(rep, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

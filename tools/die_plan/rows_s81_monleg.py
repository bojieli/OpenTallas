#!/usr/bin/env python3
"""ROWS_S81-MONLEG: re-pick every landing collector child node next to its monitor (S81 form of QC SC3-MONLEG).

Defect (FABLE-RC-S81 11-25 00:15, hub af8bee1e): partition_types[T].clock.landing_contract.collector_children[i] names the
reset-tree node whose collector receives monitor i's ready/fault (and whose reset copy resets monitor i).  S81-MONITOR-PIN-1745
re-seated the monitor band (bands.monitor_i) at its cland_dn pin, but .node kept the index computed from the old consumer
count (rst_n_t<n_consumers_then + j>), so monitor and collector are one die-span apart: c9s 118 of 252 pairs over 405 um on
83 types, 85 pairs on 71 types over 900 um (c8s col_h9_r0_p1-p3: -1009 .. -1073 ps, 16 BUFx16f over 2290 um).

Row: for every pair whose monitor band centre is more than REACH_UM (405) from its node's relay, set child.node to the
tree node nearest the band centre:
  * candidates are relays of kind tap (rst_n_t<k>) at the SAME depth as the old node (collector depth to the root, so the
    boot budget collector.boot_budget.local_registered_depths and every collector deadline are unchanged: 0 added cycles);
  * a candidate must lie within REACH_UM of the band centre AND of the child pin (child.xy_um; landing_collector.build_local
    refuses a source hop above its reach);
  * the tree OUTPUT relay of the child's own seam site (tap = n_reset_consumers + j, xy == collector_tree.outs[j] == child
    xy_um) is taken first (QC SC3-MONLEG: "the output relay at the seam"), else the nearest same-depth tap, ties by pin
    distance then name;
  * no same-depth candidate: the nearest DEEPER tap inside the reach (depth delta = cycles added on that child chain, stated
    per type in the report; the type's boot depth is re-evaluated like clock_landing_plan.local_depths), else the pair is
    listed as unfixed (--strict: exit 3).
Pairs already within REACH_UM are not touched.  Nothing but collector_children[i].node changes (plus the same field in an
optional sidecar collector.types[T].children).  Deterministic: no clock, no randomness, sorted iteration.

usage: rows_s81_monleg.py PLAN_IN PLAN_OUT [REPORT_JSON] [--sidecar-in SC --sidecar-out SC2] [--strict] [--types t1,t2]
       rows_s81_monleg.py --census PLAN_IN          (before-count only, no output file)
"""
import collections
import copy
import hashlib
import json
import os
import sys

REACH_UM = 405.0       # METHODOLOGY 12.1e: plan reach per registered hop
FAIL_UM = 900.0        # c8s calibration: leaf__t36 1021 um measures -62 ps, about 950 um is the fail line


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def centre(r):
    return [(r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0]


def tree_index(ct):
    """q -> relay dict, plus the root node (depth 0) at ct.root."""
    R = {r["q"]: r for r in ct.get("relays", [])}
    if ct.get("root") is not None:
        R.setdefault("rst_root_n", dict(q="rst_root_n", xy=ct["root"], depth=0, kind="root", tap=None))
    return R


def pairs(raw, only=None):
    """(type, child, band centre, node relay or None) for every collector child with a seated monitor band."""
    for tn in sorted(raw.get("partition_types", {})):
        t = raw["partition_types"][tn]
        lc = (t.get("clock") or {}).get("landing_contract") if isinstance(t, dict) else None
        if not lc or not lc.get("collector_children") or (only and tn not in only):
            continue
        R = tree_index(lc.get("collector_tree") or {})
        for c in lc["collector_children"]:
            if not isinstance(c, dict) or c.get("index") is None:
                continue                  # HEAD children (bus/fault/ready/seam/xy_um) have no monitor index and no monitor_* band
            b = (lc.get("bands") or {}).get(f"monitor_{c['index']}")
            if not b or not b.get("rect_um"):
                continue
            yield tn, lc, c, centre(b["rect_um"]), R.get(c.get("node")), R


def census(raw, only=None):
    """Pair counts: total, over REACH_UM, over FAIL_UM, and the types holding them."""
    rows = []
    for tn, lc, c, ctr, n, R in pairs(raw, only):
        rows.append((tn, c["index"], c.get("node"), None if n is None else man(ctr, n["xy"])))
    over = [r for r in rows if r[3] is not None and r[3] > REACH_UM]
    fail = [r for r in over if r[3] > FAIL_UM]
    return dict(pairs=len(rows), unresolved=sum(1 for r in rows if r[3] is None), over_reach=len(over),
                over_reach_types=len({r[0] for r in over}), over_fail=len(fail), over_fail_types=len({r[0] for r in fail}),
                max_um=round(max([r[3] for r in rows if r[3] is not None] or [0.0]), 1), over=over)


def output_relays(ct):
    """site -> relay q of the tree output relays (tap = n_reset_consumers + j, xy == outs[j])."""
    n0 = ct.get("n_reset_consumers")
    res = {}
    if n0 is None:
        return res
    for j, site in enumerate(ct.get("outs") or []):
        for r in ct.get("relays", []):
            if r.get("kind") == "tap" and r.get("tap") == n0 + j and list(r["xy"]) == list(site):
                res[tuple(site)] = r["q"]
    return res


def pick(lc, c, ctr, R):
    """-> (new node q, why) or (None, why-not).  Never returns a node farther than REACH_UM from the monitor or the pin."""
    old = R.get(c.get("node"))
    if old is None:
        return None, "old node absent from the tree"
    ok = [r for r in R.values() if r["kind"] == "tap" and man(ctr, r["xy"]) <= REACH_UM and man(c["xy_um"], r["xy"]) <= REACH_UM]
    same = [r for r in ok if r["depth"] == old["depth"]]
    out = output_relays(lc["collector_tree"]).get(tuple(c["xy_um"]))
    key = lambda r: (man(ctr, r["xy"]), man(c["xy_um"], r["xy"]), r["q"])
    if out is not None and any(r["q"] == out for r in same):
        return out, "seam output relay, same depth"
    if same:
        return min(same, key=key)["q"], "nearest same-depth tap"
    deeper = [r for r in ok if r["depth"] > old["depth"]]
    if deeper:
        return min(deeper, key=lambda r: (r["depth"],) + key(r))["q"], "nearest deeper tap"
    return None, "no tap within reach of monitor and pin at the same or deeper depth"


def boot_depth(lc):
    """clock_landing_plan.local_depths for one type: max over collector nodes of graph distance to the root node, + 1."""
    adj = collections.defaultdict(list)
    for r in lc["collector_tree"].get("relays", []):
        adj[r["q"]].append(r["d"])
        adj[r["d"]].append(r["q"])
    root = lc.get("collector_root_node") or "rst_root_n"
    dist = {root: 0}
    todo = [root]
    while todo:
        n = todo.pop()
        for q in adj[n]:
            if q not in dist:
                dist[q] = dist[n] + 1
                todo.append(q)
    nodes = [s.get("node", f"rst_n_t{s.get('tap', 0)}") for s in lc.get("collector_local_sources", [])]
    nodes += [c["node"] for c in lc.get("collector_children", [])]
    return max([dist.get(n, 0) + 1 for n in nodes] or [0])


def apply(raw, only=None):
    """Re-pick the nodes in place; -> report dict (types, unfixed, before/after census, changes[(type,index)]->new node)."""
    before = census(raw, only)
    changes, unfixed, rep_types = {}, [], {}
    depth0 = {}
    for tn, lc, c, ctr, n, R in list(pairs(raw, only)):
        depth0.setdefault(tn, boot_depth(lc))
        if n is None or man(ctr, n["xy"]) <= REACH_UM:
            continue
        new, why = pick(lc, c, ctr, R)
        if new is None:
            unfixed.append(dict(type=tn, index=c["index"], node=c["node"], um=round(man(ctr, n["xy"]), 1), why=why))
            continue
        r = R[new]
        rep_types.setdefault(tn, []).append(dict(
            index=c["index"], part=c.get("part"), old=c["node"], new=new, old_um=round(man(ctr, n["xy"]), 1),
            new_um=round(man(ctr, r["xy"]), 1), pin_um=round(man(c["xy_um"], r["xy"]), 1), depth_old=n["depth"],
            depth_new=r["depth"], cycles_added=r["depth"] - n["depth"], why=why))
        changes[(tn, c["index"])] = new
        c["node"] = new
    added = {}
    for tn in sorted(rep_types):
        lc = raw["partition_types"][tn]["clock"]["landing_contract"]
        added[tn] = boot_depth(lc) - depth0[tn]
    after = census(raw, only)
    for k in ("over",):
        before.pop(k), after.pop(k)
    return dict(before=before, after=after, changed_pairs=len(changes), changed_types=len(rep_types), unfixed=unfixed,
                boot_depth_added_cycles=added, max_child_cycles_added=max([x["cycles_added"] for v in rep_types.values() for x in v] or [0]),
                types=rep_types), changes


def apply_sidecar(sc, changes):
    """collector.types[T].children[i].node, same (type, index) key; a child that is absent from the sidecar is an error."""
    n = 0
    types = ((sc.get("collector") or {}).get("types")) or {}
    for (tn, i), new in sorted(changes.items()):
        rows = [r for r in (types.get(tn) or {}).get("children", []) if r.get("index") == i]
        if len(rows) != 1:
            raise SystemExit(f"sidecar: type {tn} child {i}: {len(rows)} rows")
        if rows[0].get("node") != new:
            rows[0]["node"] = new
            n += 1
    return n


# ---- SRC form (S81-MONLEG 11-25, COORD KV/QC sweep): collector_local_sources whose status flops (band centre) or status pins
# are over REACH_UM from their node.  The bind rule (landing_collector.build_local) judges xy_um / status_pins_xy_um; the ring's
# ready/fault flops sit in the band (clock_landing_plan), so the band centre is judged as well.  Same-depth, same-kind relay
# within reach of every point; 0 cycles; tap key kept consistent (a source with a tap key only moves to an rst_n_t<k> node).
import re as _re


def src_points(s, nxy):
    pts = s.get("status_pins_xy_um") or [s.get("xy_um") or nxy]
    b = s.get("band") if isinstance(s.get("band"), dict) else None
    if b and b.get("rect_um"):
        pts = list(pts) + [centre(b["rect_um"])]
    return pts


def src_hop(s, nxy):
    return max(man(p, nxy) for p in src_points(s, nxy))


def src_rows(raw, only=None):
    for tn in sorted(raw.get("partition_types", {})):
        t = raw["partition_types"][tn]
        lc = (t.get("clock") or {}).get("landing_contract") if isinstance(t, dict) else None
        if not lc or not lc.get("collector_local_sources") or not isinstance(lc.get("collector_tree"), dict) or (only and tn not in only):
            continue
        R = tree_index(lc["collector_tree"])
        for i, s in enumerate(lc["collector_local_sources"]):
            n = R.get(s.get("node", f"rst_n_t{s.get('tap', 0)}"))
            if n is not None:
                yield tn, lc, i, s, n, R


def src_census(raw, only=None):
    over = [(tn, i, s.get("node"), src_hop(s, n["xy"])) for tn, lc, i, s, n, R in src_rows(raw, only) if src_hop(s, n["xy"]) > REACH_UM]
    return dict(over_reach=len(over), over_reach_types=len({o[0] for o in over}), over_fail=sum(1 for o in over if o[3] > FAIL_UM),
                max_um=round(max([o[3] for o in over] or [0.0]), 1), over=over)


def src_pick(s, n, R):
    tapped = "tap" in s
    ok = [r for r in R.values() if r["depth"] == n["depth"] and r["kind"] == n["kind"] and src_hop(s, r["xy"]) <= REACH_UM
          and (not tapped or _re.fullmatch(r"rst_n_t\d+", r["q"]))]
    if not ok:
        return None
    return min(ok, key=lambda r: (src_hop(s, r["xy"]), r["q"]))["q"]


def apply_src(raw, only=None):
    """In place; -> (report, ops).  ops = replace ops with old-value checks (node, and tap when the source carries one)."""
    ops, rep, unfixed = [], {}, []
    for tn, lc, i, s, n, R in list(src_rows(raw, only)):
        h = src_hop(s, n["xy"])
        if h <= REACH_UM:
            continue
        new = src_pick(s, n, R)
        base = f"/partition_types/{tn}/clock/landing_contract/collector_local_sources/{i}"
        if new is None:
            unfixed.append(dict(type=tn, index=i, name=s.get("name"), node=s.get("node"), um=round(h, 1)))
            continue
        was = s.get("node")
        ops.append(dict(op="replace", path=base + "/node", old=was, value=new))
        s["node"] = new
        if "tap" in s:
            nt = int(new[7:])
            ops.append(dict(op="replace", path=base + "/tap", old=s["tap"], value=nt))
            s["tap"] = nt
        rep.setdefault(tn, []).append(dict(index=i, name=s.get("name"), old=was, new=new,
                                           old_um=round(h, 1), new_um=round(src_hop(s, R[new]["xy"]), 1),
                                           depth=n["depth"], cycles_added=0))
    return dict(types=rep, changed=sum(len(v) for v in rep.values()), changed_types=len(rep), unfixed=unfixed,
                after=src_census(raw, only)["over_reach"]), ops


def check_ops(base_raw, ops):
    """Every op's old value equals the base plan's value at its path; -> number of failures."""
    bad = 0
    for o in ops:
        x = base_raw
        for k in o["path"].strip("/").split("/"):
            x = x[int(k)] if isinstance(x, list) else x[k]
        bad += x != o["old"]
    return bad


def _style(b, obj):
    for f in (lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, separators=(",", ":")) + "\n",
              lambda p: json.dumps(p) + "\n", lambda p: json.dumps(p, indent=2) + "\n"):
        if f(obj).encode() == b:
            return f
    return lambda p: json.dumps(p, indent=1) + "\n"


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    opt = {}
    pos = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--sidecar-in", "--sidecar-out", "--ops", "--row"):
            opt[a] = argv[i + 1]
            i += 2
        elif a.startswith("--types="):
            opt["types"] = set(a.split("=", 1)[1].split(","))
            i += 1
        elif a.startswith("--"):
            opt[a] = True
            i += 1
        else:
            pos.append(a)
            i += 1
    only = opt.get("types")
    if "--census" in opt:
        raw0 = json.load(open(pos[0]))
        c = census(raw0, only)
        c.pop("over")
        sc0 = src_census(raw0, only)
        sc0.pop("over")
        print("MONLEG census", json.dumps(c), "src", json.dumps(sc0))
        return 0
    pin, pout = pos[0], pos[1]
    rep_path = pos[2] if len(pos) > 2 else pout + ".monleg.json"
    pb = open(pin, "rb").read()
    raw = json.loads(pb)
    pf = _style(pb, raw)
    pre = json.loads(pb)
    rep, changes = apply(raw, only)
    ops = []
    if "--src" in opt:
        rep["src"], ops = apply_src(raw, only)
        rep["src"]["before"] = src_census(pre, only)["over_reach"]
    if "--ops" in opt:
        cops = [dict(op="replace", path=f"/partition_types/{tn}/clock/landing_contract/collector_children/{i}/node",
                     old=pre["partition_types"][tn]["clock"]["landing_contract"]["collector_children"][i]["node"], value=new)
                for (tn, i), new in sorted(changes.items())]
        ops_all = cops + ops
        rep["ops_old_value_failures"] = check_ops(pre, ops_all)
        rep["ops_count"] = len(ops_all)
        json.dump(dict(row=opt.get("--row", "MONLEG"), lane="S81-MONLEG", base_sha12=_sha(pin),
                       why="collector child / source node re-picked to the same-depth relay within 405 um of its monitor / status points "
                           "(0 cycles)", ops=ops_all,
                       check=dict(children={k: len(v) for k, v in rep["types"].items()},
                                  sources={k: len(v) for k, v in rep.get("src", {}).get("types", {}).items()})),
                  open(opt["--ops"], "w"), indent=1)
    rep.update(row="ROWS_S81-MONLEG", plan_in=pin, plan_in_sha=_sha(pin), reach_um=REACH_UM)
    if "--sidecar-in" in opt:
        sb = open(opt["--sidecar-in"], "rb").read()
        sc = json.loads(sb)
        rep["sidecar_children_changed"] = apply_sidecar(sc, changes)
        open(opt["--sidecar-out"], "w").write(_style(sb, sc)(sc))
        rep["sidecar_out_sha"] = _sha(opt["--sidecar-out"])
    if "--strict" in opt and rep["unfixed"]:
        print("MONLEG REFUSE", json.dumps(rep["unfixed"][:5]))
        return 3
    open(pout, "w").write(pf(raw))
    rep["plan_out_sha"] = _sha(pout)
    json.dump(rep, open(rep_path, "w"), indent=1, sort_keys=True)
    print("MONLEG before", json.dumps(rep["before"]))
    print("MONLEG after ", json.dumps(rep["after"]))
    print("MONLEG changed", rep["changed_pairs"], "pairs on", rep["changed_types"], "types; unfixed", len(rep["unfixed"]),
          "; max child cycles added", rep["max_child_cycles_added"], "; boot depth added", sum(rep["boot_depth_added_cycles"].values()))
    print("MONLEG plan_out", rep["plan_out_sha"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""G0 reverse-collector / reset-relay hop reach (SEAM-HOP-1, COORD 11-12): the SAME rule bind uses in
landing_collector.build_local ("reverse collector <child>-><node>: <d>um exceeds 405"), run on the plan alone.

A soft type with clock.landing_contract.collector_tree registers a ready-AND / fault-OR chain along the reverse of its
local reset tree.  Active nodes = the reset taps of collector_local_sources and collector_children and every ancestor
up to the collector root; every active edge (node -> parent, Manhattan between the two relay sites) and every source
-> its tap hop must be <= 405 um, else the bind stops with an EMIT error one whole round later.  ERROR check
"collector_reach", one finding per type and edge (first max_per_type per type, then a count).

    python3 tools/die_plan/collector_reach.py PLAN[.gz] [--json OUT]
"""
import argparse
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

REACH_UM = 405.0
TOL = 1e-6


def type_findings(tn, t, reach=REACH_UM):
    """[dict(type, kind, src, dst, hop_um)] over the active edges of one type's collector tree (empty = fine / no tree)."""
    lc = ((t.get("clock") or {}).get("landing_contract") or {})
    tree = lc.get("collector_tree")
    if not isinstance(tree, dict) or tree.get("hard") or not tree.get("relays"):
        return []
    sources = list(lc.get("collector_local_sources") or []) + list(lc.get("collector_children") or [])
    if not sources:
        return []
    root = lc.get("collector_root_node") or "rst_root_n"
    relays = {r["q"]: r for r in tree["relays"]}
    xy = {"rst_root_n": tuple(tree["root"]), **{q: tuple(r["xy"]) for q, r in relays.items()}}
    if root not in xy:
        return []
    adj = defaultdict(list)
    for q, r in relays.items():
        adj[q].append(r["d"])
        adj[r["d"]].append(q)
    parent, queue = {root: None}, [root]
    while queue:
        n = queue.pop()
        for o in adj[n]:
            if o not in parent:
                parent[o] = n
                queue.append(o)
    out, active = [], set()
    for src in sources:
        node = src.get("node", f"rst_n_t{src.get('tap', 0)}")
        if node not in xy:
            continue
        pins = src.get("status_pins_xy_um") or [src.get("xy_um", xy[node])]
        hop = max(abs(p[0] - xy[node][0]) + abs(p[1] - xy[node][1]) for p in pins)
        if hop > reach + TOL:
            out.append(dict(type=tn, kind="source", src=src.get("name", "?"), dst=node, hop_um=round(hop, 3)))
        while node in parent and node not in active:
            active.add(node)
            node = parent[node]
            if node is None:
                break
    for node in sorted(active):
        p = parent.get(node)
        if p is None or node == root:
            continue
        d = abs(xy[node][0] - xy[p][0]) + abs(xy[node][1] - xy[p][1])
        if d > reach + TOL:
            out.append(dict(type=tn, kind="edge", src=node, dst=p, hop_um=round(d, 3)))
    return out


def find_all(raw, reach=REACH_UM):
    rows = []
    for tn, t in raw["partition_types"].items():
        rows += type_findings(tn, t, reach)
    return rows


def check_collector_reach(P, R, reach=REACH_UM, max_per_type=3):
    """ERROR per violating active collector edge; returns the summary dict for the G0 report."""
    rows = find_all(P.raw, reach)
    seen = defaultdict(int)
    for r in sorted(rows, key=lambda r: -r["hop_um"]):
        seen[r["type"]] += 1
        if seen[r["type"]] <= max_per_type:
            what = "reverse collector" if r["kind"] == "edge" else "collector source"
            R.err("collector_reach", f"{what} {r['src']}->{r['dst']}: {r['hop_um']:.3f}um exceeds {reach:g} "
                  f"(type {r['type']}; the bind stops on this as EMIT <type>: {what} ...)", type=r["type"])
    extra = sum(max(0, n - max_per_type) for n in seen.values())
    if extra:
        R.err("collector_reach", f"... {extra} more over-reach collector edges in {len(seen)} types (summary.collector_reach)")
    worst = sorted(rows, key=lambda r: -r["hop_um"])[:10]
    return dict(reach_um=reach, edges_over=len(rows), types_over=len(seen), worst=worst)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    raw = json.loads(gzip.open(a.plan, "rt").read()) if a.plan.endswith(".gz") else json.loads(Path(a.plan).read_text())
    rows = find_all(raw)
    print(f"{len(rows)} over-reach collector edges in {len({r['type'] for r in rows})} types")
    for r in sorted(rows, key=lambda r: -r["hop_um"])[:10]:
        print(f"  {r['hop_um']:8.1f} um  {r['type']}  {r['kind']} {r['src']}->{r['dst']}")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

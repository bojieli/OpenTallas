#!/usr/bin/env python3
"""DIE-QC-68 11-04: re-derive the landing collector's reset-tree nodes after the collector_tree republish.

republish_collector_trees.py renumbers relay nodes; sidecar collector children / local_sources / root still name the old
ones (bind: "collector source child0 -> rst_n_t28: 2482.816um exceeds 405"). Node choice follows clock_landing_plan.compose:
a child sits at _monitor_endpoints' dst_node, the type root at its src_node or RT.leaf_tap, a local source at the nearest
reset tap. Pins, bands and relays stay. Rows that still exceed reach are reported.

    renode_collector.py PLAN SIDECAR [--write]   (run from the repository root)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "tools/die_plan")
import clock_landing_plan as CLP
import reset_tree as RT
import schema

REACH = 405.0


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def main(plan_path, side_path, write):
    raw = json.loads(Path(plan_path).read_text())
    stext = Path(side_path).read_text()
    side = json.loads(stext)
    P = schema.Plan(raw, Path(plan_path))
    Wf = RT.wf_plan(P)
    col = side["collector"]
    n, far, shown = 0, [], 0
    for tn, inf in col["types"].items():
        tree = inf.get("tree")
        if not tree or tree.get("hard"):
            continue
        xy = {"rst_root_n": tree["root"], **{r["q"]: r["xy"] for r in tree["relays"]}}
        for ch in inf.get("children") or []:
            parts = col["parts"]
            part = ch["part"]
            dst = parts[part]["parent"]
            try:
                end = CLP._monitor_endpoints(P, Wf, part, dst, lambda q: ch["xy_um"])
            except ValueError:
                end = None
            node = end["dst_node"] if end else ch.get("node")
            if node not in xy:
                node = min(xy, key=lambda q: man(xy[q], ch["xy_um"]))
            if node != ch.get("node"):
                n += 1
            ch["node"] = node
            hop = man(ch["xy_um"], xy[node])
            if hop > REACH:
                near = min(xy, key=lambda q: man(xy[q], ch["xy_um"]))
                far.append([tn, "child", part, node, round(hop, 1), near, round(man(xy[near], ch["xy_um"]), 1)])
                ch["node"] = near
        for src in inf.get("local_sources") or []:
            node = src.get("node", f"rst_n_t{src.get('tap', 0)}")
            pt = src.get("xy_um", xy.get(node))
            if node not in xy or man(pt, xy[node]) > REACH:
                near = min((q for q in xy if q.startswith("rst_n_t")), key=lambda q: man(xy[q], pt))
                far.append([tn, "source", src["name"], node, round(man(pt, xy[node]), 1) if node in xy else None, near, round(man(xy[near], pt), 1)])
                n += 1
                if "node" in src:
                    src["node"] = near
                else:
                    src["tap"] = int(near.rsplit("t", 1)[1])
        rt = inf.get("collector_root_node")
        if rt and rt not in xy:
            far.append([tn, "root", rt])
    print(f"renode: {n} rows changed; {len(far)} rows needed the nearest node")
    for row in far[:60]:
        print(row)
    print("still over reach:", sum(1 for r in far if len(r) > 6 and r[6] > REACH))
    if write:
        fmt = {"indent": 1} if stext.startswith("{\n") else {}
        Path(side_path).write_text(json.dumps(side, **fmt) + ("\n" if stext.endswith("\n") else ""))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--write" in sys.argv)

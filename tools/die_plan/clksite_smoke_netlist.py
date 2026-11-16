import json, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import die_trial as D
import schema as S
PLAN = sys.argv[2]
P = S.Plan(S.load(PLAN), Path(PLAN))
site = D.clock_site(P)


def kit_nodes(tree):
    T = json.load(open(tree))
    nodes = {int(k): dict(v) for k, v in T["nodes"].items()}
    by = {}
    for t in T["taps"]:
        by.setdefault(t["node"], []).append((t["part"], t["port"], t["xy"][0], t["xy"][1]))
    for i, v in nodes.items():
        v["taps"] = by.get(i, [])
        v["kids"] = list(v.get("kids", []))
    taps = [(t["part"], t["port"], t["xy"][0], t["xy"][1]) for t in T["taps"]]
    return nodes, taps, T["meta"]


for tree in sys.argv[3:]:
    t0 = time.time()
    nodes, taps, meta = kit_nodes(tree)
    try:
        v, place, tap_ports, node_buf, parent_of = D.tree_netlist(nodes, taps, rep_um=float(meta.get("rep_um", 150)), site=site,
                                                                  clock_cell=meta.get("clock_cell", "buf"))
        names = [p[0] for p in place]
        print(tree, "OK cells", v.count("\n"), "placed", len(place), "unique", len(set(names)), "tap_ports", len(tap_ports),
              "bad_parent", sum(1 for k, p in parent_of.items() if p not in node_buf.values() and p not in parent_of),
              "t=%.0fs" % (time.time() - t0))
    except Exception as e:
        import traceback; traceback.print_exc(limit=3)
        print(tree, "FAIL", repr(e)[:300])

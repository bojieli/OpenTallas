#!/usr/bin/env python3
"""DIE-HEAD-5: DIE-HEAD-2 mk_proof.py + per-tap START-TREE-1 tree_path (root h + U+0100 child-index char per tree level) and
per-tree-cell cppr_node_range_ps keyed by that path, so die_sta_related --cppr-lca credits CPPR to the TRUE last common
tree node (12.4b) instead of the die root for cross-region pairs.  Without --cppr-lca the output is used as before.
DIE-HEAD-2 (4): die_sta_related proof-dir export from a die_trial routed die-clock run (combo GRT, FB1 one entry
per partition).  NOT a die_clock_mesh proof: this only re-packages the run's own numbers.

    mk_proof.py RUN_DIR MAP_JSON OUT_DIR      (RUN_DIR/clk/tree.json, RUN_DIR/out_<C>/arr_<C>.txt)

Per tap port t_<part>__clk: late = 833.333 - slack_max_rise (= max arrival, output delay 0), early = slack_min_rise
(= min arrival), slew = slew_max_rise.  cppr_node = the partition's clock region from MAP_JSON part_region (feed40);
region node = the last common tree cell of all the region's entries (its arrivals = that cell's Y max/min arrivals);
die root 'h' = cell b0.  cppr_node_range_ps = late - early at that node (CPPR credit cap, 12.4b: credit only to the
region root, which is at or above every in-region pair's true LCA = conservative).  stages_from_root = cells on the
entry's chain to the root (leaf included), node_stages likewise, so die_sta_related's class-A stage count = cells below
the node (= landed_phase_ocv's count).  mesh.json carries only the tap list (port, part, xy) for the nearest-tap INFO
and HB4 seam-bit counts; droop_regions.json = {port: region} (shared droop: same feed40 region, else one-sided)."""
import json
import sys
from pathlib import Path

run, mp, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
tree = json.loads((run / "clk" / "tree.json").read_text())
pr = json.loads(mp.read_text())["part_region"]


def chain(c):
    o = [c]
    while c in tree["parent_of"]:
        c = tree["parent_of"][c]
        o.append(c)
    return o


leaf = {t["port"]: tree["node_buf"][str(t["node"])] for t in tree["taps"]}
tap = {t["port"]: t for t in tree["taps"]}
root = chain(next(iter(leaf.values())))[-1]
assert root == "b0", root
reg_ports = {}
for p, t in tap.items():
    reg_ports.setdefault(pr[t["part"]], []).append(p)
rnode = {}
for r, ps in reg_ports.items():
    common = None
    for p in ps:
        ch = chain(leaf[p])
        common = ch if common is None else [c for c in common if c in set(ch)]
    rnode[r] = common[0]          # deepest common cell (chains are leaf..root, order kept)
kids = {}
for c, par in sorted(tree["parent_of"].items()):
    kids.setdefault(par, []).append(c)
pathof = {root: "h"}
stack = [root]
while stack:
    c = stack.pop()
    for i, k in enumerate(sorted(kids.get(c, []))):
        pathof[k] = pathof[c] + chr(0x100 + i)
        stack.append(k)
for C in ("TT", "FF"):
    T, N = {}, {}
    for ln in (run / f"out_{C}" / f"arr_{C}.txt").read_text().splitlines():
        x = ln.split()
        if x and x[0] == "T":
            T[x[1]] = (float(x[2]), float(x[3]), float(x[4]))
        elif x and x[0] == "N":
            N[x[1]] = (float(x[2]), float(x[3]))
    # CPPR-LCA chooses any shared path prefix, not only a region root. Every
    # physical tree cell needs the same measured geometry/stages/arrival fields.
    nodes = {pathof[c]:c for c in pathof}
    nodes.update(h=root, **{r:c for r,c in rnode.items()})
    meta = dict(corner=C, basis=f"die_trial combo GRT-RC routed die clock {run} (DIE-HEAD-2 mk_proof.py; regions = feed40 map)",
                node_cell=nodes,
                node_stages={n: len(chain(c)) for n, c in nodes.items()},
                node_xy_um={n: tree["sites"][c] for n, c in nodes.items()},
                node_late_ps={n: N[c][0] for n, c in nodes.items()},
                node_early_ps={n: N[c][1] for n, c in nodes.items()},
                cppr_node_range_ps=dict({pathof[c]: max(0.0, N[c][0] - N[c][1]) for c in pathof if c in N},
                                        **{n: max(0.0, N[c][0] - N[c][1]) for n, c in nodes.items()}))
    taps = []
    for p, t in sorted(tap.items()):
        late, early, slew = T[p]
        taps.append(dict(port=p, part=t["part"], late_ps=late, early_ps=early, slew_ps=slew, cppr_node=pr[t["part"]],
                         stages_from_root=len(chain(leaf[p])), xy_um=t["xy"], leaf_cell=leaf[p],
                         tree_path=pathof[leaf[p]]))
    meta["taps"] = taps
    (out / f"tap_arrivals_{C}.json").write_text(json.dumps(meta, indent=0) + "\n")
(out / "mesh.json").write_text(json.dumps(dict(note="tap list only (no mesh): nearest-tap/HB4 bit counts",
                                               taps=[dict(port=p, part=t["part"], xy=t["xy"]) for p, t in sorted(tap.items())])) + "\n")
(out / "droop_regions.json").write_text(json.dumps({p: pr[t["part"]] for p, t in tap.items()}) + "\n")
print(json.dumps(dict(taps=len(tap), regions=len(rnode), region_nodes=rnode,
                      node_stages={r: len(chain(c)) for r, c in rnode.items()}), indent=0))

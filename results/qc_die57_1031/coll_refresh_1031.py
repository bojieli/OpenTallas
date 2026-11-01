#!/usr/bin/env python3
"""DIE-QC-58 10-31 (COORD 22:5x (1)): refresh the stale QC landing-collector entries of the as-built sidecar.

Strict bind on plan_qc52 A2 (bb805ef2b38, --asbuilt results/qc_die57_1031/bind/final_asbuilt.json) stops at
'EMIT collector rst_n_t18: raw reset parent rst_rl_16 absent' (type sle_ctl__cl372cea1c).  Cause: the sidecar collector
(copied from results/qc_die33_1029/bind/sidecar.json, 10-29) still carries the OLD per-type reset trees, while the
wrapper RTL is emitted from reset_tree.for_type(plan) and the plan landing_contract already mirrors those trees
(collector_tree == for_type on every refreshed type, checked by the caller's analysis).  Same class as the S81 t4/t13
collector re-derive (delta_alltap_coll_1030.py, DIE-S81-45 f0c3003d798): here the re-derived collector already exists
in the plan, so the sidecar entries are taken from the plan landing_contract (tree / local_sources / children /
root node) for every type whose sidecar tree differs from the plan's while the plan's equals the emitted tree
(--types file).  collector_root_xy is re-read from the new tree when the root is a tree node.  Boot budget
local_registered_depths / ready_at_glue_max_cycles are recomputed with compose's law (self-checked on the old depths
first; left unchanged with a note if the recursion does not reproduce the stored value).  Nothing else changes
(asserted).  usage: coll_refresh_1031.py PLAN SIDECAR TYPES.txt REPORT.json   (rewrites SIDECAR in place)"""
import copy
import json
import sys
from collections import defaultdict

sys.path.insert(0, "tools/die_plan")
import clock_landing_plan as CLP  # noqa: E402

KEYS = (("tree", "collector_tree"), ("local_sources", "collector_local_sources"),
        ("children", "collector_children"), ("collector_root_node", "collector_root_node"))


def local_depth(inf):
    tree, rootnode = inf["tree"], inf["collector_root_node"]
    if tree.get("hard"):
        return len(tree["relays"]) + 1
    adj = defaultdict(list)
    for r in tree["relays"]:
        adj[r["q"]].append(r["d"])
        adj[r["d"]].append(r["q"])
    dist = {rootnode: 0}
    todo = [rootnode]
    while todo:
        n = todo.pop()
        for q in adj[n]:
            if q not in dist:
                dist[q] = dist[n] + 1
                todo.append(q)
    nodes = [f"rst_n_t{s['tap']}" for s in inf["local_sources"]] + [c["node"] for c in inf["children"]]
    return max([dist[n] + 1 for n in nodes] or [0])


def main():
    pp, sp, tp, rp = sys.argv[1:5]
    raw = json.load(open(pp))
    stext = open(sp).read()
    side = json.loads(stext)
    compact = json.dumps(side, separators=(",", ":")) + "\n" == stext
    sorig = copy.deepcopy(side)
    col = side["collector"]
    ct = col["types"]
    types = [t.strip() for t in open(tp) if t.strip()]
    rep = {}
    for tn in types:
        ent = ct[tn]
        lc = raw["partition_types"][tn]["clock"]["landing_contract"]
        assert ent["tree"] != lc["collector_tree"], tn
        old = {k: ent.get(k) for k, _ in KEYS}
        for k, lk in KEYS:
            ent[k] = copy.deepcopy(lc[lk])
        rn = ent["collector_root_node"]
        if rn != "rst_root_n":
            ent["collector_root_xy"] = next(r["xy"] for r in ent["tree"]["relays"] if r["q"] == rn)
        # every node the collector names exists in the new tree
        qs = {r["q"]: r["d"] for r in ent["tree"]["relays"]}
        for n in [rn] + [c["node"] for c in ent["children"]] + [f"rst_n_t{s['tap']}" for s in ent["local_sources"]]:
            assert n == "rst_root_n" or n in qs, (tn, n)
        assert [s["name"] for s in ent["local_sources"]] == [s["name"] for s in old["local_sources"]], tn
        assert [c["part"] for c in ent["children"]] == [c["part"] for c in old["children"]], tn
        rep[tn] = dict(relays=[len(old["tree"]["relays"]), len(ent["tree"]["relays"])],
                       root=[old["collector_root_node"], rn],
                       children=[[a["node"], b["node"]] for a, b in zip(old["children"], ent["children"])],
                       source_taps=[[a.get("tap"), b.get("tap")] for a, b in zip(old["local_sources"], ent["local_sources"])])
    bb = col.get("boot_budget")
    if isinstance(bb, dict) and "local_registered_depths" in bb:
        parts = col["parts"]
        kids = defaultdict(list)
        for e in col["edges"]:
            kids[e["dst"]].append(dict(part=e["src"], seam=e["seam"]))

        def run(depths):
            dl = {}

            def deadline(pn):
                if pn not in dl:
                    ch = [deadline(c["part"]) + (21 if c["seam"] else CLP.STATUS_FACE_CYCLES) for c in kids[pn]]
                    dl[pn] = max([bb["raw_reset_release_max_cycles"] + 21] + ch) + depths[pn]
                return dl[pn]
            return deadline(col["root"])
        ok = run(bb["local_registered_depths"]) == bb["ready_at_glue_max_cycles"]
        rep["_boot_selfcheck"] = ok
        if ok:
            new = dict(bb["local_registered_depths"])
            for pn in new:
                tn = parts[pn]["type"]
                if tn in rep:
                    new[pn] = local_depth(ct[tn])
            r0 = bb["ready_at_glue_max_cycles"]
            bb["local_registered_depths"] = new
            bb["ready_at_glue_max_cycles"] = run(new)
            rep["_boot"] = dict(ready_at_glue_max_cycles=[r0, bb["ready_at_glue_max_cycles"]],
                                depth_changes={pn: [sorig["collector"]["boot_budget"]["local_registered_depths"][pn], d]
                                               for pn, d in new.items()
                                               if sorig["collector"]["boot_budget"]["local_registered_depths"][pn] != d})
    for k in side:
        if k != "collector":
            assert side[k] == sorig[k], k
    for k in col:
        if k not in ("types", "boot_budget"):
            assert col[k] == sorig["collector"][k], k
    for tn in ct:
        if tn not in rep:
            assert ct[tn] == sorig["collector"]["types"][tn], tn
    open(sp, "w").write(json.dumps(side, separators=(",", ":")) + "\n" if compact else json.dumps(side, indent=1) + "\n")
    json.dump(rep, open(rp, "w"), indent=1)
    print(len([t for t in rep if not t.startswith("_")]), "types refreshed; boot", json.dumps(rep.get("_boot", rep.get("_boot_selfcheck")))[:400])


if __name__ == "__main__":
    main()

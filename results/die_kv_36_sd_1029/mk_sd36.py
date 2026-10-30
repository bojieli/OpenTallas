#!/usr/bin/env python3
"""DIE-KV-36 KV-022 (fix-only plan/sidecar delta sd36): the sys_SD / sys_SD_v1 landing COLLECTOR tree is stale.
The event26 sidecar collector.types[T].tree (and its copy plan partition_types[T].clock.landing_contract.collector_tree)
was composed on the pre-PHY-abstract base (17 taps, several over the x6 PHY macro, e.g. rst_n_t10 @ (1702.08, 406.08)),
while the kit/bound reset tree (tools/die_plan/reset_tree.for_type on the CURRENT plan, PHY macro = blockage) has 15
taps, all off the macro.  The collector then sites u_cland_collect_rst_n_t10 on the macro (3_3 GP OT_CLAND fail) and
its rst_n net (rst_n_t10 of the CURRENT tree, at (4.32, 734.4)) is ~1.7 mm away.
Delta (no new rule): tree := reset_tree.for_type(P, T) of the current plan (the same tree the kit RTL/ reset_tree.tcl
carry); each collector local source re-tapped to the nearest current reset tap within the existing 405-um reach
(landing_collector.build_local rule); everything else unchanged.  Applied to the sidecar and to every plan given.
variant B: SD36_TAP=rst_n_t5 (both sources on one tap).
usage: mk_sd36.py TOOLS SIDECAR_IN SIDECAR_OUT PLAN_IN PLAN_OUT [PLAN_IN PLAN_OUT ...]"""
import json, sys, copy, hashlib
from collections import defaultdict
sys.path.insert(0, sys.argv[1])
import schema as S, reset_tree as RT
TYPES = ("kv3_sys_SD", "kv3_sys_SD_v1")
MACRO = (17.28 - 4.32, 54.0 - 4.32, 17.28 + 1848.96 + 4.32, 54.0 + 972.0 + 4.32)   # x6 PHY + halo, type frame
REACH = 405.0
man = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
on_macro = lambda p: MACRO[0] < p[0] < MACRO[2] and MACRO[1] < p[1] < MACRO[3]


def depth_to_root(tree, node, root="rst_root_n"):
    par = {r["q"]: r["d"] for r in tree["relays"]}
    n, k = node, 0
    while n != root:
        n = par[n]; k += 1
    return k


def new_tree(P, tn):
    T = RT.for_type(P, tn)
    keep = ("root", "depth", "own_depth", "relays", "max_hop_um", "reach_um", "taps", "n_tree", "n_pad")
    return {k: (list(T[k]) if k == "root" else T[k]) for k in keep if k in T}


def retap(tree, sources):
    taps = {r["q"]: r["xy"] for r in tree["relays"] if r["q"].startswith("rst_n_t")}
    out, rec = [], []
    for s in sources:
        if FORCE:   # variant B: every local source on ONE named reset tap (still inside the 405-um reach)
            q, xy = FORCE, taps[FORCE]
        else:
            q, xy = min(taps.items(), key=lambda kv: (man(kv[1], s["xy_um"]), kv[0]))
        hop = man(xy, s["xy_um"])
        assert hop <= REACH + 1e-6, (s["name"], q, hop)
        s2 = dict(s, tap=int(q[len("rst_n_t"):]))
        out.append(s2); rec.append(dict(source=s["name"], old_tap=s["tap"], new_tap=s2["tap"], hop_um=round(hop, 2)))
    return out, rec


import os
FORCE = os.environ.get("SD36_TAP")   # unset = variant A (nearest tap per source)
tools, sin, sout = sys.argv[1:4]
plans = list(zip(sys.argv[4::2], sys.argv[5::2]))
P0 = S.Plan(json.load(open(plans[0][0])), plans[0][0])
side = json.load(open(sin)); rep = dict(types={})
trees = {tn: new_tree(P0, tn) for tn in TYPES}
for tn in TYPES:
    ct = side["collector"]["types"][tn]
    old = ct["tree"]
    srcs, rec = retap(trees[tn], ct["local_sources"])
    assert not ct["children"], "sys_SD collector has no children (leaf)"
    old_nodes = [f"rst_n_t{s['tap']}" for s in ct["local_sources"]]
    new_nodes = [f"rst_n_t{s['tap']}" for s in srcs]
    r = dict(old_taps=sum(x["q"].startswith("rst_n_t") for x in old["relays"]), new_taps=sum(x["q"].startswith("rst_n_t") for x in trees[tn]["relays"]),
             old_relays=len(old["relays"]), new_relays=len(trees[tn]["relays"]),
             old_relays_on_macro=sorted(x["q"] for x in old["relays"] if on_macro(x["xy"])),
             new_relays_on_macro=sorted(x["q"] for x in trees[tn]["relays"] if on_macro(x["xy"])),
             old_depth=old["depth"], new_depth=trees[tn]["depth"], new_max_hop_um=trees[tn].get("max_hop_um"),
             sources=rec,
             collector_local_depth_old=max(depth_to_root(old, n) for n in old_nodes) + 1,
             collector_local_depth_new=max(depth_to_root(trees[tn], n) for n in new_nodes) + 1)
    # reverse collector path sites (what landing_place FIRMs) + hops
    par = {x["q"]: x["d"] for x in trees[tn]["relays"]}; xy = {x["q"]: x["xy"] for x in trees[tn]["relays"]}
    xy["rst_root_n"] = trees[tn]["root"]
    path, n = [], new_nodes[0]
    while True:
        path.append((n, xy[n]))
        if n == "rst_root_n": break
        n = par[n]
    r["collector_path"] = [[a, [round(b[0], 2), round(b[1], 2)]] for a, b in path]
    r["collector_path_max_hop_um"] = round(max(man(a[1], b[1]) for a, b in zip(path, path[1:])), 2)
    r["collector_path_on_macro"] = [a for a, b in path if on_macro(b)]
    rep["types"][tn] = r
    ct["tree"] = trees[tn]; ct["local_sources"] = srcs
bb = side["collector"].get("boot_budget", {})
ld = bb.get("local_registered_depths", {})
for pn, tn in (("sys_SW", "kv3_sys_SD"), ("sys_SE", "kv3_sys_SD_v1")):
    if pn in ld:
        rep["types"][tn]["boot_local_depth_sidecar"] = ld[pn]
        assert rep["types"][tn]["collector_local_depth_new"] <= ld[pn], (pn, ld[pn], rep["types"][tn])
json.dump(side, open(sout, "w"), indent=1)
rep["sidecar_out_sha256"] = hashlib.sha256(open(sout, "rb").read()).hexdigest()
rep["plans"] = {}
for pin, pout in plans:
    raw = json.load(open(pin)); n = 0
    for tn in TYPES:
        lc = raw["partition_types"][tn].get("clock", {}).get("landing_contract")
        if lc and "collector_tree" in lc:
            lc["collector_tree"] = side["collector"]["types"][tn]["tree"]
            lc["collector_local_sources"] = side["collector"]["types"][tn]["local_sources"]; n += 1
    raw["note"] = (raw.get("note", "") + " | DIE-KV-36 sd36: sys_SD/_v1 landing collector tree = current reset tree (PHY-free), sources re-tapped").strip(" |")
    json.dump(raw, open(pout, "w"), indent=1)
    rep["plans"][pout] = dict(types_patched=n, sha256=hashlib.sha256(open(pout, "rb").read()).hexdigest())
print(json.dumps(rep, indent=1))

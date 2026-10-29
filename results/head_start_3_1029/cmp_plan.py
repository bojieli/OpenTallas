#!/usr/bin/env python3
"""compare a re-plan to leaf_plan4: stage set, parents, edges, offsets, retime; summary numbers"""
import json, sys, collections
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
def idx(d):
    return {g["region"]: g for g in d["regions"]}
A, B = idx(a), idx(b)
r = dict(stages_old=len(A), stages_new=len(B), only_old=len(set(A) - set(B)), only_new=len(set(B) - set(A)))
c = collections.Counter()
ex = collections.defaultdict(list)
for k in set(A) & set(B):
    x, y = A[k].get("start_from") or {}, B[k].get("start_from") or {}
    for f in ("parent", "edge", "offset_from_parent", "J_nominal"):
        if x.get(f) != y.get(f):
            c[f] += 1
            if len(ex[f]) < 3: ex[f].append((k, x.get(f), y.get(f)))
    if A[k].get("origin_cycles") != B[k].get("origin_cycles"):
        c["origin_cycles"] += 1
        if len(ex["origin_cycles"]) < 3: ex["origin_cycles"].append((k, A[k].get("origin_cycles"), B[k].get("origin_cycles")))
r["changed"] = dict(c); r["examples"] = ex
s = b["summary"]
r["summary_new"] = {k: s.get(k) for k in ("regions", "tree_edges", "tree_edges_clean", "tree_edges_fall", "fail", "below_100ps",
                                          "worst_margin_lo_ps", "worst_margin_lo_port", "min_sync_dist_clean_ps",
                                          "start_skew_limit_min_ps", "max_path_ambiguous_cycles")}
st = s.get("start_tree", {})
r["start_tree_new"] = {k: st.get(k) for k in ("virtual_nodes", "retime_nodes", "start_clean", "start_fail", "start_width_ps",
                                              "start_min_sync_dist_ps", "leg_ps", "reach_fail")}
sd = sorted((g["start_from"]["sync_dist_ps"], g["region"]) for g in b["regions"] if g.get("start_from"))
r["sync_dist_min5"] = sd[:5]; r["sync_dist_lt100"] = sum(1 for x in sd if x[0] < 100)
oc = [g.get("origin_cycles") for g in b["regions"] if not str(g["region"]).startswith("st:")]
r["data_origin_cycles"] = dict(n=len(oc), min=min(oc), max=max(oc))
print(json.dumps(r, indent=1, default=str))

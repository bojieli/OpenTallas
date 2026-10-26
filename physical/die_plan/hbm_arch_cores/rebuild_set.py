#!/usr/bin/env python3
"""HBM-CORE-LAT-R4: HBM core restructure set on the B1 plan = measured natural insertion (core_latency_actions.json)
crossed with the master-plan 12.9d core_insertion_model / core_reach gates (gates.json of a die_infra master-plan run).
All numbers are model/diagnostic, UNCHECKED (12.9f). Usage: rebuild_set.py ACTIONS GATES R3INPUTS OUT"""
import json, sys
act, gates, r3, out = sys.argv[1:5]
A = json.load(open(act)); G = json.load(open(gates))["gates"]
M = {x["module"]: x for x in G["core_insertion_model"]["all"]}
R = {x["module"]: x for x in G["core_reach"]["restructure"]}
T = {x["module"]: x for x in json.load(open(r3))["types"]}
rows = []
for m, x in sorted(M.items(), key=lambda kv: -kv[1]["pred_TT_ps"]):
    a = A.get(m, {}); meas = a.get("measured_tt_ps"); pred = x["pred_TT_ps"]
    isl = R.get(m, {}).get("in_core_islands")
    if a.get("action") == "IP_DECLARED":
        cls = "IP_DECLARED"
    elif pred > 270 or (isl and x["farthest_um"] > 200):
        cls = "INTERNAL_HTREE_ISLANDS" if pred > 270 else "REACH_GT200_INTERNAL_HTREE_MODEL_IN_WINDOW"
    elif meas is not None and meas > 290:
        cls = "CENTRE_ENTRY_STRUCTURED_TREE"
    elif pred < 230:
        cls = "SHALLOW_FIXED_TRUNK (12.8c)" if meas is None or meas < 230 else "OK_OR_CENTRE"
    else:
        cls = "OK_CENTRE"
    rows.append(dict(module=m, inst=a.get("instances"), measured_edge_entry_tt_ps=meas, old_action=a.get("action"),
                     model_centre_tt_ps=pred, model_centre_ff_ps=x["pred_FF_ps"], farthest_um=x["farthest_um"],
                     entry_um=x["entry_um"], cls=cls,
                     island_grid=(isl or {}).get("grid"), leaf_reach_um=(isl or {}).get("leaf_reach_um"),
                     r3_sink_inputs=m in T, r3_coords=(T.get(m) or {}).get("coords")))
cnt = {}
for r in rows: cnt[r["cls"]] = cnt.get(r["cls"], 0) + 1
disagree = [r["module"] for r in rows if r["measured_edge_entry_tt_ps"] and r["measured_edge_entry_tt_ps"] > 290 and r["model_centre_tt_ps"] <= 270]
json.dump(dict(schema="hbm_core_rebuild_set/1", status="UNCHECKED (model + diagnostic)", gates_src=gates,
               model=G["core_insertion_model"]["model"], counts=cnt, n_types=len(rows),
               measured19_model_pass_with_centre=disagree, rows=rows), open(out, "w"), indent=1)
print(cnt); print("measured>290 but centre-model<=270:", disagree)

from pathlib import Path
import json, hashlib, gzip
Q = Path("/srv/opentallas-scratch2/claude")
O = Q/"wt/codex-qc-clock-0336/results/qc_clock_codex_0336/a0_frame_bindings"
src = Q/"codex-qc-a0-0336/impact/a0_public_clock_frames.json"
raw = src.read_bytes()
frames = json.loads(raw)
tf = Q/"codex-qc-clock-0336/reach_safe/out/kit/clock/tree.json"
t = json.load(open(tf))
taps = {(a["part"],a["port"].rsplit("__",1)[-1]):a for a in t["taps"]}
early = {(a["part"],a["port"]):a["early_model_ps"] for v in t["meta"]["site_legal"]["balance"]["region_dme"].values() for a in v.get("early_taps",[])}
with gzip.open(O/"public_core_tap_bindings.json.gz","rt") as f:
    base = json.load(f)
rows = []
for rr in base["cores"]:
    r = dict(rr)
    c = r["cohort"]
    fr = frames["types"][c]
    pn = r["proof_port"].rsplit("__",1)[-1]
    a = taps[(r["part"],pn)]
    assert max(abs(x-y) for x,y in zip(a["xy"],r["tap_die_xy_um"])) < 1e-6
    assert fr["public_ck"]["layer"] == r["public_native_pin"]["layer"]
    assert max(abs(x-y) for x,y in zip(fr["public_ck"]["xy_um"],r["public_native_pin"]["core_xy_um"])) < 1e-6
    r["tap_node"] = a["node"]
    r["tap_driver"] = a.get("driver") or t["node_buf"][str(a["node"])]
    r["old_generator_corner_average_early_model_ps"] = early[(r["part"],pn)]
    r["external_model_input_slew_ps"] = frames["external_input_slew_ps"]
    r["candidate_model"] = dict(fr, binding_status="PUBLIC_E_ABI_BOUND_MODEL_ONLY" if fr["related_pair_qualified"] else "PUBLIC_E_ABI_BOUND_MODEL_UNQUALIFIED")
    r["candidate_mean_delta_from_current_core_ps"] = {k:fr["corners"][k]["weighted_mean_ps"]-r["old_core_insertion_ps"][k] for k in ["TT","FF"]}
    rows.append(r)
new = dict(scope="SOURCE-ONLY binding of exact safe-graph core taps to public-E models. No source-arrival/slew readout, timing price, SDC or adoption; physical graph still FAIL89 PHY sites.", source_plan=base["plan"], source_plan_sha256=base["plan_sha256"], safe_tree=str(tf), safe_tree_sha256=hashlib.sha256(tf.read_bytes()).hexdigest(), frame_file=str(src), frame_sha256=hashlib.sha256(raw).hexdigest(), entry_feed_rule="E feed included exactly once in each model; external landing offset separate.", cores=rows)
with gzip.open(O/"public_E_safe_core_bindings.json.gz","wt") as f:
    json.dump(new,f)
(O/"public_E_frames_MODEL_ONLY.json").write_bytes(raw)
summary = dict(scope=new["scope"], cores=len(rows), cohorts={k:dict(cores=v["cores"],local_model_qualified=v["related_pair_qualified"],geometry_installed=v["actual_clock_geometry_installed"],clock_cells=v["clock_cells"]) for k,v in frames["types"].items()}, safe_tree_sha256=new["safe_tree_sha256"], frame_sha256=new["frame_sha256"], mean_delta_from_current_core_ps={k:{c:v["corners"][c]["weighted_mean_ps"]-v["corners"][c]["old_percore_insertion_ps"] for c in ["TT","FF"]} for k,v in frames["types"].items()}, input_slew_assumption_ps=frames["external_input_slew_ps"], entry_feed_included_once=True, source_arrivals_available=False)
(O/"public_E_safe_summary.json").write_text(json.dumps(summary,indent=1)+"\n")
print(json.dumps(summary))

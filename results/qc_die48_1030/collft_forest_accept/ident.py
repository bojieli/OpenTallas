import sys, json, gzip, hashlib
sys.path.insert(0, sys.argv[1])
import core_infra as CI, master_slice as MS
fx = sys.argv[2]
fix = json.load(open(fx + "/forest_fixture.json")); trees = json.load(gzip.open(fx + "/tree_packed_actual_pins.json.gz"))
models = json.load(gzip.open(fx + "/packed_full_models.json.gz"))
out = []
for port in [e["port"] for e in fix["clock_entries"]]:
    t = dict(trees[port]["core_tree"]); t.pop("coordinate_basis", None)
    mc = models[port]["corners"]; lm = {c: {l["node"]: l for l in mc[c]["leaf_means"]} for c in ("TT", "FF")}
    t["leaves"] = [dict(l, sinks=[s + "/CLK" for s in l["sinks"]], pin_latency_ps={c: dict(min=lm[c][l["node"]]["min_ps"], max=lm[c][l["node"]]["max_ps"]) for c in ("TT","FF")}) for l in t["leaves"]]
    q = dict(measured_timing_used=False, electrical_latency_qualified=True, source="h", model="h", band_policy="info", window_policy="info",
             corners={c: dict(slew_max=mc[c]["slew_max_ps"], leaf_min=min(l["pin_latency_ps"][c]["min"] for l in t["leaves"]), leaf_max=max(l["pin_latency_ps"][c]["max"] for l in t["leaves"])) for c in ("TT","FF")})
    for c in ("TT","FF"): q["corners"][c]["leaf_window"] = q["corners"][c]["leaf_max"] - q["corners"][c]["leaf_min"]
    t["model_qualification"] = q
    e = next(x for x in fix["clock_entries"] if x["port"] == port)
    sl = dict(schema=MS.SCHEMA, module=fix["module"], kind="core", outline_um=fix["outline_um"], pushdown={"islands": []},
              islands=[dict(name="i", rect_um=[0, 0, *fix["outline_um"]], clock_pin=dict(layer="M5", xy_um=e["xy_um"]))], bays=[],
              core_clock_port=port, core_tree=t, pg_obstructions_um={})
    plan = CI.compile_slice(sl)
    blob = CI.emit_tcl(sl) + CI.emit_cts_tcl(plan) + json.dumps(plan, sort_keys=True)
    out.append(port + " " + hashlib.sha256(blob.encode()).hexdigest()[:16])
print("\n".join(out))

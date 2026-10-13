#!/usr/bin/env python3
"""results/fleet_viz/element_registry/s81_hc_tiles_20261013.json from the hc_tile_qualification*.json records (qualified tiles only)"""
import json, subprocess, sys, datetime
from pathlib import Path
WT = Path("/home/ubuntu/wt/s81hc-1013")
full = lambda c: subprocess.run(["git", "-C", str(WT), "rev-parse", c], capture_output=True, text=True).stdout.strip()
recs = []
for rel in sys.argv[1:]:
    q = json.loads((WT / rel).read_text())
    for mod, t in q["tiles"].items():
        if not t["qualified"]:
            continue
        ok = [r for r in t["routes"] if r["ok"]]
        mu = t["mutant"]["result"]["runs"]
        recs.append(dict(
            element=mod, target="DeepSeek ROM", owner="Claude:s81hc-1013", recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            description="S81 HC hard leaf qualified by the production-shape composition gate (NG 256, HIER 3, CNL_PIN 1, CHAIN_STEP 6, LANE_SPECIALIZE 1): bit-exact with a probe showing the tile only at its routed parameters; one-edit mutant inside the module fails. Standalone leaf only: HC parent assembly and family throughput are not qualified by this record.",
            source=dict(commit=full(q["bench_source"]), paths=[t["module_file"], "tools/s81_suhc/hc_gate.py", "tools/s81_suhc/hc_tile_bench.sh"]),
            exactness=dict(
                positive=dict(status="PASS: 0 / 1940 rows x3 runs; %d instance(s), all at routed tuples %s%s" % (
                    t["probe"]["instances"], json.dumps([{k: v for k, v in p.items() if k in ("C", "PIN_STAGE", "CHAIN_STEP", "HALF", "RLY", "RF", "DW", "DEPTH", "FIFO_SLICE")} for p in t["probe"]["params_seen"]]),
                    ("; inert parameters not compared: " + ", ".join(t["probe"].get("inert_differing") or [])) if t["probe"].get("inert_differing") else ""), evidence=[rel]),
                negative=dict(status="PASS (mutant FAILS): %s -> %s; error rows %s" % (t["mutant"]["edit"][0], t["mutant"]["edit"][1], [x["err_rows"] for x in mu]), evidence=[rel])),
            physical=dict(status="CLOSED: " + "; ".join("%s (%s)" % (r["physical_job"], r["reason"]) for r in ok), corners=dict(route="TT", hold="FF"),
                          evidence=["results/closure_loop/%s/verdict.json" % r["physical_job"] for r in ok] + [r["kit"] + "/views" for r in ok]),
            integration=dict(status="production composition instantiates the routed tuple (probe); parent assembly not started", evidence=[rel])))
dst = WT / "results/fleet_viz/element_registry/s81_hc_tiles_20261013.json"
dst.write_text(json.dumps(dict(schema_version=1, records=recs), indent=1) + "\n")
print(len(recs), "records ->", dst)

#!/usr/bin/env python3
"""DIE-HEAD-50 plan event l48c = l48b + HEAD fclk_out sender fix on every exporter type (COORD 08:06 (4)).
Root cause (DIE-HEAD-49 08:44 FINDING): every HEAD exporter carried landing_contract source_clock_port clk (left over from
the DIE-HEAD-9 one-entry COPY, tools/s81_head/head_regional_one_entry.py); the plan default (clock_landing_plan
FORWARD_SOURCE tap) is the nearest tap port.  This restores the default: source_clock_port = nearest tap port (schema.tap_grid, the set gen accepts) to the
fclk_out pin (same metric as the plan), forwarded_clock_only_inputs = true on the type.  Exports whose nearest tap is the
root clk stay unchanged.  Measured on hd_turn_a (l48r, 4_cts): sender rel_min -93.3 -> +115.9 FF, -98.2 -> +149.2 TT.
usage: make_l48c.py SRC_DIR EXPORTERS_JSON OUT_DIR  (EXPORTERS_JSON = [type] -> [[pin, nearest_tap, dist_um]])"""
import json, shutil, sys
from pathlib import Path
src, exf, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
raw = json.loads((src / "source_plan.json").read_text()); ex = json.loads(exf.read_text()); rep = {}
for tn, rows in ex.items():
    lc = raw["partition_types"][tn]["clock"]["landing_contract"]; pins = {p["name"]: p for p in lc["pins"]}; ch = []
    for name, tap, dist in rows:
        p = pins[name]
        if tap == "clk" or p.get("source_clock_port") == tap: continue
        ch.append([name, p.get("source_clock_port"), tap, dist]); p["source_clock_port"] = tap
    if ch:
        lc["forwarded_clock_only_inputs"] = True; rep[tn] = ch
if out.exists(): shutil.rmtree(out)
shutil.copytree(src, out)
(out / "source_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
(out / "l48c_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print(len(rep), "types", sum(len(v) for v in rep.values()), "exports changed")

#!/usr/bin/env python3
"""DIE-KV-13 10-28: KV plan-event delta (die-local, until the shared compose fix): a forwarded clock output's landing
contract source_clock_port must name a clock INPUT of the bound partition RTL.  The KV binder emits ONE `clk` input per
partition (every R4 tap-grid pin clk_t<i> is a physical pin of that same net; bind_s2 RTL: assign fclk_out_ft1_o = clk),
while clock_landing_plan._finish picks the nearest tap-grid NAME (clk_t4...), which clock_landings (ROOT-MERGE-125,
DIE-HEAD-9 FACE (c)) then rejects: "fclk_out_ft1_o contract source_clock_port clk_t4 is not an input port of the type".
This maps every tap-grid name clk_t<i> to `clk` (same net, same RTL as before ROOT-MERGE-125); other names are kept.
    kv_fclk_source_clk.py PLAN_IN PLAN_OUT"""
import json
import re
import sys

p = json.load(open(sys.argv[1]))
n = 0
for tn, t in p["partition_types"].items():
    for q in t.get("clock", {}).get("landing_contract", {}).get("pins", []):
        s = q.get("source_clock_port")
        if s and re.fullmatch(r"clk_t\d+", s):
            q["source_clock_port_tap"] = s
            q["source_clock_port"] = "clk"
            n += 1
json.dump(p, open(sys.argv[2], "w"), indent=1)
print(json.dumps(dict(mapped=n)))

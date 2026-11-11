#!/usr/bin/env python3
"""DIE-KV-98: kv3_hub_Wi clk_t70 (added tap) -> legal site after the CPL-KV-PV hub_Wi delta. usage: tapfix.py PLAN_IN PLAN_OUT
The delta moves host__qkd_hr_cdc_ci +103.68 um; the added tap clk_t70 (859.32, 194.32) then lies inside the moved core's
halo (G0 grid_explicit_sites ValueError, no report). Nearest legal site by search over the plan's own placement_boxes +
TAP_CLEAR_UM spacing: (859.32, 259.84), 65.5 um above. Clock-tap site only; the netlist is untouched (EQ unchanged)."""
import json, sys
p = json.load(open(sys.argv[1]))
for t in p["partition_types"]["kv3_hub_Wi"]["clock"]["added_taps"]:
    if t["name"] == "clk_t70":
        assert t["xy"] == [859.32, 194.32], t["xy"]; t["xy"] = [859.32, 259.84]
json.dump(p, open(sys.argv[2], "w"), indent=1); open(sys.argv[2], "a").write("\n")

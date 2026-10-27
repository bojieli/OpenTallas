#!/bin/bash
set -euo pipefail
cd /w
python3 r17_delta_inputs.py inputs/candidate_oneqc0733.json inputs/r2_plan_orig.json inputs/die_tree_plan.json inputs/d51 51.84
SA="--r2 inputs/d51/r2_plan_d43.json --stage inputs/stage_table.json --lanes vss --islands type --feed periodic --island-edge-sym --row-at 10471.68=10445.76,5227.2=5218.56 --lift-lane deepest --row-slots holder --centre-channel 51.84 --centre-split 34.56 --chan-hc 3 --chan-lanes 1,5,2,4"
O=out/guard51
mkdir -p "$O"
python3 r17_phys_sites.py $SA --out "$O/sites" > "$O/sites.log" 2>&1
python3 r16_seamfix.py inputs/d51/plan_d43.json "$O/sites/r15_top_sites.json" "$O/spec_seamfix.json" > "$O/seamfix.log" 2>&1
python3 -c 'import json; p="out/guard51/";s=json.load(open(p+"spec_seamfix.json"));s["exact_reserve"]=True;s["channel_hosts"]=True;json.dump(s,open(p+"spec_exact.json","w"))'
python3 die_plan/die_clock_mesh.py build inputs/d51/plan_d43.json --explicit-cells "$O/spec_exact.json" --ndr 16w --out "$O/dry_exact" > "$O/dry_exact.log" 2>&1
printf 'DRY_GUARD51_DONE\n'

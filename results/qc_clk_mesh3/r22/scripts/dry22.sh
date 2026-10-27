#!/bin/sh
# dry21.sh NAME LIFT : d43b dry exact build with --chan-lane0-um LIFT (R22 lane-1 move)
N=$1; L=$2; O=out/$N; mkdir -p $O
SA="--r2 inputs/d43/r2_plan_d43.json --stage inputs/stage_table.json --lanes vss --islands type --feed periodic --island-edge-sym --row-at 10471.68=10445.76,5227.2=5218.56 --lift-lane deepest --row-slots holder --centre-channel 43.2 --centre-split 30.24 $L"
python3 r17_phys_sites.py $SA --out $O/sites > $O/sites.log 2>&1
python3 r16_seamfix.py inputs/d43/plan_d43.json $O/sites/r15_top_sites.json $O/spec_seamfix.json > $O/seamfix.log 2>&1
python3 -c "import json;s=json.load(open(\"$O/spec_seamfix.json\"));s[\"exact_reserve\"]=True;s[\"channel_hosts\"]=True;json.dump(s,open(\"$O/spec_exact.json\",\"w\"))"
python3 die_plan/die_clock_mesh.py build inputs/d43/plan_d43.json --explicit-cells $O/spec_exact.json --ndr 16w --out $O/dry_exact > $O/dry_exact.log 2>&1
echo DRY_DONE $N $L rc $?

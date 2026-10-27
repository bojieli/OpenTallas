#!/bin/sh
# HOLD-REPAIR-2 10-26: QC canary coll_ftc (coll_f4) under clock.io_hold plan_demand. Plan = main QC die_plan.json (@74517416c8)
# + clock.io_hold plan_demand + clock.hold_demand = results/hold_repair_1026/<scen>/plan_hold_demand.json (plan copy must sit in
# physical/die_plan/qwen_compute/ so plan-relative cores/ pin tables resolve). Kits then run via ot-run (epyc1):
#   ot-run --mem 32 --threads 8 --dir $D -- bash $D/gen_<scen>/run_kit.sh $D/gen_<scen>/coll_ftc route 32 8
set -e; W=$(cd "$(dirname "$0")/../.." && pwd); D=${D:-/srv/opentallas-scratch2/claude/hold-repair2-1026}
for s in mesh20_flat region_flat; do
python3 -I - $s $W <<PY
import json,sys
s,W=sys.argv[1],sys.argv[2]
P=json.load(open(f"{W}/physical/die_plan/qwen_compute/die_plan.json"))
P["clock"]["io_hold"]="plan_demand"; P["clock"]["hold_demand"]=json.load(open(f"{W}/results/hold_repair_1026/{s}/plan_hold_demand.json"))
json.dump(P,open(f"{W}/physical/die_plan/qwen_compute/hr2_{s}.json","w"),indent=1)
PY
python3 -I $W/tools/die_plan/gen.py phys $W/physical/die_plan/qwen_compute/hr2_$s.json --out $D/gen_$s --types coll_ftc --rtl-root $W --hold-ff-margin 5
done

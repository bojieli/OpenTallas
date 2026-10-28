#!/bin/bash
# LOCALITY-SCORE-2: v2 (tree proposer + spine/fish/dme feeds, current-ring and count-aligned modes) for all 5 dies.
# Run from the repo root on a fleet host.  VSCALE scales every v (calibration sensitivity: measured LAND-HEAD-3 rib
# hops 250-290 ps per ~708 um = 353-410 ps/mm vs the 340 ps/mm trunk fit -> VSCALE=1.15 is the pessimistic reading).
set -e
VS=${VSCALE:-1.0}
O=${OUT:-results/locality_1027/v2}
I=results/locality_1027/inputs
v() { python3 -c "print(round($1*$VS,1))"; }
CAL=$(cat results/locality_1027/v2_calib.txt)
L="python3 tools/die_plan/locality.py v2 --span-mm 3.5 --tree 2:3.5,3.5:5,1.5:3 --out $O"
HBM=${HBM_PLAN:-/srv/opentallas-scratch2/claude/hbm-streets2-1027/c18/die_plan.json}
$L --calib "$CAL" --die head --v-ps-mm $(v 340) --plan physical/die_plan/s81_head/die_plan.json     --map landpart=part &
$L --calib "$CAL" --die qc   --v-ps-mm $(v 199) --plan physical/die_plan/qwen_compute/die_plan.json --map slices=$I/qc_slices_regions.json &
$L --calib "$CAL" --die kv   --v-ps-mm $(v 321) --plan physical/die_plan/qwen_kvsys/die_plan.json   --map land128=$I/kv_land_regions_128.json &
$L --calib "$CAL" --die hbm  --v-ps-mm $(v 340) --plan $HBM --map c18quad=$I/hbm_c18_quad_regions.json &
$L --calib "$CAL" --die s81  --v-ps-mm $(v 340) --plan physical/die_plan/s81/die_plan.json          --map land179=$I/s81_regions_179.json &
wait

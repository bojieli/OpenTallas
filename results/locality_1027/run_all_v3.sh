#!/bin/bash
# LOCALITY-SCORE-3: v3 = the ADOPTED count-aligned ring (MESO-COUNT-1 count_align_plan.py, joint TT+FF, DEPTH 4/8)
# for all 5 dies at MEASURED clock wire speeds.  Run from the repo root on a fleet host.  VSCALE = sensitivity
# (LAND-HEAD-3 measured rib hops 353-410 ps/mm -> 1.15 is the pessimistic reading).
set -e
VS=${VSCALE:-1.0}
O=${OUT:-results/locality_1027/v3}
I=results/locality_1027/inputs
v() { python3 -c "print(round($1*$VS,1))"; }
L="python3 tools/die_plan/locality.py v3 --span-mm 3.5 --tree 2:3.5,3.5:5,1.5:3 --out $O"
HBM=${HBM_PLAN:-/srv/opentallas-scratch2/claude/hbm-streets2-1027/c18/die_plan.json}
$L --die head --v-ps-mm $(v 349) --v-note "HEAD measured 335-349 ps/mm (LAND-HEAD-3), upper value x$VS" --plan physical/die_plan/s81_head/die_plan.json --map landpart=part &
$L --die qc   --v-ps-mm $(v 199) --v-note "QC measured 199 ps/mm x$VS" --plan physical/die_plan/qwen_compute/die_plan.json --map slices=$I/qc_slices_regions.json &
$L --die kv   --v-ps-mm $(v 321) --v-note "KV measured 321 ps/mm x$VS" --plan physical/die_plan/qwen_kvsys/die_plan.json --map land128=$I/kv_land_regions_128.json &
$L --die hbm  --v-ps-mm $(v 349) --v-note "HBM not measured: conservative = highest measured die (HEAD 349) x$VS" --plan $HBM --map c18quad=$I/hbm_c18_quad_regions.json &
$L --die s81  --v-ps-mm $(v 335) --v-note "S81 measured ~335 ps/mm x$VS" --plan physical/die_plan/s81/die_plan.json --map land179=$I/s81_regions_179.json --map dies81=$I/s81_dies81_regions.json &
wait

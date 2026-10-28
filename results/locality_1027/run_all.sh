#!/bin/bash
# LOCALITY-SCORE-1: baseline + proposed region maps for all 5 dies (run from the repo root on a fleet host).
# v = measured TT clock trunk delay per mm: HEAD ~340 (LAND-HEAD-2: 6.1 ns / ~17 mm), KV 321 (LAND-KV-1: 130 ps per
# 405 um BUFx24 stage), QC 199 (QC-SLICECLK-2 fit); S81 340 (same family/stack as HEAD, ASSUMED), HBM 340 (LAND-HBM-1 basis).
set -e
O=results/locality_1027
I=$O/inputs
SPAN=${SPAN:-3.5}
L="python3 tools/die_plan/locality.py both --span-mm $SPAN --out $O"
$L --die s81  --v-ps-mm 340 --plan physical/die_plan/s81/die_plan.json          --regions $I/s81_regions_179.json  --tag land179
$L --die head --v-ps-mm 340 --plan physical/die_plan/s81_head/die_plan.json     --regions part                     --tag landpart
$L --die qc   --v-ps-mm 199 --plan physical/die_plan/qwen_compute/die_plan.json --regions $I/qc_slices_regions.json --tag slices
$L --die kv   --v-ps-mm 321 --plan physical/die_plan/qwen_kvsys/die_plan.json   --regions $I/kv_land_regions_128.json --tag land128
$L --die hbm  --v-ps-mm 340 --plan ${HBM_PLAN:-/srv/opentallas-scratch2/claude/hbm-streets2-1027/c18/die_plan.json} --regions $I/hbm_c18_quad_regions.json --tag c18quad

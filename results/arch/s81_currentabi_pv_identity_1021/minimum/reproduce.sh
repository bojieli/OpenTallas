#!/bin/bash
set -euo pipefail
source tools/s81_dv/svc_rs/rs_files.sh
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for CASE in lp entry nonentry; do
case "$CASE" in
 lp) TOP=dsdv_svc_attw_n1_f_lp; PARAMS=(-GSRAM_MACRO=1 -GROOT=1 -GPMEM=1 -GTLX=6 -GROLE_EXT=1);;
 entry) TOP=dsdv_svc_rs_c_group72; PARAMS=(-GENTRY=1 -GSRAM_MACRO=1 -GPMEM=1);;
 nonentry) TOP=dsdv_svc_rs_c_group72; PARAMS=(-GENTRY=0 -GSRAM_MACRO=1 -GPMEM=1);;
esac
"$V" --lint-only --top-module "$TOP" -GPV_IDENTITY=1 "${PARAMS[@]}" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
 -I"$D" -DOT_SVC_GROUP72 -DOT_SVC_LAND_SRAM -DOT_SVC_ATT_SRAM -DOT_ATTN_HGRP_HARD -DOT_ATTN_HGRP8 -DOT_HGRP8_MOD=ot_s81svc8_hgrp_s81_bounded "${RS_DEF[@]}" "${RS_SRC[@]}" "${RS_LIB[@]}" \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 rtl/lib/ot_reset_sync.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_n32.sv rtl/common/landed_parent/ot_pl_land_field_copies.sv rtl/common/landed_parent/ot_pl_land_reset_forest.sv \
 "$D/dsdv_svc_rs_glue.sv" "$D/attw/lp/dsdv_svc_attw_n1_f_lp.sv" tools/s81_dv/svc_rs/attn1/ot_s81svc8_hgrp_s81_bounded_bb.v \
 "$D/group72/dsdv_svc_face72.sv" "$D/group72/dsdv_svc_rs_c_group72.sv" "$D/group72/dsdv_svc_group72.sv" > ../out/minimum_${CASE}.log 2>&1
echo "MINIMUM_HIERARCHY_PASS $CASE PV_IDENTITY1 productionNTP1/SRAM1/PMEM1/TEXT1 actualLP/currentcore, hard arithmeticinterfaces; no numerical/physical/token claim"
done

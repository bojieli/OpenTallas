#!/bin/bash
# HBMc/TILES 10-22: issue-restructure equivalence (4 seeds x 2M edges) + mutant (load issue restricted to bank 0) must FAIL.
set -euo pipefail
OUT=$(realpath -m "${1:?outputdir}");mkdir -p "$OUT"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
D=rtl/hbm_accel/loader/service_native/split
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
"$V" --binary --timing -j 4 -Wno-fatal --x-initial 0 ${DEFS:-} --top-module tb_eq $D/tb_hbm_dma_load_issue_equiv.sv $D/ot_hbm_svc_vmdel_lane_load_static.sv $D/tb_hbm_dma_load_df174_reference.sv $M --Mdir "$OUT/obj" > "$OUT/build.log" 2>&1
for s in 1 7 13 21; do "$OUT/obj/Vtb_eq" +verilator+seed+$s | grep -E "EQ_DONE|DMA_EQ" | tee -a "$OUT/eq.log"; done
[ "$(grep -c 'DMA_EQ PASS' "$OUT/eq.log")" = 4 ]
sed 's/ wire issue=raw_issue||load_cmd_ok;/ wire issue=raw_issue||(load_cmd_ok\&\&load_cmd[0]==0);/' $D/ot_hbm_svc_vmdel_lane_load_static.sv > "$OUT/mut.sv"
grep -q 'load_cmd\[0\]==0);' "$OUT/mut.sv"
"$V" --binary --timing -j 4 -Wno-fatal --x-initial 0 ${DEFS:-} --top-module tb_eq $D/tb_hbm_dma_load_issue_equiv.sv "$OUT/mut.sv" $D/tb_hbm_dma_load_df174_reference.sv $M --Mdir "$OUT/objm" > "$OUT/buildm.log" 2>&1
if "$OUT/objm/Vtb_eq" +verilator+seed+1 > "$OUT/mut.log" 2>&1; then echo DMA_ISSUE_EQUIV_MUTANT_ESCAPED; exit 3; fi
grep -q CE_MISMATCH "$OUT/mut.log"
echo DMA_ISSUE_EQUIV_ALL_PASS

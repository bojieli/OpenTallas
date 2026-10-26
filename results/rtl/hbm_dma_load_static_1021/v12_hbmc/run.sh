#!/bin/bash
set -euo pipefail
LANE=/home/ubuntu/scratch/hbmc-tiles/dma/v12
cd "$LANE"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
sha256sum *.sv *.v > source_hashes.txt
for mut in 0 1; do
 "$V" --binary --timing -j 4 -Wno-fatal +define+MUT=$mut --top-module tb_hbm_dma_load_static ot_hbm_svc_vmdel_lane_load_static.sv tb_hbm_dma_load_static.sv ot_sram_1r1w_128x256_m1_r2c2.v --Mdir "$LANE/obj_$mut" > "build_$mut.log" 2>&1
 set +e
 "$LANE/obj_$mut/Vtb_hbm_dma_load_static" > "bench_$mut.log" 2>&1
 rc=$?
 set -e
 cat "bench_$mut.log"
 if [ "$mut" = 0 ];then [ "$rc" = 0 ] && grep -q 'DMA_LOAD_STATIC PASS' bench_0.log;else [ "$rc" != 0 ] && grep -q 'DMA_LOAD_STATIC FAIL' bench_1.log;fi
done
"$V" --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_svc_vmdel_lane_n_lockstep tb_hbm_dma_load_raw_lockstep.sv ot_hbm_svc_vmdel_lane_load_static.sv ot_hbm_svc_static_vm_delivery_split.sv ot_sram_1r1w_128x256_m1_r2c2.v --Mdir "$LANE/obj_raw" > build_raw.log 2>&1
"$LANE/obj_raw/Vtb_hbm_svc_vmdel_lane_n_lockstep" > bench_raw.log 2>&1
cat bench_raw.log
grep -q 'VMDEL_N_LOCKSTEP PASS MUT=0' bench_raw.log
echo DMA_LOAD_V11_ALL_PASS

"$V" --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_dma_load_actual_qnorm384 ot_hbm_svc_vmdel_lane_load_static.sv tb_hbm_dma_load_actual_qnorm384.sv ot_sram_1r1w_128x256_m1_r2c2.v --Mdir "$LANE/obj_actual" > build_actual.log 2>&1
"$LANE/obj_actual/Vtb_hbm_dma_load_actual_qnorm384" > bench_actual.log 2>&1
cat bench_actual.log
grep -q 'ACTUAL_QNORM384 PASS' bench_actual.log
echo DMA_LOAD_V11_FULL_PASS

"$V" --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_dma_load_bank1 ot_hbm_svc_vmdel_lane_load_static.sv tb_hbm_dma_load_bank1.sv ot_sram_1r1w_128x256_m1_r2c2.v --Mdir "$LANE/obj_bank1" >build_bank1.log 2>&1
"$LANE/obj_bank1/Vtb_hbm_dma_load_bank1" >bench_bank1.log 2>&1
cat bench_bank1.log
grep -q 'DMA_LOAD_BANK1 PASS' bench_bank1.log
echo DMA_LOAD_V11_BANKS_FULL_PASS

"$V" --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_dma_load_overlap ot_hbm_svc_vmdel_lane_load_static.sv tb_hbm_dma_load_overlap.sv ot_sram_1r1w_128x256_m1_r2c2.v --Mdir "$LANE/obj_overlap" >build_overlap.log 2>&1
"$LANE/obj_overlap/Vtb_hbm_dma_load_overlap" >bench_overlap.log 2>&1
cat bench_overlap.log
grep -q 'DMA_LOAD_OVERLAP PASS' bench_overlap.log
echo DMA_LOAD_V11_ALL_CHECKS_PASS

"$V" --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_dma_load_fill_overlap ot_hbm_svc_vmdel_lane_load_static.sv tb_hbm_dma_load_fb912_reference.sv tb_hbm_dma_load_fill_overlap.sv ot_sram_1r1w_128x256_m1_r2c2.v --Mdir "$LANE/obj_fill_overlap" >build_fill_overlap.log 2>&1
"$LANE/obj_fill_overlap/Vtb_hbm_dma_load_fill_overlap" >bench_fill_overlap.log 2>&1
cat bench_fill_overlap.log
grep -q 'DMA_LOAD_FILL_OVERLAP PASS' bench_fill_overlap.log
echo DMA_LOAD_V11_HAZARD_ALL_PASS

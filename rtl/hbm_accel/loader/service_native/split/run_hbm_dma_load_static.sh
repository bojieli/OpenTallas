#!/bin/bash
set -euo pipefail
OUT=$(realpath -m "${1:?outputdir}");MODE=${2:-all};mkdir -p "$OUT"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
D=rtl/hbm_accel/loader/service_native/split
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
mut=0;[ "$MODE" = mut ] && mut=1
"$V" --binary --timing -j ${VL_JOBS:-4} -Wno-fatal ${DEFS:-} +define+MUT=$mut --top-module tb_hbm_dma_load_static "$D/ot_hbm_svc_vmdel_lane_load_static.sv" "$D/tb_hbm_dma_load_static.sv" "$M" --Mdir "$OUT/obj_load" > "$OUT/build.log" 2>&1
set +e
"$OUT/obj_load/Vtb_hbm_dma_load_static" > "$OUT/bench.log" 2>&1
rc=$?
set -e
cat "$OUT/bench.log"
[ "$MODE" = mut ] && exit "$rc"
[ "$rc" = 0 ]
"$V" --binary --timing -j ${VL_JOBS:-4} -Wno-fatal ${DEFS:-} --top-module tb_hbm_svc_vmdel_lane_n_lockstep "$D/tb_hbm_dma_load_raw_lockstep.sv" "$D/ot_hbm_svc_vmdel_lane_load_static.sv" "$D/ot_hbm_svc_static_vm_delivery_split.sv" "$M" --Mdir "$OUT/obj_raw" > "$OUT/raw.build.log" 2>&1
"$OUT/obj_raw/Vtb_hbm_svc_vmdel_lane_n_lockstep" > "$OUT/raw.log" 2>&1
cat "$OUT/raw.log"
grep -q 'VMDEL_N_LOCKSTEP PASS MUT=0' "$OUT/raw.log"
echo DMA_LOAD_STATIC_ALL_PASS

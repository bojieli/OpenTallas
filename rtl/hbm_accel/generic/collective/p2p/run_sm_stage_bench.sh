#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1");shift;mkdir -p "$OUT";cd "$ROOT"
P=rtl/hbm_accel/generic/collective/p2p
verilator --binary --timing -O2 -j "${JOBS:-4}" -Wno-fatal -Wno-WIDTH --top-module tb_hgi_coll_sm_stage --Mdir "$OUT/obj" "$@" "$P/tb_hgi_coll_sm_stage.sv" "$P/ot_hgi_coll_sm_stage.sv" physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v > "$OUT/build.log" 2>&1 || { tail -35 "$OUT/build.log";exit 2; }
"$OUT/obj/Vtb_hgi_coll_sm_stage" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
grep -q '^SM_STAGE PASS ' "$OUT/run.log"
for scenario in 1 2 3 4 5 6;do
 "$OUT/obj/Vtb_hgi_coll_sm_stage" +fault="$scenario" > "$OUT/fault-$scenario.log" 2>&1
 grep -q '^SM_STAGE FAULT PASS ' "$OUT/fault-$scenario.log"
 cat "$OUT/fault-$scenario.log"
done

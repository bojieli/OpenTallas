#!/bin/bash
set -euo pipefail
W=$(cd "$(dirname "$0")/../../../.." && pwd)
FBROOT=$(cd "$(dirname "$0")" && pwd)
O=$(realpath -m "$1")
cd "$W" 
source tools/s81_dv/svc_rs/rs_files.sh
mkdir -p "$O"
git rev-parse HEAD > "$O/source_commit.txt"
sha256sum "${RS_SRC[@]}" "$FBROOT/tb_svc_feedback.sv" > "$O/sources.sha256"
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --binary --timing -Wno-fatal -Wno-WIDTH --top-module tb_svc_feedback --unroll-count 4 -fno-dfg -j 8 -CFLAGS -O0 -Mdir "$O/obj" \
 -Irtl/dsrom_sys/s81_dv/svc_rs "${RS_SRC[@]}" "${RS_LIB[@]}" \
 rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_mem_ar.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_160x256_m1_r0c0/ot_sram_1r1w_160x256_m1_r0c0.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.v \
 "$FBROOT/tb_svc_feedback.sv" > "$O/build.log" 2>&1
for nv in 2 8 40; do
 "$O/obj/Vtb_svc_feedback" +nv=$nv | tee "$O/run_nv$nv.log"
 grep -q 'FEEDBACK PASS' "$O/run_nv$nv.log"
done
"$O/obj/Vtb_svc_feedback" +nv=2 +early=1 | tee "$O/run_early.log"
grep -q 'FEEDBACK NEGATIVE_CAUGHT' "$O/run_early.log" 

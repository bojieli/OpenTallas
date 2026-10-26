#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
RUN=${1:?fresh run dir}
mkdir -p "$RUN"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing -j 2 --build-jobs 1 -Wno-fatal --top-module tb_s81_vp_norepair -Mdir "$RUN/obj" "$ROOT/results/token_pass/s81_vp_norepair_2148/tb.sv" "$ROOT/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v" "$ROOT/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r0c0/ot_sram_1r1w_512x128_m4_r0c0.v" > "$RUN/build.log" 2>&1
"$RUN/obj/Vtb_s81_vp_norepair" > "$RUN/base.log" 2>&1
set +e
"$RUN/obj/Vtb_s81_vp_norepair" +MUT > "$RUN/mutant.log" 2>&1
rc=$?
set -e
if [ "$rc" = 0 ]; then echo 'MUTANT ESCAPED';exit 1;fi
grep -q VP_NOREPAIR_PASS "$RUN/base.log"
grep -q VP_NOREPAIR.mismatch "$RUN/mutant.log"
echo 'VP_NOREPAIR_GATE_PASS baseline exact / address mutant CAUGHT'

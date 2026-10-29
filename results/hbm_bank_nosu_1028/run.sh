#!/usr/bin/env bash
set -euo pipefail
ROOT=${1:?source}; OUT=${2:?out}; D=rtl/hbm_accel/generic/vm/static/faces_q0
mkdir -p "$OUT"
cd "$ROOT"
iverilog -g2012 -s tb_bank_nosu -o "$OUT/bench.vvp" \
 results/hbm_bank_nosu_1028/tb_bank_nosu.sv \
 "$D/hfd_vms_bank_native_q0_faces.sv" "$D/hfd_vms_bank_native_q0_faces_nosu.sv" \
 "$D/ot_vms_bank_q0_faces_core.sv" "$D/ot_vms_bank_q0_faces_body.sv" \
 rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$OUT/build.log" 2>&1
for mode in positive FORBID_READ FORBID_WRITE MUT_RESPONSE;do
 rc=0;args=(); [[ $mode = positive ]] || args=("+$mode")
 vvp "$OUT/bench.vvp" "${args[@]}" > "$OUT/$mode.log" 2>&1 || rc=$?
 if [[ $mode = MUT_RESPONSE ]];then
  [[ $rc != 0 ]] && grep -q 'group1 .* mismatch' "$OUT/$mode.log"
 else
  [[ $rc = 0 ]] && grep -q 'NOSU_LOCKSTEP PASS' "$OUT/$mode.log"
  [[ $mode = positive ]] || grep -q 'NOSU_FORBIDDEN_GRANT CAUGHT' "$OUT/$mode.log"
 fi
 tail -n 2 "$OUT/$mode.log"
done

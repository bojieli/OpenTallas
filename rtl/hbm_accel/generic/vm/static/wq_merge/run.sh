#!/usr/bin/env bash
# usage: run.sh OUTDIR [LEAF_MUT] [DONE_LAT]
set -euo pipefail
cd "$(dirname "$0")/../../../../../.."
O=${1:?out dir}; M=${2:-0}; L=${3:-4}
mkdir -p "$O"
S=rtl/hbm_accel/generic/vm/static
src=($S/wq_merge/hfd_vms_wq2_merge.sv $S/wq_merge/tb_vms_wq2_merge.sv
     $S/faces_q2/hfd_vms_bank_native_q2_faces.sv $S/faces_q2/ot_vms_bank_q2_faces_core.sv $S/faces_q2/ot_vms_bank_q2_faces_body.sv
     $S/faces_q0/hfd_vms_bank_native_q0_faces.sv $S/faces_q0/ot_vms_bank_q0_faces_core.sv $S/faces_q0/ot_vms_bank_q0_faces_body.sv
     $S/ot_vms_ce_counter_pipe.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
iverilog -g2012 -s tb_vms_wq2_merge -Ptb_vms_wq2_merge.LEAF_MUT=$M -Ptb_vms_wq2_merge.DONE_LAT=$L -o "$O/tb.vvp" "${src[@]}" > "$O/build.log" 2>&1 || { cat "$O/build.log"; echo "WQ2_MERGE BENCH FAIL: build"; exit 1; }
rc=0; vvp "$O/tb.vvp" > "$O/sim.log" 2>&1 || rc=$?
cat "$O/sim.log" | tail -12
[[ $rc == 0 ]] && grep -q "WQ2_MERGE BENCH PASS" "$O/sim.log" || { echo "WQ2_MERGE BENCH FAIL rc=$rc"; exit 1; }

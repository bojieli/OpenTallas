#!/usr/bin/env bash
# HBM-P4-QUANT 10-23: per-quadrant wq2 merge equivalence. usage: run_q.sh OUTDIR SID BID [LEAF_MUT] [SIDMUT]
set -euo pipefail
cd "$(dirname "$0")/../../../../../.."
O=${1:?out dir}; SID=${2:?sid}; BID=${3:?bid}; M=${4:-0}; SM=${5:-0}
mkdir -p "$O"
S=rtl/hbm_accel/generic/vm/static
src=($S/wq_merge/hfd_vms_wq2_merge.sv $S/wq_merge/tb_vms_wq2_merge_q.sv
     $S/faces_q2/hfd_vms_bank_native_q2_faces.sv $S/faces_q2/ot_vms_bank_q2_faces_core.sv $S/faces_q2/ot_vms_bank_q2_faces_body.sv
     $S/faces_q0/hfd_vms_bank_native_q0_faces.sv $S/faces_q0/ot_vms_bank_q0_faces_core.sv $S/faces_q0/ot_vms_bank_q0_faces_body.sv
     $S/ot_vms_ce_counter_pipe.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
iverilog -g2012 -s tb_vms_wq2_merge_q -Ptb_vms_wq2_merge_q.LEAF_MUT=$M -Ptb_vms_wq2_merge_q.SID=$SID -Ptb_vms_wq2_merge_q.BID=$BID \
  -Ptb_vms_wq2_merge_q.SIDMUT=$SM -o "$O/tb.vvp" "${src[@]}" > "$O/build.log" 2>&1 || { cat "$O/build.log"; echo "WQ2_MERGE BENCH FAIL: build"; exit 1; }
rc=0; vvp "$O/tb.vvp" > "$O/sim.log" 2>&1 || rc=$?
sha256sum "${src[@]}" > "$O/sources.sha256"
tail -3 "$O/sim.log"
[[ $rc == 0 ]] && grep -q "WQ2_MERGE BENCH PASS" "$O/sim.log" || { echo "WQ2_MERGE BENCH FAIL rc=$rc sid=$SID bid=$BID mut=$M sidmut=$SM"; exit 1; }

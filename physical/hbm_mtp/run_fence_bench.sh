#!/bin/bash
# mtp-hbm 2026-10-08: ot_gpu_rf_visibility_fence_p vs the original fence (physical/hbm_mtp/bench/tb_fence_p.sv).
#   run_fence_bench.sh <out dir> <MUT 0|1> [seeds...]   prints FENCE_P PASS/FAIL per seed; exit 0 iff every seed PASSes
set -u
O=$1; M=$2; shift 2; mkdir -p $O; cd "$(dirname "$0")/../.."
rc=0
for s in ${@:-7 3 11 29}; do
  iverilog -g2012 -Ptb_fence_p.MUT=$M -Ptb_fence_p.SEED=$s -o $O/fp_${M}_${s}.vvp -s tb_fence_p physical/hbm_mtp/bench/tb_fence_p.sv \
    physical/hbm_mtp/rtl/ot_gpu_rf_visibility_fence_p.sv physical/hbm_mtp/rtl/ot_hfd_mtp_skid.sv rtl/gpu/ot_gpu_rf_visibility_fence.sv || exit 2
  L=$(vvp -n $O/fp_${M}_${s}.vvp | grep -m1 '^FENCE_P'); echo "seed $s: $L"
  case "$L" in "FENCE_P PASS"*) ;; *) rc=1;; esac
done
exit $rc

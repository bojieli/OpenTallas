#!/bin/bash
set -eu
out=$1; mutant=$2; shift 2
mkdir -p "$out"
cd "$(dirname "$0")/../.."
rc=0
for seed in "${@:-7}"; do
  iverilog -g2012 -Ptb_fence_pinret.MUT="$mutant" -Ptb_fence_pinret.SEED="$seed" -o "$out/pinret_${mutant}_${seed}.vvp" -s tb_fence_pinret \
   physical/hbm_mtp/bench/tb_fence_pinret.sv physical/hbm_mtp/rtl/ot_gpu_rf_visibility_fence_p2.sv \
   physical/hbm_mtp/rtl/ot_fence_pin_return.sv rtl/common/ot_sc_pfifo.sv rtl/gpu/ot_gpu_rf_visibility_fence.sv
  sim_rc=0
  vvp -n "$out/pinret_${mutant}_${seed}.vvp" > "$out/pinret_${mutant}_${seed}.log" 2>&1 || sim_rc=$?
  cat "$out/pinret_${mutant}_${seed}.log"
  if [ "$sim_rc" != 0 ]; then rc=1; fi
  if ! rg -q '^FENCE_P PASS' "$out/pinret_${mutant}_${seed}.log"; then rc=1; fi
 done
exit "$rc"

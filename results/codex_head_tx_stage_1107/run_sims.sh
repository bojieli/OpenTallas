#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")" || exit 90
for mut in 0 1 2 3 4 5 6; do
  docker run --rm --memory=8g --cpus=4 -v "$PWD:/proof" -w /proof verilator/verilator:v5.032 \
    --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb -GCHMUT=$mut \
    --Mdir obj_$mut -o tbx -Irtl tb.sv rtl/ot_s81_kp4_enc_la.sv rtl/enc_ref.sv rtl/ot_s81_kp4_common.sv > build_$mut.log 2>&1
  rc=$?; echo "BUILD $mut $rc"; test "$rc" = 0 || exit "$rc"
  any_diff=0
  if test "$mut" = 0 || test "$mut" = 4; then reset_cases="$(seq 3600 3609)"; else reset_cases=3600; fi
  for r in $reset_cases; do
    stdbuf -oL -eL ./obj_$mut/tbx +RESET_AT=$r > run_${mut}_reset_${r}.log 2>&1
    rc=$?; echo "RUN $mut RESET $r EXIT $rc"; grep TX_CH_STAGE run_${mut}_reset_${r}.log
    if test "$mut" = 0; then test "$rc" = 0 || exit "$rc";
    elif test "$rc" != 0; then
      grep -q STAGE_DIFF run_${mut}_reset_${r}.log || exit 93
      any_diff=1
    fi
  done
  if test "$mut" != 0; then
    if test "$any_diff" = 0; then
      if test "$mut" = 4; then echo "MUTANT4_HEADER_DELAY_BYPASS_EQUIVALENT_ON_ALL_10_RESET_PHASES";
      else echo "MUTANT $mut SURVIVED"; exit 92; fi
    else echo "MUTANT $mut CAUGHT"; fi
  fi
done
echo "TX_CH_STAGE_PHASE_PROOF COMPLETE; READ MUTANT4 CLASSIFICATION"

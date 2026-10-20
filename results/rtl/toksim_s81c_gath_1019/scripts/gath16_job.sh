#!/usr/bin/env bash
# TOKSIM-S81C/GATH: the remaining 28 owner views (die,stack) of the L2 / L20 real-fixture gather cases on the SAME exe
# (obj Vtb_toksim_gath built on ot-epyc7 against the release svc_rs protect-libs; sha256 in out/exe.sha256)
set -uo pipefail
sha256sum Vtb_toksim_gath > out/exe.sha256
for C in $(cat cases/list.txt); do C=${C%%:*}
  ( ./Vtb_toksim_gath +dir=$PWD/cases/$C +seed=1 +static_io=1 +sel_gap=0 > out/run_${C}_g0.log 2>&1
    echo "$C g0: $(grep -h '^GATH_T ' out/run_${C}_g0.log) | $(grep -h '^SVCRS ' out/run_${C}_g0.log | grep -o 'sc_errors=[0-9]*.*verdict=[A-Z]*')" ) &
done
wait; echo "HOST $(hostname) done $(date)"

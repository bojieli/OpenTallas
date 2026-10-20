#!/bin/bash
set -euo pipefail
ROOT=$(pwd)
mkdir -p proofs
for width in 328 257; do
  for mutant in BASE DATA RESET CLOCK; do
    flags=()
    if [[ $mutant != BASE ]]; then flags+=(-DOT_HBM_PARENT_STATION_MUT_$mutant); fi
    iverilog -g2012 -s tb_hbm_parent_station32 -Ptb_hbm_parent_station32.W=$width "${flags[@]}" -o proofs/sim_${width}_${mutant} src/ot_hbm_parent_station32.sv src/tb_hbm_parent_station32.sv
    rc=0
    vvp proofs/sim_${width}_${mutant} > proofs/rtl_${width}_${mutant}.log 2>&1 || rc=$?
    if [[ $mutant == BASE && $rc != 0 ]]; then cat proofs/rtl_${width}_${mutant}.log; exit 1; fi
    if [[ $mutant != BASE && $rc == 0 ]]; then echo "MUTANT SURVIVED $width $mutant"; exit 1; fi
    cat proofs/rtl_${width}_${mutant}.log
  done
done
echo 'ALL_DIRECT_RTL_COUPONS_PASS two widths + six rejected mutants'

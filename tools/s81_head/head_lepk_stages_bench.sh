#!/bin/bash
# DIE-HEAD-84 11-07 hd_lep0N leg-stage bench. Run in a dir holding rtl/ (the kit rtl), models/ (SRAM sim models), the new
# ot_s81hd_lep0N_core.sv + ot_s81hd_lep_nr.sv and rtl/dsrom_sys/s81_head/test/tb_head_lepk_stages.sv; heavy: through ot-run.
# DIE-HEAD-84 hd_lep0N leg-stage bench: build + run the transaction bench for the planned counts, a stress count,
# a zero-count control and three mutants (each must FAIL).  Usage: run_bench.sh BENCH_DIR
set -uo pipefail
B=$1; cd "$B"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
SRC="$(ls rtl/*.sv | grep -v -e ot_s81hd_lep0N.sv -e ot_s81hd_lep0N_core.sv -e ot_s81hd_lep_nr.sv) ot_s81hd_lep0N_core.sv ot_s81hd_lep_nr.sv $(ls models/*.v) tb_head_lepk_stages.sv"
run() { # name expect defines...
  local n=$1 exp=$2; shift 2
  mkdir -p "case_$n"
  verilator --binary --timing -j 16 -Wno-fatal -Wno-lint -Wno-style --top-module tb_head_lepk_stages --Mdir "case_$n/obj" \
    -DSYNTHESIS -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF "$@" $SRC > "case_$n/build.log" 2>&1 || { echo "CASE $n BUILD_FAIL"; tail -5 "case_$n/build.log"; return; }
  timeout 3000 "case_$n/obj/Vtb_head_lepk_stages" > "case_$n/run.log" 2>&1
  local got=FAIL; grep -q "LEPK_STAGES PASS" "case_$n/run.log" && got=PASS
  local verdict=OK; [ "$got" = "$exp" ] || verdict=UNEXPECTED
  echo "CASE $n expect=$exp got=$got $verdict"; grep "^LEPK_STAGES\|^FAIL" "case_$n/run.log" | head -6
}
P="-DKTX_DUT=16'h0000 -DKRX_DUT=16'h1220 -DTXI_DUT=16'h1221 -DPIN_DUT=2 -DPOUT_DUT=3 -DPLW_DUT=3"
K="-DKTX_DUT=16'h1111 -DKRX_DUT=16'h1331 -DTXI_DUT=16'h1331 -DPIN_DUT=3 -DPOUT_DUT=3 -DPLW_DUT=3"
run plan    PASS $P
run zero    PASS -DKTX_DUT=16\'h0000 -DKRX_DUT=16\'h0000 -DTXI_DUT=16\'h0000 -DPIN_DUT=0 -DPOUT_DUT=0 -DPLW_DUT=0
run stress  PASS -DKTX_DUT=16\'h3333 -DKRX_DUT=16\'h4444 -DTXI_DUT=16\'h4444 -DPIN_DUT=4 -DPOUT_DUT=4 -DPLW_DUT=4
run mut_dbit    FAIL -DOT_S81HD_LEPK_MUT_DBIT    $K
run mut_vdepth  FAIL -DOT_S81HD_LEPK_MUT_VDEPTH  $K
run mut_muskew  FAIL -DOT_S81HD_LEPK_MUT_MUSKEW  $P
run mut_txiskew FAIL -DOT_S81HD_LEPK_MUT_TXISKEW $P
echo BENCH_DONE

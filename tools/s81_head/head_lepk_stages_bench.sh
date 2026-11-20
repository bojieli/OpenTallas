#!/bin/bash
# DIE-HEAD-84 hd_lep0N leg-stage bench: build + run the transaction bench for the planned counts, a stress count,
# a zero-count control and three mutants (each must FAIL).  Usage: run_bench.sh BENCH_DIR
# DIE-HEAD-85 11-07: ONLY="case ..." runs a subset (pass it as `ot-run ... -- env ONLY=plan bash head_lepk_stages_bench.sh DIR`;
# ot-run does not forward the environment), --build-jobs 32, and the COL0 cases (coll0 +2 legs, COORD 22:0x (A)).
# Run in a dir holding rtl/ (kit rtl), models/ (SRAM sim models), ot_s81hd_lep0N_core.sv, ot_s81hd_lep_nr.sv (generated)
# and tb_head_lepk_stages.sv (rtl/dsrom_sys/s81_head/test/).
set -uo pipefail
B=$1; cd "$B"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
SRC="$(ls rtl/*.sv | grep -v -e ot_s81hd_lep0N.sv -e ot_s81hd_lep0N_core.sv -e ot_s81hd_lep_nr.sv) ot_s81hd_lep0N_core.sv ot_s81hd_lep_nr.sv $(ls models/*.v) tb_head_lepk_stages.sv"
run() { # name expect defines...
  local n=$1 exp=$2; shift 2
  if [ -n "${ONLY:-}" ] && [[ " $ONLY " != *" $n "* ]]; then return; fi   # ONLY="plan zero ..." runs a subset
  mkdir -p "case_$n"
  verilator --binary --timing -j 16 --build-jobs 32 -Wno-fatal -Wno-lint -Wno-style --top-module tb_head_lepk_stages --Mdir "case_$n/obj" \
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
run stress  PASS -DKTX_DUT=16\'h3333 -DKRX_DUT=16\'h4444 -DTXI_DUT=16\'h4444 -DPIN_DUT=4 -DPOUT_DUT=4 -DPLW_DUT=4 -DCOL0_DUT=2
run mut_dbit    FAIL -DOT_S81HD_LEPK_MUT_DBIT    $K
run mut_vdepth  FAIL -DOT_S81HD_LEPK_MUT_VDEPTH  $K
run mut_muskew  FAIL -DOT_S81HD_LEPK_MUT_MUSKEW  $P
run mut_txiskew FAIL -DOT_S81HD_LEPK_MUT_TXISKEW $P
run plan_c0   PASS $P -DCOL0_DUT=2
run c0_only   PASS -DKTX_DUT=16\'h0000 -DKRX_DUT=16\'h0000 -DTXI_DUT=16\'h0000 -DPIN_DUT=0 -DPOUT_DUT=0 -DPLW_DUT=0 -DCOL0_DUT=4
run mut_c0bit FAIL -DOT_S81HD_LEPK_MUT_C0BIT $P -DCOL0_DUT=2
# HEAD-PLAN-R4 11-17 NF15f: the hop-halving tuple + the RX head rank (RXH), RXH alone, and two RXH mutants (must FAIL)
F="-DKTX_DUT=16'h1111 -DKRX_DUT=16'h2660 -DTXI_DUT=16'h2442 -DPIN_DUT=6 -DPOUT_DUT=8 -DPLW_DUT=3 -DCOL0_DUT=2"
# FABLE-PLAN-HEAD-NF15F 1: the NF15f tuple needs K-link credit depth >= the measured round trip (lanes 1/2 RX ~24):
# KCRED 28 = production (slack on lanes 1/2), 24 = floor, 12 = the old depth (pair A/B release collision, FAIL).
# The bench peer e-lane stays CORE_CRED 12 in every case (the peer type does not change).
K="-DKCRED_DUT=28"
run nf15f       PASS $F $K -DRXH_DUT=1
run nf15f_norxh PASS $F $K
run nf15f_k24   PASS $F -DKCRED_DUT=24 -DRXH_DUT=1
run nf15f_k12   FAIL $F -DKCRED_DUT=12 -DRXH_DUT=1
run rxh_only    PASS -DKTX_DUT=16\'h0000 -DKRX_DUT=16\'h0000 -DTXI_DUT=16\'h0000 -DPIN_DUT=0 -DPOUT_DUT=0 -DPLW_DUT=0 -DRXH_DUT=1
run mut_rxhbit  FAIL -DOT_S81HD_LEPK_MUT_RXHBIT  $F $K -DRXH_DUT=1
run mut_rxhskew FAIL -DOT_S81HD_LEPK_MUT_RXHSKEW $F $K -DRXH_DUT=1
# RST-FAN-1d 11-20 (HEAD-CROSSING-1119, COORD 300 um hop cap): the core reset fan (RFAN 5 levels, 64 leaves) + u_lep's
# mapped reset tree (RTG 47 groups / RTR 4 root copies, each fed by its own fan leaf)
# (+ KTR 16'h3112 and the rxvb_q own locals in the production case) on the NF15f tuple: same transactions as ref, every reset leaf on one edge (+RFAN core, +RFAN+3 u_lep rr); proportional and the
# production hd_lep0N maps (r8b placed loads), stages-free, and a leaf-skew mutant (must FAIL the uniform-release check).
RT="-DRTG_DUT=47 -DRTR_DUT=4 -DRTGS_DUT=752'h03bc03bb03ba03b903a90389036903490329030902fb02e802e502df02bf029f029b0287027b026d024d02350229021b01fb01eb01cb01c701bf01b101a701a50191017c015c013c011c011600f600d600c000a000800060004000200000 -DRTRM_DUT=188'h23030000002002203111111111100000000032203333000"
RX="-DKTR_DUT=16'h3112 -DRFAN_DUT=5 -DRFN1_DUT=2 -DRFN2_DUT=4 -DRFN3_DUT=6 -DRFMX_DUT=1 -DRFPL_DUT=512'h00010402010102010102020404000003030303000004040404040404000003030000040404040403030105050202010202020201010101010101020202030301 -DRFPM_DUT=32'h00000100 -DRFPQ_DUT=48'h020300010103"
# FABLE-CBC-HEAD-0130 row 5: credit-return stages apart from KTX (hd_lep0N KTR 16'h3112, lane 0 = low nibble)
run nf15f_ktr    PASS $F $K -DRXH_DUT=1 -DKTR_DUT=16\'h3112
run nf15f_rfan   PASS $F $K -DRXH_DUT=1 -DRFAN_DUT=5 -DRFN1_DUT=2 -DRFN2_DUT=4 -DRFN3_DUT=6
run nf15f_rfanx  PASS $F $K -DRXH_DUT=1 $RX $RT
run rfan_only    PASS -DKTX_DUT=16\'h0000 -DKRX_DUT=16\'h0000 -DTXI_DUT=16\'h0000 -DPIN_DUT=0 -DPOUT_DUT=0 -DPLW_DUT=0 -DRFAN_DUT=3 -DRFN1_DUT=2
run mut_rfanskew FAIL -DOT_RST_FAN_MUT_SKEW $F $K -DRXH_DUT=1 $RX $RT
echo BENCH_DONE

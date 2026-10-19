#!/usr/bin/env bash
# MU-S81/LINK (2026-10-18): multi-user end-slice link benches on Verilator 5.050 (the closure daemon's version).
#   base   tb_s81sl_lep_mu seeds (PASS expected)
#   mut    TAGDROP / WRONGCOPY (ot_s81sl_lep_core) and LANDOVR (dsdv_mu_land): each must FAIL
#   regr   the pre-MU benches on the refactored file (MU_EN 0 tops): tb_s81sl_lep seeds 1 7, TB_LEP_NH seed 1,
#          tb_s81sl_lep_host seed 3, and the SWAP mutant (must still FAIL)
# Usage (cwd = repo root): run_lep_mu_bench.sh OUTDIR [base|mut|regr|all] [single mutant name]
set -u
O=${1:?outdir}; WHAT=${2:-all}; ONE=${3:-}; mkdir -p "$O"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
L=rtl/dsrom_sys/s81_link; SL=rtl/dsrom_sys/s81_dv/slice
SRCS="rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv
 $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dsyn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dchn.sv
 $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dec.sv $L/ot_pdie_serdes.sv
 physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v
 physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 $SL/ot_s81sl_slice_lep.sv $SL/dsdv_mu_land.sv"
D="+define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2"
build() { n=$1; top=$2; tb=$3; shift 3
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style +incdir+$L $D "$@" \
    --top-module $top -Mdir $O/$n $SRCS $SL/test/$tb --build-jobs ${J:-8} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
    > $O/build_$n.log 2>&1 || { echo "BUILD_FAILED $n"; grep -m10 %Error $O/build_$n.log; return 2; }
}
bad=0
run() { n=$1; exp=$2; re=$3; shift 3   # run <name> <PASS|FAIL> <verdict regex> <plusargs/-G already built>
  "$O/$n/V${TOP}" > "$O/$n.log" 2>&1; v=$(grep -m1 -E "^(PASS|FAIL) " "$O/$n.log")
  echo "$n: $v"
  case $exp in PASS) echo "$v" | grep -q -E "$re" || bad=1 ;; FAIL) echo "$v" | grep -q -E "$re" || { echo "  $n NOT detected"; bad=1; } ;; esac
}
if [ "$WHAT" = base ] || [ "$WHAT" = all ]; then
  TOP=tb_s81sl_lep_mu
  for s in 1 5; do build mu_s$s $TOP tb_s81sl_lep_mu.sv -GSEED=$s || bad=1; run mu_s$s PASS '^PASS lep_mu'; done
fi
if [ "$WHAT" = mut ] || [ "$WHAT" = all ]; then
  TOP=tb_s81sl_lep_mu
  for m in OT_S81SL_LEP_MUT_TAGDROP OT_S81SL_LEP_MUT_WRONGCOPY OT_DSDV_MU_LAND_MUT_OVR; do
    [ -n "$ONE" ] && [ "$ONE" != "$m" ] && continue
    n=mut_${m##*MUT_}; build $n $TOP tb_s81sl_lep_mu.sv +define+$m || bad=1; run $n FAIL '^FAIL lep_mu'
  done
fi
if [ "$WHAT" = regr ] || [ "$WHAT" = all ]; then
  TOP=tb_s81sl_lep
  build regr_lep tb_s81sl_lep tb_s81sl_lep.sv || bad=1
  "$O/regr_lep/Vtb_s81sl_lep" > $O/regr_lep_s1.log 2>&1; echo "regr_lep s1: $(grep -m1 -E '^(PASS|FAIL) ' $O/regr_lep_s1.log)"; grep -q '^PASS lep' $O/regr_lep_s1.log || bad=1
  build regr_lep7 tb_s81sl_lep tb_s81sl_lep.sv -GSEED=7 || bad=1
  "$O/regr_lep7/Vtb_s81sl_lep" > $O/regr_lep_s7.log 2>&1; echo "regr_lep s7: $(grep -m1 -E '^(PASS|FAIL) ' $O/regr_lep_s7.log)"; grep -q '^PASS lep' $O/regr_lep_s7.log || bad=1
  build regr_nh tb_s81sl_lep tb_s81sl_lep.sv +define+TB_LEP_NH || bad=1
  "$O/regr_nh/Vtb_s81sl_lep" > $O/regr_nh_s1.log 2>&1; echo "regr_nh s1: $(grep -m1 -E '^(PASS|FAIL) ' $O/regr_nh_s1.log)"; grep -q '^PASS lep' $O/regr_nh_s1.log || bad=1
  build regr_host tb_s81sl_lep_host tb_s81sl_lep_host.sv -GSEED=3 || bad=1
  "$O/regr_host/Vtb_s81sl_lep_host" > $O/regr_host_s3.log 2>&1; echo "regr_host s3: $(grep -m1 -E '^(PASS|FAIL) ' $O/regr_host_s3.log)"; grep -q '^PASS' $O/regr_host_s3.log || bad=1
  build regr_swap tb_s81sl_lep tb_s81sl_lep.sv +define+OT_S81SL_LEP_MUT_SWAP || bad=1
  "$O/regr_swap/Vtb_s81sl_lep" > $O/regr_swap.log 2>&1; echo "regr_swap: $(grep -m1 -E '^(PASS|FAIL) ' $O/regr_swap.log)"; grep -q '^FAIL lep' $O/regr_swap.log || bad=1
fi
[ $bad = 0 ] && echo "LEP_MU_GATE PASS" || echo "LEP_MU_GATE FAIL"
exit $bad

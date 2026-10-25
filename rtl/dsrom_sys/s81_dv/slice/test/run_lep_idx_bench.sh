#!/usr/bin/env bash
# S81/H4 (2026-10-24): index rank-tree frames of the s_0N lep (ot_s81sl_lep_mu_ab_idx), Verilator 5.050 (daemon version).
#   base  tb_s81sl_lep_idx seeds 1 / 5 (PASS expected)
#   mut   OT_S81SL_LEP_MUT_IDXPAIR / OT_S81SL_LEP_MUT_IDXDMX: each must FAIL
#   regr  the copy-A/B MU bench at the production opt-ins (IDX_EN 0 path of the edited core): tb_s81sl_lep_mu
#         P_RX_SRAM/P_IN_PIPE/P_NATIVE32 = 1 seed 1, and run_lep_mu_bench.sh regr (pre-MU tops + SWAP mutant)
# Usage (cwd = repo root): run_lep_idx_bench.sh OUTDIR [base|mut|regr|all]
set -u
O=${1:?outdir}; WHAT=${2:-all}; mkdir -p "$O"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
L=rtl/dsrom_sys/s81_link; SL=rtl/dsrom_sys/s81_dv/slice
SRCS="rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_sram_oldread_wreg.sv rtl/lib/ot_sram_showahead_1r1w.sv
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
 rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv
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
run() { n=$1; top=$2; exp=$3; re=$4
  "$O/$n/V$top" > "$O/$n.log" 2>&1; v=$(grep -m1 -E "^(PASS|FAIL) " "$O/$n.log")
  echo "$n: $v"
  echo "$v" | grep -q -E "^$exp $re" || { echo "  $n: expected $exp"; bad=1; }
}
if [ "$WHAT" = base ] || [ "$WHAT" = all ]; then
  for s in 1 5; do build idx_s$s tb_s81sl_lep_idx tb_s81sl_lep_idx.sv -GSEED=$s && run idx_s$s tb_s81sl_lep_idx PASS lep_idx || bad=1; done
fi
if [ "$WHAT" = mut ] || [ "$WHAT" = all ]; then
  for m in OT_S81SL_LEP_MUT_IDXPAIR OT_S81SL_LEP_MUT_IDXDMX; do
    n=mut_${m##*MUT_}; build $n tb_s81sl_lep_idx tb_s81sl_lep_idx.sv +define+$m && run $n tb_s81sl_lep_idx FAIL lep_idx || bad=1
  done
fi
if [ "$WHAT" = regr ] || [ "$WHAT" = all ]; then
  build regr_mu_t5 tb_s81sl_lep_mu tb_s81sl_lep_mu.sv -GP_RX_SRAM=1 -GP_IN_PIPE=1 -GP_NATIVE32=1 && \
    run regr_mu_t5 tb_s81sl_lep_mu PASS lep_mu || bad=1
  bash $SL/test/run_lep_mu_bench.sh $O/regr_lep_mu regr || bad=1
fi
[ $bad = 0 ] && echo "LEP_IDX_GATE PASS" || echo "LEP_IDX_GATE FAIL"
exit $bad

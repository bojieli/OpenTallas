#!/usr/bin/env bash
# S81-XDIE (2026-10-24): benches of the reserve-pair (RELEASE_RACK 2.1) end-slice endpoints on Verilator 5.050 (the closure
# daemon's version).  Sources = run_lep_mu_bench.sh.
#   hab    tb_s81sl_lep_hab (s_7N host plane + pair B at once, ot_s81sl_lep_mu_hab): seeds 3 / 7 at P_PROD 0 and seed 3 at
#          P_PROD 1 (die opt-ins RX_SRAM / IN_PIPE / NATIVE32 1)                                                -> PASS
#   habm   mutants on tb_s81sl_lep_hab: WRONGCOPY, TAGDROP, HACCB, KSOFF (P_PROD 0) and HSTAMP, HACCB (P_PROD 1)     -> FAIL
#   pab    tb_s81sl_lep_mu +define+TB_P_HAB (die P = ot_s81sl_lep_mu_hab: pair-B copy windows, landing, RETURN phase
#          pair-B merge, latency-user identity vs single-user reference): seeds 1 / 5, and the t5c opt-ins seed 1 -> PASS;
#          TB_P_HAB mutants WRONGCOPY / TAGDROP / STALEHD                                                         -> FAIL
#   ab     the unchanged copy-A/B (s_0S, s_0N) master: tb_s81sl_lep_mu seed 1 and t5c opt-ins seed 1           -> PASS
# Usage (cwd = repo root): run_lep_hab_bench.sh OUTDIR [hab|habm|pab|ab|all]
set -u
O=$(realpath -m "${1:?outdir}"); WHAT=${2:-all}; mkdir -p "$O"; rm -f "$O"/*.bad
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
one() { n=$1; top=$2; tb=$3; exp=$4; re=$5; shift 5
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style +incdir+$L $D "$@" \
    --top-module $top -Mdir $O/$n $SRCS $SL/test/$tb --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
    > $O/build_$n.log 2>&1 || { echo "$n: BUILD_FAILED"; grep -m10 %Error $O/build_$n.log; touch $O/$n.bad; return; }
  $O/$n/V$top > $O/$n.log 2>&1; v=$(grep -m1 -E "^(PASS|FAIL) " $O/$n.log)
  echo "$n: $v"; grep -m2 -E "STATS|LEPHAB_F" $O/$n.log | sed 's/^/  /'
  case $exp in PASS) echo "$v" | grep -q -E "$re" || touch $O/$n.bad ;;
               FAIL) echo "$v" | grep -q -E "$re" || { echo "  $n NOT detected"; touch $O/$n.bad; } ;; esac
}
H=tb_s81sl_lep_hab; M=tb_s81sl_lep_mu
if [ "$WHAT" = hab ] || [ "$WHAT" = all ]; then
  one hab_s3 $H $H.sv PASS '^PASS lep_hab' -GSEED=3 & one hab_s7 $H $H.sv PASS '^PASS lep_hab' -GSEED=7 &
  one hab_prod_s3 $H $H.sv PASS '^PASS lep_hab' -GSEED=3 -GP_PROD=1 & wait
fi
if [ "$WHAT" = habm ] || [ "$WHAT" = all ]; then
  for m in WRONGCOPY TAGDROP HACCB KSOFF; do one habm_$m $H $H.sv FAIL '^FAIL lep_hab' +define+OT_S81SL_LEP_MUT_$m & done; wait
  for m in HSTAMP HACCB; do one habm_prod_$m $H $H.sv FAIL '^FAIL lep_hab' -GP_PROD=1 +define+OT_S81SL_LEP_MUT_$m & done; wait
fi
if [ "$WHAT" = pab ] || [ "$WHAT" = all ]; then
  one pab_s1 $M $M.sv PASS '^PASS lep_mu' +define+TB_P_HAB -GSEED=1 & one pab_s5 $M $M.sv PASS '^PASS lep_mu' +define+TB_P_HAB -GSEED=5 &
  one pab_t5c_s1 $M $M.sv PASS '^PASS lep_mu' +define+TB_P_HAB -GSEED=1 -GP_RX_SRAM=1 -GP_IN_PIPE=1 -GP_NATIVE32=1 & wait
  for m in WRONGCOPY TAGDROP STALEHD; do one pabm_$m $M $M.sv FAIL '^FAIL lep_mu' +define+TB_P_HAB +define+OT_S81SL_LEP_MUT_$m & done; wait
fi
if [ "$WHAT" = ab ] || [ "$WHAT" = all ]; then
  one ab_s1 $M $M.sv PASS '^PASS lep_mu' -GSEED=1 & one ab_t5c_s1 $M $M.sv PASS '^PASS lep_mu' -GSEED=1 -GP_RX_SRAM=1 -GP_IN_PIPE=1 -GP_NATIVE32=1 & wait
fi
ls $O/*.bad >/dev/null 2>&1 && bad=1 || bad=0
[ $bad = 0 ] && echo "LEP_HAB_GATE PASS" || { echo "LEP_HAB_GATE FAIL: $(cd $O && ls *.bad | tr '\n' ' ')"; }
exit $bad

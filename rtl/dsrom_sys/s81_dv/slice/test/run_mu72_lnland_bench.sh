#!/usr/bin/env bash
# STW-S81-LAND 10-21: MU72 lane landing bench (tb_s81_mu72_lnland) on Verilator 5.050 (the closure daemon's version).
#   base  P_LAND 1 / CRED 12: phase 0 seeds 1 2 (exact +6), phase-offset clocks seed 3            -> PASS
#   mut   P_MUT 1 / 2 / 3 (missing landing edge on K->N, N->K, credit) and P_CRED 8 with landing  -> FAIL
#   kit   P_KIT 1 (u_lep RX_SRAM / IN_PIPE / NATIVE32 1 as the tops): seeds 1, ph 3 -> PASS; P_MUT 1 -> FAIL
#   r4l   P_R4L 1 (die-side successor end, regional lep r4l on K/KA/KB + 4 landed lanes): seeds 1, ph 3 -> PASS;
#         P_MUT 1 / 2 / 3 -> FAIL
#   nst   S81/PORTFIX-FLT 10-25: P_NST 1 (ot_s81_mu72_lnland_nst, the status-less landing of s_0N / s_0S / s_7S, kit
#         lep params): seeds 1, ph 3 -> PASS; P_MUT 1 / 2 / 3 -> FAIL
# Usage (cwd = repo root): run_mu72_lnland_bench.sh OUTDIR [base|mut|kit|r4l|nst|all]
set -u
O=$(realpath -m "${1:?outdir}"); WHAT=${2:-all}; mkdir -p "$O"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
SL=rtl/dsrom_sys/s81_dv/slice; L=rtl/dsrom_sys/s81_link; M1=physical/asap7_memory_macros; M2=physical/asap7_memory_macros_v2
SRCS="rtl/link/ot_link_crc32.sv rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_relay_tree3.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv
 rtl/lib/ot_sram_oldread_b64.sv rtl/lib/ot_sram_oldread_wreg.sv rtl/lib/ot_sram_showahead_b64.sv rtl/lib/ot_sram_showahead_1r1w.sv
 rtl/common/ot_link_credit_rx_b64.sv rtl/common/ot_link_credit_tx_rc.sv
 rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv
 $M2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v $M2/ot_sram_1r1w2c_256x64_m1/ot_sram_1r1w2c_256x64_m1.v
 $M2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $M2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 $M2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v $M1/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
 $L/ot_pdie_serdes.sv $SL/ot_s81sl_slice_lep.sv $(ls rtl/common/landed_parent/*.sv)
 $SL/mu72/ot_s81_mu72_land.sv $SL/mu72/ot_s81_mu72_lnland.sv
 $SL/ot_s81sl_lep_mu_ab_regional.sv $SL/ot_s81sl_lep_mu_ab_regional_r3r.sv $SL/ot_s81sl_lep_mu_ab_regional_r4l.sv"
D="-DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF"   # = the CLOSED CRED12 lane kits (dscoll_lane_{w,e}_s12g spec defines)
rm -f $O/*.bad
one() { n=$1; exp=$2; shift 2
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style +incdir+$L $D "$@" \
    --top-module tb_s81_mu72_lnland -Mdir $O/$n $SRCS $SL/test/tb_s81_mu72_lnland.sv --build-jobs ${J:-8} \
    -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build_$n.log 2>&1 || { echo "$n: BUILD_FAILED"; grep -m10 %Error $O/build_$n.log; touch $O/$n.bad; return; }
  $O/$n/Vtb_s81_mu72_lnland > $O/$n.log 2>&1
  v=$(grep -m1 -E "^(PASS|FAIL) " $O/$n.log); s=$(grep -m1 MU72_LNLAND_STATS $O/$n.log)
  echo "$n: $v"; echo "  $s"
  case $exp in PASS) echo "$v" | grep -q '^PASS mu72_lnland' || touch $O/$n.bad ;; FAIL) echo "$v" | grep -q '^FAIL mu72_lnland' || { echo "  $n NOT detected"; touch $O/$n.bad; } ;; esac
}
if [ "$WHAT" = base ] || [ "$WHAT" = all ]; then
  one base_s1 PASS -GSEED=1 & one base_s2 PASS -GSEED=2 & one base_ph_s3 PASS -GSEED=3 -GP_PH=1 & wait
fi
if [ "$WHAT" = mut ] || [ "$WHAT" = all ]; then
  one mut1_kn_unlanded FAIL -GP_MUT=1 & one mut2_nk_unlanded FAIL -GP_MUT=2 & one mut3_credit_unlanded FAIL -GP_MUT=3 &
  one mut_cred8 FAIL -GP_CRED=8 & wait
fi
if [ "$WHAT" = kit ] || [ "$WHAT" = kr ] || [ "$WHAT" = all ]; then     # the die's lep params (RX_SRAM / IN_PIPE / NATIVE32 1, = lepmu kits)
  one kit_s1 PASS -GP_KIT=1 -GSEED=1 & one kit_ph_s3 PASS -GP_KIT=1 -GSEED=3 -GP_PH=1 & one kit_mut1 FAIL -GP_KIT=1 -GP_MUT=1 & wait
fi
if [ "$WHAT" = r4l ] || [ "$WHAT" = kr ] || [ "$WHAT" = all ]; then
  one r4l_s1 PASS -GP_R4L=1 -GSEED=1 & one r4l_ph_s3 PASS -GP_R4L=1 -GSEED=3 -GP_PH=1 & wait
  one r4l_mut1 FAIL -GP_R4L=1 -GP_MUT=1 & one r4l_mut2 FAIL -GP_R4L=1 -GP_MUT=2 & one r4l_mut3 FAIL -GP_R4L=1 -GP_MUT=3 & wait
fi
if [ "$WHAT" = nst ] || [ "$WHAT" = all ]; then
  one nst_s1 PASS -GP_NST=1 -GP_KIT=1 -GSEED=1 & one nst_ph_s3 PASS -GP_NST=1 -GP_KIT=1 -GSEED=3 -GP_PH=1 & wait
  one nst_mut1 FAIL -GP_NST=1 -GP_KIT=1 -GP_MUT=1 & one nst_mut2 FAIL -GP_NST=1 -GP_KIT=1 -GP_MUT=2 & one nst_mut3 FAIL -GP_NST=1 -GP_KIT=1 -GP_MUT=3 & wait
fi
ls $O/*.bad >/dev/null 2>&1 && bad=1 || bad=0
[ $bad = 0 ] && echo "MU72_LNLAND_BENCH PASS" || echo "MU72_LNLAND_BENCH FAIL"; exit $bad

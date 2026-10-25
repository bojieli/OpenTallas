#!/usr/bin/env bash
# S81/PORTFIX-DEAD (10-25): Verilator lint of every new / changed die master of the dead-port items (repo root).
#   lint_dead.sh OUTDIR [TOP...]   (default: all).  Children outside the slice family that these items do not touch
#   (coll lanes, link endpoints) are waived with -Wno-MODMISSING, as the kit lint stage; every changed interface
#   (lp variants, capc5r / capc2 variants, lep_mu_a_nrt, xg masters without xw_v) is read and checked.
set -u; O=${1:?outdir}; shift; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
S=rtl/dsrom_sys/s81_dv/slice; L=$S/landed
SRCS=$(sed -n 's/^SRCS="\(.*\)"$/\1/p' $L/c1x/ot_s81sl_slice_c1x_lp_bench.sh | tr ' ' '\n' | grep -v "landed/c1x/\|/tb_" | tr '\n' ' ')
SRCS="$SRCS $S/ot_s81sl_cap_tr.sv $S/ot_s81sl_cap_rt.sv rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv $S/ot_s81sl_xgt.sv $S/ot_s81sl_xgt_xo.sv
 $S/ot_s81sl_xg_xo.sv $S/ot_s81sl_xrt.sv $S/ot_s81sl_rstopt.sv $S/ot_s81sl_rstopt_xo.sv $S/ot_s81sl_rstop_xo.sv $S/ot_s81sl_xs4.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v
 rtl/common/landed_parent/ot_pl_land_n32.sv rtl/common/landed_parent/ot_pl_land_rst_copy.sv rtl/common/landed_parent/ot_pl_land_reset_forest.sv
 $S/lp/ot_s81sl_capc5r.sv $S/lp/ot_s81sl_capc5r_w3.sv $S/lp/ot_s81sl_capc5r_e6.sv
 $S/cap_end/ot_s81_retn_fwd.sv $S/cap_end/ot_s81sl_cap_trn.sv $S/cap_end/ot_s81sl_cap_rt_w.sv $S/cap_end/ot_s81sl_cap_end.sv
 $S/cap_end/ot_s81sl_capc2_w3.sv $S/cap_end/ot_s81sl_slice_w3.sv $S/ot_s81sl_slice_c3x.sv
 $L/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp.sv $L/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp_e6.sv $L/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp_w3.sv
 $L/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_w_e6.sv $L/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_w_w3.sv
 $L/c3x_k8_cap5r/ot_s81sl_slice_c3x_k8_cap5r_lp_w3.sv $L/c3x_k8_cap5r/ot_s81sl_slice_c3x_k8_cap5r_w_w3.sv
 rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_sram_oldread_wreg.sv rtl/lib/ot_sram_showahead_1r1w.sv
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv
 $S/ot_s81sl_slice_lep.sv $S/dsdv_mu_land.sv $S/mu72/ot_s81_mu72_land.sv $S/mu72/ot_s81_mu72_lnland.sv
 $S/mu72/ot_s81sl_slice_lepw_mu_72.sv $S/mu72/ot_s81sl_slice_lepe_nh_mu_72.sv $S/mu72/ot_s81sl_slice_lepe_mu_72.sv
 $S/mu72/ot_s81sl_slice_lepw_mab_hbc_prod_mu_72.sv"
TOPS=${*:-"ot_s81sl_capc5r_w3 ot_s81sl_capc5r_e6 ot_s81sl_capc2_w3 ot_s81sl_slice_c1x_k8_cap5r_lp ot_s81sl_slice_c1x_k8_cap5r_w_w3
 ot_s81sl_slice_c1x_k8_cap5r_w_e6 ot_s81sl_slice_c3x_k8_cap5r_w_w3 ot_s81sl_slice_w3 ot_s81sl_slice_sukv_raw512_w3
 ot_s81sl_slice_lepw_mu_72 ot_s81sl_slice_lepe_nh_mu_72 ot_s81sl_slice_lepe_mu_72 ot_s81sl_slice_lepw_mab_hbc_prod_mu_72
 ot_s81sl_xg ot_s81sl_xg_xo ot_s81sl_xgt ot_s81sl_xgt_xo ot_s81sl_slice_c1x ot_s81sl_slice_c3x"}
bad=0
for T in $TOPS; do
  $V --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING -Wno-MULTITOP -DSYNTHESIS \
    -DDSFD_PQ_STATIC_X2 +define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2 +incdir+rtl/dsrom_sys/s81_link \
    --top-module $T $SRCS > $O/lint_$T.log 2>&1
  e=$(grep -c '^%Error' $O/lint_$T.log); w=$(grep -c '^%Warning-\(PINMISSING\|PINNOTFOUND\|WIDTHEXPAND\|WIDTHTRUNC\|PINCONNECTEMPTY\)' $O/lint_$T.log)
  echo "LINT $T errors $e pin/width-warnings $w"; [ "$e" = 0 ] || { bad=1; grep -m5 '^%Error' $O/lint_$T.log; }
done
[ $bad = 0 ] && echo "LINT_DEAD PASS" || echo "LINT_DEAD FAIL"; exit $bad

#!/usr/bin/env bash
# MU-S81/LINK: lint of the lep leaf tops (kit lint form), the MU top, dsdv_mu_land (SRAM 1) and the MU cluster variants
# (missing slice / lane modules waived with -Wno-MODMISSING, as the kit lint stage).  cwd = repo root.
set -u; O=${1:?outdir}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
S="rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv rtl/dsrom_sys/s81_dv/slice/dsdv_mu_land.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
bad=0
lint() { n=$1; body=$2
  printf 'module ot_lint_top; %s endmodule\n' "$body" > $O/top_$n.sv
  $V --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top $O/top_$n.sv $S > $O/lint_$n.log 2>&1
  e=$(grep -c '^%Error' $O/lint_$n.log); echo "lint $n: errors $e"; [ "$e" = 0 ] || { bad=1; grep -m5 '^%Error' $O/lint_$n.log; }
}
lint lep 'ot_s81sl_lep u_top ();'
lint lep_nh 'ot_s81sl_lep_nh u_top ();'
lint lep_mu 'ot_s81sl_lep_mu u_top ();'
lint lep_mu_ab0_host 'ot_s81sl_lep_mu #(.HOST_EN(1), .AB_EN(0)) u_top ();'
lint land128 'dsdv_mu_land #(.SRAM(1)) u_top ();'
lint land256 'dsdv_mu_land #(.SRAM(1), .NB(160)) u_top ();'
lint cl_w_mu_ab 'ot_s81sl_slice_lep #(.SIDE(0), .HOST_EN(0), .MU_EN(1), .AB_EN(1)) u_top ();'
lint cl_e_mu_host 'ot_s81sl_slice_lep #(.SIDE(1), .HOST_EN(1), .MU_EN(1), .AB_EN(0)) u_top ();'
lint masters 'ot_s81sl_slice_lepw a (); ot_s81sl_slice_lepe b (); ot_s81sl_slice_lepe_nh c ();'
lint masters_mu 'ot_s81sl_slice_lepw_mu a (); ot_s81sl_slice_lepw_mus b (); ot_s81sl_slice_lepe_mu c (); ot_s81sl_slice_lepe_nh_mus d (); ot_s81sl_slice_lepw_mab e ();'   # MU-S81/DIE
[ $bad = 0 ] && echo "LEP_MU_LINT PASS" || echo "LEP_MU_LINT FAIL"; exit $bad

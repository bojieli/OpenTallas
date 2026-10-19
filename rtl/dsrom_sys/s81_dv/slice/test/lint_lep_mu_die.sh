#!/usr/bin/env bash
# MU-S81-2/DIE: lint of the multi-user die masters (ot_s81sl_slice_lep_mu.sv on lep_mu_a / lep_mu_ab / lep_mu HOST_EN 1 +
# dsdv_mu_land) and of dsdv_seq_host_mux (closed hslot + hwin).  Slice / lane / seq_host modules are waived with
# -Wno-MODMISSING, as the kit lint stage.  cwd = repo root.
set -u; O=${1:?outdir}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
S="rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep_mu.sv rtl/dsrom_sys/s81_dv/slice/dsdv_mu_land.sv
 rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hslot.sv rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvh.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
bad=0
lint() { n=$1; body=$2
  printf 'module ot_lint_top; %s endmodule\n' "$body" > $O/top_$n.sv
  $V --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top $O/top_$n.sv $S > $O/lint_$n.log 2>&1
  e=$(grep -c '^%Error' $O/lint_$n.log); echo "lint $n: errors $e"; [ "$e" = 0 ] || { bad=1; grep -m5 '^%Error' $O/lint_$n.log; }
}
lint hwin 'dsdv_mu_hwin #(.NSLOT(47), .NEV(8), .NEP(4), .NRT(2)) u_top ();'
lint seq_host_mux 'dsdv_seq_host_mux u_top ();'
lint cl_w_a 'ot_s81sl_slice_lep_mux #(.SIDE(0), .HOST_EN(0), .AB_EN(0)) u_top ();'
lint cl_w_ab 'ot_s81sl_slice_lep_mux #(.SIDE(0), .HOST_EN(0), .AB_EN(1)) u_top ();'
lint cl_e_h 'ot_s81sl_slice_lep_mux #(.SIDE(1), .HOST_EN(1), .AB_EN(0)) u_top ();'
lint cl_e_a 'ot_s81sl_slice_lep_mux #(.SIDE(1), .HOST_EN(0), .AB_EN(0)) u_top ();'
lint masters_mu 'ot_s81sl_slice_lepw_mu a (); ot_s81sl_slice_lepw_mus b (); ot_s81sl_slice_lepe_mu c (); ot_s81sl_slice_lepe_nh_mus d (); ot_s81sl_slice_lepw_mab e ();'
lint relays 'dsfd_dvrlyh_512_NS a (); dsfd_dvrlyh_512_SN b (); dsfd_dvrlyh_562_NS c ();'
[ $bad = 0 ] && echo "LEP_MU_DIE_LINT PASS" || echo "LEP_MU_DIE_LINT FAIL"; exit $bad

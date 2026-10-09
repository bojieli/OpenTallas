# PRE_CTS hook, TUhalf -cx (review-0400 R5, drive-0212): the cg hook (cg_pushdown clones u_icg per sink cluster and
# re-creates gclk on every clone) plus the landing gate u_head_icg: after the pushdown, headclk is re-declared on every
# head-gate output (clones included) and the clock-gating checks are set on both gates, so CTS sees both gates as clock
# gates with their generated clocks.  The procs come from headclk_procs.tcl (make_sdc.py --landing-procs-out): ORFS
# re-reads write_sdc output between stages, which keeps the generated clocks but not the SDC's procs.
source /src/physical/hbm_ha2_fixedpins_20261007/cx_landing/headclk_procs.tcl
source /src/physical/hbm_ha2_fixedpins_20261007/cg_gclk_pre_cts.tcl
rename ot_cgpd_cts_orig ot_cx_cts_orig
proc ot_cgpd_cts_orig {args} {
  ot_ha2_headclk_define
  ot_cx_cts_orig {*}$args
}

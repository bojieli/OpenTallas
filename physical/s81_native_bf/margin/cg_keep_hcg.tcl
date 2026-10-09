# bf-insertion 2026-10-08: keep the BF half-rate clock gate ONE gate under cg_pushdown.tcl (chain this hook BEFORE
# cg_pushdown in OT_CTS_FIX_HOOKS).  HALF_PHL puts the phase register g_half.ph on u_hcg.u_icg's own clock net
# (ph_local.tcl) so ph -> ENA is local and skew-free; pushdown cloned u_icg 128x and broke that (ph -> clone ENA gating
# check -755.8 ps at 730 on bfh_halfphl_a730_tt_hm10_639afaedc).  The element's own gates (g_wake leaves) still clone.
lappend ::ot_cg_exclude {g_half.u_hcg.u_icg*}

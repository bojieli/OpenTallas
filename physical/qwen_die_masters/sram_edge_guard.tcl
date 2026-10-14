# SRAM / hard-macro edge guard for ref_tile kits (spec "boundary_tcl": sourced from pre_cts, pre_grt and post_drt).
# Applies the shared whole-GCell guard physical/common_flow/macro_edge_via_guard.tcl (1.2 um of the top routing layer
# taken out per macro edge parallel to that layer, pin stub free): added before GRT, removed after DRT, nothing at CTS,
# so the exported view carries only real metal.  The loop's hold ECO re-applies the same guard (hold_eco.sh ECO_MEG).
# Why here (q13b-kvend 2026-10-13): qkd_sbufp_ref-q14 closed timing in -arg1 (TT +116.41 / FF +0.69) but kept 2-5 M4
# "Short / Metal Spacing inst:u.u_m net:u.g_s[*].u_sl/*" markers at the SRAM's east pin edge (x 204.47..204.552, macro
# edge 204.552) on all three routes: a net assigned an over-macro M5 track in the GCell straddling the edge jogs on M4
# through the macro OBS.  Same shape as the s81su qnq/qbe finding the guard was written for.
set ot_seg_stage [file tail [dict get [info frame -1] file]]
puts "OT_SRAM_EDGE_GUARD hook invoked caller=$ot_seg_stage"
if {[string match *pre_grt.tcl $ot_seg_stage]} {
  set ::env(OT_MEG_MODE) add; source /src/physical/common_flow/macro_edge_via_guard.tcl; unset ::env(OT_MEG_MODE)
} elseif {[string match *post_drt.tcl $ot_seg_stage]} {
  set ::env(OT_MEG_MODE) remove; source /src/physical/common_flow/macro_edge_via_guard.tcl; unset ::env(OT_MEG_MODE)
}

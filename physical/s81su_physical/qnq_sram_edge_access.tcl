# SRAM edge access for dsfd_su_t_qnq (ref_tile spec boundary_tcl: sourced from pre_cts, pre_grt and post_drt).
# 2026-10-13 [s81su-qnqb]: the 0.024..0.30 um strip this file used to create only moved the M4 bridge to the first free
# over-macro M5 track inside it (x 214.908 / 214.956; spx DRC 2, sp8 DRC 3 / 5, every violation on that track).  It now
# applies the shared whole-GCell guard physical/common_flow/macro_edge_via_guard.tcl (1.2 um of M5 per vertical macro
# edge, pin stub free): added before GRT, removed after DRT, nothing at CTS.  The loop's hold ECO re-applies the same guard.
set cx_stage [file tail [dict get [info frame -1] file]]
puts "CX_SU_QNQ SRAM hook invoked caller=$cx_stage"
if {[string match *pre_grt.tcl $cx_stage]} {
  set ::env(OT_MEG_MODE) add; source /src/physical/common_flow/macro_edge_via_guard.tcl; unset ::env(OT_MEG_MODE)
} elseif {[string match *post_drt.tcl $cx_stage]} {
  set ::env(OT_MEG_MODE) remove; source /src/physical/common_flow/macro_edge_via_guard.tcl; unset ::env(OT_MEG_MODE)
}

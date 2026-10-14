# dsfd_engram_c POST_CTS (el1013-s81-engram 2026-10-13): vclk fixed (see pre_cts_engc.tcl).  Output hold follows the
# view flow's FF model (vclk_latency.tcl: receiver flops at the earliest FF insertion + 40): min delay = V - V_ff - 40,
# V_ff = ENGC_VCLK_FF_PS (the same effective insertion at FF).
set ot_ev [lindex [get_property [get_clocks vclk] sources] 0]
if {[info exists ::env(ENGC_VCLK_PS)] && [info exists ::env(ENGC_VCLK_FF_PS)]} {
  set_clock_latency $::env(ENGC_VCLK_PS) [get_clocks vclk]
  set ot_omin [expr {$::env(ENGC_VCLK_PS) - $::env(ENGC_VCLK_FF_PS) - 40}]
  set_output_delay -min $ot_omin -clock vclk [all_outputs]
  puts "OT_ENGC_VCLK fixed: vclk latency $::env(ENGC_VCLK_PS) ps (FF $::env(ENGC_VCLK_FF_PS)), output min delay $ot_omin ps"
} else { error "OT_ENGC_VCLK: ENGC_VCLK_PS / ENGC_VCLK_FF_PS not set (--orfs-var)" }

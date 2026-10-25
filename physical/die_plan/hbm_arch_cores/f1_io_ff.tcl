# HBM-CORES 2026-10-25 F1 (per-corner IO clock basis, GEOM-REVIEW 04:37 cond. 1): the parent's FF clock tree is
# not at the TT plan latency.  For the in-flow (BC) hold repair, output-port hold is referenced to the FF IO latency
# OT_IO_FF_LATENCY_PS (= plan I x measured FF/TT pin-reg ratio): output -min delay = I_TT - I_FF, i.e. exactly the
# FF vclk latency for the output direction, so no hold padding is inserted on output ports.  Inputs keep the kit
# contract.  Signoff uses the kit SDC (+ the per-corner CORE_FF_VCLK reference once SIGNOFF adopts it).
if {[info exists ::env(OT_IO_FF_LATENCY_PS)] && [info exists ::env(OT_IO_TT_LATENCY_PS)]} {
  set ::ot_omin [expr {$::env(OT_IO_TT_LATENCY_PS) - $::env(OT_IO_FF_LATENCY_PS)}]
  set_output_delay -min $::ot_omin -clock [get_clocks vclk] [all_outputs]
  puts "OT_F1 output -min $::ot_omin (I_TT $::env(OT_IO_TT_LATENCY_PS) I_FF $::env(OT_IO_FF_LATENCY_PS))"
}
source /work/hold_cap.tcl

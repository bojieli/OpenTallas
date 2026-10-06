# Dedicated W2 context: use actual parent clocks, crossings and per-port arcs.
# An absent binding is a HOLD, never the historical 90/100ps network estimate.
if {![info exists ::env(OT_W2_ACTUAL_BOUNDARY_SDC)]} {
 error "W2 HOLD: actual mapped-parent clock/IO/reset binding is absent"
}
source $::env(OT_W2_ACTUAL_BOUNDARY_SDC)
set_units -time ps -capacitance fF
foreach name {clk_sm clk_mem} {
 set clock [get_clocks -quiet $name]
 if {[llength $clock]!=1} {error "W2 HOLD: actual clock $name is not uniquely bound"}
}
set p [get_property [get_clocks clk_sm] period]
if {abs($p-833.3333333333334)>0.001} {error "W2 HOLD: clk_sm period changed from the sized contract"}
set_clock_uncertainty -setup 60 [get_clocks {clk_sm clk_mem}]
set_clock_uncertainty -hold 25 [get_clocks {clk_sm clk_mem}]
# CTS and extracted interconnect supply network insertion; no ideal latency.
set_propagated_clock [get_clocks {clk_sm clk_mem}]
# IO timing, receiver loads and legitimate CDC constraints come solely from the
# actual parent binding. There are no reset/IO false paths or dummy captures here.

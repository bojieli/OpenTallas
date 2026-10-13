# Same-phase regional clocks, all cross-root paths timed. No false paths.
set ring_region_period [get_property [get_clocks core_clk] period]
for {set r 0} {$r < 9} {incr r} {
 set p [get_ports [format {data_clk[%d]} $r]]
 if {[llength $p] != 1} { error "Missing ring regional clock $r" }
 create_clock -name ring_data_$r -period $ring_region_period $p
}
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# Clock creation must precede input-delay assignment for the new clock ports.
unset_input_delay -clock core_clk [get_ports {data_clk*}]
if {[get_property [get_clocks core_clk] is_propagated]} {
 set_propagated_clock [get_clocks {ring_data_*}]
}

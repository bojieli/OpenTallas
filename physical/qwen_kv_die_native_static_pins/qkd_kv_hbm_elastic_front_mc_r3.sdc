
# Four actual die-delivered storage clocks; ordinary STA between same-phase HBM roots.
for {set i 0} {$i<4} {incr i} {
 create_clock -name hdata_$i -period [get_property [get_clocks core_clk] period] [get_ports [format {pll_hbm_data[%d]} $i]]
 set_clock_uncertainty -setup 60 [get_clocks hdata_$i]
 set_clock_uncertainty -hold 25 [get_clocks hdata_$i]
 if {[get_property [get_clocks core_clk] is_propagated]} {set_propagated_clock [get_clocks hdata_$i]}
}

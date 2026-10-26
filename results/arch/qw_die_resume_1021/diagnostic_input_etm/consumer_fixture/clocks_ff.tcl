# DOMS stream
# INSERTION_COMPENSATED ff
# OWNER_CLOCK_BUDGET v1
set_cmd_units -time ps
set ot_clock_bound 0
# PHYSICAL_DIAGNOSTIC_ONLY; NOT_A_DIE_RESULT
set ot_clock_boundary_unmeasured 0
set ot_clock_qualification UNMEASURED
set ot_sta_qualification UNMEASURED
set ot_region_qualification UNMEASURED
set ot_pins {}
set p [get_pins -quiet {ucie_kv/clk}]
if {[llength $p] != 1} { error "clock boundary pin missing or ambiguous: ucie_kv/clk" }
lappend ot_pins [lindex $p 0]
create_clock -name stream -period 833.333000 $ot_pins
# DIAGNOSTIC UNMEASURED_INPUT_BOUNDARY ucie_kv/clk; internal/native R UNPROVEN; no insertion compensation
incr ot_clock_boundary_unmeasured
# BUDGET stream -> stream: setup 60 + skew 90 ps; hold H1 100 ps
set_clock_uncertainty -setup 150.000000 -from [get_clocks stream] -to [get_clocks stream]
set_clock_uncertainty -hold 100.000000 -from [get_clocks stream] -to [get_clocks stream]
set_propagated_clock [all_clocks]
puts "OT_COMPENSATED_CLOCK corner=ff bound=$ot_clock_bound"
puts "OT_DIAGNOSTIC_INPUT_BOUNDARY clock_qualification=UNMEASURED sta_qualification=UNMEASURED region_qualification=UNMEASURED refs=$ot_clock_boundary_unmeasured"

# NATIVE-REF 2026-10-18 regression: route-time IO reference of a CLOSED route's netlist, old (origin/main 2cac78ec5
# pinflop_ref.tcl: 3-hop search, raw macro pin) vs new (PF-HOLDPAD).  Env: CHILD_LIBS / CHILD_LEFS (space lists), REFGLOB.
set L /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $L/lef/asap7_tech_1x_201209.lef
read_lef $L/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f $::env(CHILD_LEFS) { read_lef $f }
foreach f [glob $L/lib/NLDM/*SEQ*RVT_TT*.lib* $L/lib/NLDM/*SIMPLE*RVT_TT*.lib* $L/lib/NLDM/*INVBUF*RVT_TT*.lib* $L/lib/NLDM/*AO*RVT_TT*.lib* $L/lib/NLDM/*OA*RVT_TT*.lib*] { read_liberty $f }
foreach f $::env(CHILD_LIBS) { read_liberty $f }
read_db /base/6_final.odb
read_sdc /base/6_final.sdc
read_spef /base/6_final.spef
set_propagated_clock [all_clocks]
sta::worst_slack_cmd max
set ins [all_inputs -no_clocks]
puts "INPUTS [llength $ins]"
source /m/old_pinflop_ref.tcl
set t0 [clock milliseconds]
set o [ot_pf_ref $ins]
set how pinflop
if {![llength $o]} { set o [lindex [all_registers -clock_pins] 0]; set how first_register }
puts [format "OLD ref %s (%s) arrival_max %.1f  search_ms %d" [get_full_name $o] $how [get_property $o arrival_max_rise] [expr {[clock milliseconds]-$t0}]]
source /m2/pinflop_ref.tcl
set ::env(ADDITIONAL_LIBS) $::env(CHILD_LIBS)
set t0 [clock milliseconds]
set n [ot_pf_ref $ins]
set how pinflop
if {![llength $n]} { set n [lindex [all_registers -clock_pins] 0]; set how first_register }
puts [format "NEW ref %s (%s) raw %.1f ot_pf_arr max %.1f min %.1f  search_ms %d" [get_full_name $n] $how [get_property $n arrival_max_rise] [ot_pf_arr $n max] [ot_pf_arr $n min] [expr {[clock milliseconds]-$t0}]]
# first-register fallback under the new arrival read (a hard child pin now counts at + its insertion)
set f [lindex [all_registers -clock_pins] 0]
puts [format "FIRST %s raw %.1f ot_pf_arr %.1f" [get_full_name $f] [get_property $f arrival_max_rise] [ot_pf_arr $f max]]
# the kit workaround (explicit REFGLOB, median member) for comparison
set gm {}
foreach c [get_cells -quiet -hierarchical $::env(REFGLOB)] { set p [get_pins -quiet "[get_full_name $c]/CLK"]; if {[llength $p]} { lappend gm $p } }
if {[llength $gm]} { set g [ot_pf_median $gm "REFGLOB $::env(REFGLOB)"]; puts [format "GLOB ref %s arrival %.1f" [get_full_name $g] [ot_pf_arr $g max]] } else { puts "GLOB none" }

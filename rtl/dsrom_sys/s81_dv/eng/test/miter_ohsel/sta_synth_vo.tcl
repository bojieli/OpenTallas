# zero-wire TT estimate on a synth netlist: worst path into u_xq.vo_b / vo_a from the rung select flops
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /k/macros/*_tt.lib] { read_liberty $f }
read_verilog $::env(NET)
link_design dsdv_eng_rr_e
read_sdc /k/constraint.sdc
set ends {}
foreach c [all_registers -cells] { set n [get_full_name $c]; if {[regexp {^u_xq\.vo_[ab]\[} $n]} { lappend ends [get_pins $n/D] } }
puts "vo endpoints [llength $ends]"
set fr {}
foreach c [all_registers -cells] { set n [get_full_name $c]; if {[regexp $::env(FROMPAT) $n]} { lappend fr [get_pins $n/CLK] } }
puts "select flop CLK pins [llength $fr]"
report_checks -path_delay max -from $fr -to $ends -fields {fanout cap slew} -digits 1
foreach p [find_timing_paths -path_delay max -from $fr -to $ends -group_path_count 2000 -endpoint_path_count 1] { lappend sl [get_property $p slack] }
set sl [lsort -real $sl]
puts "VO_SLACK n=[llength $sl] worst=[lindex $sl 0] median=[lindex $sl [expr {[llength $sl]/2}]]"

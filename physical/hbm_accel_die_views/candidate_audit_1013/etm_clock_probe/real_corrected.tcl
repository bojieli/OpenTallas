read_liberty /probe/real_tt.lib
read_verilog /probe/real.v
link_design realmini
set_cmd_units -time ns -capacitance fF
set ot_clock_missing {}
set ot_clock_bound 0
set ot_dom [dict create]
set ot_lat {}
set ot_level_clocks [dict create]
set ot_early 0
set ot_etm_corrected 0
set ot_tree [dict create {ck} {0.044167 0.045716}]
set p [get_pins -quiet {a/ck[0]}]; foreach alt {{a/ck} {a/clk} {a/ck?} {a/ck?[0]}} { if {![llength $p]} { set p [get_pins -quiet $alt] } }; if {![llength $p]} { lappend ot_clock_missing {a/ck[0]} } else { dict lappend ot_dom clk_stream $p; dict set ot_level_clocks clk_stream clk_stream; foreach pp $p { set pn [lindex [split [get_full_name $pp] /] end]; set tc {0 0}; if {[dict exists $ot_tree $pn]} { set tc [dict get $ot_tree $pn]; incr ot_etm_corrected }; lappend ot_lat [list clk_stream [expr {0.150000 + [lindex $tc 0]}] [expr {0.150000 + [lindex $tc 1]}] $pp] } }
set ot_tree [dict create {ck} {0.044167 0.045716}]
set p [get_pins -quiet {b/ck[0]}]; foreach alt {{b/ck} {b/clk} {b/ck?} {b/ck?[0]}} { if {![llength $p]} { set p [get_pins -quiet $alt] } }; if {![llength $p]} { lappend ot_clock_missing {b/ck[0]} } else { dict lappend ot_dom clk_stream__early_tap $p; dict set ot_level_clocks clk_stream__early_tap clk_stream; foreach pp $p { set pn [lindex [split [get_full_name $pp] /] end]; set tc {0 0}; if {[dict exists $ot_tree $pn]} { set tc [dict get $ot_tree $pn]; incr ot_etm_corrected }; lappend ot_lat [list clk_stream__early_tap [expr {0.150000 + [lindex $tc 0]}] [expr {0.150000 + [lindex $tc 1]}] $pp] } ; incr ot_early [llength $p] }
set ot_tree [dict create {ck} {0.044167 0.045716}]
set p [get_pins -quiet {c/ck[0]}]; foreach alt {{c/ck} {c/clk} {c/ck?} {c/ck?[0]}} { if {![llength $p]} { set p [get_pins -quiet $alt] } }; if {![llength $p]} { lappend ot_clock_missing {c/ck[0]} } else { dict lappend ot_dom clk_serial $p; dict set ot_level_clocks clk_serial clk_serial; foreach pp $p { set pn [lindex [split [get_full_name $pp] /] end]; set tc {0 0}; if {[dict exists $ot_tree $pn]} { set tc [dict get $ot_tree $pn]; incr ot_etm_corrected }; lappend ot_lat [list clk_serial [expr {0.150000 + [lindex $tc 0]}] [expr {0.150000 + [lindex $tc 1]}] $pp] } }
set ot_tree [dict create {ck} {0.044167 0.045716}]
set p [get_pins -quiet {d/ck[0]}]; foreach alt {{d/ck} {d/clk} {d/ck?} {d/ck?[0]}} { if {![llength $p]} { set p [get_pins -quiet $alt] } }; if {![llength $p]} { lappend ot_clock_missing {d/ck[0]} } else { dict lappend ot_dom clk_stream $p; dict set ot_level_clocks clk_stream clk_stream; foreach pp $p { set pn [lindex [split [get_full_name $pp] /] end]; set tc {0 0}; if {[dict exists $ot_tree $pn]} { set tc [dict get $ot_tree $pn]; incr ot_etm_corrected }; lappend ot_lat [list clk_stream [expr {0.150000 + [lindex $tc 0]}] [expr {0.150000 + [lindex $tc 1]}] $pp] } }
if {[dict exists $ot_dom clk_stream]} { create_clock -name clk_stream -period 0.833333 [dict get $ot_dom clk_stream] }
if {[dict exists $ot_dom clk_stream__early_tap]} { create_clock -name clk_stream__early_tap -period 0.833333 [dict get $ot_dom clk_stream__early_tap] }
if {[dict exists $ot_dom clk_serial]} { create_clock -name clk_serial -period 1.111111 [dict get $ot_dom clk_serial] }
if {[dict exists $ot_dom clk_serial__early_tap]} { create_clock -name clk_serial__early_tap -period 1.111111 [dict get $ot_dom clk_serial__early_tap] }
if {[dict exists $ot_dom clk_hbm]} { create_clock -name clk_hbm -period 1.024000 [dict get $ot_dom clk_hbm] }
if {[dict exists $ot_dom clk_hbm__early_tap]} { create_clock -name clk_hbm__early_tap -period 1.024000 [dict get $ot_dom clk_hbm__early_tap] }
if {[dict exists $ot_dom clk_link]} { create_clock -name clk_link -period 0.833333 [dict get $ot_dom clk_link] }
if {[dict exists $ot_dom clk_link__early_tap]} { create_clock -name clk_link__early_tap -period 0.833333 [dict get $ot_dom clk_link__early_tap] }
foreach e $ot_lat { lassign $e d early late p; set_clock_latency -source -early -clock $d $early $p; set_clock_latency -source -late -clock $d $late $p; incr ot_clock_bound }
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 0.150 [all_clocks]
set_clock_uncertainty -hold 0.025 [all_clocks]
dict for {a da} $ot_level_clocks { dict for {b db} $ot_level_clocks { if {$da eq $db && ([string match *__early_tap $a] || [string match *__early_tap $b])} { set_clock_uncertainty -setup -from [get_clocks $a] -to [get_clocks $b] 0.210 } } }
set cl [all_clocks]
dict for {a da} $ot_level_clocks { dict for {b db} $ot_level_clocks { if {$da ne $db} { set_false_path -from [get_clocks $a] -to [get_clocks $b] } } }
puts "OT_CLOCK_CONTEXT corner=tt bound=$ot_clock_bound missing=[llength $ot_clock_missing] early_tap_pins=$ot_early etm_corrected_pins=$ot_etm_corrected"
puts "OT_CLOCK_MISSING [lrange $ot_clock_missing 0 40]"
write_sdc /probe/real_corrected.sdc
report_checks -path_delay max -group_path_count 2 -format full_clock_expanded -digits 6

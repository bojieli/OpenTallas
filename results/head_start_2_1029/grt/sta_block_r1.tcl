58801:# ---- HEAD-START-2 additions: placed-body readback (LL assertion) + START reg2reg STA on the real cells, GRT RC
58802-set bb [open /out/bbox_$::env(CORNER).txt w]
58803-set dbu [[[ord::get_db_block] getTech] getDbUnitsPerMicron]
58804-foreach i [[ord::get_db_block] getInsts] { set n [$i getName]; if {[string match ck_* $n] || [string match start_* $n]} { set b [$i getBBox]; puts $bb "$n [$i getOrient] [expr {double([$b xMin])/$dbu}] [expr {double([$b yMin])/$dbu}] [expr {double([$b xMax])/$dbu}] [expr {double([$b yMax])/$dbu}]" } }
58805-close $bb
58806-catch {unset_input_delay -clock vclk [get_ports root]} e1; puts "OT_UNSET_IN $e1"
58807-catch {unset_output_delay -clock vclk [get_ports t_*]} e2; puts "OT_UNSET_OUT $e2"
58808-delete_clock [get_clocks vclk]
58809-create_clock -name dck -period 833.333 [get_ports root]
58810-set_propagated_clock [get_clocks dck]
58811-set sta_crpr_enabled 1
58812-if {$::env(CORNER) eq "TT"} {
58813-  set_clock_uncertainty -setup 60 [get_clocks dck]
58814-  set_clock_uncertainty -hold 25 [get_clocks dck]
58815-  set_timing_derate -late -data -cell_delay 1.10
58816-  set_timing_derate -late -data -net_delay 1.05
58817-} else {
58818-  set_clock_uncertainty -setup 60 [get_clocks dck]
58819-  set_clock_uncertainty -hold 25 [get_clocks dck]
58820-}
58821-set ff [all_registers -edge_triggered]
58822-puts "OT_STA regs [llength $ff]"
58823-set eh [open /out/endpoint_slack_$::env(CORNER).txt w]
58824-foreach p [get_pins -of_objects $ff -filter "direction==input"] {
58825-  set n [get_full_name $p]
58826-  if {![string match */D $n]} {continue}
58827-  puts $eh "$n [get_property $p slack_max] [get_property $p slack_min]"
58828-}
58829-close $eh
58830-report_checks -path_delay max -group_path_count 10 -format full_clock_expanded -fields {slew cap input_pins} -digits 2 > /out/setup_$::env(CORNER).rpt
58831-report_checks -path_delay min -group_path_count 10 -format full_clock_expanded -fields {slew cap input_pins} -digits 2 > /out/hold_$::env(CORNER).rpt
58832-report_worst_slack -max
58833-report_worst_slack -min
58834-report_tns
58835-write_db /out/combo_$::env(CORNER).odb
58836-puts OT_DONE

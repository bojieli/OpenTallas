# Read-only diagnostic on a real W5 checkpoint; no constraint changes.
set_units -time ps -capacitance fF
set_propagated_clock [all_clocks]
report_units
report_clock_properties [all_clocks]
report_clock_latency -include_internal_latency -digits 6
report_clock_skew -setup -digits 6
report_clock_skew -hold -digits 6
check_setup -verbose
report_checks -unconstrained -path_delay min_max -format full_clock_expanded -digits 6
proc w5_class {n} {
 set n [string map {\\ ""} $n]
 if {[string match u_return* $n]} {
  if {[regexp {by_t|u_dt} $n]} {return return_tag}
  if {[regexp {[/\.](at|bt)\[} $n]} {return return_tag_queue}
  if {[regexp {u_add} $n]} {return return_adder}
  if {[regexp {[/\.](ad|bd)\[|by_d|u_fd} $n]} {return return_payload}
  return return_control
 }
 if {[string match u_bst* $n]} {return BST_capture}
 if {[regexp {^u_(settings|go_source)} $n]} {return source_checked_state}
 if {[string match u_ld* $n]} {return loader}
 if {[string match u_stage.u_ao* $n]} {
  if {[regexp {qualify|sticky|fault_spine|u_freeze} $n]} {return AO_quarantine}
  if {[regexp {g_sh|sh_clk} $n]} {return AO_retained_shadow}
  if {[regexp {u_sched|u_ctl} $n]} {return AO_scheduler_controller}
  return AO_replay_CDC
 }
 if {[string match u_stage.g_el* $n]} {
  if {[regexp {g_ir|r_xs|u_dif} $n]} {return domain_ingress_DIF}
  if {[regexp {g_mac} $n]} {return domain_MAC}
  return domain_control_result
 }
 return enclosing_IO
}
set rows [open $::so_out/endpoints.tsv w]
puts $rows "class\tmode\tendpoint\tslack_ps\tunconstrained\tstartpoint_count"
set clocks [open $::so_out/clock_terminals.tsv w]
puts $clocks "pin\tclocks"
foreach p [all_registers -clock_pins] {
 puts $clocks "[get_full_name $p]\t[join [lmap c [get_property $p clocks] {get_full_name $c}] ,]"
}
close $clocks
set ends [lsort -unique [concat [sta::endpoints] [all_registers -data_pins] [all_registers -async_pins] [all_outputs]]]
set worst [dict create]
foreach e $ends {
 set n [get_full_name $e];set class [w5_class $n]
 foreach mode {max min} {
  set paths [find_timing_paths -to $e -path_delay $mode -endpoint_path_count 1]
  if {![llength $paths]} {
   set starts [get_fanin -to $e -flat -startpoints_only -trace_arcs timing]
   puts $rows "$class\t$mode\t$n\tInf\t1\t[llength $starts]"
   continue
  }
  set slack Inf;set unconstrained 0
  foreach path $paths {
   if {[$path is_unconstrained]} {set unconstrained 1;continue}
   set s [get_property $path slack]
   if {$s<$slack} {set slack $s}
  }
  puts $rows "$class\t$mode\t$n\t$slack\t$unconstrained\t-1"
  set key "$class.$mode"
  if {$slack ne "Inf" && (![dict exists $worst $key] || $slack<[lindex [dict get $worst $key] 0])} {
   dict set worst $key [list $slack $e]
  }
 }
}
close $rows
dict for {key value} $worst {
 set p [lindex $value 1]
 puts "W5_CLASS_WORST $key [lindex $value 0] [get_full_name $p]"
 report_checks -to $p -path_delay [lindex [split $key .] end] -format full_clock_expanded -digits 6 -fields {slew cap input net fanout} > $::so_out/$key.rpt
}
set gates [open $::so_out/gate_macro_terminals.tsv w]
puts $gates "cell\tref\tpin\tclocks"
foreach c [get_cells -hierarchical *] {
 set ref [get_property $c ref_name]
 if {$ref ni {ICGx1_ASAP7_75t_R ot_rom_4096x274_m8 DLLx1_ASAP7_75t_R}} {continue}
 set n [get_full_name $c]
 foreach p [get_pins -of_objects $c] {
  puts $gates "$n\t$ref\t[get_full_name $p]\t[join [lmap clock [get_property $p clocks] {get_full_name $clock}] ,]"
 }
 report_checks -to $c -path_delay min_max -format full_clock_expanded -digits 6 -fields {slew cap input net fanout} > $::so_out/terminal_[string map {/ _ \\ _} $n].rpt
 if {$ref eq "ot_rom_4096x274_m8"} {
  report_checks -from $c -path_delay min_max -format full_clock_expanded -digits 6 -fields {slew cap input net fanout} > $::so_out/macro_[string map {/ _ \\ _} $n].rpt
 }
}
close $gates
report_check_types -recovery -removal -verbose -digits 6
report_check_types -max_slew -max_capacitance -max_fanout -violators -verbose -digits 6
puts W5_ENDPOINT_AUDIT_COMPLETE

set ::so_libs {{/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_DFFHQNH2V2X_RVT_SS_nldm_FAKE.lib} {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_DFFHQNV2X_RVT_SS_nldm_FAKE.lib} {/so_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_ss.lib}}
set ::so_odb /so_res/4_cts.odb
set ::so_sdc /so_res/4_cts.sdc
set ::so_spef {}
set ::so_platform /OpenROAD-flow-scripts/flow/platforms/asap7
set ::so_pdn_tcl {}
set ::so_saif {}
set ::so_saif_scope {}
set ::so_groups {}
set ::so_inst_power {}
set ::so_derate 0.0
set ::so_vdd 0.63
set ::so_bump_pitch 140
set ::so_bump_size 50
set ::so_out /so_out/SS
file mkdir /so_out/SS

proc emit {key value} { puts "SIGNOFF $key=$value" }
proc sum_list {l} { set s 0.0; foreach x $l { set s [expr {$s + $x}] }; return $s }


read_db $::so_odb
if {$::so_pdn_tcl ne ""} {
    # a PDN variant: rip the route's grid up and build the variant's (before any
    # Liberty is read: pdngen then sees only the LEF masters)
    pdngen -ripup
    source $::so_pdn_tcl
    pdngen
}
foreach lib $::so_libs { read_liberty $lib }
read_sdc $::so_sdc
if {$::so_spef ne ""} {
    read_spef $::so_spef
} else {
    # pre-route stage (e.g. 4_cts.odb): placement-estimated wire parasitics
    source $::so_platform/setRC.tcl
    estimate_parasitics -placement
}
set_cmd_units -time ns -power W

emit corner.name SS

set_thread_count 4
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

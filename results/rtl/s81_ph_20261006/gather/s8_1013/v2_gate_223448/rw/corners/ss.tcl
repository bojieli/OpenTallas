set ::env(OT_GATE_SIGNOFF_SDC) /src/physical/ref_tile/dsfd_gth_rw/signoff.sdc
# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain $plat/lib/NLDM/*RVT_SS*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    set w [string map {_tt.lib _ss.lib} $w]
    if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }
  }
}
read_db $base/4_1_cts.odb
if {[file exists $base/4_cts.sdc]} { read_sdc $base/4_cts.sdc } else { read_sdc $base/3_place.sdc }
set_propagated_clock [all_clocks]
source $plat/setRC.tcl
estimate_parasitics -placement
# Classify the same die-context boundary constraints as signoff, after RC is
# available. The saved CTS SDC alone can restore plain, primary-clock IO budgets.
if {[info exists ::env(OT_GATE_SIGNOFF_SDC)]} {
  set ot_pc_sdc $::env(OT_GATE_SIGNOFF_SDC)
  if {![file isfile $ot_pc_sdc]} { error "GATE_PC: missing signoff SDC $ot_pc_sdc" }
  set ::ot_ce_corner ss
  read_sdc $ot_pc_sdc
  puts "GATE_PC constraints signoff $ot_pc_sdc (TT placement RC; diagnostic)"
} else {
  puts "GATE_PC constraints saved CTS SDC (diagnostic; no signoff boundary replay)"
}
proc kind {pin end} {
  if {[llength [get_ports -quiet [get_full_name $pin]]]} { return [expr {$end ? "out" : "in"}] }
  set c [get_cells -quiet -of_objects $pin]
  if {[llength $c] && [get_property [get_lib_cells -of_objects $c] is_memory] == 1} { return macro }
  if {[llength $c] && [regexp {^ot_|sram|rom} [get_property $c ref_name]]} { return macro }
  return reg
}
set cls [dict create]
foreach p [find_timing_paths -path_delay max -group_path_count 300 -endpoint_path_count 1 -sort_by_slack] {
  set s [get_property $p slack]
  set k "[kind [get_property $p startpoint] 0]->[kind [get_property $p endpoint] 1]"
  if {![dict exists $cls $k]} { dict set cls $k [list 0 $s [get_full_name [get_property $p endpoint]]] }
  lassign [dict get $cls $k] n w e
  dict set cls $k [list [incr n] [expr {min($w, $s)}] $e]
}
dict for {k v} $cls { lassign $v n w e; puts [format "GATE_PC %-12s %4d paths, worst slack %.1f ps (e.g. %s)" $k $n $w $e] }
puts "GATE_PC setup WNS [sta::worst_slack_cmd max] hold WNS [sta::worst_slack_cmd min]"

puts "S81_ACTUAL_CORNER ss fixedCTS placementRC signoff833.333 uncertainty60/25"
report_clock_properties [all_clocks]
check_setup -verbose
report_check_types -max_slew -max_capacitance -max_fanout -violators
report_checks -path_delay max -group_path_count 30 -format full_clock_expanded -fields {slew cap fanout}
report_checks -path_delay min -group_path_count 30 -format full_clock_expanded -fields {slew cap fanout}
exit

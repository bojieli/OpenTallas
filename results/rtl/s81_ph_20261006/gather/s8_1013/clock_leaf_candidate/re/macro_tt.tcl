set ::env(OT_GATE_SIGNOFF_SDC) /src/physical/ref_tile/dsfd_gth_re/signoff.sdc
# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain $plat/lib/NLDM/*RVT_TT*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    set w [string map {_tt.lib _tt.lib} $w]
    if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }
  }
}
read_db /probe/clock_candidate.odb
if {[file exists $base/4_cts.sdc]} { read_sdc $base/4_cts.sdc } else { read_sdc $base/3_place.sdc }
set_propagated_clock [all_clocks]
source $plat/setRC.tcl
estimate_parasitics -placement
# Classify the same die-context boundary constraints as signoff, after RC is
# available. The saved CTS SDC alone can restore plain, primary-clock IO budgets.
if {[info exists ::env(OT_GATE_SIGNOFF_SDC)]} {
  set ot_pc_sdc $::env(OT_GATE_SIGNOFF_SDC)
  if {![file isfile $ot_pc_sdc]} { error "GATE_PC: missing signoff SDC $ot_pc_sdc" }
  set ::ot_ce_corner tt
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

puts "S81_ACTUAL_CORNER tt fixedCTS placementRC signoff833.333 uncertainty60/25"
report_clock_properties [all_clocks]
check_setup -verbose
report_check_types -max_slew -max_capacitance -max_fanout -violators


set ::ot_ck_act [dict create]
proc ot_ck_active {p} {
  set c [get_cells -quiet -of_objects $p]
  if {![llength $c]} { return "" }
  set k "[get_property $c ref_name]/[get_property $p lib_pin_name]"
  if {[dict exists $::ot_ck_act $k]} { return [dict get $::ot_ck_act $k] }
  sta::redirect_string_begin
  catch {report_edges -from $p}
  set r [sta::redirect_string_end]
  set on 0; set fr {}
  foreach l [split $r "\n"] {
    if {[regexp {^\S} $l]} { set on [regexp {(Clk|En) to Q} $l]; continue }
    if {$on && [regexp {^\s+([\^v])\s+->} $l -> e]} { if {[lsearch -exact $fr $e] < 0} { lappend fr $e } }
  }
  set a [expr {[llength $fr] == 1 ? ([lindex $fr 0] eq "^" ? "r" : "f") : ""}]
  dict set ::ot_ck_act $k $a
  return $a
}
proc ot_ck_arr {p clk} {
  set half 0.0
  if {![catch {list [$clk waveform] [$clk period] [get_property $clk period]} w]} {
    lassign $w wf ps pu
    if {[llength $wf] >= 2 && $ps > 0} { set half [expr {([lindex $wf 1] - [lindex $wf 0]) * $pu / $ps}] } }
  set ar [get_property $p arrival_max_rise]; set af [get_property $p arrival_max_fall]
  set okr [string is double -strict $ar]; set okf [string is double -strict $af]
  if {!($okr && $okf)} { return [expr {$okr ? $ar : ($okf ? $af : "")}] }
  set t [ot_ck_active $p]
  set lo [expr {$ar <= $af ? "r" : "f"}]
  if {$t eq ""} { set t $lo }
  set v [expr {$t eq "r" ? $ar : $af}]
  return [expr {$t eq $lo ? $v : $v - $half}]
}

set clk [lindex [get_clocks core_clk] 0]
foreach p [all_registers -clock_pins -clock $clk] {puts "OT_CK 1 [ot_ck_arr $p $clk]"}
foreach inst [[ord::get_db_block] getInsts] {
 if {![[$inst getMaster] isBlock]} continue
 set it [$inst findITerm clk];if {$it eq "NULL"} continue
 set p [get_pins "[$inst getName]/clk"]
 puts "OT_MC [get_full_name $p] [ot_ck_arr $p $clk] [get_property $p slew_max_rise] [[$it getNet] getName]"
}
puts "OLD_SOURCE_PLUS_NEW_CLOCK_LEAF_READ_ONLY_DIAGNOSTIC_NO_ADOPTION"
exit

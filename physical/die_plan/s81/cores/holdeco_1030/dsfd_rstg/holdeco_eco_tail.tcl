# ===== DIE-S81-36/HOLDECO: one-block FF hold ECO (owner 12.19: measured arrivals + 10 ps margin) =====
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set TGT [expr {[info exists ::env(OT_TGT)] ? $::env(OT_TGT) : 10.0}]
set CELL [expr {[info exists ::env(OT_CELL)] ? $::env(OT_CELL) : "HB1xp67_ASAP7_75t_R"}]
set blk [ord::get_db_block]
proc wsig {n} { set w [$n getWire]; if {$w eq "NULL"} { return "-" }; return [$w getLength][$w getId] }
# snapshot: inst locations + net wire signatures
set loc0 {}; foreach i [$blk getInsts] { dict set loc0 [$i getName] [$i getLocation] }
set ws0 {}; foreach n [$blk getNets] { if {[$n getSigType] in {POWER GROUND}} continue; set w [$n getWire]; dict set ws0 [$n getName] [expr {$w eq "NULL" ? "-" : "[$w getLength]/[$w length]"}] }
proc viols {tgt} {
  set r {}
  foreach p [find_timing_paths -path_delay min -group_path_count 1000 -endpoint_path_count 1 -slack_max $tgt -sort_by_slack] {
    lappend r [list [get_property $p slack] [get_full_name [get_property $p endpoint]]]
  }
  return $r
}
set v0 [viols $TGT]
puts "ECO PRE n_below_tgt [llength $v0] worst [lindex [lindex $v0 0] 0]"
set added {}; set k 0
for {set pass 0} {$pass < 6} {incr pass} {
  set v [viols $TGT]
  if {![llength $v]} break
  puts "ECO PASS $pass below [llength $v] worst [lindex [lindex $v 0] 0]"
  foreach e $v {
    lassign $e sl pin
    set pt [get_pins $pin]
    set net [get_nets -of_objects $pt]
    set inst [sta::sta_to_db_inst [get_cells -of_objects $pt]]
    set xy [$inst getLocation]
    set nm "hxeco_$k"; incr k
    insert_buffer -buffer_cell $CELL -net [get_full_name $net] -load_pins [list $pt] -location [list [expr {[lindex $xy 0]/1000.0}] [expr {[lindex $xy 1]/1000.0}]] -buffer_name $nm -net_name ${nm}_n
    lappend added $nm
  }
}
set v1 [viols $TGT]
puts "ECO ADDED [llength $added] still_below [llength $v1] worst_after [expr {[llength $v1] ? [lindex [lindex $v1 0] 0] : "none"}] (no parasitics on new nets yet)"
remove_fillers
set nlock 0
foreach i [$blk getInsts] { if {[dict exists $loc0 [$i getName]] && [$i getPlacementStatus] ni {LOCKED FIRM COVER}} { $i setPlacementStatus FIRM; incr nlock } }
puts "ECO FIRM_EXISTING $nlock"
detailed_placement
check_placement -verbose
# moved insts
set moved {}; set movedo {}; set newo {}; set newn {}
foreach i [$blk getInsts] {
  set n [$i getName]
  if {[dict exists $loc0 $n] && [dict get $loc0 $n] ne [$i getLocation]} { lappend moved $n; lappend movedo $i }
  if {![dict exists $loc0 $n]} { lappend newo $i; lappend newn $n }
}
puts "ECO MOVED [llength $moved] [lrange $moved 0 20]"
# dirty nets = nets on added or moved insts
set dirty {}
puts "ECO NEW_INSTS [llength $newo] [lrange $newn 0 5]"
foreach i [concat $newo $movedo] {
  foreach it [$i getITerms] { set nt [$it getNet]; if {$nt ne "NULL" && [$nt getSigType] ni {POWER GROUND}} { dict set dirty [$nt getName] 1 } }
}
puts "ECO DIRTY_NETS [dict size $dirty]"
foreach n [dict keys $dirty] { set nt [$blk findNet $n]; set w [$nt getWire]; if {$w ne "NULL"} { odb::dbWire_destroy $w } }
set_routing_layers -signal M2-M7 -clock M4-M7
set ndt 0
foreach n [$blk getNets] {
  if {[$n getSigType] in {POWER GROUND}} continue
  if {[dict exists $dirty [$n getName]]} continue
  if {[$n getWire] ne "NULL"} { $n setDoNotTouch 1; incr ndt }
}
puts "ECO DONT_TOUCH_NETS $ndt"
global_route -allow_congestion
detailed_route -output_drc /out/eco_drc.rpt -verbose 1
filler_placement {FILLERxp5_ASAP7_75t_R FILLER_ASAP7_75t_R DECAPx1_ASAP7_75t_R DECAPx2_ASAP7_75t_R DECAPx4_ASAP7_75t_R DECAPx6_ASAP7_75t_R DECAPx10_ASAP7_75t_R}
check_placement -verbose
# untouched nets keep their wires?
set same 0; set chg 0; set chg_names {}
foreach n [$blk getNets] {
  if {[$n getSigType] in {POWER GROUND}} continue
  set nm [$n getName]
  if {[dict exists $dirty $nm] || ![dict exists $ws0 $nm]} continue
  set w [$n getWire]; set s [expr {$w eq "NULL" ? "-" : "[$w getLength]/[$w length]"}]
  if {$s eq [dict get $ws0 $nm]} { incr same } else { incr chg; if {[llength $chg_names] < 10} { lappend chg_names $nm } }
}
puts "ECO UNTOUCHED_NETS same $same changed $chg $chg_names"
write_db /out/6_final.odb
set phys {}; foreach m [[[ord::get_db] getLibs] getMasters] {}; foreach i [$blk getInsts] { set mn [[$i getMaster] getName]; if {[string match TAPCELL* $mn] || [string match FILLER* $mn] || [string match DECAP* $mn]} { dict set phys $mn 1 } }
puts "ECO PHYS_ONLY [dict keys $phys]"
write_verilog -remove_cells [dict keys $phys] /out/6_final.v
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file $P/rcx_patterns.rules
write_spef /out/6_final.spef
puts "ECO DONE"
exit

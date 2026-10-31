# ===== S81-CORES-KITS-7 attn_hcore rt22m near-miss ECO (form = DIE-S81-36/HOLDECO, owner 12.19 measured arrivals + 10 ps margin) =====
# + TT slew repeaters on 3 long W-column nets + 4 setup-cone upsizes; hold buffers at the load pin xy
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set TGT [expr {[info exists ::env(OT_TGT)] ? $::env(OT_TGT) : 10.0}]
set CELL [expr {[info exists ::env(OT_CELL)] ? $::env(OT_CELL) : "HB1xp67_ASAP7_75t_R"}]
set blk [ord::get_db_block]
set ndt0 0; foreach n [$blk getNets] { if {[$n isDoNotTouch]} { $n setDoNotTouch 0; incr ndt0 } }; puts "ECO CLEARED_DT_IN $ndt0"
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
set resized {}
set rk 0
proc ib {net loads x y} {
  global rk; set nm "rpeco_$rk"; incr rk
  insert_buffer -buffer_cell BUFx4f_ASAP7_75t_R -net $net -load_pins [get_pins $loads] -location [list $x $y] -buffer_name $nm -net_name ${nm}_n
  set b [lindex [get_cells ${nm}*] 0]; set bn [get_full_name $b]
  puts "ECO REPEATER $bn net $net at ($x,$y) loads [llength $loads]"
  return $bn
}
# TT slew: long vertical nets on the W column (x~6), BUFx3 drivers at y~207, loads down to y~35
set a [ib net6064 {_233049_/A2 _234935_/A1 _238706_/A1 _236840_/A1 _234473_/A1} 6 55]
set b [ib net6064 [list _238245_/A1 _235428_/A1 _237324_/A1 $a/A] 6 97]
ib net6064 [list $b/A] 6 145
set a [ib net6059 {_233079_/A2 _234965_/A1 _236872_/A1 _238736_/A1 _234510_/A1 _235458_/A1} 6 55]
set b [ib net6059 [list _238282_/A1 _237358_/A1 _239447_/A1 $a/A] 6 105]
ib net6059 [list $b/A] 6 150
set a [ib _016591_ {_139379_/D _225325_/A _270976_/D} 8 110]
ib _016591_ [list $a/A] 7 60
# TT setup near-miss (-14.85, cone y[29] -> u_k1 r[*]): upsize the weak high-fanout stages
foreach {inm m} {fanout7220 BUFx6f_ASAP7_75t_R fanout7219 BUFx6f_ASAP7_75t_R _202700_ AO221x2_ASAP7_75t_R place5351 BUFx6f_ASAP7_75t_R} {
  set c [get_cells $inm]; puts "ECO RESIZE $inm [get_property $c ref_name] -> $m"
  replace_cell $c $m; lappend resized [$blk findInst $inm]
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
    set it [$inst findITerm [get_property $pt lib_pin_name]]
    set axy [$it getAvgXY]
    if {[lindex $axy 0]} { set xy [lrange $axy 1 2] } else { set xy [$inst getLocation] }
    set nm "hxeco_$k"; incr k
    insert_buffer -buffer_cell $CELL -net [get_full_name $net] -load_pins [list $pt] -location [list [expr {[lindex $xy 0]/1000.0}] [expr {[lindex $xy 1]/1000.0}]] -buffer_name $nm -net_name ${nm}_n
    lappend added $nm
  }
}
set v1 [viols $TGT]
puts "ECO ADDED [llength $added] still_below [llength $v1] worst_after [expr {[llength $v1] ? [lindex [lindex $v1 0] 0] : "none"}] (no parasitics on new nets yet)"
remove_fillers
set nlock 0
set rsn [lmap r $resized {$r getName}]
foreach i [$blk getInsts] { if {[dict exists $loc0 [$i getName]] && [$i getName] ni $rsn && [$i getPlacementStatus] ni {LOCKED FIRM COVER}} { $i setPlacementStatus FIRM; incr nlock } }
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
foreach i [concat $newo $movedo $resized] {
  foreach it [$i getITerms] { set nt [$it getNet]; if {$nt ne "NULL" && [$nt getSigType] ni {POWER GROUND}} { dict set dirty [$nt getName] 1 } }
}
puts "ECO DIRTY_NETS [dict size $dirty]"
foreach n [dict keys $dirty] { set nt [$blk findNet $n]; set w [$nt getWire]; if {$w ne "NULL"} { odb::dbWire_destroy $w } }
set_routing_layers -signal M2-M5 -clock M2-M5
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
foreach n [$blk getNets] { $n setDoNotTouch 0 }
write_db /out/6_final.odb
puts "ECO DONE"
exit

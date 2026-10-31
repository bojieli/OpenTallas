# ===== S81-CORES-KITS-7 vq ECO-2 on the hx DB: long-wire slew repeaters (BUFx4f chains) on 3 nets only; 0 existing cells moved =====
# targets: net2910 (place2911 -> 8 OA21 A1, ~80 um), _08676_ / _08668_ (DFFHQNx1 QN -> sxeco_0/1, ~120 um)
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set TGT [expr {[info exists ::env(OT_TGT)] ? $::env(OT_TGT) : 10.0}]
set CELL [expr {[info exists ::env(OT_CELL)] ? $::env(OT_CELL) : "HB1xp67_ASAP7_75t_R"}]
set blk [ord::get_db_block]
proc wsig {n} { set w [$n getWire]; if {$w eq "NULL"} { return "-" }; return [$w getLength][$w getId] }
# snapshot: inst locations + net wire signatures
set loc0 {}; foreach i [$blk getInsts] { dict set loc0 [$i getName] [$i getLocation] }
set ws0 {}; foreach n [$blk getNets] { if {[$n getSigType] in {POWER GROUND}} continue; set w [$n getWire]; dict set ws0 [$n getName] [expr {$w eq "NULL" ? "-" : "[$w getLength]/[$w length]"}] }
set rk 0
proc ib {net loads x y} {
  global rk; set nm "rpeco_$rk"; incr rk
  insert_buffer -buffer_cell BUFx4f_ASAP7_75t_R -net $net -load_pins [get_pins $loads] -location [list $x $y] -buffer_name $nm -net_name ${nm}_n
  set b [lindex [get_cells ${nm}*] 0]; set bn [get_full_name $b]
  puts "ECO REPEATER $bn net $net at ($x,$y) loads [llength $loads]"
  return $bn
}
# net2910: place2911 (47,36) -> 8 OA21 A1 (x 22..103, y 95..120)
set l2 [ib net2910 {_62870_/A1 _63496_/A1 _64062_/A1} 30 113]
set r2 [ib net2910 {_63213_/A1 _63779_/A1 _64345_/A1 _64628_/A1 _64911_/A1} 95 108]
ib net2910 [list $l2/A $r2/A] 55 72
# _08676_: u_c[70] QN (170,38) -> sxeco_0 (49,37); _08668_: u_c[78] QN -> sxeco_1
foreach {net ld} {_08676_ sxeco_09141/A _08668_ sxeco_19142/A} {
  set d [get_pins -of_objects [get_nets $net] -filter direction==output]
  set dc [sta::sta_to_db_inst [get_cells -of_objects $d]]; set dxy [$dc getLocation]; set dx [expr {[lindex $dxy 0]/1000.0}]; set dy [expr {[lindex $dxy 1]/1000.0}]
  set lc [sta::sta_to_db_inst [get_cells -of_objects [get_pins $ld]]]; set lxy [$lc getLocation]; set lx [expr {[lindex $lxy 0]/1000.0}]; set ly [expr {[lindex $lxy 1]/1000.0}]
  puts "ECO CHAIN $net drv ($dx,$dy) load ($lx,$ly)"
  set cur $ld
  foreach f {0.05 0.40 0.70} {
    set cur [ib $net [list $cur] [expr {$lx+($dx-$lx)*$f}] [expr {$ly+($dy-$ly)*$f}]]/A
  }
}
set resized {}
set added {}; foreach i [$blk getInsts] { if {![dict exists $loc0 [$i getName]]} { lappend added [$i getName] } }
puts "ECO ADDED [llength $added] $added"
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
write_db /out/6_final.odb
puts "ECO DONE"
exit

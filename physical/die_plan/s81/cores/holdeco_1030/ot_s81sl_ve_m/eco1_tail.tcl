# ===== S81-CORES-KITS-7 generic long-wire slew ECO (BUFx4f chains on the sign-off TT/FF slew violator nets only); 0 existing cells moved =====
# set ::SLEWPINS before sourcing
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set TGT [expr {[info exists ::env(OT_TGT)] ? $::env(OT_TGT) : 10.0}]
set CELL [expr {[info exists ::env(OT_CELL)] ? $::env(OT_CELL) : "HB1xp67_ASAP7_75t_R"}]
set blk [ord::get_db_block]
set ndt0 0; foreach n [$blk getNets] { if {[$n isDoNotTouch]} { $n setDoNotTouch 0; incr ndt0 } }; puts "ECO CLEARED_DT_IN $ndt0"
proc wsig {n} { set w [$n getWire]; if {$w eq "NULL"} { return "-" }; return [$w getLength][$w getId] }
# snapshot: inst locations + net wire signatures
set loc0 {}; foreach i [$blk getInsts] { dict set loc0 [$i getName] [$i getLocation] }
set ws0 {}; foreach n [$blk getNets] { if {[$n getSigType] in {POWER GROUND}} continue; set w [$n getWire]; dict set ws0 [$n getName] [expr {$w eq "NULL" ? "-" : "[$w getLength]/[$w length]"}] }
set rk 0
set RB BUFx4f_ASAP7_75t_R
proc ib {net loads x y} {
  global rk; set nm "slweco_$rk"; incr rk
  insert_buffer -buffer_cell $::RB -net $net -load_pins [get_pins $loads] -location [list $x $y] -buffer_name $nm -net_name ${nm}_n
  set b [lindex [get_cells ${nm}*] 0]; set bn [get_full_name $b]
  puts "ECO REPEATER $bn net $net at ([format %.1f $x],[format %.1f $y]) loads [llength $loads]"
  return $bn
}
proc pxy {p} { set c [sta::sta_to_db_inst [get_cells -of_objects [get_pins $p]]]; set l [$c getLocation]; return [list [expr {[lindex $l 0]/1000.0}] [expr {[lindex $l 1]/1000.0}]] }
# generic long-wire slew fix: per violating net, a BUFx4f chain (~40 um segments) from the driver to the violating loads' centroid
set bynet {}
foreach p $::SLEWPINS { set n [get_full_name [get_nets -of_objects [get_pins $p]]]; dict lappend bynet $n $p }
dict for {net vl} $bynet {
  set d [get_pins -of_objects [get_nets $net] -filter direction==output]
  lassign [pxy [get_full_name $d]] dx dy
  set cx 0; set cy 0; foreach p $vl { lassign [pxy $p] x y; set cx [expr {$cx+$x}]; set cy [expr {$cy+$y}] }
  set cx [expr {$cx/[llength $vl]}]; set cy [expr {$cy/[llength $vl]}]
  set dist [expr {abs($dx-$cx)+abs($dy-$cy)}]
  set nrep [expr {max(1, int(ceil($dist/40.0))-1)}]
  puts "ECO SLEWNET $net drv [get_full_name $d] ([format %.1f $dx],[format %.1f $dy]) vloads [llength $vl] centroid ([format %.1f $cx],[format %.1f $cy]) dist [format %.1f $dist] reps $nrep"
  set cur $vl
  for {set k 0} {$k < $nrep} {incr k} {
    set f [expr {double($k+1)/($nrep+1)}]
    set b [ib $net $cur [expr {$cx+($dx-$cx)*$f}] [expr {$cy+($dy-$cy)*$f}]]
    set cur [list $b/A]
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
foreach n [$blk getNets] { $n setDoNotTouch 0 }
write_db /out/6_final.odb
puts "ECO DONE"
exit

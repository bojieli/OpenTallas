# ===== S81-CORES-KITS-7 setup near-miss ECO: upsize weak fanout buffers on TT setup paths (TT sign-off session); resized cells only legalised =====
# 
set P /OpenROAD-flow-scripts/flow/platforms/asap7
set TGT [expr {[info exists ::env(OT_TGT)] ? $::env(OT_TGT) : 10.0}]
set CELL [expr {[info exists ::env(OT_CELL)] ? $::env(OT_CELL) : "HB1xp67_ASAP7_75t_R"}]
set blk [ord::get_db_block]
set ndt0 0; foreach n [$blk getNets] { if {[$n isDoNotTouch]} { $n setDoNotTouch 0; incr ndt0 } }; puts "ECO CLEARED_DT_IN $ndt0"
proc wsig {n} { set w [$n getWire]; if {$w eq "NULL"} { return "-" }; return [$w getLength][$w getId] }
# snapshot: inst locations + net wire signatures
set loc0 {}; foreach i [$blk getInsts] { dict set loc0 [$i getName] [$i getLocation] }
set ws0 {}; foreach n [$blk getNets] { if {[$n getSigType] in {POWER GROUND}} continue; set w [$n getWire]; dict set ws0 [$n getName] [expr {$w eq "NULL" ? "-" : "[$w getLength]/[$w length]"}] }
# setup near-miss: upsize weak buffers (BUFx2/BUFx3/BUFx4/BUFx4f, fanout >= 6) on TT setup paths with slack < SLK
set SLK 8.0
set resized_names {}
for {set pass 0} {$pass < 3} {incr pass} {
  set ends [find_timing_paths -path_delay max -group_path_count 400 -endpoint_path_count 1 -slack_max $SLK -sort_by_slack]
  puts "ECO SETUP PASS $pass paths [llength $ends] worst [expr {[llength $ends] ? [get_property [lindex $ends 0] slack] : "none"}]"
  if {![llength $ends]} break
  set cand {}
  foreach pe $ends {
    foreach pt [get_property $pe points] {
      set p [get_property $pt pin]
      if {[get_property $p direction] ne "output"} continue
      set c [get_cells -of_objects $p]; set m [get_property $c ref_name]
      if {![regexp {^BUFx(2|3|4|4f)_ASAP7_75t_R$} $m]} continue
      if {[string match ot_rt_* [get_full_name $c]] || [string match clkbuf* [get_full_name $c]]} continue
      set fo [llength [get_pins -of_objects [get_nets -of_objects $p] -filter direction==input]]
      if {$fo < 6} continue
      dict set cand [get_full_name $c] $m
    }
  }
  set n 0
  dict for {cn m} $cand { if {$cn in $resized_names} continue; replace_cell [get_cells $cn] BUFx6f_ASAP7_75t_R; lappend resized_names $cn; incr n; puts "ECO RESIZE $cn $m -> BUFx6f" }
  if {!$n} break
}
set resized {}; foreach cn $resized_names { set ri [$blk findInst $cn]; $ri setPlacementStatus PLACED; lappend resized $ri }
set ends [find_timing_paths -path_delay max -group_path_count 400 -endpoint_path_count 1 -slack_max 0 -sort_by_slack]
puts "ECO SETUP AFTER viol [llength $ends] (SPEF of resized nets unchanged; sign-off re-extracts)"
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

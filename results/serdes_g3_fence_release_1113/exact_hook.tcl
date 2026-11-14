read_db /work/run/results/asap7/dp_serdes__t2/base/3_5_place_dp-failed.odb
set b [ord::get_db_block]
set gs {}; set clocks {}; set ng 0
foreach i [$b getInsts] { foreach t [$i getITerms] { if {[[$t getMTerm] getSigType] eq "CLOCK"} { dict set clocks [list [$i getName] [[$t getMTerm] getName]] [[$t getNet] getName] } } }
foreach r [$b getRegions] {
 if {![string match sl_* [$r getName]]} continue
 set boxes {};foreach bx [$r getBoundaries] { lappend boxes [list [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]] }
 set names {}
 foreach g [$r getGroups] { foreach i [$g getInsts] {lappend names [$i getName]} }
 dict set gs [$r getName] [list $boxes $names]
 incr ng
}
if {$ng != 6} {error "expected exactly6 sl_ fences, got$ng"}
puts "FENCE_FIXTURE removed exactly $ng groups; clocks [dict size $clocks]"
set ::env(RESULTS_DIR) /diag
set sl_cfg [dict create release_regions_before_dpl 1]
source /release.tcl
detailed_placement
set code [catch {check_placement -verbose} why]
puts "FENCE_FIXTURE check_placement_rc $code detail $why"
set clkbad 0
dict for {key net} $clocks { lassign $key name pin;set i [$b findInst $name];if {$i eq "NULL" || [[[$i findITerm $pin] getNet] getName] ne $net} {incr clkbad} }
puts "FENCE_FIXTURE clock_net_changes $clkbad"
set f [open /diag/group_locality.tsv w]
puts $f "group\tmembers\toutside_original\tmax_excursion_dbu"
dict for {name item} $gs {
 lassign $item boxes names;set out 0;set maxd 0
 foreach nm $names {
  set i [$b findInst $nm];set bb [$i getBBox];set best 99999999
  foreach box $boxes {lassign $box x0 y0 x1 y1;set d [expr {max(0,$x0-[$bb xMin],[$bb xMax]-$x1,$y0-[$bb yMin],[$bb yMax]-$y1)}];set best [expr {min($best,$d)}]}
  if {$best>0} {incr out};set maxd [expr {max($maxd,$best)}]
 }
 puts $f "$name\t[llength $names]\t$out\t$maxd"
}
close $f
write_db /diag/legalized.odb
if {$code || $clkbad} {error "fixture physical checks failed"}

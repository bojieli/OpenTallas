# Local reset consumers only: small legal-row control bands, no exclusive regions.
# Six same-edge reset copies replace one global driver. See local source miter.
global lc_b lc_u lc_used lc_done lc_log
set lc_b [ord::get_db_block]
set lc_u [$lc_b getDbUnitsPerMicron]
proc lc_seq {i} {regexp -nocase {DFF|SDFF|DFFE} [[$i getMaster] getName]}
proc lc_outputs {i} {
 set out {}; foreach t [$i getITerms] { if {[$t getIoType] eq "OUTPUT"} {set n [$t getNet]; if {$n ne "NULL"} {lappend out $n}} }; return $out
}
proc lc_consumers {sources} {
 set todo {}; foreach i $sources {set todo [concat $todo [lc_outputs $i]]}
 set seen {};set cells {};set steps 0
 while {[llength $todo]} {
  set n [lindex $todo 0];set todo [lrange $todo 1 end]
  if {[dict exists $seen [$n getName]]} continue
  dict set seen [$n getName] 1
  foreach t [$n getITerms] {
   if {[$t getIoType] ne "INPUT"} continue
   set i [$t getInst];dict set cells [$i getName] $i
   if {![lc_seq $i]} {set todo [concat $todo [lc_outputs $i]]}
  }
  incr steps;if {$steps>4000} {error "LOCAL_CONTROL unexpectedly large reset cone"}
 }
 return [dict values $cells]
}
set lc_used {};set lc_done {};set lc_log [open $::env(RESULTS_DIR)/ot_local_control_pose.tsv w]
# Occupancy already fixed by face hooks must be preserved.
foreach i [$lc_b getInsts] {
 if {[$i getPlacementStatus] in {FIRM LOCKED}} {lassign [$i getLocation] x y;set m [$i getMaster];lappend lc_used [list $x $y [expr {$x+[$m getWidth]}] [expr {$y+[$m getHeight]}]]}
}
proc lc_pose {group cells box} {
 global lc_b lc_u lc_used lc_done lc_log
 lassign $box x0 y0 x1 y1
 set x0 [expr {round($x0*$lc_u)}];set x1 [expr {round($x1*$lc_u)}]
 set y0 [expr {round($y0*$lc_u)}];set y1 [expr {round($y1*$lc_u)}]
 set rows {};foreach r [$lc_b getRows] {lassign [$r getOrigin] rx ry;if {$ry>=$y0 && $ry+[[ $r getSite] getHeight]<=$y1} {lappend rows [list $ry $r]}}
 set rows [lsort -integer -index 0 $rows];set count 0
 foreach i [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} $cells] {
  set name [$i getName];if {[dict exists $lc_done $name]} continue
  if {[$i getPlacementStatus] in {FIRM LOCKED}} {
   lassign [$i getLocation] fx fy;set fm [$i getMaster]
   if {$group eq "root" && $fx>=$x0 && $fx+[$fm getWidth]<=$x1 && $fy>=$y0 && $fy+[$fm getHeight]<=$y1} {
    dict set lc_done $name 1
    puts $lc_log "$group-fixed-face\t$name\t[expr {double($fx)/$lc_u}]\t[expr {double($fy)/$lc_u}]"
    continue
   }
   error "LOCAL_CONTROL reset consumer overlaps fixed face: $name"
  }
  set m [$i getMaster];set w [$m getWidth];set h [$m getHeight];set placed 0
  foreach rr $rows {
   lassign $rr y r;lassign [$r getOrigin] rx ry;set sw [[$r getSite] getWidth]
   set xx [expr {$rx+int(ceil(double($x0-$rx)/$sw))*$sw}]
   for {set x $xx} {$x+$w<=$x1} {incr x $sw} {
    set bad 0;foreach b $lc_used {lassign $b bx by ex ey;if {$x<$ex && $x+$w>$bx && $y<$ey && $y+$h>$by} {set bad 1;break}}
    if {$bad} continue
    $i setOrient [$r getOrient];$i setLocation $x $y;$i setPlacementStatus FIRM
    lappend lc_used [list $x $y [expr {$x+$w}] [expr {$y+$h}]];dict set lc_done $name 1
    puts $lc_log "$group\t$name\t[expr {double($x)/$lc_u}]\t[expr {double($y)/$lc_u}]"
    incr count;set placed 1;break
   }
   if {$placed} break
  }
  if {!$placed} {error "LOCAL_CONTROL band exhausted: $group $name"}
 }
 puts "LOCAL_CONTROL_POSE $group $count cells in $box"
}
set lc_sources {}
foreach group {ctrl dv ctx div0 div1 rope} {
 set sources {};foreach i [$lc_b getInsts] {if {[regexp [format {[/\.]u_reset_%s[/\.]} $group] [$i getName]] && [lc_seq $i]} {lappend sources $i}}
 if {[llength $sources]==0 && $group in {div0 div1 rope}} {
  puts "LOCAL_CONTROL $group unobservable reset source pruned; no mission reset consumer"
  continue
 }
 if {[llength $sources]!=1} {error "LOCAL_CONTROL expected one retained reset source $group; got [llength $sources]"}
 dict set lc_sources $group $sources
}
set roots {};foreach group [dict keys $lc_sources] {set roots [concat $roots [dict get $lc_sources $group]]}
foreach i [$lc_b getInsts] {if {[regexp {^u_fcore[./]rr0} [$i getName]] && [lc_seq $i]} {lappend roots $i}}
if {[llength $roots] != 1+[dict size $lc_sources]} {error "LOCAL_CONTROL missing first reset stage"}
lc_pose root $roots {70 74 85 80}
foreach {group box} {ctrl {35 73 65 83} dv {35 86 115 98} ctx {35 57 115 69} div0 {35 112 115 124} div1 {35 32 115 44} rope {35 12 115 24}} {
 if {![dict exists $lc_sources $group]} continue
 set sinks [lc_consumers [dict get $lc_sources $group]]
 set clean {};foreach i $sinks {if {![dict exists $lc_done [$i getName]]} {lappend clean $i}}
 if {![llength $clean]} {error "LOCAL_CONTROL empty reset consumer group $group"}
 lc_pose $group $clean $box
}
close $lc_log

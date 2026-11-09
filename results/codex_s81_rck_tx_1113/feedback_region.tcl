# Private TX structural form: cluster the measured parity recurrence and its source registers.
# Zero cycle change. Recomputed on the current mapped graph; no anonymous cell-name list.
proc ot_rck_feedback_members {} {
 set b [ord::get_db_block];set roots {};set boundary {};set cells {};set q {};set seen {}
 foreach i [$b getInsts] {
  if {[string match {*u_enc.rem_q*} [$i getName]] && [string match {DFF*} [[$i getMaster] getName]]} {
   dict set roots [$i getName] $i
   foreach t [$i getITerms] {if {[[$t getMTerm] getName] eq "D"} {lappend q [$t getNet]}}
  }
 }
 if {[dict size $roots]!=300} {error "RCK_FEEDBACK: expected 300 parity registers, found [dict size $roots]"}
 while {[llength $q]} {
  set n [lindex $q end];set q [lrange $q 0 end-1]
  if {$n eq "NULL" || [dict exists $seen [$n getName]]} {continue}
  dict set seen [$n getName] 1
  foreach t [$n getITerms] {
   if {[$t getIoType] ne "OUTPUT"} {continue}
   set i [$t getInst];set name [$i getName];set m [[$i getMaster] getName]
   if {[regexp {^(DFF|DHL|DLL|SDF|ASYNC|ICG)} $m]} {dict set boundary $name $i;continue}
   if {[dict exists $cells $name]} {continue}
   dict set cells $name $i
   foreach it [$i getITerms] {if {[$it getIoType] eq "INPUT"} {lappend q [$it getNet]}}
  }
 }
 return [dict merge $roots $boundary $cells]
}
proc ot_rck_feedback_create {} {
 set b [ord::get_db_block];set u [expr {double([$b getDbUnitsPerMicron])}]
 set members [ot_rck_feedback_members];set box {62.64 62.64 153.36 153.36};lassign $box x0 y0 x1 y1
 set area 0
 dict for {name i} $members {
  set m [$i getMaster];set area [expr {$area+[$m getWidth]*double([$m getHeight])/$u/$u}]
  if {[$i getGroup] ne "NULL" && [$i getGroup] ne ""} {error "RCK_FEEDBACK: existing group on $name"}
  if {[$i getPlacementStatus] eq "FIRM" || [$i getPlacementStatus] eq "LOCKED"} {error "RCK_FEEDBACK: unexpected fixed boundary member $name"}
 }
 set fill [expr {$area/(($x1-$x0)*($y1-$y0))}]
 if {$fill>.40} {error "RCK_FEEDBACK: region fill $fill exceeds modeled 0.40; revise region before placement"}
 set r [odb::dbRegion_create $b ot_rck_feedback];$r setRegionType EXCLUSIVE
 odb::dbBox_create $r [expr {round($x0*$u)}] [expr {round($y0*$u)}] [expr {round($x1*$u)}] [expr {round($y1*$u)}]
 set g [odb::dbGroup_create $r ot_rck_feedback];$g setType VOLTAGE_DOMAIN
 dict for {name i} $members {$g addInst $i}
 puts "RCK_FEEDBACK: members [dict size $members] area_um2 $area fill $fill box $box"
}
proc ot_rck_feedback_release {} {
 set b [ord::get_db_block]
 foreach g [$b getGroups] {
  if {[$g getName] ne "ot_rck_feedback"} {continue}
  set count [llength [$g getInsts]];set r [$g getRegion]
  odb::dbGroup_destroy $g
  if {$r ne "NULL"} {odb::dbRegion_destroy $r}
  puts "RCK_FEEDBACK: release before DPL, cells $count"
 }
}

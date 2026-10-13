read_db $::env(OV_OLD_DB)
set b [ord::get_db_block]
proc dump_logic {block path} {
 set lines {}
 foreach i [$block getInsts] {
  if {[[$i getMaster] getName] eq "TAPCELL_ASAP7_75t_R"} {continue}
  set pins {}
  foreach it [$i getITerms] {
   set n [$it getNet]; set netname ""
   if {$n ne "NULL"} {set netname [$n getName]}
   lappend pins [list [[$it getMTerm] getName] $netname]
  }
  lappend lines [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [lsort $pins]]
 }
 set f [open $path w]; puts $f [join [lsort $lines] "\n"]; close $f
 return [llength $lines]
}
set before [dump_logic $b /work/logic_before.tsv]
set sites {}
foreach r [$b getRows] {dict set sites [[$r getSite] getName] [$r getSite]}
set count [llength [$b getInsts]]
set removed 0
foreach i [$b getInsts] {
 if {[[$i getMaster] getName] eq "TAPCELL_ASAP7_75t_R"} {odb::dbInst_destroy $i; incr removed}
}
foreach r [$b getRows] {odb::dbRow_destroy $r}
set fd [open /work/fresh_geometry.tsv]
set rows 0; set taps 0
while {[gets $fd line] >= 0} {
 set v [split $line "\t"]
 lassign $v kind name master x y orient
 if {$kind eq "ROW"} {
  set site [dict get $sites $master]
  if {$site eq "NULL"} {error "site not found $master"}
  odb::dbRow_create $b $name $site $x $y $orient [lindex $v 6] [lindex $v 7] [lindex $v 8]
  incr rows
 } else {
  set m [[ord::get_db] findMaster $master]
  set i [odb::dbInst_create $b $m $name]
  $i setOrient $orient; $i setLocation $x $y; $i setPlacementStatus [lindex $v 6]
  incr taps
 }
}
close $fd
puts "OV_WARM preserved_logic=[expr {$count-$removed}] replaced_fixed=$removed->$taps rows=$rows"
set after [dump_logic $b /work/logic_after.tsv]
if {$before != $after} {error "logical instance count changed"}
puts "OV_WARM logic_count_before=$before after=$after nets=[llength [$b getNets]]"
write_db $::env(OV_WARM_DB)

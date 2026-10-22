source /audit/native_pg_binding.tcl
read_db [lindex [glob /route/work/orfs/results/asap7/*/base/6_final.odb] 0]
set b [ord::get_db_block]
set f [open /audit/native_pg.tsv w]
puts $f "instance\tmaster\tpin\trole\tactual_net\tactual_role\texpected_net\tstatus\tprotected\tregion"
set mapping_ok 1
if {[catch {ot_pg_prepare $b} mapping]} {set mapping_ok 0; puts "MAPPING_REFUSED $mapping"}
set masters [dict create]
set count 0; set bad 0
foreach inst [$b getInsts] {
 set master [$inst getMaster]
 dict set masters [$master getName] $master
 foreach mt [$master getMTerms] {
  set role [$mt getSigType]
  if {$role ni {POWER GROUND}} continue
  incr count
  set pin [$mt getName]; set term [$inst findITerm $pin]
  set an ""; set ar ""; set en ""; set status PASS
  if {$term eq "NULL"} {set status MISSING_ITERM} else {
   set net [$term getNet]
   if {$net ne "NULL"} {set an [$net getName]; set ar [$net getSigType]}
   if {!$mapping_ok} {set status MAPPING_REFUSED} elseif {[catch {ot_pg_expected $mapping $inst $term} expected]} {set status $expected} else {
    set en [$expected getName]
    if {$net ne $expected} {set status WRONG_OR_MISSING_NET}
   }
  }
  if {$status ne "PASS"} {incr bad}
  set region [$inst getRegion]
  if {$region ne "NULL"} {set region [$region getName]}
  puts $f [join [list [$inst getName] [$master getName] $pin $role $an $ar $en $status [$inst isDoNotTouch] $region] "\t"]
 }
}
close $f
set f [open /audit/master_pg.tsv w]
puts $f "master\twidth\theight\tpin\trole\tgeometry"
dict for {name master} $masters {
 foreach mt [$master getMTerms] {
  if {[$mt getSigType] ni {POWER GROUND}} continue
  set geo {}
  foreach mp [$mt getMPins] {foreach box [$mp getGeometry] {lappend geo [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}
  puts $f [join [list $name [$master getWidth] [$master getHeight] [$mt getName] [$mt getSigType] $geo] "\t"]
 }
}
close $f
set f [open /audit/global_rules.tsv w]
foreach rule [$b getGlobalConnects] {set r [$rule getRegion]; if {$r ne "NULL"} {set r [$r getName]}; puts $f [join [list [$rule getInstPattern] [$rule getPinPattern] [[$rule getNet] getName] $r] "\t"]}
close $f
puts "AUDIT_DONE instances=[llength [$b getInsts]] master_pg_terminals=$count failures=$bad mapping_ok=$mapping_ok"
exit

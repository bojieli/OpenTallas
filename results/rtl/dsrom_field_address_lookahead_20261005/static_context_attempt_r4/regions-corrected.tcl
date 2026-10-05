# Exact disjoint Maxwell slots translated by sp_capture origin [15182.64,13471.92].
set block [ord::get_db_block]
set scale [$block getDbUnitsPerMicron]
proc ctx_region {block name box} {
 set r [odb::dbRegion_create $block $name]
 $r setRegionType EXCLUSIVE
 set b {};foreach x $box {lappend b [expr {round($x*[$block getDbUnitsPerMicron])}]}
 odb::dbBox_create $r {*}$b
 set g [odb::dbGroup_create $block $name];$r addGroup $g
 return $g
}
set ig [ctx_region $block issuer {4.32 4.32 69.12 12.96}]
set pg [ctx_region $block provider {73.44 4.32 203.04 90.72}]
# Kept table output nets bind a reverse comb cone; stop at kept launch addresses.
set seen {};set todo {}
foreach n [$block getNets] {
 set boundary_name [string map [list "\\" ""] [$n getName]]
 if {[regexp {^(ph_q[01]|st_q)(\[|$)} $boundary_name]} {lappend todo $n}
}
if {[llength $todo]==0} {error "provider kept boundary nets absent"}
while {[llength $todo]} {
 set n [lindex $todo 0];set todo [lrange $todo 1 end]
 set boundary_name [string map [list "\\" ""] [$n getName]]
 if {[regexp {^(provider_addr|phase_launch)(\[|$)} $boundary_name]} {continue}
 foreach it [$n getITerms] {
  if {[$it getIoType] ne "OUTPUT"} {continue}
  set inst [$it getInst];set name [$inst getName]
  if {[dict exists $seen $name]} {continue}
  dict set seen $name 1
  foreach pin [$inst getITerms] {
   if {[$pin getIoType] eq "INPUT"} {
    set next [$pin getNet];if {$next ne "NULL"} {lappend todo $next}
   }
  }
 }
}
set pa 0.;set ia 0.;set pc 0;set ic 0
foreach inst [$block getInsts] {
 set master [$inst getMaster];if {[$master isBlock]} {error "unexpected macro"}
 if {[regexp {SPACER|WELLTAP} [$master getType]]} {continue}
 set area [expr {double([$master getWidth])*[$master getHeight]/$scale/$scale}]
 if {[dict exists $seen [$inst getName]]} {$pg addInst $inst;set pa [expr {$pa+$area}];incr pc} else {$ig addInst $inst;set ia [expr {$ia+$area}];incr ic}
}
puts "CONTEXT_REGIONS provider_cells=$pc provider_area=$pa issuer_cells=$ic issuer_area=$ia"
if {$pa>5598.72 || $ia>279.936} {error "mapped named-slot 50pct budget exceeded"}

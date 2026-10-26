# Real forward payload / row ownership, applied after pin-register placement.
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
array set members {0 {} 1 {} 2 {} 3 {}}
foreach inst [$b getInsts] {
 set n [$inst getName];set q -1
 if {[regexp {u_ot_pr_core\.(arc|brc|wqc|adc|bdc|s_val)\[([0-9]+)\]} $n -> v bit]} {
  if {$v eq "arc" || $v eq "brc"} {set c [expr {$bit/6}];if {$c>=8 && $c<24} {set q [expr {($c-8)/4}]}}
  if {$v eq "wqc"} {set c [expr {$bit/14}];if {$c>=8 && $c<24} {set q [expr {($c-8)/4}]}}
  if {$v eq "adc" || $v eq "bdc"} {set c [expr {$bit/224}];if {$c>=4 && $c<8} {set q [expr {$c-4}]}}
  if {$v eq "s_val" && $bit<512} {set q [expr {$bit/128}]}
 } elseif {[regexp {u_ot_pr_core\.g_e\[([0-9]+)\].*\.u_f[./]} $n -> lane]} {
  if {$lane<16} {set q [expr {$lane/4}]}
 } elseif {[regexp {u_ot_pr_core\.g_fw\[([0-9]+)\]} $n -> lane]} {
  if {$lane<16} {set q [expr {$lane/4}]}
 } elseif {[regexp {u_ot_pr_core\.g_dec\[([0-9]+)\]} $n -> c]} {
  if {$c>=8 && $c<24} {set q [expr {($c-8)/4}]}
 }
 if {$q<0 || [[$inst getMaster] isBlock]} continue
 if {[$inst isFixed]} {$inst setPlacementStatus PLACED}
 lappend members($q) $inst
}
set boxes {{2.16 2.16 125.28 216.0} {125.28 2.16 248.4 216.0} {2.16 216.0 125.28 429.84} {125.28 216.0 248.4 429.84}}
for {set q 0} {$q<4} {incr q} {
 if {[llength $members($q)]<100} {error "OT_GF quadrant $q has too few actual members: [llength $members($q)]"}
 lassign [lindex $boxes $q] x0 y0 x1 y1
 set area 0.0
 foreach i $members($q) {set m [$i getMaster];set area [expr {$area+[$m getWidth]*[$m getHeight]/double($dbu*$dbu)}]}
 set util [expr {$area/(($x1-$x0)*($y1-$y0))}]
 if {$util>0.5} {error "OT_GF quadrant $q utilisation $util exceeds 0.5"}
 set r [odb::dbRegion_create $b ot_gf_$q]
 $r setRegionType INCLUSIVE
 odb::dbBox_create $r [expr {round($x0*$dbu)}] [expr {round($y0*$dbu)}] [expr {round($x1*$dbu)}] [expr {round($y1*$dbu)}]
 set gr [odb::dbGroup_create $r ot_gf_$q]
 foreach i $members($q) {$gr addInst $i}
 puts "OT_GF quadrant=$q actual_members=[llength $members($q)] area_um2=$area utilisation=$util box=[lindex $boxes $q]"
}
puts "OT_GF PASS four real forward ownership groups"

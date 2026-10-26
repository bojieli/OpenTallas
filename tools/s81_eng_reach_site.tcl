# Legalize the existing moved reset leaf to the nearest real placement row.
set es_b [ord::get_db_block]
set es_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set es_n 0
set es_row {}; set es_best 1e30
foreach es_r [$es_b getRows] {
 lassign [$es_r getOrigin] es_rx es_ry
 set es_d [expr {abs($es_ry-240.0*$es_dbu)}]
 if {$es_d < $es_best} {set es_row $es_r;set es_best $es_d}
}
lassign [$es_row getOrigin] es_rx es_ry
set es_pitch [[$es_row getSite] getWidth]
set es_x [expr {$es_rx+round((180.0*$es_dbu-$es_rx)/double($es_pitch))*$es_pitch}]
foreach es_i [$es_b getInsts] {
 set es_nm [string map {\\ {}} [$es_i getName]]
 if {[regexp {^u_r[.]g_tleaf\[0\][.]q} $es_nm]} {
  $es_i setPlacementStatus PLACED
  $es_i setOrient [$es_row getOrient]
  $es_i setLocation $es_x $es_ry
  incr es_n
 }
}
if {$es_n != 1} {error "engine reset leaf: expected one leaf0, got$es_n"}
puts "ENG_REACH_SITE leaf0: legal row at $es_x,$es_ry; released for local legalization"

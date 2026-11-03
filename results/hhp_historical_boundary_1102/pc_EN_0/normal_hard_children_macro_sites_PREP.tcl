# GENERATED: explicit core macro plan (same registered RTL and external slot)
set blk [ord::get_db_block]
set dbu [$blk getDbUnitsPerMicron]
proc ot_macro_literal_name {name} {return [string map [list {\[} {[} {\]} {]}] $name]}
set ot_macro_names {}
foreach candidate [$blk getInsts] {
  if {[[$candidate getMaster] getType] ne "BLOCK"} {continue}
  dict lappend ot_macro_names [ot_macro_literal_name [$candidate getName]] $candidate
}
foreach {inst master x y orient} {  {u_core_kvpc1} qkd_kvs_pc 552.576 198.72 R0
  {u_core_kvpc2} qkd_kvs_pc 552.576 959.04 R0
  {u_core_kvpc3} qkd_kvs_pc 85.44000000000001 959.04 MY
} {
  set i [$blk findInst $inst]
  if {$i eq {NULL} || $i eq {}} {
    set key [ot_macro_literal_name $inst]
    set hit {}
    if {[dict exists $ot_macro_names $key]} {set hit [dict get $ot_macro_names $key]}
    if {[llength $hit] != 1} {error "planned macro $inst: [llength $hit] literal bracket matches"}
    set i [lindex $hit 0]
  }
  if {[[$i getMaster] getName] ne $master} {error "wrong planned macro master $inst"}
  $i setOrient $orient
  $i setLocation 0 0
  set bb [$i getBBox]
  $i setLocation [expr {round($x*$dbu)-[$bb xMin]}] [expr {round($y*$dbu)-[$bb yMin]}]
  $i setPlacementStatus FIRM
}

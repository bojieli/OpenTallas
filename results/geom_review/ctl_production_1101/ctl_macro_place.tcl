# GENERATED: explicit core macro plan (same registered RTL and external slot)
set blk [ord::get_db_block]
set dbu [$blk getDbUnitsPerMicron]
proc ot_macro_literal_name {name} {return [string map [list {\[} {[} {\]} {]}] $name]}
set ot_macro_names {}
foreach candidate [$blk getInsts] {
  if {[[$candidate getMaster] getType] ne "BLOCK"} {continue}
  dict lappend ot_macro_names [ot_macro_literal_name [$candidate getName]] $candidate
}
foreach {inst master x y orient} {  {u_leaf.u_lprg.genblk1.g_s2.u_rowa_b0} ctl_sram_1r1w_64x128_p192 103.68 60.48 R0
  {u_leaf.u_lprg.genblk1.g_s2.u_rowa_b1} ctl_sram_1r1w_64x128_p192 216.0 60.48 R0
  {u_leaf.u_lprg.genblk1.g_s2.u_rowb_b0} ctl_sram_1r1w_64x128_p192 103.68 155.52 R0
  {u_leaf.u_lprg.genblk1.g_s2.u_rowb_b1} ctl_sram_1r1w_64x128_p192 216.0 155.52 R0
  {u_leaf.u_wprg.g_sr.genblk1.g_s2.u_rows_b0} ctl_sram_1r1w_64x128_p192 103.68 250.56 R0
  {u_leaf.u_wprg.g_sr.genblk1.g_s2.u_rows_b1} ctl_sram_1r1w_64x128_p192 216.0 250.56 R0
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
  $i setPlacementStatus LOCKED
}

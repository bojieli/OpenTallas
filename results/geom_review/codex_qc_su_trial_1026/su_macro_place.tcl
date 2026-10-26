# Candidate SU lane0 actual native TLM bank sites, no interface or RTL change.
# X remains on the4.32um PG lattice; Y+.012 aligns native M4 pins to symmetric.024.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set seen {}
foreach i [$b getInsts] {
  if {[[$i getMaster] getName] ne "ot_sram_1r1w2c_128x64_m1"} continue
  set nm [$i getName]
  if {![regexp {g_native_bank\[([01])\][./]u_tlm$} $nm -> k]} { error "unplanned SU SRAM instance $nm" }
  if {[dict exists $seen $k]} { error "duplicate SU SRAM bank$k" }
  dict set seen $k $nm
  set x [lindex {168.48 216.00} $k]
  set y 120.972
  $i setOrient R0
  set bb [[$i getMaster] getBBox]
  $i setLocation [expr {round($x*$dbu)-[$bb xMin]}] [expr {round($y*$dbu)-[$bb yMin]}]
  $i setPlacementStatus FIRM
  puts "SU_SRAM_PLANNED $nm $x $y"
}
if {[dict size $seen] != 2} { error "expected2 actual native TLM banks, found[dict size $seen]" }

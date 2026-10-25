# PATH-QC-SU btab_s6 PRE_GLOBAL_ROUTE: kit drv.tcl, then an M5 pin-access keep-out band over each SRAM pin edge.
# Why (btab_t2 DRT stuck 3 violations from iter ~25 to 60+): the macro abstract has 0.024 M4 edge pins and the M4 OBS
# starts 0.072 in (0.048 open strip, wide-OBS spacing 0.072); M5 over the macro is open, so a VIA45 on the M5 tracks at
# edge+0.012 / edge+0.060 puts its M4 pad (+-0.023) into the strip -> short (twp_d[51] x 86.472-86.483) or spacing
# (twp_d[248] x 181.152) to the OBS.  The only legal access is planar M4 from outside the macro: block M5 over the
# inner 0.096 of both pin edges (outside track edge-0.036 and every PDN stripe untouched).  Routing blockage only.
source /work/drv.tcl
set b [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]; set m5 [[ord::get_db_tech] findLayer M5]
set d [expr {round(0.096 * $dbu)}]; set n 0
foreach i [$b getInsts] {
  if {![[$i getMaster] isBlock]} continue
  set bb [$i getBBox]
  odb::dbObstruction_create $b $m5 [$bb xMin] [$bb yMin] [expr {[$bb xMin] + $d}] [$bb yMax]
  odb::dbObstruction_create $b $m5 [expr {[$bb xMax] - $d}] [$bb yMin] [$bb xMax] [$bb yMax]
  incr n 2
}
puts "S6B_PIN_EDGE_KEEPOUT M5 $n bands (0.096 um) over [expr {$n/2}] macros"

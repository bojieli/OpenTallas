# S81-CORE-LAT-R13 core_family_slice census: legal-site + PG description for core_plan_to_infra (from R8 dump_sites.tcl, read-only).
# env ODB OUT
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
proc um {v} { return [format %.4f [expr {$v / double($::u)}]] }
set f [open $::env(OUT) w]
set d [$b getDieArea]; puts $f "DIE [um [$d xMin]] [um [$d yMin]] [um [$d xMax]] [um [$d yMax]]"
set r0 [lindex [$b getRows] 0]
set nrows [llength [$b getRows]]
lassign [$r0 getOrigin] rx ry
puts $f "ROW0 [um $rx] [um $ry] site_w [um [[$r0 getSite] getWidth]] site_h [um [[$r0 getSite] getHeight]] nrows $nrows nsites [$r0 getSiteCount] orient0 [$r0 getOrient]"
foreach r [$b getRows] { lassign [$r getOrigin] x y; puts $f "ROW [um $x] [um $y] [$r getOrient] [$r getSiteCount]" }
foreach i [$b getInsts] {
  set s [$i getPlacementStatus]
  if {$s in {FIRM LOCKED COVER}} { set bb [$i getBBox]; puts $f "FIXED [$i getName] [[$i getMaster] getName] [um [$bb xMin]] [um [$bb yMin]] [um [$bb xMax]] [um [$bb yMax]]" }
}
# OpenDB hard placement blockages are independent of fixed instances/row cuts.
# Preserve their exact rectangles: no extra macro halo or routing obstruction.
foreach k [$b getBlockages] {
  if {[$k isSoft] || [$k getMaxDensity] > 0} continue
  set bb [$k getBBox]
  puts $f "BLOCKAGE [$k getId] [um [$bb xMin]] [um [$bb yMin]] [um [$bb xMax]] [um [$bb yMax]]"
}
foreach n {BUFx2_ASAP7_75t_R BUFx8_ASAP7_75t_R BUFx10_ASAP7_75t_R BUFx12_ASAP7_75t_R BUFx12f_ASAP7_75t_R BUFx16f_ASAP7_75t_R BUFx24_ASAP7_75t_R BUFx6f_ASAP7_75t_R BUFx5_ASAP7_75t_R BUFx4f_ASAP7_75t_R ICGx1_ASAP7_75t_R ICGx2_ASAP7_75t_R ICGx3_ASAP7_75t_R ICGx4_ASAP7_75t_R ICGx4DC_ASAP7_75t_R ICGx5_ASAP7_75t_R ICGx8DC_ASAP7_75t_R} {
  set m [[ord::get_db] findMaster $n]; puts $f "MASTER $n [um [$m getWidth]] [um [$m getHeight]]" }
foreach net [$b getNets] {
  if {![$net isSpecial]} continue
  foreach sw [$net getSWires] { foreach w [$sw getWires] {
    if {[$w isVia]} { continue   ;# via boxes unused by core_plan_to_infra.read_sites (PG straps only)
    } else { set ln [[$w getTechLayer] getName]
      if {$ln in {M4 M5}} { puts $f "PG [$net getName] $ln [um [$w xMin]] [um [$w yMin]] [um [$w xMax]] [um [$w yMax]]" } }
  } }
}
puts $f "DBU $u"
set ca [$b getCoreArea]; puts $f "CORE_DBU [$ca xMin] [$ca yMin] [$ca xMax] [$ca yMax]"
foreach i [$b getInsts] {
 set bb [$i getBBox]
 puts $f [list INST [$i getName] [[$i getMaster] getName] [$i getPlacementStatus] [$i getOrient] [um [$bb xMin]] [um [$bb yMin]] [um [$bb xMax]] [um [$bb yMax]]]
}
foreach bt [$b getBTerms] { foreach bp [$bt getBPins] { foreach bb [$bp getBoxes] {
 puts $f [list BTERM [$bt getName] [$bt getIoType] [$bt getSigType] [[$bb getTechLayer] getName] [um [$bb xMin]] [um [$bb yMin]] [um [$bb xMax]] [um [$bb yMax]]]
}}}
foreach net [$b getNets] {
 if {![$net isSpecial]} continue
 foreach sw [$net getSWires] { foreach w [$sw getWires] {
  if {![$w isVia]} continue
  set via [$w getBlockVia]; if {$via eq "NULL"} {set via [$w getTechVia]}
  lassign [$w getViaXY] vx vy
  foreach box [$via getBoxes] {
   set ln [[$box getTechLayer] getName]
   if {$ln in {M4 M5}} {
    puts $f [list PGVIA [$net getName] $ln [um [expr {$vx+[$box xMin]}]] [um [expr {$vy+[$box yMin]}]] [um [expr {$vx+[$box xMax]}]] [um [expr {$vy+[$box yMax]}]]]
   }
  }
 }}
}
close $f
puts DUMP_SITES_DONE
source /out/geom_dump.tcl
exit

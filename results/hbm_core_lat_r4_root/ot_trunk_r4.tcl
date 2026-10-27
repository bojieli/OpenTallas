# HBM-CORE-LAT-R4 (METHODOLOGY 12.8c, COORD RULING HBM-CORE-LAT-R3 (3)): fixed plan-computed clock trunk on a shallow
# core.  POST_CTS hook: the clock port net (after TritonCTS built the local tree from the centre entry) is cut and a
# chain of OT_TRUNK_N identical OT_TRUNK_CELL buffers is inserted between the port and every former load, placed FIRM
# in the master-plan entry island (OT_TRUNK_ISLAND = x0 y0 x1 y1 um), dont_touch.  Cell + N come from
# results/hbm_core_lat_r3_root/trunk_chain.json (plan NLDM, chosen before any build); nothing here is measured or
# tuned.  Then the kit's own POST_CTS chain (f4_chain_leaf.tcl -> tap_balance.tcl, the latter OT_TAP_REPORT_ONLY=1).
uplevel #0 {
set tr_blk [ord::get_db_block]
set tr_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set tr_cell $::env(OT_TRUNK_CELL); set tr_n $::env(OT_TRUNK_N)
lassign $::env(OT_TRUNK_ISLAND) tr_x0 tr_y0 tr_x1 tr_y1
set tr_port [expr {[info exists ::env(OT_TRUNK_PORT)] ? $::env(OT_TRUNK_PORT) : "clk"}]
set tr_m [[ord::get_db] findMaster $tr_cell]
if {$tr_m eq "NULL"} { error "OT_TRUNK no master $tr_cell" }
set tr_bt [$tr_blk findBTerm $tr_port]
if {$tr_bt eq "NULL"} { error "OT_TRUNK no port $tr_port" }
set tr_pnet [$tr_bt getNet]
if {[$tr_blk findInst ot_trunk_s0] ne "NULL"} { error "OT_TRUNK already inserted" }
set tr_loads {}
foreach it [$tr_pnet getITerms] { if {[$it isInputSignal]} { lappend tr_loads $it } }
if {![llength $tr_loads]} { error "OT_TRUNK clock port net has no loads" }
# rows inside the island: centre row first, cells abutted from the island centre, site-aligned
set tr_cx [expr {round(($tr_x0 + $tr_x1) / 2.0 * $tr_dbu)}]; set tr_cy [expr {round(($tr_y0 + $tr_y1) / 2.0 * $tr_dbu)}]
set tr_rows {}
foreach r [$tr_blk getRows] {
  set b [$r getBBox]
  if {[$b yMin] >= round($tr_y0*$tr_dbu) && [$b yMax] <= round($tr_y1*$tr_dbu) && [$b xMin] <= round($tr_x0*$tr_dbu) && [$b xMax] >= round($tr_x1*$tr_dbu)} {
    lappend tr_rows [list [expr {abs(([$b yMin] + [$b yMax]) / 2 - $tr_cy)}] $r]
  }
}
if {![llength $tr_rows]} { error "OT_TRUNK no row inside the island" }
set tr_rows [lsort -integer -index 0 $tr_rows]
set tr_w [$tr_m getWidth]
set tr_per [expr {int(floor((round($tr_x1*$tr_dbu) - round($tr_x0*$tr_dbu)) / double($tr_w))) - 1}]
set tr_prev $tr_pnet; set tr_k 0; set tr_ri 0
for {set i 0} {$i < $tr_n} {incr i} {
  if {$tr_k >= $tr_per} { incr tr_ri; set tr_k 0 }
  if {$tr_ri >= [llength $tr_rows]} { error "OT_TRUNK island too small for $tr_n x $tr_cell" }
  set row [lindex $tr_rows $tr_ri 1]; set rb [$row getBBox]
  set site [[$row getSite] getWidth]
  set x [expr {round($tr_x0*$tr_dbu) + $site + $tr_k * $tr_w}]
  set x [expr {[$rb xMin] + int(ceil(($x - [$rb xMin]) / double($site))) * $site}]
  set inst [odb::dbInst_create $tr_blk $tr_m ot_trunk_s$i]
  $inst setOrient [$row getOrient]; $inst setLocation $x [$rb yMin]; $inst setPlacementStatus FIRM
  set out [odb::dbNet_create $tr_blk ot_trunk_n[expr {$i + 1}]]
  $out setSigType CLOCK
  foreach it [$inst getITerms] {
    set mt [$it getMTerm]
    if {[$mt getSigType] in {POWER GROUND}} continue
    if {[$mt getIoType] eq "INPUT"} { $it connect $tr_prev } elseif {[$mt getIoType] eq "OUTPUT"} { $it connect $out }
  }
  $inst setDoNotTouch 1
  set tr_prev $out; incr tr_k
}
foreach it $tr_loads { $it disconnect; $it connect $tr_prev }
for {set i 1} {$i <= $tr_n} {incr i} { [$tr_blk findNet ot_trunk_n$i] setDoNotTouch 1 }
global_connect
puts "OT_TRUNK inserted $tr_n x $tr_cell in island {$tr_x0 $tr_y0 $tr_x1 $tr_y1} rows_used [expr {$tr_ri + 1}] loads_moved [llength $tr_loads] (FIRM, dont_touch)"
estimate_parasitics -placement
}
if {[info exists ::env(OT_TRUNK_NEXT_TCL)] && $::env(OT_TRUNK_NEXT_TCL) ne ""} { source $::env(OT_TRUNK_NEXT_TCL) }

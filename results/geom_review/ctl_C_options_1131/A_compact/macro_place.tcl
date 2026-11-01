# Proposed FIRM SRAM sites; held until functional gate and plan event review.
set blk [ord::get_db_block]
set dbu [$blk getDbUnitsPerMicron]
set hit {}
foreach i [$blk getInsts] { if {[$i getName] eq {u_leaf.u_wprg.g_sr.genblk1.g_s2.u_rows_b0}} {lappend hit $i} }
if {[llength $hit] != 1} {error {u_leaf.u_wprg.g_sr.genblk1.g_s2.u_rows_b0: expected one current SRAM}}
set i [lindex $hit 0]
$i setOrient MY
$i setLocation 0 0
set bb [$i getBBox]
$i setLocation [expr {round(12.972*$dbu)-[$bb xMin]}] [expr {round(19.98*$dbu)-[$bb yMin]}]
$i setPlacementStatus FIRM
set hit {}
foreach i [$blk getInsts] { if {[$i getName] eq {u_leaf.u_wprg.g_sr.genblk1.g_s2.u_rows_b1}} {lappend hit $i} }
if {[llength $hit] != 1} {error {u_leaf.u_wprg.g_sr.genblk1.g_s2.u_rows_b1: expected one current SRAM}}
set i [lindex $hit 0]
$i setOrient R0
$i setLocation 0 0
set bb [$i getBBox]
$i setLocation [expr {round(116.172*$dbu)-[$bb xMin]}] [expr {round(19.98*$dbu)-[$bb yMin]}]
$i setPlacementStatus FIRM
set hit {}
foreach i [$blk getInsts] { if {[$i getName] eq {u_leaf.u_lprg.genblk1.g_s2.u_rowb_b0}} {lappend hit $i} }
if {[llength $hit] != 1} {error {u_leaf.u_lprg.genblk1.g_s2.u_rowb_b0: expected one current SRAM}}
set i [lindex $hit 0]
$i setOrient MY
$i setLocation 0 0
set bb [$i getBBox]
$i setLocation [expr {round(12.972*$dbu)-[$bb xMin]}] [expr {round(113.916*$dbu)-[$bb yMin]}]
$i setPlacementStatus FIRM
set hit {}
foreach i [$blk getInsts] { if {[$i getName] eq {u_leaf.u_lprg.genblk1.g_s2.u_rowb_b1}} {lappend hit $i} }
if {[llength $hit] != 1} {error {u_leaf.u_lprg.genblk1.g_s2.u_rowb_b1: expected one current SRAM}}
set i [lindex $hit 0]
$i setOrient R0
$i setLocation 0 0
set bb [$i getBBox]
$i setLocation [expr {round(116.172*$dbu)-[$bb xMin]}] [expr {round(113.916*$dbu)-[$bb yMin]}]
$i setPlacementStatus FIRM
set hit {}
foreach i [$blk getInsts] { if {[$i getName] eq {u_leaf.u_lprg.genblk1.g_s2.u_rowa_b0}} {lappend hit $i} }
if {[llength $hit] != 1} {error {u_leaf.u_lprg.genblk1.g_s2.u_rowa_b0: expected one current SRAM}}
set i [lindex $hit 0]
$i setOrient MY
$i setLocation 0 0
set bb [$i getBBox]
$i setLocation [expr {round(12.972*$dbu)-[$bb xMin]}] [expr {round(207.9*$dbu)-[$bb yMin]}]
$i setPlacementStatus FIRM
set hit {}
foreach i [$blk getInsts] { if {[$i getName] eq {u_leaf.u_lprg.genblk1.g_s2.u_rowa_b1}} {lappend hit $i} }
if {[llength $hit] != 1} {error {u_leaf.u_lprg.genblk1.g_s2.u_rowa_b1: expected one current SRAM}}
set i [lindex $hit 0]
$i setOrient R0
$i setLocation 0 0
set bb [$i getBBox]
$i setLocation [expr {round(116.172*$dbu)-[$bb xMin]}] [expr {round(207.9*$dbu)-[$bb yMin]}]
$i setPlacementStatus FIRM

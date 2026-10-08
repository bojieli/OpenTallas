# Top-region placement only: no EXCLUSIVE fence or secondary Nesterov solver.
set block [ord::get_db_block]
if {[llength [$block getRegions]] != 0} {error "unexpected placement regions"}
# Match actual tapcell row-cut halo (2um), distinct from placement halo (1um).
set nm 0
set dbu [$block getDbUnitsPerMicron]
foreach inst [$block getInsts] {
 if {! [[$inst getMaster] isBlock]} {continue}
 set bb [$inst getBBox]
 create_blockage -inst [$inst getName] -region [list [expr {[$bb xMin]/double($dbu)-2.0}] [expr {[$bb yMin]/double($dbu)-2.0}] [expr {[$bb xMax]/double($dbu)+2.0}] [expr {[$bb yMax]/double($dbu)+2.0}]]
 incr nm
}
if {$nm != 56} {error "expected 56 native delay macros, got $nm"}
puts "OT_HEAD_NATIVE_BLOCKAGES macros=$nm manually_placed_box=125.28,48.60,174.96,89.64"
# The right clock corridor must contain real cut rows wide enough for CTS.
set corridor_rows 0
set min_width 1e30
foreach row [$block getRows] {
 lassign [$row getOrigin] x y
 if {$x <287448 || $y<7200 || $y>139587} {continue}
 set width [expr {[$row getSiteCount]*[[$row getSite] getWidth]}]
 set min_width [expr {min($min_width,$width)}]
 incr corridor_rows
}
if {$corridor_rows<100 || $min_width<5000} {error "missing actual right clock corridor: rows=$corridor_rows width=$min_width"}
puts "OT_HEAD_NATIVE_CLOCK_CORRIDOR rows=$corridor_rows min_width_dbu=$min_width"

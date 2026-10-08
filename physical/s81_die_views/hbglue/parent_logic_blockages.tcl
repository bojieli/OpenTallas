# Top-region placement only: no EXCLUSIVE fence or secondary Nesterov solver.
set block [ord::get_db_block]
if {[llength [$block getRegions]] != 0} {error "unexpected placement regions"}
foreach rect {{4.32 4.32 125.28 145.68} {174.96 4.32 295.68 145.68} {125.28 4.32 174.96 48.60} {125.28 89.64 174.96 145.68}} {
 create_blockage -region $rect
}
# Explicit macro obstructions are retained for CTS after periphery is released.
set nm 0
set dbu [$block getDbUnitsPerMicron]
foreach inst [$block getInsts] {
 if {! [[$inst getMaster] isBlock]} {continue}
 set bb [$inst getBBox]
 create_blockage -inst [$inst getName] -region [list [expr {[$bb xMin]/double($dbu)}] [expr {[$bb yMin]/double($dbu)}] [expr {[$bb xMax]/double($dbu)}] [expr {[$bb yMax]/double($dbu)}]]
 incr nm
}
if {$nm != 56} {error "expected 56 native delay macros, got $nm"}
puts "OT_HEAD_NATIVE_BLOCKAGES four_peripheral macros=$nm allowed_box=125.28,48.60,174.96,89.64"

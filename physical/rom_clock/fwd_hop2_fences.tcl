# --step-tcl POST_PDN hook for the ot_fwd_link_hop2 fixture: stage A's flops and its forwarding inverter fenced at
# the west edge, stage B's flops at the east edge; fence centroids 440 um apart (>= the 430.56 um link span).
# Geometry only; no timing constraint.
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
proc fence {block dbu name x0 x1} {
  set r [odb::dbRegion_create $block $name]
  odb::dbBox_create $r [expr {int($x0 * $dbu)}] [expr {int(5 * $dbu)}] [expr {int($x1 * $dbu)}] [expr {int(155 * $dbu)}]
  return $r
}
set west [fence $block $dbu tx_west 5 35]
set east [fence $block $dbu rx_east 445 475]
set nw 0; set ne 0
foreach inst [$block getInsts] {
  if {![[$inst getMaster] isSequential]} { continue }
  set n [$inst getName]
  if {[string match "u_a.*" $n]} { $west addInst $inst; incr nw } elseif {[string match "u_b.*" $n]} { $east addInst $inst; incr ne }
}
# stage A's forwarding inverter (u_a.active.u_fwd_inv, kept hierarchy) at the launching end
set ni 0
foreach inst [$block getInsts] {
  if {[string match "u_a.*u_fwd_inv*" [$inst getName]]} { $west addInst $inst; incr ni }
}
puts "OT_FENCE tx_west sequential $nw inverter $ni; rx_east sequential $ne"
if {$nw == 0 || $ne == 0 || $ni != 1} { error "ot_fwd_link_hop2 fence: unexpected instance names" }

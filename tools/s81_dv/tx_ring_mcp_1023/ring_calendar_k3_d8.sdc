# STW-S81d-TOPK 2026-10-23: calendar-ring K-cycle relation (dsdv_tx_ring_slice, K=3, D=8), scoped to ring slice
# bank -> q only.  A slot is written at source edge n and read at destination edge n+K (K edges already priced in the
# TX lookup pipe LP); it is next overwritten at source edge n+D.  Setup is therefore checked at K edges, hold at
# edge -1 (H=K; exact bound would be H=D-1, so one-plus cycles of hold margin are kept).  Every other path, including
# rsel/warm -> q and q -> downstream, remains single-cycle.  No clock, uncertainty or IO change.
set ot_rm_from {}
set ot_rm_to {}
foreach c [get_cells -hierarchical *] {
  set n [get_full_name $c]
  if {![string match *g_ring* $n] || ![string match *g_slice* $n]} continue
  if {[string match {*u/bank\[*} $n] || [string match {*u.bank\[*} $n]} { lappend ot_rm_from $c }
  if {[string match {*u/q\[*} $n] || [string match {*u.q\[*} $n] || [string match {*u/q_reg*} $n]} { lappend ot_rm_to $c }
}
puts "OT_RING_MCP K=3 D=8 from=[llength $ot_rm_from] to=[llength $ot_rm_to]"
if {[llength $ot_rm_from] > 0 && [llength $ot_rm_to] > 0} {
  set_multicycle_path -setup 3 -from $ot_rm_from -to $ot_rm_to
  set_multicycle_path -hold 3 -from $ot_rm_from -to $ot_rm_to
}

# UCIE6 (HBM-OWN/PHY 10-21) PRE_DETAIL_PLACE pin-driver placement repair, kit-specific (hbm_pdie_ucie_colh / coli).
# ucie5f route (hbm_pdie_ucie_colf-ucie5f-b5f0313fd, TT -341.65): GPL scattered the 513 pma_tx port drivers (ORFS output
# buffers + resizer wire buffers) across the S strip, median 78.5 / max 250.8 um from their ports (worst PMA_TX484 driver
# at (3.24,4.05) for a port at (249.04,0.04): 517.7 ps final wire).  The nets are macro pin -> buffers -> port only (no
# logic, no flop), so GPL had nothing pulling them home.  Here, after the 3_4 resizer and before DPL, every buffer of
# each S-face PMA output chain (pma_tx[*], pma_tck) is put on the straight segment from its port to its u_ptx macro pin,
# nearest-to-port first; DPL then legalises locally.  No netlist edit, no new cell, PMA macro / clock contract unchanged.
set ot_tb [ord::get_db_block]
set ot_td [$ot_tb getDbUnitsPerMicron]
set ot_tn 0; set ot_tc 0; set ot_tmax 0.0
foreach ot_bt [$ot_tb getBTerms] {
  set ot_nm [$ot_bt getName]
  if {[string first {pma_tx[} $ot_nm] != 0 && $ot_nm ne {pma_tck}} continue
  set ot_px 0; set ot_py 0
  foreach ot_bp [$ot_bt getBPins] { foreach ot_bx [$ot_bp getBoxes] {
    set ot_px [expr {([$ot_bx xMin]+[$ot_bx xMax])/2}]; set ot_py [expr {([$ot_bx yMin]+[$ot_bx yMax])/2}] } }
  set ot_net [$ot_bt getNet]
  set ot_chain {}; set ot_mx {}; set ot_my {}
  for {set ot_k 0} {$ot_k < 24} {incr ot_k} {
    set ot_drv {}
    foreach ot_it [$ot_net getITerms] { if {[$ot_it isOutputSignal]} { set ot_drv $ot_it } }
    if {$ot_drv eq {}} break
    set ot_in [$ot_drv getInst]
    if {[[$ot_in getMaster] isBlock]} {
      set ot_r [$ot_drv getBBox]
      set ot_mx [expr {([$ot_r xMin]+[$ot_r xMax])/2}]; set ot_my [expr {([$ot_r yMin]+[$ot_r yMax])/2}]
      break
    }
    set ot_ins {}
    foreach ot_it [$ot_in getITerms] { if {[$ot_it isInputSignal] && [$ot_it getNet] ne {NULL} && [$ot_it getNet] ne {}} { lappend ot_ins $ot_it } }
    if {[llength $ot_ins] != 1} break
    lappend ot_chain $ot_in
    set ot_net [[lindex $ot_ins 0] getNet]
  }
  if {$ot_mx eq {} || [llength $ot_chain] == 0} continue
  set ot_n [llength $ot_chain]
  set ot_j 0
  foreach ot_in $ot_chain {
    incr ot_j
    set ot_t [expr {double($ot_j) / ($ot_n + 1)}]
    set ot_m [$ot_in getMaster]
    set ot_x [expr {round($ot_px + $ot_t*($ot_mx-$ot_px) - [$ot_m getWidth]/2.0)}]
    set ot_y [expr {round($ot_py + $ot_t*($ot_my-$ot_py) - [$ot_m getHeight]/2.0)}]
    set ot_bb [$ot_in getBBox]
    set ot_d [expr {(abs([$ot_bb xMin]-$ot_x)+abs([$ot_bb yMin]-$ot_y))/double($ot_td)}]
    if {$ot_d > $ot_tmax} { set ot_tmax $ot_d }
    $ot_in setLocation $ot_x [expr {max($ot_y, 0)}]
    $ot_in setPlacementStatus PLACED
    incr ot_tc
  }
  incr ot_tn
}
if {$ot_tn < 513} { error "UCIE6_TXDRV expected >= 513 PMA output chains (pma_tx), placed $ot_tn" }
puts [format "UCIE6_TXDRV %d PMA output chains, %d buffers put on their port->macro segment (max move %.1f um)" $ot_tn $ot_tc $ot_tmax]

# UCIE7 (HBM-OWN/PHY2 10-21) PRE_GLOBAL_PLACE pin_hook_after_flops, kit-specific (hbm_pdie_ucie_colk / colm).
# coli/colj/colg gates FAILED the ck_rck boundary pin-flop spread (93.6 / 91.5 / 84 ps TT > 80): the rck region's only
# boundary flop is the rst_rck reset synchroniser u_lpr_rck (2 stages), which io_flop_at_pins fixed at the N pin,
# 260-430 um above the rck register mass (u_prr / u_rm write side beside the rxm top, pma_rck macro pin, SRAM wclk).
# Its lone CTS branch arrived 59-94 ps after the macro boundary pin.  Structural landing: the synchroniser pair is
# placed IN the rck region (just above the rxm pma_rck pin, in the PMA-top channel), so it shares the rck mass's
# local tree; the reset port wire (quasi-static, in->reg slack +436 ps at 216 um) is the repeated input hop, capped
# at 380 um (< 405 reach).  No netlist edit, no new cell, PMA / clock / reset contract unchanged.  The pair is FIRM
# through GPL + resizer (so the port wire is buffered for its true length) and re-targeted to the measured rck sink
# median + released for DPL by hbm_pdie_ucie_rck_rst_land.tcl.
set ot_rb [ord::get_db_block]
set ot_rd [$ot_rb getDbUnitsPerMicron]
set ot_rprx [$ot_rb findInst u_prx]
if {$ot_rprx eq "NULL" || $ot_rprx eq ""} { error "UCIE7_RCK_RST no u_prx" }
set ot_rbb [$ot_rprx getBBox]
set ot_rpin [$ot_rb findBTerm rst_rck]
if {$ot_rpin eq "NULL" || $ot_rpin eq ""} { error "UCIE7_RCK_RST no rst_rck port" }
set ot_rpy 0
foreach ot_bp [$ot_rpin getBPins] { foreach ot_bx [$ot_bp getBoxes] { set ot_rpy [expr {([$ot_bx yMin]+[$ot_bx yMax])/2}] } }
# seed: 16 um right of the rxm pma_rck pin (local x 4.75), 13.4 um above the rxm top (5.4 halo + 8)
set ot_rx [expr {[$ot_rbb xMin] + round(20.75*$ot_rd)}]
set ot_ry [expr {[$ot_rbb yMax] + round(13.4*$ot_rd)}]
set ot_rymin [expr {$ot_rpy - round(380.0*$ot_rd)}]
if {$ot_ry < $ot_rymin} { set ot_ry $ot_rymin }
set ot_rl {}
foreach ot_ri [$ot_rb getInsts] {
  if {[string match {u_lpr_rck.*} [string map {\\ {}} [$ot_ri getName]]] && ![[$ot_ri getMaster] isBlock]} { lappend ot_rl $ot_ri }
}
if {[llength $ot_rl] != 2} { error "UCIE7_RCK_RST expected 2 u_lpr_rck synchroniser flops, found [llength $ot_rl]" }
set ot_rk 0
foreach ot_ri [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} $ot_rl] {
  $ot_ri setPlacementStatus PLACED
  $ot_ri setLocation [expr {$ot_rx + $ot_rk*round(2.16*$ot_rd)}] $ot_ry
  $ot_ri setPlacementStatus FIRM
  puts [format "UCIE7_RCK_RST seed %s at (%.2f, %.2f) FIRM (rst_rck pin y %.2f)" [$ot_ri getName] [expr {double($ot_rx + $ot_rk*round(2.16*$ot_rd))/$ot_rd}] [expr {double($ot_ry)/$ot_rd}] [expr {double($ot_rpy)/$ot_rd}]]
  incr ot_rk
}

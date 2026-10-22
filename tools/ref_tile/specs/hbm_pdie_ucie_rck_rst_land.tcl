# UCIE7 (HBM-OWN/PHY2 10-21) PRE_DETAIL_PLACE: land the rst_rck synchroniser pair u_lpr_rck at the measured median of
# the ck_rck register mass (all other ck_rck std-cell sinks after GPL + resizer), y capped 380 um below the rst_rck pin
# (reach) and >= 50 um below it (clear of the N rx face band); released PLACED so DPL legalises it locally.
# Pairs with hbm_pdie_ucie_rck_rst_seed.tcl (PRE_GLOBAL_PLACE).  No netlist edit.
set ot_lb [ord::get_db_block]
set ot_ld [$ot_lb getDbUnitsPerMicron]
set ot_lpin [$ot_lb findBTerm rst_rck]
set ot_lpy 0
foreach ot_bp [$ot_lpin getBPins] { foreach ot_bx [$ot_bp getBoxes] { set ot_lpy [expr {([$ot_bx yMin]+[$ot_bx yMax])/2}] } }
set ot_lck [[$ot_lb findBTerm ck_rck] getNet]
set ot_lxs {}; set ot_lys {}; set ot_lpair {}
foreach ot_it [$ot_lck getITerms] {
  set ot_li [$ot_it getInst]
  if {[[$ot_li getMaster] isBlock]} continue
  if {[string match {u_lpr_rck.*} [string map {\\ {}} [$ot_li getName]]]} continue
  set ot_bb [$ot_li getBBox]
  lappend ot_lxs [expr {([$ot_bb xMin]+[$ot_bb xMax])/2}]
  lappend ot_lys [expr {([$ot_bb yMin]+[$ot_bb yMax])/2}]
}
foreach ot_li [$ot_lb getInsts] {
  if {[string match {u_lpr_rck.*} [string map {\\ {}} [$ot_li getName]]] && ![[$ot_li getMaster] isBlock]} { lappend ot_lpair $ot_li }
}
if {[llength $ot_lpair] != 2} { error "UCIE7_RCK_LAND expected 2 u_lpr_rck flops, found [llength $ot_lpair]" }
if {[llength $ot_lxs] < 100} { error "UCIE7_RCK_LAND only [llength $ot_lxs] ck_rck std-cell sinks on the port net (clock net buffered before DPL?)" }
set ot_lxs [lsort -integer $ot_lxs]; set ot_lys [lsort -integer $ot_lys]
set ot_lm [expr {[llength $ot_lxs]/2}]
set ot_tx [lindex $ot_lxs $ot_lm]; set ot_ty [lindex $ot_lys $ot_lm]
set ot_lymin [expr {$ot_lpy - round(380.0*$ot_ld)}]
set ot_lymax [expr {$ot_lpy - round(50.0*$ot_ld)}]
if {$ot_ty < $ot_lymin} { set ot_ty $ot_lymin }
if {$ot_ty > $ot_lymax} { set ot_ty $ot_lymax }
set ot_k 0
foreach ot_li [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} $ot_lpair] {
  set ot_ob [$ot_li getBBox]
  set ot_x [expr {$ot_tx + $ot_k*round(2.16*$ot_ld)}]
  $ot_li setPlacementStatus PLACED
  $ot_li setLocation $ot_x $ot_ty
  puts [format "UCIE7_RCK_LAND %s (%.2f, %.2f) -> (%.2f, %.2f) PLACED; rck median of %d sinks, rst_rck pin y %.2f (hop %.1f um)" \
    [$ot_li getName] [expr {double([$ot_ob xMin])/$ot_ld}] [expr {double([$ot_ob yMin])/$ot_ld}] [expr {double($ot_x)/$ot_ld}] \
    [expr {double($ot_ty)/$ot_ld}] [llength $ot_lxs] [expr {double($ot_lpy)/$ot_ld}] [expr {double($ot_lpy-$ot_ty)/$ot_ld}]]
  incr ot_k
}

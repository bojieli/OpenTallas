# Redistribute existing output hold cells before GPL. No cells/nets/stages are added.
# The r2 failures were confined to the eastmost 10.8um despite low global usage.
set rs_blk [ord::get_db_block]
set rs_u [$rs_blk getDbUnitsPerMicron]
set rs_ca [$rs_blk getCoreArea]
set rs_cell_count [llength [$rs_blk getInsts]]
set rs_net_count [llength [$rs_blk getNets]]
set rs_count 0
foreach rs_bt [$rs_blk getBTerms] {
  if {[$rs_bt getIoType] ne "OUTPUT" || [$rs_bt getSigType] ne "SIGNAL"} continue
  set rs_drv ""
  foreach rs_it [[$rs_bt getNet] getITerms] {
    if {[$rs_it isOutputSignal]} { set rs_drv [$rs_it getInst]; break }
  }
  if {$rs_drv eq "" || ![regexp {^ot_ohdrv_([0-9]+)_2$} [$rs_drv getName] -> rs_id]} continue
  set rs_x 0; set rs_y 0
  foreach rs_bp [$rs_bt getBPins] {
    foreach rs_bx [$rs_bp getBoxes] {
      set rs_x [expr {([$rs_bx xMin]+[$rs_bx xMax])/2.0}]
      set rs_y [expr {([$rs_bx yMin]+[$rs_bx yMax])/2.0}]
      break
    }
    break
  }
  if {$rs_x < ([$rs_ca xMin]+[$rs_ca xMax])/2.0} { error "relay hold stagger requires east output pins" }
  scan $rs_id %d rs_index
  set rs_col [expr {$rs_index % 8}]
  foreach rs_name [list "ot_ohdrv_${rs_id}_0" "ot_outhold_${rs_id}_1" "ot_ohdrv_${rs_id}_2"] rs_depth {25.92 17.28 8.64} {
    set rs_i [$rs_blk findInst $rs_name]
    if {$rs_i eq "NULL"} { error "missing existing output hold cell $rs_name" }
    set rs_w [[$rs_i getMaster] getWidth]
    set rs_h [[$rs_i getMaster] getHeight]
    set rs_px [expr {[$rs_ca xMax]-($rs_depth+0.864*$rs_col)*$rs_u-$rs_w}]
    set rs_py [expr {max([$rs_ca yMin],min($rs_y,[$rs_ca yMax]-$rs_h))}]
    if {$rs_px < [$rs_ca xMin]} { error "output hold bands exceed selected core" }
    $rs_i setLocation [expr {round($rs_px)}] [expr {round($rs_py)}]
    $rs_i setPlacementStatus FIRM
    incr rs_count
  }
}
if {[llength [$rs_blk getInsts]] != $rs_cell_count || [llength [$rs_blk getNets]] != $rs_net_count} { error "physical hold redistribution changed cell/net count" }
if {$rs_count == 0} { error "no existing output hold stages found for relay stagger" }
puts "RELAY_HOLD_STAGGER: moved $rs_count existing cells into three eight-column bands; no cell/net/register changes"

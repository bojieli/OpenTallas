# R2 pad only: retain existing netlist and place dedicated output INV/BUF chains
# beside their pins. The standard pin-flop hook anchors registers behind this
# strip. All cells are released for normal detailed placement and timing repair.
set pd_block [ord::get_db_block]
set pd_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set pd_core [$pd_block getCoreArea]
set pd_die [$pd_block getDieArea]
set pd_candidates {}
set pd_maxw 0.0
set pd_seen [dict create]
foreach pd_bt [$pd_block getBTerms] {
  if {[$pd_bt getIoType] ne "OUTPUT"} continue
  set pd_net [$pd_bt getNet]
  if {$pd_net eq "NULL" || [$pd_net getSigType] ne "SIGNAL"} continue
  set pd_chain {}; set pd_ff ""
  for {set pd_hop 0} {$pd_hop < 8} {incr pd_hop} {
    set pd_driver ""
    foreach pd_it [$pd_net getITerms] { if {[$pd_it isOutputSignal]} {set pd_driver $pd_it; break} }
    if {$pd_driver eq ""} break
    set pd_inst [$pd_driver getInst]
    set pd_master [[$pd_inst getMaster] getName]
    if {[string match "DFF*" $pd_master]} {set pd_ff $pd_inst; break}
    if {![regexp {^(INV|BUF)} $pd_master]} break
    # Only dedicated chains: never relocate a driver serving internal logic.
    set pd_loads 0
    foreach pd_it [$pd_net getITerms] {if {[$pd_it isInputSignal]} {incr pd_loads}}
    if {$pd_loads > 1} {set pd_chain {}; break}
    lappend pd_chain $pd_inst
    set pd_in [$pd_inst findITerm A]
    if {$pd_in eq "NULL"} break
    set pd_net [$pd_in getNet]
    if {$pd_net eq "NULL"} break
  }
  if {$pd_ff eq "" || ![llength $pd_chain]} continue
  set pd_box [$pd_bt getBBox]
  set pd_x [expr {([$pd_box xMin]+[$pd_box xMax])/2.0}]
  set pd_y [expr {([$pd_box yMin]+[$pd_box yMax])/2.0}]
  set pd_dist [list [expr {$pd_x-[$pd_die xMin]}] [expr {[$pd_die xMax]-$pd_x}] [expr {$pd_y-[$pd_die yMin]}] [expr {[$pd_die yMax]-$pd_y}]]
  set pd_min [lindex [lsort -real $pd_dist] 0]
  set pd_side [lindex {W E S N} [lsearch -exact $pd_dist $pd_min]]
  set pd_axis [expr {$pd_side in {W E} ? $pd_y : $pd_x}]
  lappend pd_candidates [list $pd_side $pd_axis $pd_x $pd_y $pd_chain]
  foreach pd_inst $pd_chain {set pd_maxw [expr {max($pd_maxw,double([[$pd_inst getMaster] getWidth])/$pd_dbu)}]}
}
if {![llength $pd_candidates]} {error "PAD_DRIVER_STRIP: no dedicated output chain"}
set pd_cols 16
set pd_pitch [expr {$pd_maxw+0.12}]
# Reserve enough room for every existing driver width, plus a clear register band.
set ::env(OT_OFLOP_COLS) 16
set ::env(OT_OFLOP_GAP) [expr {max(8.0,$pd_cols*$pd_pitch+1.0)}]
set pd_cw [expr {double([$pd_core xMax]-[$pd_core xMin])/$pd_dbu}]
set pd_ch [expr {double([$pd_core yMax]-[$pd_core yMin])/$pd_dbu}]
if {$::env(OT_OFLOP_GAP)+$pd_cols*1.28 > $pd_cw/2.0-2.0 || $::env(OT_OFLOP_GAP)+$pd_cols*0.27 > $pd_ch/2.0-2.0} {
  error "PAD_DRIVER_STRIP: existing driver widths leave no separate legal register band"
}
set ::env(OT_OFLOP_AUTO) 0
set pd_ff_helper [expr {[info exists ::env(OT_PAD_DRIVER_FF_HELPER)] ? $::env(OT_PAD_DRIVER_FF_HELPER) : "/src/physical/qwen_die_masters/io_flop_at_pins.tcl"}]
source $pd_ff_helper
foreach pd_side {W E S N} {set pd_count($pd_side) 0}
set pd_fixed {}
foreach pd_row [lsort -real -index 1 $pd_candidates] {
  lassign $pd_row pd_side pd_axis pd_x pd_y pd_chain
  foreach pd_inst $pd_chain {
    set pd_name [$pd_inst getName]
    if {[dict exists $pd_seen $pd_name]} continue
    dict set pd_seen $pd_name 1
    set pd_col [expr {$pd_count($pd_side)%$pd_cols}]
    incr pd_count($pd_side)
    set pd_w [[$pd_inst getMaster] getWidth]
    set pd_h [[$pd_inst getMaster] getHeight]
    set pd_gap [expr {round((0.25+$pd_col*$pd_pitch)*$pd_dbu)}]
    if {$pd_side eq "W"} {set pd_x [expr {[$pd_core xMin]+$pd_gap}];set pd_y [expr {$pd_axis-$pd_h/2.0}]
    } elseif {$pd_side eq "E"} {set pd_x [expr {[$pd_core xMax]-$pd_gap-$pd_w}];set pd_y [expr {$pd_axis-$pd_h/2.0}]
    } elseif {$pd_side eq "S"} {set pd_x [expr {$pd_axis-$pd_w/2.0}];set pd_y [expr {[$pd_core yMin]+round((0.25+$pd_col*0.27)*$pd_dbu)}]
    } else {set pd_x [expr {$pd_axis-$pd_w/2.0}];set pd_y [expr {[$pd_core yMax]-round((0.25+$pd_col*0.27)*$pd_dbu)-$pd_h}]}
    set pd_x [expr {max([$pd_core xMin],min($pd_x,[$pd_core xMax]-$pd_w))}]
    set pd_y [expr {max([$pd_core yMin],min($pd_y,[$pd_core yMax]-$pd_h))}]
    $pd_inst setOrient R0
    $pd_inst setLocation [expr {round($pd_x)}] [expr {round($pd_y)}]
    $pd_inst setPlacementStatus FIRM
    lappend pd_fixed $pd_name
  }
}
# The existing release hook handles this combined list; no cell stays FIRM in DPL.
set pd_file [open $::env(RESULTS_DIR)/ot_out_flop_at_pins.txt a]
foreach pd_name $pd_fixed {puts $pd_file $pd_name}
close $pd_file
puts "PAD_DRIVER_STRIP: [llength $pd_candidates] output ports, [llength $pd_fixed] existing drivers anchored; FF gap $::env(OT_OFLOP_GAP), no cells/nets added"

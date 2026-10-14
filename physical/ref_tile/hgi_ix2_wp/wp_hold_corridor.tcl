# WP r3: preserve the recipe-2 hold circuit, but give every south/north
# output chain three distinct legal rows.  The former coincident FIRM
# BUF/HB/BUF seeds legalised across the launch seam (r2 GRT overflow 132).
# Pack chains by the measured maximum cell width; every lane's x intervals
# are disjoint.  The pin-flop planner then measures this actual hold strip.
set ::env(OT_IOHOLD_IN) 1
set ::env(OT_INHOLD_DRV) BUFx4f_ASAP7_75t_R
set ::env(OT_OFLOP_HOPS) 8
set ::env(OT_OFLOP_ALLOW_NONE) 1
source /src/physical/dsrom_window_source/leaf_iohold.tcl
set wp_blk [ord::get_db_block]
set wp_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set wp_core [$wp_blk getCoreArea]
set wp_site [expr {int(round(0.054 * $wp_dbu))}]
set wp_row [expr {int(round(0.27 * $wp_dbu))}]
set wp_chains(B) {}; set wp_chains(T) {}
foreach wp_inst [$wp_blk getInsts] {
    if {![regexp {^ot_outhold_([0-9]+)_1$} [$wp_inst getName] -> wp_id]} continue
    scan $wp_id %d wp_idx
    set wp_pin_net [$wp_blk findNet [format "ot_outhold_p%05d" $wp_idx]]
    if {$wp_pin_net eq "NULL"} { error "WP hold chain lost its pin net" }
    set wp_bt [lindex [$wp_pin_net getBTerms] 0]
    set wp_x 0; set wp_y 0
    foreach wp_bp [$wp_bt getBPins] {
        foreach wp_box [$wp_bp getBoxes] {
            set wp_x [expr {([$wp_box xMin]+[$wp_box xMax])/2}]
            set wp_y [expr {([$wp_box yMin]+[$wp_box yMax])/2}]
            break
        }
        break
    }
    set wp_bottom [expr {abs($wp_y - [$wp_core yMin])}]
    set wp_top [expr {abs($wp_y - [$wp_core yMax])}]
    set wp_side_dist [expr {min(abs($wp_x - [$wp_core xMin]),abs($wp_x - [$wp_core xMax]))}]
    if {$wp_side_dist < min($wp_bottom,$wp_top)} continue
    set wp_side [expr {$wp_bottom <= $wp_top ? "B" : "T"}]
    lappend wp_chains($wp_side) [list $wp_x $wp_idx]
}
foreach wp_side {B T} {
    set wp_ends {}; set wp_depth 0; set wp_count 0
    foreach wp_item [lsort -integer -index 0 $wp_chains($wp_side)] {
        lassign $wp_item wp_x wp_idx
        set wp_cells [list [$wp_blk findInst [format "ot_ohdrv_%05d_0" $wp_idx]] \
                           [$wp_blk findInst [format "ot_outhold_%05d_1" $wp_idx]] \
                           [$wp_blk findInst [format "ot_ohdrv_%05d_2" $wp_idx]]]
        set wp_width 0
        foreach wp_cell $wp_cells {
            if {$wp_cell eq "NULL"} { error "WP hold chain incomplete" }
            set wp_master [$wp_cell getMaster]
            set wp_width [expr {max($wp_width,[$wp_master getWidth])}]
            if {[$wp_master getHeight] > $wp_row} { error "WP hold master taller than one row" }
        }
        set wp_x [expr {[$wp_core xMin] + int(floor(double($wp_x-[$wp_core xMin])/$wp_site))*$wp_site}]
        set wp_x [expr {max([$wp_core xMin],min($wp_x,[$wp_core xMax]-$wp_width))}]
        set wp_lane 0
        while {$wp_lane < [llength $wp_ends] && $wp_x < [lindex $wp_ends $wp_lane]} { incr wp_lane }
        if {$wp_lane == [llength $wp_ends]} { lappend wp_ends 0 }
        lset wp_ends $wp_lane [expr {$wp_x+$wp_width+$wp_site}]
        set wp_k 0
        foreach wp_cell $wp_cells {
            set wp_inset [expr {(3*$wp_lane+3-$wp_k)*$wp_row}]
            set wp_y [expr {$wp_side eq "B" ? [$wp_core yMin]+$wp_inset : [$wp_core yMax]-$wp_inset-$wp_row}]
            if {$wp_y < [$wp_core yMin] || $wp_y+$wp_row > [$wp_core yMax]} { error "WP hold corridor exceeds core" }
            $wp_cell setLocation $wp_x $wp_y
            $wp_cell setPlacementStatus FIRM
            set wp_depth [expr {max($wp_depth,$wp_inset+$wp_row)}]
            incr wp_k
        }
        incr wp_count
    }
    puts "WP_HOLD_CORRIDOR side=$wp_side chains=$wp_count lanes=[llength $wp_ends] depth_um=[expr {double($wp_depth)/$wp_dbu}]"
}
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl

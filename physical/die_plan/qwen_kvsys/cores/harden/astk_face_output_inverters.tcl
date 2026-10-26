# ASTK6: keep a weak DFF QN and its sole polarity inverter together after
# output face flops move. Run after zone/face guides release, before DPL.
# Selection: sole QN-to-INV sink inside output face bank (the INV may feed
# ordinary output buffers). No logic or timing exception changes. Ordinary placed logic can legalize
# around the selected output chain cells; all flops and fixed cells are reserved.
namespace eval ot_fpi {
    variable occ
    variable site
    variable row
    proc reserve {x0 y0 x1 y1} {
        variable occ; variable site; variable row
        for {set x [expr {int(floor($x0/double($site)))}]} {$x < int(ceil($x1/double($site)))} {incr x} {
            for {set y [expr {int(floor($y0/double($row)))}]} {$y < int(ceil($y1/double($row)))} {incr y} {
                dict set occ "$x,$y" 1
            }
        }
    }
    proc free {x0 y0 x1 y1} {
        variable occ; variable site; variable row
        for {set x [expr {int(floor($x0/double($site)))}]} {$x < int(ceil($x1/double($site)))} {incr x} {
            for {set y [expr {int(floor($y0/double($row)))}]} {$y < int(ceil($y1/double($row)))} {incr y} {
                if {[dict exists $occ "$x,$y"]} {return 0}
            }
        }
        return 1
    }
}
uplevel #0 {
set ot_fpi_b [ord::get_db_block]
set ot_fpi_u [$ot_fpi_b getDbUnitsPerMicron]
set ot_fpi_site [expr {int(round(0.054*$ot_fpi_u))}]
set ot_fpi_core [$ot_fpi_b getCoreArea]
set ::ot_fpi::site $ot_fpi_site
set ::ot_fpi::row [expr {int(round(0.27*$ot_fpi_u))}]
set ::ot_fpi::occ [dict create]
set ot_fpi_row_orient [dict create]
foreach ot_fpi_row [$ot_fpi_b getRows] {
    lassign [$ot_fpi_row getOrigin] ot_fpi_rx ot_fpi_ry
    dict set ot_fpi_row_orient $ot_fpi_ry [$ot_fpi_row getOrient]
}
foreach ot_fpi_i [$ot_fpi_b getInsts] {
    set ot_fpi_m [[$ot_fpi_i getMaster] getName]
    set ot_fpi_s [$ot_fpi_i getPlacementStatus]
    if {![regexp {^DFF} $ot_fpi_m] && $ot_fpi_s ni {FIRM LOCKED FIXED}} {continue}
    set ot_fpi_q [$ot_fpi_i getBBox]
    ot_fpi::reserve [$ot_fpi_q xMin] [$ot_fpi_q yMin] [$ot_fpi_q xMax] [$ot_fpi_q yMax]
}
set ot_fpi_path /work/face_output_inverters.tsv
if {[info exists ::env(OT_FACE_INV_REPORT)]} {set ot_fpi_path $::env(OT_FACE_INV_REPORT)}
set ot_fpi_f [open $ot_fpi_path w]
puts $ot_fpi_f "ff\tinv\tff_x\tff_y\told_x\told_y\tnew_x\tnew_y\told_um\tnew_um\tports"
set ot_fpi_moved 0; set ot_fpi_selected 0; set ot_fpi_missing {}
foreach ot_fpi_inv [$ot_fpi_b getInsts] {
    if {![regexp {^INV} [[$ot_fpi_inv getMaster] getName]]} {continue}
    set ot_fpi_in ""; set ot_fpi_out ""
    foreach ot_fpi_t [$ot_fpi_inv getITerms] {
        set ot_fpi_dir [[$ot_fpi_t getMTerm] getIoType]
        if {$ot_fpi_dir eq "INPUT"} {set ot_fpi_in $ot_fpi_t}
        if {$ot_fpi_dir eq "OUTPUT"} {set ot_fpi_out $ot_fpi_t}
    }
    if {$ot_fpi_in eq "" || $ot_fpi_out eq ""} {continue}
    set ot_fpi_n [$ot_fpi_in getNet]; set ot_fpi_on [$ot_fpi_out getNet]
    if {$ot_fpi_n eq "NULL" || $ot_fpi_on eq "NULL"} {continue}
    if {[llength [$ot_fpi_n getITerms]] != 2 || [llength [$ot_fpi_n getBTerms]] != 0} {continue}
    set ot_fpi_ports {}
    foreach ot_fpi_p [$ot_fpi_on getBTerms] {
        if {[$ot_fpi_p getIoType] eq "OUTPUT"} {lappend ot_fpi_ports [$ot_fpi_p getName]}
    }
        set ot_fpi_ff ""
    foreach ot_fpi_t [$ot_fpi_n getITerms] {
        if {[[$ot_fpi_t getMTerm] getName] eq "QN" && [regexp {^DFF} [[[$ot_fpi_t getInst] getMaster] getName]]} {
            set ot_fpi_ff [$ot_fpi_t getInst]
        }
    }
    if {$ot_fpi_ff eq ""} {continue}
    if {![string match {*g_tc_faces.u_qo_face/*} [$ot_fpi_ff getName]]} {continue}
    incr ot_fpi_selected
    # Include the private output buffers: moving just the polarity INV
    # leaves its own weak Y wire stretched back to the old controller.
    set ot_fpi_chain [list $ot_fpi_inv]
    set ot_fpi_walk $ot_fpi_on
    for {set ot_fpi_depth 0} {$ot_fpi_depth < 8} {incr ot_fpi_depth} {
        if {[llength [$ot_fpi_walk getBTerms]]} {break}
        set ot_fpi_loads {}
        foreach ot_fpi_t [$ot_fpi_walk getITerms] {
            if {[[$ot_fpi_t getMTerm] getIoType] eq "INPUT"} {lappend ot_fpi_loads $ot_fpi_t}
        }
        if {[llength $ot_fpi_loads] != 1 || [llength [$ot_fpi_walk getITerms]] != 2} {break}
        set ot_fpi_next [[lindex $ot_fpi_loads 0] getInst]
        if {![regexp {^(BUF|INV)} [[$ot_fpi_next getMaster] getName]]} {break}
        set ot_fpi_nextnet ""
        foreach ot_fpi_t [$ot_fpi_next getITerms] {
            if {[[$ot_fpi_t getMTerm] getIoType] eq "OUTPUT"} {set ot_fpi_nextnet [$ot_fpi_t getNet]}
        }
        if {$ot_fpi_nextnet eq "" || $ot_fpi_nextnet eq "NULL"} {break}
        lappend ot_fpi_chain $ot_fpi_next
        set ot_fpi_walk $ot_fpi_nextnet
    }
    foreach ot_fpi_inv $ot_fpi_chain {
    set ot_fpi_fb [$ot_fpi_ff getBBox]; set ot_fpi_ib [$ot_fpi_inv getBBox]
    set ot_fpi_fx [expr {([$ot_fpi_fb xMin]+[$ot_fpi_fb xMax])/2.0}]
    set ot_fpi_fy [expr {([$ot_fpi_fb yMin]+[$ot_fpi_fb yMax])/2.0}]
    set ot_fpi_ox [expr {([$ot_fpi_ib xMin]+[$ot_fpi_ib xMax])/2.0}]
    set ot_fpi_oy [expr {([$ot_fpi_ib yMin]+[$ot_fpi_ib yMax])/2.0}]
    set ot_fpi_old [expr {(abs($ot_fpi_ox-$ot_fpi_fx)+abs($ot_fpi_oy-$ot_fpi_fy))/$ot_fpi_u}]
    set ot_fpi_nx $ot_fpi_ox; set ot_fpi_ny $ot_fpi_oy
    if {$ot_fpi_old > 2.0} {
        set ot_fpi_w [[$ot_fpi_inv getMaster] getWidth]
        set ot_fpi_h [[$ot_fpi_inv getMaster] getHeight]
        set ot_fpi_y [$ot_fpi_fb yMin]
        set ot_fpi_target ""
        # Nearest legal row; same row preferred, then up to eight neighboring rows. Search gaps beside
        # the actual flop bank, never displacing another flop/fixed cell.
        foreach ot_fpi_dy {0 1 -1 2 -2 3 -3 4 -4 5 -5 6 -6 7 -7 8 -8} {
        set ot_fpi_y [expr {[$ot_fpi_fb yMin]+$ot_fpi_dy*$::ot_fpi::row}]
        if {$ot_fpi_y < [$ot_fpi_core yMin] || $ot_fpi_y+$ot_fpi_h > [$ot_fpi_core yMax]} {continue}
        if {![dict exists $ot_fpi_row_orient $ot_fpi_y]} {continue}
        for {set ot_fpi_dx 0} {$ot_fpi_dx <= 160 && $ot_fpi_target eq ""} {incr ot_fpi_dx} {
            foreach ot_fpi_x [list [expr {[$ot_fpi_fb xMax]+($ot_fpi_dx+1)*$ot_fpi_site}] [expr {[$ot_fpi_fb xMin]-$ot_fpi_w-($ot_fpi_dx+1)*$ot_fpi_site}]] {
                set ot_fpi_x [expr {int(round($ot_fpi_x/double($ot_fpi_site)))*$ot_fpi_site}]
                if {$ot_fpi_x < [$ot_fpi_core xMin] || $ot_fpi_x+$ot_fpi_w > [$ot_fpi_core xMax]} {continue}
                if {[ot_fpi::free $ot_fpi_x $ot_fpi_y [expr {$ot_fpi_x+$ot_fpi_w}] [expr {$ot_fpi_y+$ot_fpi_h}]]} {
                    set ot_fpi_target [list $ot_fpi_x $ot_fpi_y [dict get $ot_fpi_row_orient $ot_fpi_y]]; break
                }
            }
        }
        if {$ot_fpi_target ne ""} {break}
        }
        if {$ot_fpi_target eq ""} {lappend ot_fpi_missing [$ot_fpi_inv getName]; continue}
        $ot_fpi_inv setPlacementStatus PLACED
        $ot_fpi_inv setOrient [lindex $ot_fpi_target 2]
        $ot_fpi_inv setLocation 0 0
        set ot_fpi_q [$ot_fpi_inv getBBox]
        $ot_fpi_inv setLocation [expr {[lindex $ot_fpi_target 0]-[$ot_fpi_q xMin]}] [expr {[lindex $ot_fpi_target 1]-[$ot_fpi_q yMin]}]
        $ot_fpi_inv setPlacementStatus FIRM
        set ot_fpi_q [$ot_fpi_inv getBBox]
        ot_fpi::reserve [$ot_fpi_q xMin] [$ot_fpi_q yMin] [$ot_fpi_q xMax] [$ot_fpi_q yMax]
        set ot_fpi_nx [expr {([$ot_fpi_q xMin]+[$ot_fpi_q xMax])/2.0}]
        set ot_fpi_ny [expr {([$ot_fpi_q yMin]+[$ot_fpi_q yMax])/2.0}]
        incr ot_fpi_moved
    }
    set ot_fpi_new [expr {(abs($ot_fpi_nx-$ot_fpi_fx)+abs($ot_fpi_ny-$ot_fpi_fy))/$ot_fpi_u}]
    puts $ot_fpi_f "[$ot_fpi_ff getName]\t[$ot_fpi_inv getName]\t[expr {$ot_fpi_fx/$ot_fpi_u}]\t[expr {$ot_fpi_fy/$ot_fpi_u}]\t[expr {$ot_fpi_ox/$ot_fpi_u}]\t[expr {$ot_fpi_oy/$ot_fpi_u}]\t[expr {$ot_fpi_nx/$ot_fpi_u}]\t[expr {$ot_fpi_ny/$ot_fpi_u}]\t$ot_fpi_old\t$ot_fpi_new\t$ot_fpi_ports"
    }
}
close $ot_fpi_f
puts "OT_FACE_OUTPUT_INVERTERS selected=$ot_fpi_selected moved=$ot_fpi_moved missing=[llength $ot_fpi_missing] report=$ot_fpi_path"
if {[llength $ot_fpi_missing]} {error "no legal local-row output-chain site near face FF: [lrange $ot_fpi_missing 0 7]"}
}

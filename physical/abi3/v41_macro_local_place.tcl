# POST_MACRO_PLACE hook for a one-SRAM VM or MP1 ME local physical cut.
# It fixes only the producer/first-capture registers beside the selected
# macro's real M4 pin sides. Any orientation other than R0 is rejected.
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set macro {}
foreach inst [$block getInsts] {
    if {[string match *u_sram [$inst getName]]} { lappend macro $inst }
}
if {[llength $macro] != 1} { error "local cut requires one u_sram, found [llength $macro]" }
set macro [lindex $macro 0]
if {[$macro getOrient] ne "R0"} { error "local pin-side plan requires R0, got [$macro getOrient]" }
set box [$macro getBBox]
set mx [expr {double([$box xMin])/$dbu}]
set my [expr {double([$box yMin])/$dbu}]
set mw [expr {double([$box xMax]-[$box xMin])/$dbu}]
set kind [expr {$mw > 130.0 ? "vm" : "me"}]
set left {}
set right {}
foreach inst [$block getInsts] {
    set n [$inst getName]
    set master [$inst getMaster]
    if {![string match *DFF* [$master getName]]} { continue }
    set side {}
    if {$kind eq "vm"} {
        if {[regexp {wr_local_mask_q\[} $n]} {
            set side right
        } elseif {[regexp {wr_local_data_q\[([0-9]+)\]} $n -> bit]} {
            set side [expr {$bit < 70 ? "left" : "right"}]
        } elseif {[regexp {(rd_capture|rd_v_q|rd_group_q|rd_row_q|wr_local_en_q|wr_local_row_q|wr_v_q|wr_group_q|wr_row_q)} $n]} {
            set side left
        } elseif {[regexp {wr_mask_q\[} $n]} {
            set side right
        } elseif {[regexp {wr_data_q\[([0-9]+)\]} $n -> bit]} {
            set side [expr {$bit < 70 ? "left" : "right"}]
        }
    } else {
        if {[regexp {wm_q\[} $n]} {
            set side right
        } elseif {[regexp {(q_local_r|pre_v_r|pre_e_r|pre_d_r|rq_v_r|rq_q_r|rq_plg_r|hit_q|wa_q|wd_q)} $n]} {
            set side left
        }
    }
    if {$side eq "left"} { lappend left $n }
    if {$side eq "right"} { lappend right $n }
}
set left [lsort -dictionary $left]
set right [lsort -dictionary $right]
set ncol_left [expr {$kind eq "vm" ? 16 : 22}]
set ncol_right [expr {$kind eq "vm" ? 14 : 18}]
set x_pitch 1.296
set y_pitch 0.540
set ybase [expr {$my+2.0}]
set placed 0
foreach n $left {
    set col [expr {$placed % $ncol_left}]
    set row [expr {$placed / $ncol_left}]
    set x [expr {$mx - 1.5 - ($col+1)*$x_pitch}]
    set y [expr {$ybase+$row*$y_pitch}]
    place_inst -name $n -location "$x $y" -status FIRM
    incr placed
}
set placed 0
foreach n $right {
    set col [expr {$placed % $ncol_right}]
    set row [expr {$placed / $ncol_right}]
    set x [expr {$mx+$mw+1.5+$col*$x_pitch}]
    set y [expr {$ybase+$row*$y_pitch}]
    place_inst -name $n -location "$x $y" -status FIRM
    incr placed
}
puts "OT_LOCAL_PLACE kind=$kind macro=[$macro getName] origin=${mx},${my} width=$mw left=[llength $left] right=[llength $right]"
if {[llength $left] < 100 || [llength $right] < 40} {
    error "local cut did not retain required left/right registered payload"
}

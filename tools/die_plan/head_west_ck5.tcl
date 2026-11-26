# Exact HEAD West ff95 native post-tap seats, after stock cap and reset affinity.
# Names and coordinates pin the reviewed native placement. No clock connection changes.
namespace eval ::ot_hdwest_ck5 {
variable seats {
    {{u_rg2.u_lfan.g_l3.g_n3\[0\].n3_r$_DFF_PN0_} DFFASRHQNx1_ASAP7_75t_R clk_t12 {787296 610208} {439992 736830} MX 473923 {441936 665550} R180}
    {{u_rg1.u_lfan.g_leaf\[2\].leaf_r$_DFF_PN0_} DFFASRHQNx1_ASAP7_75t_R clk_t51 {441696 759264} {63396 640980} R0 496312 {147690 652320} MY}
    {{u_rg1.u_txl.g_tx\[1\].g_safe_write.u_m.g_slice\[23\].valid_r$_DFF_PN0_} DFFASRHQNx1_ASAP7_75t_R clk_t54 {25440 884512} {59022 548370} MX 369727 {} -}
    {{u_rg1.u_ltree.g_local\[24\].local_r$_DFF_PN0__rtap_clk_t54} DFFASRHQNx1_ASAP7_75t_R clk_t54 {25440 884512} {56673 530145} R0 385516 {} -}
    {{u_rg2.u_txl.g_tx\[2\].g_safe_write.u_m.g_slice\[3\].forwarded\[0\]$_DFFE_PP_} DFFHQNx1_ASAP7_75t_R clk_t10 {93856 597216} {457650 567810} R180 394047 {} -}
    {{u_rg1.u_ltree.g_local\[11\].local_r$_DFF_PN0_} DFFASRHQNx1_ASAP7_75t_R clk_t18 {199200 644768} {58914 536760} R0 248022 {} -}
}
proc box {o} {
    set r [$o getBBox]
    return [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
}
proc overlap {a b} {
    lassign $a ax ay az aw
    lassign $b bx by bz bw
    expr {$ax<$bz && $az>$bx && $ay<$bw && $aw>$by}
}
proc ck_distance {pin xy} {
    lassign [$pin getAvgXY] valid x y
    if {!$valid} { error "HEAD West CK5: clock pin has no placed shape" }
    lassign $xy px py
    expr {abs($x-$px)+abs($y-$py)}
}
proc long_clock_receivers {block} {
    set long {}
    foreach root [$block getBTerms] {
        if {![regexp {^(clk(_t[0-9]+|_c[0-9]+)?|fclk_in_coll_i[012])$} [$root getName]]} {continue}
        set net [$root getNet]
        if {$net eq "NULL"} {continue}
        lassign [box $root] a b c d
        set xy [list [expr {($a+$c)/2}] [expr {($b+$d)/2}]]
        foreach pin [$net getITerms] {
            set t [$pin getMTerm]
            if {[$t getIoType] ne "INPUT"} {continue}
            if {[$t getSigType] ne "CLOCK" && ![regexp -nocase {^(clk|clkn|ck|gclk|clock)$} [$t getName]]} {continue}
            if {[ck_distance $pin $xy] > 405000} {lappend long [[$pin getInst] getName]}
        }
    }
    return [lsort -unique $long]
}
proc run {} {
    variable seats
    set block [ord::get_db_block]
    if {[$block getDbUnitsPerMicron] != 1000} { error "HEAD West CK5: unexpected DBU scale" }
    set expected_long {}
    foreach row $seats { if {[lindex $row 7] ne {}} { lappend expected_long [lindex $row 0] } }
    if {[long_clock_receivers $block] ne [lsort $expected_long]} {
        error "HEAD West CK5: native over-405 receiver census differs from ff95"
    }
    set pending {}
    foreach row $seats {
        lassign $row name master tap tap_xy old old_ori expected_dbu new new_ori
        set inst [$block findInst $name]
        set root [$block findBTerm $tap]
        if {$inst eq "NULL" || $root eq "NULL" || [[$inst getMaster] getName] ne $master} {
            error "HEAD West CK5: exact clock receiver changed $name $tap"
        }
        set pin [$inst findITerm CLK]
        if {$pin eq "NULL" || [$pin getNet] ne [$root getNet]} {
            error "HEAD West CK5: owning tap changed $name $tap"
        }
        lassign [box $root] x0 y0 x1 y1
        if {[list [expr {($x0+$x1)/2}] [expr {($y0+$y1)/2}]] ne $tap_xy} {
            error "HEAD West CK5: bridge tap origin changed $tap"
        }
        set old_dbu [ck_distance $pin $tap_xy]
        if {[$inst getLocation] ne $old || [$inst getOrient] ne $old_ori ||
            [$inst getPlacementStatus] ne "PLACED" || $old_dbu != $expected_dbu} {
            error "HEAD West CK5: original detailed-placement site changed $name"
        }
        if {$new eq {}} {continue}
        lassign $new x y
        lassign [box $inst] a b c d
        set rect [list $x $y [expr {$x+$c-$a}] [expr {$y+$d-$b}]]
        set legal 0
        foreach ordrow [$block getRows] {
            lassign [box $ordrow] r0 r1 r2 r3
            if {$r1!=$y || [lindex $rect 3]>$r3 || $x<$r0 || [lindex $rect 2]>$r2} {continue}
            set site [$ordrow getSite]
            if {($x-$r0)%[$site getWidth]} {continue}
            set allowed [expr {[$ordrow getOrient] eq "R0" ? [list R0 MY] : [list MX R180]}]
            if {$new_ori in $allowed} {set legal 1; break}
        }
        if {!$legal} {error "HEAD West CK5: requested site left a legal row $name"}
        foreach blockage [$block getBlockages] {
            if {![$blockage isSoft] && [overlap $rect [box $blockage]]} {
                error "HEAD West CK5: new seat intersects blockage $name"
            }
        }
        foreach row2 $pending {
            if {[overlap $rect [lindex $row2 end]]} {error "HEAD West CK5: target seats overlap $name"}
        }
        lappend pending [list $inst $pin $tap_xy $old_dbu $new $new_ori $rect]
    }
    foreach other [$block getInsts] {
        if {[$other getPlacementStatus] in {UNPLACED NONE SUGGESTED}} {continue}
        set region [box $other]
        if {[[$other getMaster] isBlock]} {
            lassign $region a b c d
            set region [list [expr {$a-9000}] [expr {$b-9000}] [expr {$c+9000}] [expr {$d+9000}]]
        }
        foreach req $pending {
            if {$other ne [lindex $req 0] && [overlap [lindex $req end] $region]} {
                error "HEAD West CK5: requested seat occupied by [$other getName]"
            }
        }
    }
    foreach req $pending {
        lassign $req inst pin tap_xy old_dbu new new_ori rect
        $inst setOrient $new_ori
        $inst setLocation {*}$new
        $inst setPlacementStatus FIRM
        set new_dbu [ck_distance $pin $tap_xy]
        if {$new_dbu>399500 || [box $inst] ne $rect} {
            error "HEAD West CK5: native new clock pin or footprint changed [$inst getName]"
        }
        puts "OT_HEAD_WEST_CK5 [$inst getName] $old_dbu -> $new_dbu DBU"
    }
    if {[llength [long_clock_receivers $block]]} {error "HEAD West CK5: a clock leg still exceeds 405 um"}
}
}
::ot_hdwest_ck5::run

# Exact HEAD West d51 native post-tap seats, after stock cap and reset affinity.
# Names and coordinates pin the reviewed native placement. No clock connection changes.
namespace eval ::ot_hdwest_ck5 {
variable seats {
    {{u_rg1.u_lfan.g_leaf\[2\].leaf_r$_DFF_PN0_} DFFASRHQNx1_ASAP7_75t_R clk_t51 {441696 759264} {25110 693900} R0 {106110 693900} MY}
    {{u_rg1.u_txl.g_tx\[1\].g_safe_write.u_m.g_slice\[23\].valid_r$_DFF_PN0_} DFFASRHQNx1_ASAP7_75t_R clk_t54 {25440 884512} {25056 429570} MX {25110 485190} MX}
    {{u_rg1.u_ltree.g_local\[24\].local_r$_DFF_PN0__rtap_clk_t54} DFFASRHQNx1_ASAP7_75t_R clk_t54 {25440 884512} {32778 464940} R0 {31320 490860} R0}
    {{u_rg2.u_txl.g_tx\[2\].g_safe_write.u_m.g_slice\[3\].forwarded\[0\]$_DFFE_PP_} DFFHQNx1_ASAP7_75t_R clk_t8 {89632 528096} {457488 568080} MY {454032 562950} MX}
    {{u_rg1.u_ltree.g_local\[11\].local_r$_DFF_PN0_} DFFASRHQNx1_ASAP7_75t_R clk_t53 {25440 867232} {52542 486270} MX {52380 494640} R0}
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
proc run {} {
    variable seats
    set block [ord::get_db_block]
    if {[$block getDbUnitsPerMicron] != 1000} { error "HEAD West CK5: unexpected DBU scale" }
    set pending {}
    foreach row $seats {
        lassign $row name master tap tap_xy old old_ori new new_ori
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
        if {$old_dbu<=399500} { continue }
        if {[$inst getLocation] ne $old || [$inst getOrient] ne $old_ori ||
            [$inst getPlacementStatus] ne "PLACED"} {
            error "HEAD West CK5: original detailed-placement site changed $name"
        }
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
}
}
::ot_hdwest_ck5::run

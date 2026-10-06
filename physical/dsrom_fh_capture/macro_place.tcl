# Source-sized G4W16:64 real protected lane macros, one per independently
# masked FP32 lane. Local raw/correction/encoding flops stay with their macro.
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set row0 [lindex [$block getRows] 0]
set org [$row0 getOrigin]
set x0 [expr {double([lindex $org 0])/$dbu}]
set y0 [expr {double([lindex $org 1])/$dbu}]
set xp [expr {double([[$row0 getSite] getWidth])/$dbu}]
set yp [expr {double([[$row0 getSite] getHeight])/$dbu}]
proc joint_snap {v o pitch} {
    set c [expr {round(($v-$o)/$pitch)}]
    for {set d 0} {$d<1000} {incr d} {
        foreach k [list [expr {$c+$d}] [expr {$c-$d}]] {
            set z [expr {$o+$k*$pitch}]
            if {abs($z/0.048-round($z/0.048))<0.00001} {return $z}
        }
    }
    error "No site/M4 joint-grid intersection"
}
set n 0
foreach inst [$block getInsts] {
    if {[[$inst getMaster] getName] ne "ot_sram_1r1w_512x128_m4_r2c2"} {continue}
    set clean [string map [list "\\" ""] [$inst getName]]
    if {![regexp {g_bank\[(\d+)\].*u_sram} $clean -> b]} {error "Unknown macro $clean"}
    set col [expr {$b%8}]
    set row [expr {$b/8}]
    set xx [joint_snap [expr {20.0+$col*240.0}] $x0 $xp]
    set yy [joint_snap [expr {20.0+$row*70.0}] $y0 $yp]
    place_inst -name [$inst getName] -location [list $xx $yy] -orientation R0 -status FIRM
    # One region per lane contains its actual macro, encoder, corrected return
    # and capture registers. The head's shared tag/control stays outside groups.
    set region [odb::dbRegion_create $block "fh_lane_$b"]
    $region setRegionType EXCLUSIVE
    # C20 DPL failed on macro-overlapping, off-site std-cell fences.
    # Keep all fixed macros/pins; use site-aligned rows above BBox + guard5.
    set mb [$inst getBBox]
    set rx1 [expr {int(round(($x0+ceil(($xx-1-$x0)/$xp)*$xp)*$dbu))}]
    set rx2 [expr {int(round(($x0+floor(($xx+225-$x0)/$xp)*$xp)*$dbu))}]
    set ry1 [expr {int(round(($y0+ceil((double([$mb yMax])/$dbu+5-$y0)/$yp)*$yp)*$dbu))}]
    set ry2 [expr {int(round(($y0+floor(($yy+65-$y0)/$yp)*$yp)*$dbu))}]
    if {$rx1 >= $rx2 || $ry1 >= $ry2} {error "No macro-free rows bank=$b"}
    odb::dbBox_create $region $rx1 $ry1 $rx2 $ry2
    set group [odb::dbGroup_create $block "fh_lane_$b"]
    $region addGroup $group
    # The SRAM is already fixed by place_inst. GPL treats a fixed macro in a
    # std-cell fence group as movable area (measured lower-bound density1.88).
    # Group only the local standard cells; the fixed SRAM remains an obstacle
    # in this same lane region (measured lower-bound density0.12).
    foreach cell [$block getInsts] {
        set cn [string map [list "\\" ""] [$cell getName]]
        set local [expr {[string first "g_bank\[$b\].u_lane" $cn]>=0 || [string first "g_bank\[$b\]/u_lane" $cn]>=0}]
        foreach stem {g_fadd g_fused_select g_leaf g_iwg} {
            if {[string first "$stem\[$b\]" $cn]>=0} {set local 1}
        }
        if {[regexp {u_head.*(res_u|o_data1|o_data)\[(\d+)\]} $cn -> kind bit]} {
            if {$bit/32==$b} {set local 1}
        }
        if {[regexp {u_head.*u_rh.*line\[(\d+)\]} $cn -> bit]} {
            if {($bit%2048)/32==$b} {set local 1}
        }
        # Actual native request payload/capture mirror FFs follow the lane.
        if {[regexp {g_request_bank\[(\d+)\].*u_bank.*(q|check)\[(\d+)\]} $cn -> bank kind bit]} {
            set packetbit [expr {$bank*32+$bit}]
            if {$packetbit>=592 && $packetbit<2640 && ($packetbit-592)/32==$b} {set local 1}
        }
        if {$local && $cell ne $inst} {$group addInst $cell}
    }
    puts "FH_CAPTURE_MACRO bank=$b at $xx $yy group=[llength [$group getInsts]]"
    incr n
}
if {$n!=64} {error "Expected64 protected macros, placed$n"}

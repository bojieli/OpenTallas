# Fused-head quadrant (ot_hdc_v41_fh_quad), 610 x 560 um: 16 hardened SRAM lane leaves (200 x 55, pins on the WEST
# edge) in 2 columns x 8 rows, all R0: column A at x=130 (pins face the 130 um west logic channel), column B at x=400
# (pins face the 70 um channel between the columns). 12 um row gaps carry the horizontal routes. Lane l: column l/8,
# row l%8.
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
    if {[[$inst getMaster] getName] ne "ot_hdc_v41_fh_sram_lane_hardened"} {continue}
    set clean [string map [list "\\" ""] [$inst getName]]
    if {![regexp {g_bank\[(\d+)\]} $clean -> l]} {error "Unknown macro $clean"}
    set xx [joint_snap [expr {130.0 + ($l/8)*270.0}] $x0 $xp]
    set yy [joint_snap [expr {12.0 + ($l%8)*67.0}] $y0 $yp]
    place_inst -name [$inst getName] -location [list $xx $yy] -orientation R0 -status FIRM
    incr n
}
if {$n!=16} {error "Expected 16 lane leaves, placed $n"}
puts "FH_QUAD_LEAVES placed=$n"

# Fused-head half quadrant (ot_hdc_v41_fh_hquad), 470 x 300 um: 8 hardened SRAM lane leaves (200 x 55, pins WEST) in
# 2 columns x 4 rows, R0: column A at x=42.7, column B at x=270 (27 um channel between A's east edge and B's pins);
# 70 um row pitch. Lane l: column l/4, row l%4. The group logic sits in the west channel and the row gaps.
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
    # column A at 42.7 (was 40.0, 2026-10-07): at 40.0 the west M4 pins of lanes 0-3 sat under the M5 strap pair at
    # 2.3 + 7 x 5.4 um (pdn_quad.tcl), so read_row[0..1] had no via access: 16 Lef58EolKeepOut in every hquad route
    # (c073b6f60, r5 60f5a0a90). +2.7 um (half the strap pitch) puts them between pairs; column B (270) unchanged.
    set xx [joint_snap [expr {($l/4) ? 270.0 : 42.7}] $x0 $xp]
    set yy [joint_snap [expr {12.0 + ($l%4)*70.0}] $y0 $yp]
    place_inst -name [$inst getName] -location [list $xx $yy] -orientation R0 -status FIRM
    incr n
}
if {$n!=8} {error "Expected 8 lane leaves, placed $n"}
puts "FH_HQUAD_LEAVES placed=$n"

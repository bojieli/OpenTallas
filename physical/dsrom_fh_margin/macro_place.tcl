# Margin-first fused head (MARGIN=1 HARD_LANE=1): 64 protected SRAM lanes, no region fences.
# Group g = columns 2g, 2g+1 (8 rows each); rows 0-3 / 4-7 split by a 60 um control band. Bank b: g=b/16,
# col = 2g + (b%16)/8, row = b%8. 220 um column pitch leaves 46 um for the lane's W/E macro pins and logic.
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
set n 0
foreach inst [$block getInsts] {
    if {[[$inst getMaster] getName] ne "ot_sram_1r1w_512x128_m4_r2c2"} {continue}
    set clean [string map [list "\\" ""] [$inst getName]]
    if {![regexp {g_bank\[(\d+)\].*u_sram} $clean -> b]} {error "Unknown macro $clean"}
    set g [expr {$b/16}]
    set w [expr {$b%16}]
    set col [expr {2*$g + $w/8}]
    set row [expr {$w%8}]
    set xx [joint_snap [expr {30.0+$col*220.0}] $x0 $xp]
    set yy [joint_snap [expr {20.0+$row*70.0+($row>=4?60.0:0.0)}] $y0 $yp]
    place_inst -name [$inst getName] -location [list $xx $yy] -orientation R0 -status FIRM
    incr n
}
if {$n!=64} {error "Expected 64 protected macros, placed $n"}
puts "FH_MARGIN_MACROS placed=$n"

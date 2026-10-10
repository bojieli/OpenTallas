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
 if {[[$inst getMaster] getName] ne "ot_sram_1r1w_128x256_m1_r2c2"} {continue}
 set clean [string map [list "\\" ""] [$inst getName]]
 if {![regexp {banks\[(\d+)\].macros\[(\d+)\]} $clean -> bank col]} {error "Unknown P2 macro $clean"}
 set xx [joint_snap [expr {27.0+$col*125.0}] $x0 $xp]
 set yy [joint_snap [expr {70.0+$bank*56.0}] $y0 $yp]
 place_inst -name [$inst getName] -location [list $xx $yy] -orientation R0 -status FIRM
 incr n
}
if {$n!=12} {error "Expected12 real P2 SRAMs, placed$n"}
puts "P2_MACROS placed=$n"

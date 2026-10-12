# el1011-ds-mtp [p2pfx] ot_p2h_arith: the 3 128x256 SRAMs (pins on their W/E edges, M4) on a fixed grid, sorted by instance
# name (row = bank / memory index, column = macro index), >= 24 um channels and >= 20 um core margins; R0.
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set row0 [lindex [$block getRows] 0]
set org [$row0 getOrigin]
set x0 [expr {double([lindex $org 0])/$dbu}]
set y0 [expr {double([lindex $org 1])/$dbu}]
set xp [expr {double([[$row0 getSite] getWidth])/$dbu}]
set yp [expr {double([[$row0 getSite] getHeight])/$dbu}]
set die [$block getDieArea]
set W [expr {double([$die xMax])/$dbu}]
set H [expr {double([$die yMax])/$dbu}]
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
set ms {}
foreach inst [$block getInsts] {
 if {[[$inst getMaster] getName] eq "ot_sram_1r1w_128x256_m1_r2c2"} {lappend ms [list [$inst getName] $inst]}
}
set ms [lsort -index 0 $ms]
set mw 94.824; set mh 41.040
set gx [expr {($W - 3*$mw) / 4.0}]
set gy [expr {($H - 4*$mh) / 5.0}]
if {[llength $ms] != 3} {error "Expected 3 SRAMs, found [llength $ms]"}
set cols {20.16 139.2 258.24}; set rows {20.25}
set n 0
foreach e $ms {
 set inst [lindex $e 1]
 set xx [joint_snap [lindex $cols [expr {$n % 3}]] $x0 $xp]
 set yy [joint_snap [lindex $rows [expr {$n / 3}]] $y0 $yp]
 place_inst -name [$inst getName] -location [list $xx $yy] -orientation R0 -status FIRM
 incr n
}
puts "P2H_MACROS arith placed=$n"

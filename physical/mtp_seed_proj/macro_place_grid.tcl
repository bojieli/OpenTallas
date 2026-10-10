# mtp-lead 2026-10-09: generic grid placement of the 4 real 128x256 activation-buffer SRAMs of ot_dsrom_mtp_seed_ctl
# (bank {i[3],i[0]}): 2 columns x 2 rows centred in the core, sorted by instance name, >= 40 um channels
# between macros (logic + routing), >= 40 um from the left/right pin faces (fp lint: no macro on a pin edge).
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
if {[llength $ms] != 4} {error "Expected 4 seed activation SRAMs, found [llength $ms]"}
set mw 94.824; set mh 41.040
set gx [expr {($W - 2*$mw) / 3.0}]
set gy [expr {($H - 2*$mh) / 3.0}]
if {$gx < 40.0 || $gy < 30.0} {error "outline too small for the 2x2 grid: gx $gx gy $gy"}
set n 0
foreach e $ms {
 set inst [lindex $e 1]
 set col [expr {$n % 2}]; set row [expr {$n / 2}]
 set xx [joint_snap [expr {$gx + $col*($mw+$gx)}] $x0 $xp]
 set yy [joint_snap [expr {$gy + $row*($mh+$gy)}] $y0 $yp]
 place_inst -name [$inst getName] -location [list $xx $yy] -orientation R0 -status FIRM
 incr n
}
puts "SEED_PROJ_MACROS placed=$n grid gx=$gx gy=$gy"

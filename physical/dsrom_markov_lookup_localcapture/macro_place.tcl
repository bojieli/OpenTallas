# Z7: actual macro geometry, direct rd_out -> anchored capture D, no pre-mux.
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set row0 [lindex [$block getRows] 0]
set origin [$row0 getOrigin]
set x0 [expr {double([lindex $origin 0])/$dbu}]
set y0 [expr {double([lindex $origin 1])/$dbu}]
set xp [expr {double([[$row0 getSite] getWidth])/$dbu}]
set yp [expr {double([[$row0 getSite] getHeight])/$dbu}]
proc joint_snap {v o p} {
    set c [expr {round(($v-$o)/$p)}]
    for {set d 0} {$d<1000} {incr d} {
        foreach k [list [expr {$c+$d}] [expr {$c-$d}]] {
            set z [expr {$o+$k*$p}]
            if {abs($z/0.048-round($z/0.048))<0.00001} {return $z}
        }
    }
    error "no site/M4 grid intersection"
}
set macros 0
foreach macro [$block getInsts] {
    if {[[$macro getMaster] getName] ne "ot_rom_4096x274_m8"} {continue}
    set name [string map [list "\\" ""] [$macro getName]]
    if {![regexp {(^|[/\.])m([01])$} $name -> prefix bank]} {error "unexpected macro $name"}
    set mx [joint_snap 16.0 $x0 $xp]
    set my [joint_snap [expr {10.0+72.91*$bank}] $y0 $yp]
    place_inst -name [$macro getName] -location [list $mx $my] -orientation R0 -status FIRM
    puts "MD6_MACRO bank=$bank origin=$mx,$my"
    incr macros
}
if {$macros!=2} {error "expected two macros"}
# Anchor captures after RTL macro placement, before global placement/lint.

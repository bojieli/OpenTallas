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
set captures 0
set seen [dict create]
foreach macro [$block getInsts] {
    if {[[$macro getMaster] getName] ne "ot_rom_4096x274_m8"} {continue}
    set name [string map [list "\\" ""] [$macro getName]]
    if {![regexp {(^|[/\.])m([01])$} $name -> prefix bank]} {error "unexpected macro $name"}
    set mx [joint_snap 16.0 $x0 $xp]
    set my [joint_snap [expr {10.0+72.91*$bank}] $y0 $yp]
    place_inst -name [$macro getName] -location [list $mx $my] -orientation R0 -status FIRM
    set bankcaps 0
    foreach pin [$macro getITerms] {
        set pn [[$pin getMTerm] getName]
        if {![regexp {^rd_out\[([0-9]+)\]$} $pn -> bit] || $bit>=256} {continue}
        set net [$pin getNet]
        if {$net eq "NULL"} {error "missing payload net $name/$pn"}
        set sinks {}
        foreach term [$net getITerms] {
            if {$term eq $pin} {continue}
            if {[[$term getMTerm] getIoType] ne "INPUT"} {continue}
            set cell [$term getInst]
            if {![string match *DFF* [[$cell getMaster] getName]] || [[$term getMTerm] getName] ne "D"} {
                error "pre-capture logic on $name/$pn: [$cell getName]/[[$term getMTerm] getName]"
            }
            lappend sinks $cell
        }
        if {[llength $sinks]!=1} {error "expected one direct capture sink $name/$pn: [llength $sinks]"}
        set cell [lindex $sinks 0]
        if {[dict exists $seen [$cell getName]]} {error "capture reused by multiple ROM payload pins"}
        dict set seen [$cell getName] 1
        set width [expr {double([[$cell getMaster] getWidth])/$dbu}]
        # Four columns of 64 rows in the modeled 12um left landing strip.
        # Stay outside the 3um macro halo; snap to actual standard-cell sites.
        set x [expr {$x0+floor(($mx-4.0-$width-($bit%4)*1.296-$x0)/$xp)*$xp}]
        set y [expr {$y0+round(($my+2.0+($bit/4)*0.540-$y0)/$yp)*$yp}]
        if {$x<2.0 || $x+$width>$mx-3.0} {error "capture landing strip does not fit"}
        place_inst -name [$cell getName] -location [list $x $y] -status FIRM
        incr bankcaps
        incr captures
    }
    if {$bankcaps!=256} {error "bank $bank requires256 direct captures, found$bankcaps"}
    puts "MD6_LOCALCAP bank=$bank origin=$mx,$my direct_captures=$bankcaps"
    incr macros
}
if {$macros!=2 || $captures!=512} {error "Z7 requires two macros and512 local captures"}

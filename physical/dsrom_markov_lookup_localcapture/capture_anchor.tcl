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
    if {[$macro getOrient] ne "R0"} {error "capture anchoring requires R0"}
    set box [$macro getBBox]
    set mx [expr {double([$box xMin])/$dbu}]
    set my [expr {double([$box yMin])/$dbu}]
    set bankcaps 0
    set payload_pins {}
    foreach pin [$macro getITerms] {
        set pn [[$pin getMTerm] getName]
        if {[regexp {^rd_out\[([0-9]+)\]$} $pn -> bit] && $bit<256} {lappend payload_pins [list $bit $pin]}
    }
    set left_rank 0;set right_rank 0
    foreach record [lsort -integer -index 0 $payload_pins] {
        lassign $record bit pin
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
        # Actual M4 q faces:130left+126right. Use each actual pin coordinate.
        set qxy [$pin getAvgXY]
        if {[llength $qxy]!=3 || ![lindex $qxy 0]} {error "missing actual q pin coordinate"}
        set qx [expr {double([lindex $qxy 1])/$dbu}]
        set mw [expr {double([$box xMax]-[$box xMin])/$dbu}]
        if {$qx<$mx+$mw/2} {
            set rank $left_rank;incr left_rank
            set x [expr {$x0+floor(($mx-4.0-$width-($rank%4)*1.296-$x0)/$xp)*$xp}]
            if {$x<2.0 || $x+$width>$mx-3.0} {error "left capture strip does not fit"}
        } else {
            set rank $right_rank;incr right_rank
            set x [expr {$x0+ceil(($mx+$mw+4.0+($rank%4)*1.296-$x0)/$xp)*$xp}]
            if {$x+$width>188.0 || $x<$mx+$mw+3.0} {error "right capture strip does not fit"}
        }
        set y [expr {$y0+round(($my+2.0+($rank/4)*0.540-$y0)/$yp)*$yp}]
        # PG follow-pins were generated on the actual R0/MX row alternation.
        # An R0 cell on an MX row swaps VDD/VSS rails: fail rather than assume.
        set landing_rows {}
        foreach row [$block getRows] {
            set rb [$row getBBox]
            if {abs(double([$rb yMin])/$dbu-$y)<0.00001 &&
                $x>=double([$rb xMin])/$dbu &&
                $x+$width<=double([$rb xMax])/$dbu} {lappend landing_rows $row}
        }
        if {[llength $landing_rows]!=1} {error "capture has no unique actual containing row"}
        set landing_row [lindex $landing_rows 0]
        place_inst -name [$cell getName] -location [list $x $y] \
            -orientation [$landing_row getOrient] -status FIRM
        incr bankcaps
        incr captures
    }
    if {$left_rank!=130 || $right_rank!=126} {error "unexpected actual payload face count"}
    if {$bankcaps!=256} {error "bank $bank requires256 direct captures, found$bankcaps"}
    puts "MD6_LOCALCAP bank=$bank origin=$mx,$my direct_captures=$bankcaps"
    incr macros
}
if {$macros!=2 || $captures!=512} {error "Z7 requires two macros and512 local captures"}

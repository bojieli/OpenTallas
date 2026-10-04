# ot_macro_track_snap.tcl -- orientation-aware macro origin snap and a pre-route pin/track assert.
#
# Shared library for ORFS macro placement hooks (OpenROAD Tcl, OpenDB).  Source it from a hook:
#     source [file join [expr {[info exists ::env(OT_SRC_ROOT)] ? $::env(OT_SRC_ROOT) : "/src"}] \
#                       physical/common/ot_macro_track_snap.tcl]
#
# Why (results/uarch/macro_pin_access_audit_20261003): the catalog abstracts put every M4 signal pin
# centre at local y = 0.012 mod 0.048 um.  A mirror about X maps y -> H - y, so unless the macro height
# H = 0.024 mod 0.048 the MX/R180 copies land 6-18 nm off the M4 tracks, and a hook that snaps every
# origin to "0 mod 0.048" leaves all of them off-track (DRT-0419 on every pin, DRT-0255 after hours of
# detail route).  The legal origin depends on the orientation, the macro's pin offsets, its W/H and the
# platform's track offsets/pitches, so it is computed here from the master (LEF) and the tracks file.
#
# Procedures (all distances given in microns, computed internally in integer DBU):
#   ot_mts::init ?tracks_file?          parse make_tracks (default $::env(MAKE_TRACKS)); called lazily
#   ot_mts::rule master orient          {x {P S} y {P S}}: legal origin residues S mod period P (DBU)
#   ot_mts::snap_origin master orient x y   nearest legal {x y} (um) on the site/row grid
#   ot_mts::place inst x y orient ?status?  snap to the nearest legal origin that overlaps no placed
#                                           macro and stays in the die; set orient, location, status (FIRM)
#   ot_mts::assert_on_track ?-insts L? ?-label S? ?-warn_only?
#       every placed CLASS BLOCK instance: every signal pin centre must lie on a preferred-direction
#       track of its layer, using the block's own track grids (independent of the parsed file and of
#       this library's orientation table).  Prints OT_MACRO_TRACK_ASSERT and errors on any off-track pin.
#
# A pin centre must be exactly on a track (the DRT-0419 condition): a centre at a half DBU never is.
# Rotated orientations (R90 family) are supported by the transform but no catalog abstract has a legal
# origin in them.

namespace eval ot_mts {
    variable tracks      ;# layer -> list of {xoff xpitch yoff ypitch} in DBU
    variable tracks_file ""
    variable cache       ;# master,orient -> rule dict
    array set cache {}
    variable dbu 0
}

proc ot_mts::gcd {a b} { while {$b} { set t [expr {$a % $b}]; set a $b; set b $t }; return $a }
proc ot_mts::lcm {a b} { return [expr {$a / [gcd $a $b] * $b}] }

proc ot_mts::get_dbu {} {
    variable dbu
    if {!$dbu} { set dbu [[ord::get_db_tech] getDbUnitsPerMicron] }
    return $dbu
}

proc ot_mts::init {{file ""}} {
    variable tracks
    variable tracks_file
    if {$file eq ""} {
        if {![info exists ::env(MAKE_TRACKS)] || $::env(MAKE_TRACKS) eq ""} {
            error "ot_mts::init: no tracks file given and MAKE_TRACKS is not set"
        }
        set file $::env(MAKE_TRACKS)
    }
    set dbu [get_dbu]
    array unset tracks
    array set tracks {}
    set fh [open $file r]
    set text [read $fh]
    close $fh
    foreach line [split $text "\n"] {
        if {[regexp {^\s*make_tracks\s+(\S+)\s+-x_offset\s+(\S+)\s+-x_pitch\s+(\S+)\s+-y_offset\s+(\S+)\s+-y_pitch\s+(\S+)} \
                $line -> lay xo xp yo yp]} {
            lappend tracks($lay) [list [expr {round($xo*$dbu)}] [expr {round($xp*$dbu)}] \
                                       [expr {round($yo*$dbu)}] [expr {round($yp*$dbu)}]]
        }
    }
    if {![array size tracks]} { error "ot_mts::init: no make_tracks lines in $file" }
    set tracks_file $file
}

proc ot_mts::ensure_init {} {
    variable tracks_file
    if {$tracks_file eq ""} { init }
}

# Track lines of one layer on one axis as {P residues}: axis y = the horizontal lines' y coordinates.
proc ot_mts::axis_tracks {layer axis} {
    variable tracks
    set pats {}
    foreach t $tracks($layer) {
        lassign $t xo xp yo yp
        if {$axis eq "y"} { lappend pats [list $yo $yp] } else { lappend pats [list $xo $xp] }
    }
    set P 1
    foreach p $pats { set P [lcm $P [lindex $p 1]] }
    set res [dict create]
    foreach p $pats {
        lassign $p off pitch
        for {set k 0} {$k < $P / $pitch} {incr k} { dict set res [expr {($off + $k*$pitch) % $P}] 1 }
    }
    return [list $P [lsort -integer [dict keys $res]]]
}

# Oriented, macro-local box (lower-left of the placed bbox at 0,0), as DEF orientations.
proc ot_mts::xform {x1 y1 x2 y2 orient W H} {
    switch -- $orient {
        R0    { set a [list $x1 $y1]             ; set b [list $x2 $y2] }
        MX    { set a [list $x1 [expr {$H-$y1}]] ; set b [list $x2 [expr {$H-$y2}]] }
        MY    { set a [list [expr {$W-$x1}] $y1] ; set b [list [expr {$W-$x2}] $y2] }
        R180  { set a [list [expr {$W-$x1}] [expr {$H-$y1}]] ; set b [list [expr {$W-$x2}] [expr {$H-$y2}]] }
        R90   { set a [list [expr {$H-$y1}] $x1] ; set b [list [expr {$H-$y2}] $x2] }
        R270  { set a [list $y1 [expr {$W-$x1}]] ; set b [list $y2 [expr {$W-$x2}]] }
        MXR90 { set a [list $y1 $x1]             ; set b [list $y2 $x2] }
        MYR90 { set a [list [expr {$H-$y1}] [expr {$W-$x1}]] ; set b [list [expr {$H-$y2}] [expr {$W-$x2}]] }
        default { error "ot_mts::xform: unknown orientation $orient" }
    }
    lassign $a ax ay
    lassign $b bx by
    return [list [expr {min($ax,$bx)}] [expr {min($ay,$by)}] [expr {max($ax,$bx)}] [expr {max($ay,$by)}]]
}

proc ot_mts::is_signal {mterm} {
    set s [$mterm getSigType]
    return [expr {$s ne "POWER" && $s ne "GROUND"}]
}

# Combine two residue constraints {P S} into one over lcm(P1, P2).
proc ot_mts::meet {c1 c2} {
    lassign $c1 P1 S1
    lassign $c2 P2 S2
    set L [lcm $P1 $P2]
    set a [dict create]; foreach r $S1 { dict set a $r 1 }
    set b [dict create]; foreach r $S2 { dict set b $r 1 }
    set out {}
    for {set r 0} {$r < $L} {incr r} {
        if {[dict exists $a [expr {$r % $P1}]] && [dict exists $b [expr {$r % $P2}]]} { lappend out $r }
    }
    return [list $L $out]
}

# Legal origin residues for one master in one orientation: {x {P S} y {P S}} in DBU.
# Every signal pin shape on a layer with tracks constrains the axis across its preferred direction.
proc ot_mts::rule {master orient} {
    variable cache
    variable tracks
    ensure_init
    set key "[$master getName],$orient"
    if {[info exists cache($key)]} { return $cache($key) }
    set W [$master getWidth]
    set H [$master getHeight]
    set cons [dict create x [list 1 {0}] y [list 1 {0}]]
    set per [dict create]   ;# layer,axis -> dict of centre residues (2x) seen
    foreach mt [$master getMTerms] {
        if {![is_signal $mt]} { continue }
        foreach mp [$mt getMPins] {
            foreach box [$mp getGeometry] {
                set lay [$box getTechLayer]
                if {$lay eq "NULL" || $lay eq ""} { continue }
                set lname [$lay getName]
                if {![info exists tracks($lname)]} { continue }
                set axis [expr {[$lay getDirection] eq "HORIZONTAL" ? "y" : "x"}]
                lassign [xform [$box xMin] [$box yMin] [$box xMax] [$box yMax] $orient $W $H] qx1 qy1 qx2 qy2
                set c2 [expr {$axis eq "y" ? $qy1 + $qy2 : $qx1 + $qx2}]
                dict set per "$lname,$axis" $c2 1
            }
        }
    }
    dict for {la centres} $per {
        lassign [split $la ","] lname axis
        lassign [axis_tracks $lname $axis] P T
        set legal {}
        set first 1
        foreach c2 [dict keys $centres] {
            if {$c2 % 2} { set legal {}; set first 0; break }
            set c [expr {$c2 / 2}]
            set ok [dict create]
            foreach t $T { dict set ok [expr {($t - $c) % $P}] 1 }
            if {$first} {
                set legal [lsort -integer [dict keys $ok]]
                set first 0
            } else {
                set nl {}
                foreach r $legal { if {[dict exists $ok $r]} { lappend nl $r } }
                set legal $nl
            }
            if {![llength $legal]} { break }
        }
        dict set cons $axis [meet [dict get $cons $axis] [list $P $legal]]
    }
    set cache($key) $cons
    return $cons
}

# Legal grid points grid0 + k*gpitch (DBU) with residue mod P in S, nearest to target first (up to n).
proc ot_mts::snap_axis_cands {target grid0 gpitch P S what {n 1}} {
    if {![llength $S]} { error "ot_mts: $what has no legal origin on this track grid" }
    set ok [dict create]; foreach r $S { dict set ok $r 1 }
    set L [lcm $gpitch $P]
    set span [expr {($L / $gpitch + 1) * $n}]
    set k0 [expr {round(double($target - $grid0) / $gpitch)}]
    set c {}
    for {set d -$span} {$d <= $span} {incr d} {
        set v [expr {$grid0 + ($k0 + $d) * $gpitch}]
        if {[dict exists $ok [expr {$v % $P}]]} { lappend c [list [expr {abs($v - $target)}] $v] }
    }
    if {![llength $c]} { error "ot_mts: $what: site grid ($grid0 + k*$gpitch) never meets the legal residues mod $P" }
    set out {}
    foreach e [lrange [lsort -integer -index 0 [lsort -integer -index 1 $c]] 0 [expr {$n - 1}]] { lappend out [lindex $e 1] }
    return $out
}

proc ot_mts::snap_axis {target grid0 gpitch P S what} {
    return [lindex [snap_axis_cands $target $grid0 $gpitch $P $S $what 1] 0]
}

proc ot_mts::site_grid {} {
    set block [ord::get_db_block]
    set row0 [lindex [$block getRows] 0]
    if {$row0 eq ""} { error "ot_mts: block has no rows" }
    set o [$row0 getOrigin]
    set site [$row0 getSite]
    return [list [lindex $o 0] [$site getWidth] [lindex $o 1] [$site getHeight]]
}

proc ot_mts::snap_origin {master orient x y} {
    set dbu [get_dbu]
    lassign [site_grid] gx gw gy gh
    set r [rule $master $orient]
    lassign [dict get $r x] Px Sx
    lassign [dict get $r y] Py Sy
    set what "[$master getName] $orient"
    set xs [snap_axis [expr {round($x*$dbu)}] $gx $gw $Px $Sx "$what x"]
    set ys [snap_axis [expr {round($y*$dbu)}] $gy $gh $Py $Sy "$what y"]
    return [list [expr {double($xs)/$dbu}] [expr {double($ys)/$dbu}]]
}

# Placed macro footprints other than inst, as {x1 y1 x2 y2} (DBU).
proc ot_mts::placed_macro_boxes {skip} {
    set out {}
    foreach i [[ord::get_db_block] getInsts] {
        if {$i eq $skip || ![[$i getMaster] isBlock]} { continue }
        set st [$i getPlacementStatus]
        if {$st eq "NONE" || $st eq "UNPLACED"} { continue }
        set b [$i getBBox]
        lappend out [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
    }
    return $out
}

# Snap to the nearest legal origin whose footprint overlaps no other placed macro and stays inside
# the die.  A snapped origin can move up to one joint period (2.16 um in y for M4 macros); a stacked
# neighbour placed at the old "0 mod 0.048" pitch may then collide, so the next legal point is taken.
proc ot_mts::place {inst x y orient {status FIRM}} {
    set dbu [get_dbu]
    set m [$inst getMaster]
    lassign [site_grid] gx gw gy gh
    set r [rule $m $orient]
    lassign [dict get $r x] Px Sx
    lassign [dict get $r y] Py Sy
    set what "[$m getName] $orient"
    set tx [expr {round($x*$dbu)}]; set ty [expr {round($y*$dbu)}]
    set xs [snap_axis_cands $tx $gx $gw $Px $Sx "$what x" 4]
    set ys [snap_axis_cands $ty $gy $gh $Py $Sy "$what y" 4]
    if {$orient in {R90 R270 MXR90 MYR90}} {
        set fw [$m getHeight]; set fh [$m getWidth]
    } else {
        set fw [$m getWidth]; set fh [$m getHeight]
    }
    set die [[ord::get_db_block] getDieArea]
    set others [placed_macro_boxes $inst]
    set cands {}
    foreach cx $xs { foreach cy $ys {
        lappend cands [list [expr {abs($cx - $tx) + abs($cy - $ty)}] $cx $cy]
    } }
    set best {}
    foreach c [lsort -integer -index 0 $cands] {
        lassign $c d cx cy
        set x2 [expr {$cx + $fw}]; set y2 [expr {$cy + $fh}]
        if {$cx < [$die xMin] || $cy < [$die yMin] || $x2 > [$die xMax] || $y2 > [$die yMax]} { continue }
        set clash 0
        foreach o $others {
            lassign $o ox1 oy1 ox2 oy2
            if {$cx < $ox2 && $ox1 < $x2 && $cy < $oy2 && $oy1 < $y2} { set clash 1; break }
        }
        if {!$clash} { set best [list $cx $cy]; break }
    }
    if {$best eq {}} {
        error "ot_mts::place: no legal, non-overlapping origin for [$inst getName] ($what) near ($x, $y)"
    }
    lassign $best bx by
    $inst setPlacementStatus PLACED
    $inst setOrient $orient
    $inst setLocation $bx $by
    $inst setPlacementStatus $status
    set px [expr {double($bx)/$dbu}]; set py [expr {double($by)/$dbu}]
    puts [format "OT_MTS_PLACE %s %s %s requested (%.3f, %.3f) placed (%.3f, %.3f)" \
              [$inst getName] [$m getName] $orient $x $y $px $py]
    return [list $px $py]
}

# --- assert --------------------------------------------------------------------------------------------

proc ot_mts::grid_lines {block lname axis} {
    variable glines
    set key "$lname,$axis"
    if {[info exists glines($key)]} { return $glines($key) }
    set lay [[ord::get_db_tech] findLayer $lname]
    set tg [$block findTrackGrid $lay]
    if {$tg eq "NULL" || $tg eq ""} { set glines($key) {}; return {} }
    if {$axis eq "y"} { set raw [$tg getGridY] } else { set raw [$tg getGridX] }
    set l [lsort -integer -unique $raw]
    set glines($key) $l
    return $l
}

# Distance (DBU, may be .5) from c2/2 to the nearest line in the sorted list.
proc ot_mts::offset2 {lines c2} {
    if {![llength $lines]} { return -1 }
    set c [expr {$c2 / 2.0}]
    set i [lsearch -sorted -integer -bisect $lines [expr {int(floor($c))}]]
    set best {}
    foreach j [list [expr {$i - 1}] $i [expr {$i + 1}]] {
        if {$j < 0 || $j >= [llength $lines]} { continue }
        set d [expr {abs([lindex $lines $j] - $c)}]
        if {$best eq {} || $d < $best} { set best $d }
    }
    return $best
}

proc ot_mts::assert_on_track {args} {
    variable glines
    array unset glines
    array set glines {}
    set insts {}
    set label ""
    set warn_only 0
    for {set i 0} {$i < [llength $args]} {incr i} {
        switch -- [lindex $args $i] {
            -insts     { incr i; set insts [lindex $args $i] }
            -label     { incr i; set label [lindex $args $i] }
            -warn_only { set warn_only 1 }
            default    { error "ot_mts::assert_on_track: unknown option [lindex $args $i]" }
        }
    }
    set block [ord::get_db_block]
    set dbu [get_dbu]
    if {![llength $insts]} {
        foreach inst [$block getInsts] {
            if {[[$inst getMaster] isBlock]} { lappend insts $inst }
        }
    }
    set n_inst 0; set n_pins 0; set n_off 0; set n_nogrid 0; set worst 0.0
    set bad {}
    foreach inst $insts {
        set st [$inst getPlacementStatus]
        if {$st eq "NONE" || $st eq "UNPLACED"} { continue }
        incr n_inst
        set off_here 0; set max_here 0.0
        foreach it [$inst getITerms] {
            set mt [$it getMTerm]
            if {![is_signal $mt]} { continue }
            set shapes {}
            foreach mp [$mt getMPins] { foreach box [$mp getGeometry] { lappend shapes $box } }
            set single [expr {[llength $shapes] == 1}]
            if {$single} {
                # absolute pin geometry straight from OpenDB: independent of this library's xform table
                set bb [$it getBBox]
                set abs [list [list [[lindex $shapes 0] getTechLayer] [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]]
            } else {
                set abs {}
                set loc [$inst getLocation]
                set m [$inst getMaster]
                foreach box $shapes {
                    lassign [xform [$box xMin] [$box yMin] [$box xMax] [$box yMax] [$inst getOrient] \
                                 [$m getWidth] [$m getHeight]] a b c d
                    lappend abs [list [$box getTechLayer] [expr {$a + [lindex $loc 0]}] [expr {$b + [lindex $loc 1]}] \
                                      [expr {$c + [lindex $loc 0]}] [expr {$d + [lindex $loc 1]}]]
                }
            }
            foreach s $abs {
                lassign $s lay x1 y1 x2 y2
                if {$lay eq "NULL" || $lay eq ""} { continue }
                if {[$lay getType] ne "ROUTING"} { continue }
                set axis [expr {[$lay getDirection] eq "HORIZONTAL" ? "y" : "x"}]
                set lines [grid_lines $block [$lay getName] $axis]
                if {![llength $lines]} { incr n_nogrid; continue }
                incr n_pins
                set c2 [expr {$axis eq "y" ? $y1 + $y2 : $x1 + $x2}]
                set d [offset2 $lines $c2]
                if {$d > 0} {
                    incr n_off; incr off_here
                    if {$d > $max_here} { set max_here $d }
                }
            }
        }
        if {$off_here} {
            set dnm [expr {1000.0 * $max_here / $dbu}]
            if {$dnm > $worst} { set worst $dnm }
            lappend bad [format "%s(%s %s @ %.3f,%.3f: %d off, max %.1f nm)" [$inst getName] \
                [[$inst getMaster] getName] [$inst getOrient] \
                [expr {double([lindex [$inst getLocation] 0])/$dbu}] [expr {double([lindex [$inst getLocation] 1])/$dbu}] \
                $off_here $dnm]
        }
    }
    set verdict [expr {$n_off ? "FAIL" : "PASS"}]
    puts [format "OT_MACRO_TRACK_ASSERT %s%s macros=%d pins_checked=%d offtrack=%d max_offset_nm=%.1f no_track_grid=%d" \
              $verdict [expr {$label eq "" ? "" : " label=$label"}] $n_inst $n_pins $n_off $worst $n_nogrid]
    foreach b $bad { puts "OT_MACRO_TRACK_ASSERT offtrack $b" }
    if {$n_off && !$warn_only} {
        error "OT_MACRO_TRACK_ASSERT FAIL: $n_off macro signal pin centres off their preferred-direction track (max [format %.1f $worst] nm); see results/uarch/macro_pin_access_audit_20261003"
    }
    return $n_off
}

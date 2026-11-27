# Before detailed placement, seat only the single-load combinational repeaters
# on authored same-bit feedthrough paths. The ordinary place hook owns the FFs.
namespace eval ot_ft_data_corridors {
    proc data_net {i} {
        set nets {}
        foreach pin [$i getITerms] {
            if {[[$pin getMTerm] getIoType] ne "OUTPUT"} continue
            set net [$pin getNet]
            if {$net eq {} || $net eq "NULL"} continue
            if {[$net getSigType] in {POWER GROUND CLOCK}} {
                error "feedthrough data path has a clock or supply on [$i getName]"
            }
            lappend nets $net
        }
        if {[llength $nets] != 1} {error "feedthrough data path needs one connected output on [$i getName]"}
        return [lindex $nets 0]
    }

    proc chain {launch receive} {
        set i $launch
        set result [list $launch]
        set seen [dict create $launch 1]
        while {$i ne $receive} {
            set net [data_net $i]
            if {[llength [$net getBTerms]]} {error "feedthrough data path crosses a port on [$net getName]"}
            set sinks {}
            set drivers {}
            foreach pin [$net getITerms] {
                set mp [$pin getMTerm]
                set load [$pin getInst]
                set direction [$mp getIoType]
                if {$direction eq "OUTPUT"} {
                    lappend drivers $load
                } elseif {$direction eq "INPUT" && [$mp getSigType] ni {POWER GROUND CLOCK}} {
                    lappend sinks $load
                } else {
                    error "unexpected feedthrough terminal direction or role on [$net getName]"
                }
            }
            if {$drivers ne [list $i] || [llength $sinks] != 1} {
                error "feedthrough path is not exclusively owned on [$net getName]"
            }
            set i [lindex $sinks 0]
            if {[dict exists $seen $i] || ($i ne $receive && ![ot_auth_input::wire $i])} {
                error "feedthrough path fails to reach its same-bit next register at [$i getName]"
            }
            dict set seen $i 1
            lappend result $i
        }
        return $result
    }

    proc midpoint {i} {
        lassign [ot_auth_input::rectangle $i] x0 y0 x1 y1
        return [list [expr {($x0 + $x1) * 0.5}] [expr {($y0 + $y1) * 0.5}]]
    }

    proc polarity_site_rows {file pitch} {
        set stream [open $file]
        try {set data [read $stream]} finally {close $stream}
        set sites {}
        foreach line [split $data "\n"] {
            if {$line eq {} || [string index $line 0] eq "#"} continue
            lassign $line bit x y
            if {[llength $line] != 3 || ![string is integer -strict $bit]
                    || ![string is double -strict $x] || ![string is double -strict $y]
                    || [dict exists $sites $bit]} {
                error "invalid authored feedthrough polarity site: $line"
            }
            dict set sites $bit [list [expr {$x*$pitch}] [expr {$y*$pitch}]]
        }
        return $sites
    }

    proc corridor_targets {block records dbu polarity_file} {
        set wanted {}
        set slot_widths {}
        set polarity {}
        foreach record $records {
            lassign $record slot low high width keep_polarity
            if {$keep_polarity && ![dict size $polarity]} {
                set polarity [polarity_site_rows $polarity_file $dbu]
            }
            for {set k $low} {$k <= $high+1} {incr k} {dict set wanted [list $slot $k] 1}
            dict set slot_widths $slot $width
        }
        set stations {}
        foreach i [$block getInsts] {
            set name [ot_auth_input::normalized [$i getName]]
            if {![regexp {^u_bound[.]u_ft_(.+)_o_([0-9]+)/q\[([0-9]+)\].*DFF} $name -> slot stage bit]} continue
            if {![dict exists $wanted [list $slot $stage]]} continue
            set key [list $slot $stage $bit]
            if {$bit >= [dict get $slot_widths $slot] || [dict exists $stations $key]} {
                error "duplicate or out-of-range feedthrough stage bit: $name"
            }
            if {[$i getPlacementStatus] in {NONE UNPLACED}} {error "feedthrough stage bit has no physical site: $name"}
            dict set stations $key $i
        }
        set active {}
        set paths {}
        foreach record $records {
            lassign $record slot low high width keep_polarity
            for {set stage $low} {$stage <= $high} {incr stage} {
                for {set bit 0} {$bit < $width} {incr bit} {
                    set launch [dict get $stations [list $slot $stage $bit]]
                    set receive [dict get $stations [list $slot [expr {$stage+1}] $bit]]
                    set path [chain $launch $receive]
                    set last [expr {[llength $path]-1}]
                    set anchors [list 0 $last]
                    if {$stage == 0 && $keep_polarity} {
                        lassign [dict get $polarity $bit] ax ay
                        set best 1e20
                        set selected 0
                        for {set n 1} {$n < $last} {incr n} {
                            set i [lindex $path $n]
                            if {![string match INV* [[$i getMaster] getName]]} continue
                            lassign [ot_auth_input::rectangle $i] x y
                            set distance [expr {abs($ax-$x)+abs($ay-$y)}]
                            if {$distance < $best} {set best $distance;set selected $n}
                        }
                        if {$selected == 0 || $best > 5*$dbu} {
                            error "feedthrough polarity owner drift: $slot bit $bit"
                        }
                        lappend anchors $selected
                    }
                    for {set n 1} {$n < $last} {incr n} {
                        set i [lindex $path $n]
                        if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {lappend anchors $n}
                    }
                    set anchors [lsort -integer -unique $anchors]
                    foreach a [lrange $anchors 0 end-1] b [lrange $anchors 1 end] {
                        lassign [midpoint [lindex $path $a]] x0 y0
                        lassign [midpoint [lindex $path $b]] x1 y1
                        for {set n [expr {$a+1}]} {$n < $b} {incr n} {
                            set i [lindex $path $n]
                            if {[dict exists $active $i]} {error "shared feedthrough data repeater [$i getName]"}
                            set f [expr {double($n-$a)/($b-$a)}]
                            dict set active $i [list [expr {$x0+$f*($x1-$x0)}] [expr {$y0+$f*($y1-$y0)}]]
                        }
                    }
                    lappend paths $path
                }
            }
        }
        return [list $active $paths]
    }

    proc allocate {block active dbu} {
        set ::ot_auth_input::b $block
        set ::ot_auth_input::d $dbu
        set c [$block getCoreArea]
        set ::ot_auth_input::core [list [$c xMin] [$c yMin] [$c xMax] [$c yMax]]
        set ::ot_auth_input::macros {}
        set ::ot_auth_input::occ {}
        foreach blockage [$block getBlockages] {
            set box [$blockage getBBox]
            lappend ::ot_auth_input::macros [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
        }
        foreach i [$block getInsts] {
            if {[dict exists $active $i] || [$i getPlacementStatus] in {NONE UNPLACED}} continue
            set box [ot_auth_input::rectangle $i]
            if {[[$i getMaster] isBlock]} {
                lappend ::ot_auth_input::macros $box
            } else {
                ot_auth_input::occupy $box
            }
        }
        set orient {}
        foreach row [$block getRows] {
            dict set orient [lindex [$row getOrigin] 1] [$row getOrient]
        }
        set dims [list [expr {round(.054*$dbu)}] [expr {round(.27*$dbu)}]]
        lassign $dims sx sy
        set xorg [$c xMin]
        set yorg [$c yMin]
        set jitter {}
        for {set dy -8} {$dy <= 8} {incr dy} {
            for {set dx -40} {$dx <= 40} {incr dx} {
                lappend jitter [list [expr {abs($dx*$sx)+abs($dy*$sy)}] [expr {$dx*$sx}] [expr {$dy*$sy}]]
            }
        }
        set jitter [lsort -integer -index 0 $jitter]
        set moves {}
        dict for {i point} $active {
            lassign $point cx cy
            set w [[$i getMaster] getWidth]
            set h [[$i getMaster] getHeight]
            if {$h != $sy} {error "unsupported feedthrough repeater height on [$i getName]"}
            set xi [expr {$xorg + round(($cx-.5*$w-$xorg)/$sx)*$sx}]
            set yi [expr {$yorg + round(($cy-.5*$h-$yorg)/$sy)*$sy}]
            set best {}
            set score 1e20
            foreach offset $jitter {
                lassign $offset radius dx dy
                if {$radius-.5*($sx+$sy) >= $score} break
                set x [expr {$xi+$dx}]
                set y [expr {$yi+$dy}]
                if {![dict exists $orient $y]} continue
                set cost [expr {abs($x+.5*$w-$cx)+abs($y+.5*$h-$cy)}]
                if {$cost >= $score} continue
                set box [list $x $y [expr {$x+$w}] [expr {$y+$h}]]
                if {![ot_auth_input::free $box]} continue
                set best [list $x $y $box]
                set score $cost
            }
            if {$best eq {}} {error "no nearby legal feedthrough corridor site for [$i getName]"}
            lassign $best x y box
            ot_auth_input::occupy $box
            dict set moves $i [list $x $y [dict get $orient $y] [expr {$x+.5*$w}] [expr {$y+.5*$h}]]
        }
        return $moves
    }

    proc run {records polarity_file} {
        set block [ord::get_db_block]
        set dbu [$block getDbUnitsPerMicron]
        lassign [corridor_targets $block $records $dbu $polarity_file] active paths
        set moves [allocate $block $active $dbu]
        set max_path 0.0
        set max_leg 0.0
        foreach path $paths {
            set prev {}
            set length 0.0
            foreach i $path {
                set point [midpoint $i]
                if {[dict exists $moves $i]} {set point [lrange [dict get $moves $i] 3 4]}
                if {$prev ne {}} {
                    lassign $point x1 y1
                    lassign $prev x0 y0
                    set leg [expr {(abs($x1-$x0)+abs($y1-$y0))/double($dbu)}]
                    set max_leg [expr {max($max_leg,$leg)}]
                    set length [expr {$length+$leg}]
                }
                set prev $point
            }
            set max_path [expr {max($max_path,$length)}]
        }
        if {$max_path > 405.0} {error "feedthrough corridor path through placed repeaters exceeds 405um: $max_path"}
        dict for {i location} $moves {
            lassign $location x y orient
            $i setOrient $orient
            $i setLocation $x $y
            $i setPlacementStatus FIRM
        }
        puts "OT_FT_DATA_CORRIDORS same_bit_paths=[llength $paths] moved_BUF_INV=[dict size $moves] path_um=$max_path largest_leg_um=$max_leg pin_cycles=0"
    }
}

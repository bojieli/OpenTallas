# Exact opt-in DLY latch sites. The post-spread pass seats existing cells;
# the pre-CTS pass checks the stock assignment without changing any nets.
namespace eval ot_dly_site {
    proc die_error {message} { error "OT_DLY_LATCH_SITE $message" }

    proc cell {block name pattern} {
        set i [$block findInst $name]
        if {$i eq "NULL" || ![regexp $pattern [[$i getMaster] getName]]} {
            die_error "missing or wrong master for $name"
        }
        return $i
    }

    proc signal_net {i pin} {
        set t [$i findITerm $pin]
        if {$t eq "NULL" || [$t getNet] eq "NULL" || [[$t getNet] getSigType] ne "SIGNAL"} {
            die_error "missing signal [$i getName]/$pin"
        }
        return [$t getNet]
    }

    proc buffer {inst} {
        return [regexp {^(BUF|INV|HB)} [[$inst getMaster] getName]]
    }

    proc buffer_net {i want} {
        set ns {}
        foreach t [$i getITerms] {
            if {($want eq "in" && ![$t isInputSignal]) || ($want eq "out" && ![$t isOutputSignal])} continue
            set n [$t getNet]
            if {$n ne "NULL" && [$n getSigType] eq "SIGNAL"} { lappend ns $n }
        }
        if {[llength $ns] != 1} { die_error "ambiguous repeater [$i getName]/$want" }
        return [lindex $ns 0]
    }

    proc check_data {latch launch capture} {
        set n [signal_net $latch D]
        set walked {}
        for {set depth 0} {$depth < 40} {incr depth} {
            if {[dict exists $walked $n]} { die_error "cycle before [$latch getName]" }
            dict set walked $n 1
            set drivers {}
            foreach t [$n getITerms] {
                if {[$t isOutputSignal]} { lappend drivers [$t getInst] }
            }
            if {[llength $drivers] != 1 || [llength [$n getBTerms]]} {
                die_error "ambiguous data launch before [$latch getName]"
            }
            set i [lindex $drivers 0]
            if {$i eq $launch} break
            if {![buffer $i]} { die_error "wrong data launch before [$latch getName]: [$i getName]" }
            set n [buffer_net $i in]
        }
        if {$depth >= 40} { die_error "deep data launch before [$latch getName]" }

        set n [buffer_net $latch out]
        set end [signal_net $capture D]
        set walked {}
        for {set depth 0} {$depth < 40} {incr depth} {
            if {[dict exists $walked $n]} { die_error "cycle after [$latch getName]" }
            dict set walked $n 1
            set loads {}
            foreach t [$n getITerms] {
                if {[$t isInputSignal] && ![$t isOutputSignal]} { lappend loads $t }
            }
            if {[llength $loads] != 1 || [llength [$n getBTerms]]} {
                die_error "ambiguous data capture after [$latch getName]"
            }
            set t [lindex $loads 0]
            set i [$t getInst]
            if {$i eq $capture && $n eq $end && [[$t getMTerm] getName] eq "D"} { return }
            if {![buffer $i]} { die_error "wrong data capture after [$latch getName]: [$i getName]" }
            set n [buffer_net $i out]
        }
        die_error "deep data capture after [$latch getName]"
    }

    proc box {rect} {
        return [list [$rect xMin] [$rect yMin] [$rect xMax] [$rect yMax]]
    }

    proc overlaps {a b} {
        lassign $a x0 y0 x1 y1
        lassign $b u0 v0 u1 v1
        return [expr {$x0 < $u1 && $u0 < $x1 && $y0 < $v1 && $v0 < $y1}]
    }

    proc check_tap {block i tap} {
        set root [$block findBTerm $tap]
        set pin [$i findITerm CLK]
        if {$root eq "NULL" || $pin eq "NULL" || [$root getNet] eq "NULL" ||
            [$pin getNet] ne [$root getNet]} {
            die_error "clock tap changed for [$i getName], expected $tap"
        }
    }

    proc run {mode table} {
        if {$mode ni {place phase}} { die_error "unexpected mode $mode" }
        set block [ord::get_db_block]
        set dbu [$block getDbUnitsPerMicron]
        set f [open $table r]
        set text [read $f]
        close $f
        set rows {}
        set needed {}
        set names {}
        foreach line [split [string trimright $text "\n"] "\n"] {
            set fields [split $line "\t"]
            if {[llength $fields] != 8} { die_error "malformed placement table" }
            lassign $fields name master src dst tap dst_tap x_um y_um
            if {[dict exists $names $name]} { die_error "repeated latch $name" }
            dict set names $name 1
            set i [cell $block $name {^(DLL|DHL)}]
            set launch [cell $block $src {^(ASYNC_)?DFF}]
            set capture [cell $block $dst {^(ASYNC_)?DFF}]
            if {[[$i getMaster] getName] ne $master} { die_error "master drift for $name" }
            check_data $i $launch $capture
            foreach {v label} [list $x_um x $y_um y] {
                if {![string is double -strict $v] || abs($v*$dbu-round($v*$dbu)) > 0.000001} {
                    die_error "invalid $label site for $name"
                }
            }
            set x [expr {round($x_um*$dbu)}]
            set y [expr {round($y_um*$dbu)}]
            if {$mode eq "phase"} {
                if {[$i getLocation] ne [list $x $y] || [$i getPlacementStatus] ni {FIRM LOCKED}} {
                    die_error "reviewed site changed for $name"
                }
                check_tap $block $i $tap
                check_tap $block $launch $tap
                check_tap $block $capture $dst_tap
            } else {
                if {[$i getPlacementStatus] ni {PLACED SUGGESTED}} {
                    die_error "unexpected placement status for $name: [$i getPlacementStatus]"
                }
                lappend rows [list $name $i $x $y]
                dict set needed $y 1
            }
        }
        if {$mode eq "phase"} {
            puts "OT_DLY_LATCH_SITE phase PASS [dict size $names] exact launch/latch/capture taps"
            return
        }

        set sites {}
        foreach row [$block getRows] {
            set rect [box [$row getBBox]]
            set y [lindex $rect 1]
            if {[dict exists $needed $y]} {
                set site [$row getSite]
                dict lappend sites $y [list $rect [$site getWidth] [$site getHeight] [$row getOrient]]
            }
        }
        set occupied {}
        foreach inst [$block getInsts] {
            if {[[$inst getMaster] isBlock] || [$inst getPlacementStatus] in {FIRM LOCKED COVER}} {
                lappend occupied [box [$inst getBBox]]
            }
        }
        foreach blockage [$block getBlockages] {
            if {![$blockage isSoft]} { lappend occupied [box [$blockage getBBox]] }
        }

        set core [box [$block getCoreArea]]
        set moves {}
        foreach row $rows {
            lassign $row name i x y
            set m [$i getMaster]
            set area [list $x $y [expr {$x+[$m getWidth]}] [expr {$y+[$m getHeight]}]]
            lassign $area a b c d
            lassign $core ca cb cc cd
            if {$a<$ca || $b<$cb || $c>$cc || $d>$cd || ![dict exists $sites $y]} {
                die_error "outside legal rows for $name"
            }
            set orientations {}
            foreach slot [dict get $sites $y] {
                lassign $slot rect step h orientation
                lassign $rect lo _ hi top
                if {$a >= $lo && $c <= $hi && $d <= $top && $d-$b==$h && ($a-$lo)%$step==0} {
                    lappend orientations $orientation
                }
            }
            set orientations [lsort -unique $orientations]
            if {[llength $orientations] != 1} { die_error "off-grid or ambiguous row for $name" }
            foreach r $occupied {
                if {[overlaps $area $r]} { die_error "occupied or blocked row for $name at $x $y" }
            }
            lappend occupied $area
            lappend moves [list $i $x $y [lindex $orientations 0]]
        }
        foreach move $moves {
            lassign $move i x y orient
            $i setOrient $orient
            $i setLocation $x $y
            $i setPlacementStatus FIRM
        }
        puts "OT_DLY_LATCH_SITE placed [llength $moves] existing latches on exact rows"
    }
}

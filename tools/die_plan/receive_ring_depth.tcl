# Resolve paths through named input terminals of native storage/read flops.
# The path contains no flattened mapped-instance identity.
proc ot_rx_depth_resolve {ring anchor path anchors direct incoming inspect} {
    set key [list $ring {*}$anchor]
    if {![dict exists $anchors $key]} {error "OT_RX_DEPTH missing native anchor $key"}
    set cell [dict get $anchors $key]
    foreach hop $path {
        lassign $hop pin expected
        set cell [{*}$incoming $cell $pin]
        if {$cell eq ""} {error "OT_RX_DEPTH missing or ambiguous driver from $key at $pin"}
        lassign [{*}$inspect $cell] owner master not_combinational fixed
        if {$owner ne $ring || $master ne $expected || $not_combinational} {
            error "OT_RX_DEPTH conflicting role $key at $pin ($owner $master, expected $ring $expected)"
        }
    }
    # A direct writer may be a reference on a feedback branch. The selected
    # cell itself must be outside the complete pin-direct write cone.
    if {$fixed || [dict exists $direct $cell]} {
        error "OT_RX_DEPTH conflicting role $key: fixed, already grouped or direct writer"
    }
    return $cell
}

proc ot_rx_depth_key {name} {
    set normal [string map {\\ {}} $name]
    set pat {^u_bound\.u_cland_(\w+)/u_ring\.dch\[([0-9]+)\]\.(sd_c|u_dsel/y)\[([0-9]+)\]\$_DFF[^/]*$}
    if {![regexp $pat $normal -> ring chunk kind index]} {return {}}
    return [list $ring $chunk [expr {$kind eq "sd_c" ? "storage" : "read"}] $index]
}

proc ot_rx_depth_anchors {rings} {
    set anchors {}
    foreach ring $rings {
        foreach cell [cland_group_insts u_cland_$ring] {
            if {![ff_is_ff $cell]} continue
            set key [ot_rx_depth_key [$cell getName]]
            if {$key eq ""} continue
            if {[dict exists $anchors $key]} {error "OT_RX_DEPTH duplicate native anchor $key"}
            dict set anchors $key $cell
        }
    }
    return $anchors
}

proc ot_rx_depth_incoming {cell pin} {
    set net {}
    foreach term [ff_sig_iterms $cell in] {
        if {[[$term getMTerm] getName] eq $pin} {set net [$term getNet]; break}
    }
    if {$net in {NULL ""}} {return {}}
    set driver {}
    foreach port [$net getBTerms] {
        if {[$port getIoType] in {INPUT INOUT}} {return {}}
    }
    foreach term [$net getITerms] {
        if {![$term isOutputSignal]} continue
        if {$driver ne ""} {return {}}
        set driver [$term getInst]
    }
    return $driver
}

proc ot_rx_depth_inspect {cell} {
    set master [$cell getMaster]
    set owner {}
    regexp {^u_bound\.u_cland_(\w+)/} [string map {\\ {}} [$cell getName]] -> owner
    set not_combinational [expr {![$master isCore] || [ff_is_ff $cell] || [ff_is_latch $cell]
        || [string match "SDF*" [$master getName]]}]
    set fixed [expr {[$cell getPlacementStatus] in {FIRM LOCKED FIXED COVER} || [$cell getGroup] ni {NULL ""}}]
    return [list $owner [$master getName] $not_combinational $fixed]
}

proc ot_rx_depth_direct {rings} {
    global ff_blk
    set inputs {}
    set queue {}
    set seen {}
    foreach port [$ff_blk getBTerms] {
        if {[$port getIoType] ne "INPUT"} continue
        set name [string map {\\ {}} [$port getName]]
        if {![regexp {^(\w+)\[[0-9]+\]$} $name -> ring] || $ring ni $rings} continue
        set net [$port getNet]
        if {$net in {NULL ""}} {error "OT_RX_DEPTH disconnected ring input $name"}
        dict set inputs $ring 1
        if {[dict exists $seen $net]} continue
        dict set seen $net 1
        lappend queue $net
    }
    if {[dict size $inputs] != [llength $rings]} {error "OT_RX_DEPTH missing data input bus"}
    set direct {}
    # Visit each live signal net once, including buffers outside ring scope.
    # Stop at the first storage element. Direct writers never become members.
    for {set p 0} {$p < [llength $queue]} {incr p} {
        set net [lindex $queue $p]
        foreach term [$net getITerms] {
            if {![$term isInputSignal] || [$term getSigType] ne "SIGNAL"} continue
            set cell [$term getInst]
            if {[dict exists $direct $cell]} continue
            set master [$cell getMaster]
            if {![$master isCore] || [ff_is_ff $cell] || [ff_is_latch $cell]
                || [string match "SDF*" [$master getName]]} continue
            dict set direct $cell 1
            foreach out [ff_sig_iterms $cell out] {
                set next [$out getNet]
                if {$next in {NULL ""} || [dict exists $seen $next]} continue
                dict set seen $next 1
                lappend queue $next
            }
        }
    }
    return $direct
}

proc ot_rx_depth_select {regions floors picks anchors direct incoming inspect area_of} {
    set members {}
    set selected {}
    set source_area {}
    set region_area {}
    foreach pick $picks {
        lassign $pick source region anchor path expected_area
        lassign [dict get $regions $region] ring box capacity
        set cell [ot_rx_depth_resolve $ring $anchor $path $anchors $direct $incoming $inspect]
        if {[dict exists $selected $cell]} {error "OT_RX_DEPTH aliased role $region/$anchor"}
        set area [{*}$area_of $cell]
        if {abs($area-$expected_area) > .00002} {error "OT_RX_DEPTH changed role area $region/$anchor"}
        dict set selected $cell $region
        dict lappend members $region $cell
        set area_before 0.0
        if {[dict exists $source_area $source]} {set area_before [dict get $source_area $source]}
        dict set source_area $source [expr {$area_before+$area}]
        set area_before 0.0
        if {[dict exists $region_area $region]} {set area_before [dict get $region_area $region]}
        dict set region_area $region [expr {$area_before+$area}]
    }
    dict for {source floor} $floors {
        if {[dict get $source_area $source]+.00002 < $floor} {error "OT_RX_DEPTH source budget short $source"}
    }
    dict for {region prop} $regions {
        set capacity [lindex $prop 2]
        if {[dict get $region_area $region] > $capacity+.00002} {error "OT_RX_DEPTH receiving budget exceeded $region"}
    }
    return [list $members $selected $region_area]
}

proc ot_rx_depth_area {cell} {
    global ff_dbu
    set m [$cell getMaster]
    return [expr {double([$m getWidth]) * [$m getHeight] / $ff_dbu / $ff_dbu}]
}

proc ot_rx_depth_box {bb} {
    global ff_dbu
    return [lmap coordinate [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]] {
        expr {double($coordinate)/$ff_dbu}
    }]
}

proc ot_rx_depth_intersection {a b} {
    lassign $a ax ay aX aY
    lassign $b bx by bX bY
    return [expr {max(0,min($aX,$bX)-max($ax,$bx)) * max(0,min($aY,$bY)-max($ay,$by))}]
}

proc ot_rx_depth_span {a b} {
    lassign $a ax ay aX aY
    lassign $b bx by bX bY
    return [expr {max(abs($ax-$bX),abs($aX-$bx))+max(abs($ay-$bY),abs($aY-$by))}]
}

proc ot_rx_depth_guard {regions selected region_area} {
    global ff_blk ff_dbu
    # Account for physical fixed bodies, even when their center is in the adjacent bin.
    set fixed {}
    foreach cell [$ff_blk getInsts] {
        if {[$cell getPlacementStatus] in {FIRM LOCKED FIXED COVER}} {
            dict set fixed $cell [ot_rx_depth_box [$cell getBBox]]
        }
    }
    set blocked {}
    foreach block [$ff_blk getBlockages] {
        if {![$block isSoft]} {lappend blocked [ot_rx_depth_box [$block getBBox]]}
    }
    set actual {}
    dict for {region prop} $regions {
        set box [lindex $prop 1]
        # OpenDB regions use integer DBU corners; check the actual shape used.
        set box [lmap coord $box {expr {round($coord*$ff_dbu)/double($ff_dbu)}}]
        dict set actual $region $box
        foreach b $blocked {
            if {[ot_rx_depth_intersection $box $b] > .00002} {
                error "OT_RX_DEPTH receiving region intersects a hard blockage $region"
            }
        }
        set occupied 0.0
        dict for {cell b} $fixed {set occupied [expr {$occupied+[ot_rx_depth_intersection $box $b]}]}
        lassign $box x y X Y
        if {($occupied+[dict get $region_area $region]+4.0) > .70*($X-$x)*($Y-$y)+.00002} {
            error "OT_RX_DEPTH fixed bodies exceed receiving budget $region"
        }
    }
    # Live known endpoints have to stay local after ordinary pin/capture seating.
    # Unplaced unrelated logic has no trustworthy coordinates yet.
    dict for {cell region} $selected {
        set box [dict get $actual $region]
        foreach terminal [$cell getITerms] {
            if {[$terminal getSigType] ne "SIGNAL"} continue
            set net [$terminal getNet]
            if {$net in {NULL ""}} continue
            set driver [$terminal isOutputSignal]
            foreach t [$net getITerms] {
                if {$t eq $terminal || [$t getSigType] ne "SIGNAL" || [$t isOutputSignal] == $driver} continue
                set peer [$t getInst]
                if {$cell eq $peer} continue
                if {[dict exists $selected $peer]} {
                    set other [dict get $actual [dict get $selected $peer]]
                } elseif {[dict exists $fixed $peer]} {
                    lassign [dict get $fixed $peer] x y X Y
                    set cx [expr {($x+$X)/2}]; set cy [expr {($y+$Y)/2}]
                    set other [list $cx $cy $cx $cy]
                } else {
                    continue
                }
                if {[ot_rx_depth_span $box $other] > 60.00002} {
                    error "OT_RX_DEPTH known endpoint beyond 60 um $region"
                }
            }
            foreach port [$net getBTerms] {
                if {[$port getIoType] ni {INPUT OUTPUT} || ([$port getIoType] eq "OUTPUT") != $driver} continue
                lassign [ot_rx_depth_box [$port getBBox]] x y X Y
                set cx [expr {($x+$X)/2}]; set cy [expr {($y+$Y)/2}]
                if {[ot_rx_depth_span $box [list $cx $cy $cx $cy]] > 60.00002} {
                    error "OT_RX_DEPTH pin beyond 60 um $region"
                }
            }
        }
    }
}

proc ot_rx_depth_place {regions floors picks} {
    global ff_blk ff_dbu lc_b lc_u
    set lc_b $ff_blk
    set lc_u $ff_dbu
    set rings [lsort -unique [lmap r [dict values $regions] {lindex $r 0}]]
    set anchors [ot_rx_depth_anchors $rings]
    set direct [ot_rx_depth_direct $rings]
    lassign [ot_rx_depth_select $regions $floors $picks $anchors $direct \
        ot_rx_depth_incoming ot_rx_depth_inspect ot_rx_depth_area] members selected areas
    ot_rx_depth_guard $regions $selected $areas
    dict for {region prop} $regions {
        ot_lc_region $region {*}[lindex $prop 1] [dict get $members $region]
    }
    puts "OT_RX_DEPTH seated [dict size $selected] movable cells across [dict size $regions] receiving regions for [dict size $floors] source budgets"
}

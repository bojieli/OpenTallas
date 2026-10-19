# safe2 COMPLETE full-cone regional placement, after pin anchors (LEAD-QW 10-19, after safe1 r6 GPL-0305).
# Every movable std cell is owned: exclusive cones go with their clock root, mixed cones (landing read muxes,
# cross-root glue) go with their DESTINATION root (reverse ownership), so no shared seam is left.  The two
# regions abut (core: W macro block + OPROM row; hr: h16c box) and span y43.2-388.8 (the macro rows); the N/S pin bands stay top-level free area so
# cells created later by repair/CTS have legal room (r6 forced 2351um2 of them into a 18476um2 seam).
# No timing exception, density override or latency change.
namespace eval ot_lcr {
    variable block [ord::get_db_block]
    variable dbu [$block getDbUnitsPerMicron]
    variable rootnet {}; variable seq {}; variable comb {}; variable ni {}; variable no {}
    variable fwd {}; variable rev {}; variable users {}; variable drivers {}
    variable insts {}; variable seed_f {}; variable seed_r {}
}
proc ot_lcr::null {v} {expr {$v eq "NULL" || $v eq ""}}
proc ot_lcr::push {name net mask queueName} {
    upvar 1 $queueName queue
    variable $name
    upvar 0 [namespace current]::$name masks
    if {[null $net] || !$mask} return
    set old 0
    if {[dict exists $masks $net]} {set old [dict get $masks $net]}
    set next [expr {$old | $mask}]
    if {$next != $old} {dict set masks $net $next; lappend queue $net}
}
foreach {port mask} {ck_core 1 ck_hr 2} {
    set bt [$ot_lcr::block findBTerm $port]
    if {[ot_lcr::null $bt] || [ot_lcr::null [$bt getNet]]} {error "OT_LCR missing root $port"}
    dict set ot_lcr::rootnet [$bt getNet] $mask
}
# Cache topology once. Traversals stop at sequential/hard macro boundaries.
foreach inst [$ot_lcr::block getInsts] {
    set master [$inst getMaster]
    if {![string match CORE* [$master getType]] && ![$master isSequential] && ![$master isBlock]} continue
    set ins {}; set outs {}; set root 0
    foreach it [$inst getITerms] {
        if {[$it getSigType] in {POWER GROUND}} continue
        set net [$it getNet]
        if {[ot_lcr::null $net]} continue
        if {[$it isInputSignal]} {
            lappend ins $net
            if {[dict exists $ot_lcr::rootnet $net]} {set root [expr {$root | [dict get $ot_lcr::rootnet $net]}]}
        } elseif {[$it isOutputSignal]} {lappend outs $net}
    }
    dict set ot_lcr::insts $inst $inst
    dict set ot_lcr::ni $inst $ins; dict set ot_lcr::no $inst $outs
    if {[$master isSequential] || [$master isBlock]} {
        if {$root ni {1 2}} {error "OT_LCR ambiguous/unclocked sequential boundary [$inst getName] mask=$root; harden separately"}
        dict set ot_lcr::seq $inst $root
        foreach net $ins {lappend ot_lcr::seed_r $net $root}
        foreach net $outs {lappend ot_lcr::seed_f $net $root}
    } else {
        dict set ot_lcr::comb $inst 1
        foreach net $ins {dict lappend ot_lcr::users $net $inst}
        foreach net $outs {dict lappend ot_lcr::drivers $net $inst}
    }
}
# Source ownership and destination ownership are independent monotone passes.
# Never feed destination masks into source propagation: that would flood common
# controls through unrelated cones and destroy the crossing boundary.
foreach direction {fwd rev} {
    if {$direction eq "fwd"} {
        set seeds $ot_lcr::seed_f; set adj $ot_lcr::users; set targets $ot_lcr::no
    } else {
        set seeds $ot_lcr::seed_r; set adj $ot_lcr::drivers; set targets $ot_lcr::ni
    }
    set queue {}
    foreach {net mask} $seeds {ot_lcr::push $direction $net $mask queue}
    for {set cursor 0} {$cursor < [llength $queue]} {incr cursor} {
        set net [lindex $queue $cursor]
        set mask [dict get [set ot_lcr::$direction] $net]
        if {![dict exists $adj $net]} continue
        foreach inst [dict get $adj $net] {
            foreach target [dict get $targets $inst] {ot_lcr::push $direction $target $mask queue}
        }
    }
}
set members [dict create 1 {} 2 {}]
set areas [dict create 1 0.0 2 0.0]
set mixed [dict create 1 0 2 0]
set fixed 0
foreach inst [dict keys $ot_lcr::insts] {
    set master [$inst getMaster]
    if {[$master isBlock] || [$inst isFixed]} {incr fixed; continue}
    if {[dict exists $ot_lcr::seq $inst]} {
        set mask [dict get $ot_lcr::seq $inst]
    } else {
        set fm 0; set rm 0
        foreach net [concat [dict get $ot_lcr::ni $inst] [dict get $ot_lcr::no $inst]] {
            if {[dict exists $ot_lcr::fwd $net]} {set fm [expr {$fm | [dict get $ot_lcr::fwd $net]}]}
            if {[dict exists $ot_lcr::rev $net]} {set rm [expr {$rm | [dict get $ot_lcr::rev $net]}]}
        }
        set all [expr {$fm | $rm}]
        if {$all == 1 || $all == 2} {
            set mask $all
        } else {
            # mixed or rootless: destination root first (beside the capturing register), then source, else core
            if {$rm == 1 || $rm == 2} {set mask $rm} elseif {$fm == 1 || $fm == 2} {set mask $fm} else {set mask 1}
            dict incr mixed $mask
        }
    }
    if {![ot_lcr::null [$inst getGroup]]} {error "OT_LCR already grouped [$inst getName]"}
    dict lappend members $mask $inst
    dict set areas $mask [expr {[dict get $areas $mask] + [$master getWidth]*[$master getHeight]/double($ot_lcr::dbu*$ot_lcr::dbu)}]
}
# Fixed pin flops stay ungrouped (their face grants are authoritative) in the top-level N/S pin bands.
# core = W macro block + the core-clocked OPROM row above h16c (y280.8-388.8); hr = h16c box below it.
set ry0 43.2; set ry1 388.8
set boxes [dict create 1 {{2.16 43.2 453.6 388.8} {453.6 280.8 775.44 388.8}} 2 {{453.6 43.2 775.44 280.8}}]
foreach {mask name} {1 core 2 hr} {
    set rbox_a 0.0; set mac 0.0
    foreach bx [dict get $boxes $mask] {
        lassign $bx x0 y0 x1 y1
        set rbox_a [expr {$rbox_a + ($x1-$x0)*($y1-$y0)}]
        foreach inst [$ot_lcr::block getInsts] {
            if {![[$inst getMaster] isBlock]} continue
            set bb [$inst getBBox]
            set ix0 [expr {max($x0, [$bb xMin]/double($ot_lcr::dbu))}]; set ix1 [expr {min($x1, [$bb xMax]/double($ot_lcr::dbu))}]
            set iy0 [expr {max($y0, [$bb yMin]/double($ot_lcr::dbu))}]; set iy1 [expr {min($y1, [$bb yMax]/double($ot_lcr::dbu))}]
            if {$ix1 > $ix0 && $iy1 > $iy0} {set mac [expr {$mac + ($ix1-$ix0)*($iy1-$iy0)}]}
        }
    }
    set std [dict get $areas $mask]
    set free [expr {$rbox_a - $mac}]
    set fill [expr {($mac + $std)/$rbox_a}]
    set sutil [expr {$std/$free}]
    puts [format "OT_LCR region=%s cells=%d std_area_um2=%.1f mixed_cells=%d macro_um2=%.1f free_um2=%.1f fill=%.3f std_util=%.3f boxes=%s" \
        $name [llength [dict get $members $mask]] $std [dict get $mixed $mask] $mac $free $fill $sutil [dict get $boxes $mask]]
    if {$sutil > 0.60} {error "OT_LCR region $name std utilisation $sutil > 0.60: resize the outline from synthesis area"}
    set region [odb::dbRegion_create $ot_lcr::block ot_lcr_$name]
    $region setRegionType INCLUSIVE
    foreach bx [dict get $boxes $mask] {
        lassign $bx x0 y0 x1 y1
        odb::dbBox_create $region [expr {round($x0*$ot_lcr::dbu)}] [expr {round($y0*$ot_lcr::dbu)}] [expr {round($x1*$ot_lcr::dbu)}] [expr {round($y1*$ot_lcr::dbu)}]
    }
    set group [odb::dbGroup_create $region ot_lcr_$name]
    foreach inst [dict get $members $mask] {$group addInst $inst}
}
set core [$ot_lcr::block getCoreArea]
set band [expr {(([$core xMax]-[$core xMin])/double($ot_lcr::dbu)) * (($ry0 - [$core yMin]/double($ot_lcr::dbu)) + ([$core yMax]/double($ot_lcr::dbu) - $ry1))}]
puts [format "OT_LCR fixed_or_hard=%d unowned_movable=0 top_free_band_um2=%.1f" $fixed $band]
puts "OT_LCR PASS complete core/hr partition (no shared seam); pin bands left for repair-created cells"

# Full-cone regional placement, after pin anchors. Unlike failed clk2, these
# regions own combinational logic as well as flops and leave a real 43.2um
# shared seam. No timing exception, density override or latency change.
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
set groups {}; set members [dict create 1 {} 2 {} 3 {}]
set areas [dict create 1 0.0 2 0.0 3 0.0]
set fixed 0
foreach inst [dict keys $ot_lcr::insts] {
    set master [$inst getMaster]
    if {[$master isBlock] || [$inst isFixed]} {incr fixed; continue}
    if {[dict exists $ot_lcr::seq $inst]} {
        set mask [dict get $ot_lcr::seq $inst]
    } else {
        set mask 0
        foreach net [concat [dict get $ot_lcr::ni $inst] [dict get $ot_lcr::no $inst]] {
            foreach direction {fwd rev} {
                if {[dict exists [set ot_lcr::$direction] $net]} {set mask [expr {$mask | [dict get [set ot_lcr::$direction] $net]}]}
            }
        }
        if {!$mask} {set mask 3}
    }
    if {![ot_lcr::null [$inst getGroup]]} {error "OT_LCR already grouped [$inst getName]"}
    dict lappend members $mask $inst
    dict set areas $mask [expr {[dict get $areas $mask] + [$master getWidth]*[$master getHeight]/double($ot_lcr::dbu*$ot_lcr::dbu)}]
}
# Fixed pin flops are deliberately ungrouped: their face assignments remain
# authoritative. The open channel and pin bands belong to top-level cells.
set core [$ot_lcr::block getCoreArea]
set y0 [$core yMin]; set y1 [$core yMax]
foreach {mask name x0 x1} {1 core 2.16 432.0 2 hr 475.2 775.44} {
    set region [odb::dbRegion_create $ot_lcr::block ot_lcr_$name]
    $region setRegionType INCLUSIVE
    odb::dbBox_create $region [expr {round($x0*$ot_lcr::dbu)}] $y0 [expr {round($x1*$ot_lcr::dbu)}] $y1
    set group [odb::dbGroup_create $region ot_lcr_$name]
    foreach inst [dict get $members $mask] {$group addInst $inst}
    puts "OT_LCR region=$name cells=[llength [dict get $members $mask]] std_area_um2=[dict get $areas $mask] x=$x0:$x1"
}
set seam_area [expr {43.2*($y1-$y0)/double($ot_lcr::dbu)}]
set shared [dict get $areas 3]
puts "OT_LCR fixed_or_hard=$fixed shared_cells=[llength [dict get $members 3]] shared_std_area_um2=$shared seam_area_um2=$seam_area"
if {$shared > 0.55*$seam_area} {error "OT_LCR mixed/rootless cones exceed real seam capacity; harden separate core/hr leaves rather than relax density"}
puts "OT_LCR PASS full cones partitioned with real shared channel"

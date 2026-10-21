# QW-TREE-SAFE 10-21 (COLL S1 PLAND face, after s1_pl / s1_pl4 CTS FAIL: codec0 internal spread 223.2 ps with
# 5,309 sinks spread unfenced at 1-2 % std density over 734 x 864 um).  Structural fix: clock-REGION fences.
# Every sequential cell is owned by the clock port that clocks it (BFS from the port net through buffers /
# inverters); the codec core region (codec0: controller + ring core sides) is fenced into the codec band between
# the CDC column and banks 2/3, the PHY region (codec0p: ring PHY sides + PHY pin registers) into the E strip
# beside the PHY pins.  INCLUSIVE regions: members must stay inside, other cells may share the box.  The groups are
# dissolved after GPL (clock_regions_dissolve.tcl, PRE_DETAIL_PLACE) so repair / CTS cells keep a legal home.
# No timing exception, no density override, no latency change; the landing rings (ot_coll_meso_ring) carry the
# codec0 <-> codec0p crossing as before.
namespace eval ot_cr {
    variable block [ord::get_db_block]
    variable dbu [$block getDbUnitsPerMicron]
}
proc ot_cr::null {v} {expr {$v eq "NULL" || $v eq ""}}
# name port boxes(um)
set ot_cr_spec {
    codec  codec0  {{286.2 216.0 464.4 648.0}}
    phy    codec0p {{697.0 280.8 732.2 604.8}}
}
set ot_cr_n 0
foreach {name port boxes} $ot_cr_spec {
    set bt [$ot_cr::block findBTerm $port]
    if {[ot_cr::null $bt] || [ot_cr::null [$bt getNet]]} {error "OT_CR missing clock port $port"}
    set seen [dict create]
    set queue [list [$bt getNet]]
    set members {}
    set area 0.0
    set skipped_fixed 0
    for {set i 0} {$i < [llength $queue]} {incr i} {
        set net [lindex $queue $i]
        if {[dict exists $seen $net]} continue
        dict set seen $net 1
        foreach it [$net getITerms] {
            if {![$it isInputSignal]} continue
            set inst [$it getInst]
            set m [$inst getMaster]
            if {[$m isBlock]} continue
            if {[$m isSequential]} {
                if {[$inst isFixed]} {incr skipped_fixed; continue}
                if {![ot_cr::null [$inst getGroup]]} continue
                lappend members $inst
                set area [expr {$area + [$m getWidth]*[$m getHeight]/double($ot_cr::dbu*$ot_cr::dbu)}]
            } elseif {[regexp {^(BUF|INV|HB)} [$m getName]]} {
                foreach ot [$inst getITerms] {
                    if {[$ot isOutputSignal] && ![ot_cr::null [$ot getNet]]} {lappend queue [$ot getNet]}
                }
            }
        }
    }
    set ra 0.0
    foreach bx $boxes {lassign $bx x0 y0 x1 y1; set ra [expr {$ra + ($x1-$x0)*($y1-$y0)}]}
    puts [format "OT_CR region=%s port=%s seq_cells=%d seq_area_um2=%.1f fixed_pin_flops=%d box_um2=%.1f seq_util=%.3f boxes=%s" \
        $name $port [llength $members] $area $skipped_fixed $ra [expr {$area/$ra}] $boxes]
    if {[llength $members] == 0} {error "OT_CR region $name: no sequential cells on $port"}
    if {$area/$ra > 0.35} {error "OT_CR region $name seq utilisation > 0.35: enlarge the box"}
    set region [odb::dbRegion_create $ot_cr::block ot_cr_$name]
    $region setRegionType INCLUSIVE
    foreach bx $boxes {
        lassign $bx x0 y0 x1 y1
        odb::dbBox_create $region [expr {round($x0*$ot_cr::dbu)}] [expr {round($y0*$ot_cr::dbu)}] [expr {round($x1*$ot_cr::dbu)}] [expr {round($y1*$ot_cr::dbu)}]
    }
    set group [odb::dbGroup_create $region ot_cr_$name]
    foreach inst $members {$group addInst $inst}
    incr ot_cr_n
}
puts "OT_CR PASS $ot_cr_n clock-region fences (codec0 band / codec0p E strip)"

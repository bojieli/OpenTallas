# Explicit sequential ownership for twelve native regional trees.
namespace eval ot_cr {
    variable block [ord::get_db_block]
    variable dbu [$block getDbUnitsPerMicron]
}
proc ot_cr::null {v} {expr {$v eq "NULL" || $v eq ""}}
# name port boxes(um)
set ot_cr_spec {
 codec codec0 {{394.971 394.971 691.2 641.829}}
 phy codec0p {{987.429 345.6 1034.331 740.571}}
 cal cal_ck {{2.469 394.971 296.229 592.457}}
 lcal cal_lck {{296.229 394.971 394.971 641.829} {987.429 740.571 1034.331 839.314}}
 txw tx_wck {{2.469 691.2 345.6 987.429}}
 txr tx_rck {{2.469 691.2 345.6 987.429}}
 rxw rx_wck {{2.469 49.371 345.6 394.971}}
 rxr rx_rck {{2.469 49.371 345.6 394.971}}
 bank0 codec1 {{345.6 98.743 691.2 394.971}}
 bank1 codec2 {{345.6 691.2 691.2 987.429}}
 bank2 codec3 {{691.2 98.743 987.429 394.971}}
 bank3 codec4 {{691.2 691.2 987.429 987.429}}
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
puts "OT_CR PASS $ot_cr_n clock-region fences (codec0 band / codec0p E strip / cal_ck + cal_lck cal channel)"

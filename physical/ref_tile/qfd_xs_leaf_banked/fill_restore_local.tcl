# Kept bank modules accept one positive data plane. Restore inverted-Q capture
# outputs in the S capture band, so both polarities do not cross the leaf.
set fc_blk [ord::get_db_block];set fc_u [$fc_blk getDbUnitsPerMicron]
array set fc_cells {};set fc_captures 0
foreach i [$fc_blk getInsts] {
    if {![lb_seq $i] || ![regexp {(?:^|\.)wd\[([0-9]+)\]} [lb_netname $i] -> bit]} {continue}
    incr fc_captures
    set queue {};foreach p [$i getITerms] {
        if {[[$p getMTerm] getIoType]=="OUTPUT"} {lappend queue [list [$p getNet] 0]}
    }
    set inv 0;array unset fc_seen;array set fc_seen {}
    while {[llength $queue]} {
        lassign [lindex $queue 0] net depth;set queue [lrange $queue 1 end]
        if {$net=="NULL"} {continue}
        if {$depth>3} {error "FILL_RESTORE: capture bit$bit has long polarity tree"}
        foreach p [$net getITerms] {
            if {[[$p getMTerm] getIoType]!="INPUT"} {continue}
            set c [$p getInst];set n [$c getName]
            if {[info exists fc_seen($n)]} {continue};set fc_seen($n) 1
            set m [[$c getMaster] getName]
            if {[string match INV* $m]} {incr inv;set fc_cells($n) $c;continue}
            if {[string match BUF* $m]} {
                set fc_cells($n) $c
                foreach q [$c getITerms] {if {[[$q getMTerm] getIoType]=="OUTPUT"} {lappend queue [list [$q getNet] [expr {$depth+1}]]}}
            } else {error "FILL_RESTORE: QN bit$bit feeds nonlocal mask/logic$m; bank synthesis isolation failed"}
        }
    }
    if {$inv!=1} {error "FILL_RESTORE: captured bit$bit expected1 dedicated positive restore, found$inv"}
}
if {$fc_captures!=1024} {error "FILL_RESTORE: expected1024 captured data bits, found$fc_captures"}
set fc_r "NULL"
foreach r [$fc_blk getRegions] {if {[$r getName]=="dvm_fill_restore_S"} {set fc_r $r}}
if {$fc_r=="NULL"} {
    set fc_r [odb::dbRegion_create $fc_blk dvm_fill_restore_S]
    odb::dbBox_create $fc_r [expr {round(2.16*$fc_u)}] [expr {round(14.04*$fc_u)}] [expr {round(62.64*$fc_u)}] [expr {round(23.76*$fc_u)}]
    $fc_r setRegionType INCLUSIVE
    set fc_g [odb::dbGroup_create $fc_r dvm_fill_restore_group]
} else {set fc_g [lindex [$fc_r getGroups] 0]}
set fc_a 0.0
foreach n [array names fc_cells] {
    set i $fc_cells($n);set old [$i getGroup]
    if {$old!="NULL" && $old!=$fc_g} {error "FILL_RESTORE: restore already assigned to data bank$n"}
    if {$old!=$fc_g} {$fc_g addInst $i}
    set m [$i getMaster];set fc_a [expr {$fc_a+double([$m getWidth])*[$m getHeight]/$fc_u/$fc_u}]
}
puts "FILL_RESTORE PASS capture_bits=$fc_captures restore_cells=[array size fc_cells] area_um2=$fc_a S_band_um=2.16,14.04,62.64,23.76 route_admitted=0"

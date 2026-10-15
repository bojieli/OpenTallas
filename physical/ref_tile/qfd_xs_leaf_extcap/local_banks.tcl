# Structural admission hook: eight *actual* registered bank cones, not a
# rectangular outline claim. Run after I/O hold insertion before pin flops.
set lb_blk [ord::get_db_block]
set lb_dbu [$lb_blk getDbUnitsPerMicron]
proc lb_seq {inst} {return [regexp {DFF|SDFF|LATCH|DHL} [[$inst getMaster] getName]]}
proc lb_input {it} {expr {[[$it getMTerm] getIoType] == "INPUT" && [[$it getMTerm] getSigType] == "SIGNAL"}}
proc lb_netname {net} {regsub -all {\\} [$net getName] {} n;return $n}
proc lb_storage_key {i} {
    set n [lb_netname $i]
    if {[regexp {g_t\[([01])\].*g_bank\[([0-3])\].*g_e\[([0-9]+)\]} $n -> t b e]} {return [expr {$t*4+$b}]}
    if {[regexp {g_t\[([01])\].*g_e\[([0-9]+)\]} $n -> t e]} {return [expr {$t*4+$e/32}]}
    return -1
}
array set lb_roots {}
# Kept module output q is the source alias of result_q. The mapped FF
# instance uses this output name; result_q NET aliases disappear after RSZ.
# Bind only real sequential instances with the exact source bank/output path.
foreach i [$lb_blk getInsts] {
    if {[lb_seq $i] && [regexp {g_t\[([01])\].*g_bank\[([0-3])\].*(?:result_q|u_bank/q)\[([0-9]+)\]} [lb_netname $i] -> t b bit]} {
        lappend lb_roots([expr {$t*4+$b}]) $i
    }
}
if {[array size lb_roots]!=8} {error "BANK_LOCALITY: expected8 result banks, found[array size lb_roots]"}
# Localize the storage D muxes as well as the read tree. Shared write
# polarity/enable logic remains in the common channels; per-bit write muxes
# must stay with their owning memory. Count ownership before assigning groups.
array set lb_storage {}
array set lb_storage_owner {}
foreach i [$lb_blk getInsts] {
    set k [lb_storage_key $i]
    if {[lb_seq $i] && $k>=0} {
        lappend lb_storage($k) $i;set lb_storage_owner([$i getName]) $k
    }
}
array set lb_write {}
array set lb_write_owners {}
for {set k 0} {$k<8} {incr k} {
    if {![info exists lb_storage($k)] || [llength $lb_storage($k)]!=544} {error "BANK_WRITE: bank$k expected544 actual storage flops"}
    set queue $lb_storage($k);set lb_write($k) {};array unset wseen;array set wseen {}
    while {[llength $queue]} {
        set i [lindex $queue 0];set queue [lrange $queue 1 end];set n [$i getName]
        if {[info exists wseen($n)]} {continue};set wseen($n) 1
        if {[regexp -nocase {TIE(HI|LO)|TIE[01]|LOGIC[01]} [[$i getMaster] getName]]} {continue}
        if {[lb_seq $i]} {
            if {![info exists lb_storage_owner($n)]} {continue}
            if {$lb_storage_owner($n)!=$k} {error "BANK_WRITE: cross-bank feedback$n"}
        }
        lappend lb_write($k) $i;lappend lb_write_owners($n) $k
        foreach it [$i getITerms] {
            if {![lb_input $it]} {continue}
            if {[lb_seq $i] && [string toupper [[$it getMTerm] getName]] ni {D DATA}} {continue}
            set net [$it getNet];if {$net=="NULL"} {continue}
            foreach d [$net getITerms] {if {[[$d getMTerm] getIoType]=="OUTPUT"} {lappend queue [$d getInst]}}
        }
    }
}
array set lb_owner {}
set lb_total 0
for {set k 0} {$k<8} {incr k} {
    if {![info exists lb_roots($k)] || [llength $lb_roots($k)]!=17} {
        error "BANK_LOCALITY: bank$k must have17 actual result flops"
    }
    set queue $lb_roots($k);set cells {};array unset seen;array set seen {}
    while {[llength $queue]} {
        set i [lindex $queue 0];set queue [lrange $queue 1 end];set name [$i getName]
        if {[info exists seen($name)]} {continue};set seen($name) 1
        if {[regexp -nocase {TIE(HI|LO)|TIE[01]|LOGIC[01]} [[$i getMaster] getName]]} {continue}
        if {[info exists lb_owner($name)] && $lb_owner($name)!=$k} {
            error "BANK_LOCALITY: shared read-cone cell$name between bank$k and$lb_owner($name); partition not preserved"
        }
        set lb_owner($name) $k;lappend cells $i
        # Result D cones terminate at the bank's storage/select registers.
        # Do not pull the common write/clear/pin buses into a bank fence.
        if {[lb_seq $i] && [lsearch -exact $lb_roots($k) $i]<0} {continue}
        foreach it [$i getITerms] {
            if {![lb_input $it]} {continue}
            if {[lb_seq $i] && [string toupper [[$it getMTerm] getName]] ni {D DATA}} {continue}
            set net [$it getNet];if {$net=="NULL"} {continue}
            foreach driver [$net getITerms] {
                if {[[$driver getMTerm] getIoType]=="OUTPUT"} {lappend queue [$driver getInst]}
            }
        }
    }
    set wunique 0;set wshared 0
    foreach i $lb_write($k) {
        set n [$i getName]
        if {[llength $lb_write_owners($n)]>1} {incr wshared;continue}
        if {[info exists seen($n)]} {continue}
        if {[info exists lb_owner($n)] && $lb_owner($n)!=$k} {error "BANK_WRITE: conflicting read/write owner$n"}
        set lb_owner($n) $k;set seen($n) 1;lappend cells $i;incr wunique
    }
    set area 0.0;set ff 0
    foreach i $cells {
        set m [$i getMaster];set area [expr {$area+double([$m getWidth])*[$m getHeight]/$lb_dbu/$lb_dbu}]
        if {[lb_seq $i]} {incr ff}
        if {[lb_seq $i]} {
            set sk [lb_storage_key $i]
            if {$sk>=0 && $sk!=$k} {error "BANK_LOCALITY: bank$k reads cross-bank storage[$i getName]"}
        }
    }
    # Actual full read+unique-write cones are374.6..382.6um2. This
    # larger671.85um2 fence gives~58% occupancy while fixed I/O bands retain
    #24.84um S/25.92um N. Shared decode stays in common channels.
    set x0 6.48;set x1 58.32
    set physical_k [lsearch -exact {0 2 4 6 1 3 5 7} $k]
    set y0 [expr {24.84+$physical_k*14.04}]
    set y1 [expr {37.8+$physical_k*14.04}]
    set util [expr {$area/(($x1-$x0)*($y1-$y0))}]
    if {$util>0.70} {error "BANK_LOCALITY: bank$k cellarea$area exceeds70percent actual fencecapacity (util$util); resize/repartition before route"}
    set r "NULL"
    foreach old [$lb_blk getRegions] {if {[$old getName]=="dvm_local_bank_$k"} {set r $old}}
    if {$r=="NULL"} {
        set r [odb::dbRegion_create $lb_blk "dvm_local_bank_$k"]
        odb::dbBox_create $r [expr {round($x0*$lb_dbu)}] [expr {round($y0*$lb_dbu)}] [expr {round($x1*$lb_dbu)}] [expr {round($y1*$lb_dbu)}]
        $r setRegionType INCLUSIVE
        set g [odb::dbGroup_create $r "dvm_local_bank_group_$k"]
    } else {set g [lindex [$r getGroups] 0]}
    foreach i $cells {
        set old [$i getGroup]
        if {$old!="NULL" && $old!=$g} {error "BANK_LOCALITY: cell[$i getName] already belongs to another group"}
        if {$old!=$g} {
            $g addInst $i
            # A newly resized buffer can be>57um from its assigned bank,
            # beyond DPL's default27um vertical search. Seed only these new
            # movable data cells inside the real region before legalization.
            if {[info exists ::dvm_bank_rebind] && $::dvm_bank_rebind} {
                set bb [$i getBBox]
                if {[$bb xMin]<$x0*$lb_dbu || [$bb yMin]<$y0*$lb_dbu || [$bb xMax]>$x1*$lb_dbu || [$bb yMax]>$y1*$lb_dbu} {
                    if {[$i getPlacementStatus] in {FIRM LOCKED COVER}} {error "BANK_REBIND: cannot move fixed cell[$i getName]"}
                    set row [lindex [$lb_blk getRows] 0];set site [$row getSite]
                    set sw [$site getWidth];set sh [$site getHeight]
                    set m [$i getMaster]
                    set sx [expr {int((($x0+$x1)*$lb_dbu/2-[$m getWidth]/2)/$sw)*$sw}]
                    set sy [expr {int((($y0+$y1)*$lb_dbu/2)/$sh)*$sh}]
                    $i setLocation $sx $sy
                    $i setPlacementStatus PLACED
                    puts "BANK_REBIND seed_new_cell=[$i getName] bank=$k xy_dbu=$sx,$sy"
                }
            }
        }
    }
    incr lb_total [llength $cells]
    puts "BANK_LOCALITY bank=$k cells=[llength $cells] flops=$ff area_um2=$area util=$util box_um=$x0,$y0,$x1,$y1 roots=17 unique_write_added=$wunique shared_write_global=$wshared"
}
puts "BANK_LOCALITY PASS banks=8 cells=$lb_total locality_groups_bound=1 physical_route_admitted=0"

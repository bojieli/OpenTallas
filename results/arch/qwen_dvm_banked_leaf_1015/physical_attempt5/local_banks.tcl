# Structural admission hook: eight *actual* registered bank cones, not a
# rectangular outline claim. Run after I/O hold insertion before pin flops.
set lb_blk [ord::get_db_block]
set lb_dbu [$lb_blk getDbUnitsPerMicron]
proc lb_seq {inst} {return [regexp {DFF|SDFF|LATCH|DHL} [[$inst getMaster] getName]]}
proc lb_input {it} {expr {[[$it getMTerm] getIoType] == "INPUT" && [[$it getMTerm] getSigType] == "SIGNAL"}}
proc lb_netname {net} {regsub -all {\\} [$net getName] {} n;return $n}
array set lb_roots {}
# The technology-mapped flop INSTANCE retains the kept result register name,
# escaped by OpenDB. Original Q net aliases may disappear when inverted-Q
# flops are optimized into the final mux. Bind directly to actual named flops.
foreach i [$lb_blk getInsts] {
    if {[lb_seq $i] && [regexp {g_t\[([01])\].*g_bank\[([0-3])\].*result_q} [lb_netname $i] -> t b]} {
        lappend lb_roots([expr {$t*4+$b}]) $i
    }
}
if {[array size lb_roots]!=8} {error "BANK_LOCALITY: expected8 result banks, found[array size lb_roots]"}
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
            set net [$it getNet];if {$net=="NULL"} {continue}
            foreach driver [$net getITerms] {
                if {[[$driver getMTerm] getIoType]=="OUTPUT"} {lappend queue [$driver getInst]}
            }
        }
    }
    set area 0.0;set ff 0
    foreach i $cells {
        set m [$i getMaster];set area [expr {$area+double([$m getWidth])*[$m getHeight]/$lb_dbu/$lb_dbu}]
        if {[lb_seq $i]} {incr ff}
        # Cones must never select another tile/bank's storage.
        foreach it [$i getITerms] {
            if {[[$it getMTerm] getIoType]!="OUTPUT"} {continue}
            set n [$it getNet];if {$n=="NULL"} {continue}
            if {[regexp {g_t\[([01])\].*g_e\[([0-9]+)\]} [lb_netname $n] -> t e]} {
                if {$t*4+$e/32!=$k} {error "BANK_LOCALITY: bank$k reads cross-bank storage[$n getName]"}
            }
        }
    }
    # Actual failed-placement ODB measured the fixed I/O stages before
    # choosing these boxes. Reserve24.84um S and27um N; bank fence498.636um2
    # has <=1.329um2 measured fixed overlap and~54% actual occupancy.
    # This avoids both the original181% top density and the later103% N-bank
    # density caused by the40-column output pin-flop placement band.
    set x0 8.1;set x1 56.7
    set y0 [expr {24.84+$k*12.42}]
    set y1 [expr {35.1+$k*12.42}]
    set util [expr {$area/(($x1-$x0)*($y1-$y0))}]
    if {$util>0.70} {error "BANK_LOCALITY: bank$k cellarea$area exceeds70percent actual fencecapacity (util$util); resize/repartition before route"}
    set r [odb::dbRegion_create $lb_blk "dvm_local_bank_$k"]
    odb::dbBox_create $r [expr {round($x0*$lb_dbu)}] [expr {round($y0*$lb_dbu)}] [expr {round($x1*$lb_dbu)}] [expr {round($y1*$lb_dbu)}]
    $r setRegionType INCLUSIVE
    set g [odb::dbGroup_create $r "dvm_local_bank_group_$k"]
    foreach i $cells {$g addInst $i}
    incr lb_total [llength $cells]
    puts "BANK_LOCALITY bank=$k cells=[llength $cells] flops=$ff area_um2=$area util=$util box_um=$x0,$y0,$x1,$y1 roots=17"
}
puts "BANK_LOCALITY PASS banks=8 cells=$lb_total locality_groups_bound=1 physical_route_admitted=0"

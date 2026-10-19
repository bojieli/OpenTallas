# Compact199 native repair: existing dedicated boundary registers at their pins.
# Placement only; connectivity, clocks, SDC, outline and cycle count are unchanged.
set bf_blk [ord::get_db_block]
set ::bf_core [$bf_blk getCoreArea]
set ::bf_rh [[[lindex [$bf_blk getRows] 0] getSite] getHeight]
set bf_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
proc bf_band_target {box} {
    set bf_core $::bf_core; set bf_rh $::bf_rh
    set x [expr {([$box xMin]+[$box xMax])/2}]
    set y [expr {([$box yMin]+[$box yMax])/2}]
    set ds [list [expr {abs($x-[$bf_core xMin])}] [expr {abs($x-[$bf_core xMax])}] [expr {abs($y-[$bf_core yMin])}] [expr {abs($y-[$bf_core yMax])}]]
    set face [lsearch -exact $ds [lindex [lsort -integer $ds] 0]]
    if {$face == 0} {set x [$bf_core xMin]}
    if {$face == 1} {set x [expr {[$bf_core xMax]-2*$bf_rh}]}
    if {$face == 2} {set y [$bf_core yMin]}
    if {$face == 3} {set y [expr {[$bf_core yMax]-$bf_rh}]}
    return [list $x $y]
}
set bf_moved [dict create]
set bf_ports 0
foreach bt [$bf_blk getBTerms] {
    if {[$bt getSigType] in {POWER GROUND CLOCK} || [regexp {^(clk|rst)} [$bt getName]]} continue
    set bp [lindex [$bt getBPins] 0]
    if {$bp eq "" || $bp eq "NULL"} continue
    set box [lindex [$bp getBoxes] 0]
    lassign [bf_band_target $box] x y
    set net [$bt getNet]
    set chain {}; set regs {}
    if {[$bt getIoType] eq "OUTPUT"} {
        for {set k 0} {$k < 5 && $net ne "NULL" && $net ne ""} {incr k} {
            set drv ""; set loads [llength [$net getBTerms]]
            foreach t [$net getITerms] {
                if {[$t isInputSignal]} {incr loads}
                if {[$t isOutputSignal]} {set drv [$t getInst]}
            }
            if {$drv eq "" || $loads != 1} break
            set m [[$drv getMaster] getName]
            if {[string match *DFF* $m]} {lappend regs $drv; break}
            if {![regexp {^(BUF|INV|HB)} $m]} break
            lappend chain $drv
            set net ""
            foreach t [$drv getITerms] {if {[$t isInputSignal]} {set net [$t getNet]; break}}
        }
    } elseif {[$bt getIoType] eq "INPUT"} {
        # Only direct capture registers/private buffer chains qualify. Never move logic cones.
        for {set k 0} {$k < 5 && $net ne "NULL" && $net ne ""} {incr k} {
            set sinks {}
            foreach t [$net getITerms] {if {[$t isInputSignal]} {lappend sinks $t}}
            if {[llength $sinks] != 1} break
            set t [lindex $sinks 0]; set inst [$t getInst]; set m [[$inst getMaster] getName]
            if {[string match *DFF* $m] && [[$t getMTerm] getName] eq "D"} {lappend regs $inst; break}
            if {![regexp {^(BUF|INV|HB)} $m]} break
            lappend chain $inst; set net ""
            foreach q [$inst getITerms] {if {[$q isOutputSignal]} {set net [$q getNet]; break}}
        }
    }
    if {[llength $regs] == 0} {puts "BF_BAND skip [$bt getName]"; continue}
    foreach inst [concat $chain $regs] {
        if {[$inst getPlacementStatus] in {FIRM LOCKED COVER}} {error "BF_BAND protected boundary register [$inst getName]"}
        if {[dict exists $bf_moved [$inst getName]]} {error "BF_BAND shared boundary register [$inst getName]"}
        $inst setLocation $x $y
        dict set bf_moved [$inst getName] [$bt getName]
    }
    incr bf_ports
    puts "BF_BAND pin [$bt getName] cells [llength [concat $chain $regs]] target [expr {$x/double($bf_dbu)}],[expr {$y/double($bf_dbu)}]"
}
puts "BF_BAND ports $bf_ports moved [dict size $bf_moved]"
if {$bf_ports == 0} {error "BF_BAND no boundary registers found"}
detailed_placement
check_placement -verbose

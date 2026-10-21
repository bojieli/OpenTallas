# Reconstruct the original post-repeater Tcl state without repair_design or moving any cell.
read_db /baseline/out/place.odb
source /baseline/die_repeaters.tcl
set f [open /baseline/die_repeaters_step.tcl]
set found 0
while {[gets $f line]>=0} {
    if {[regexp {^set ot_die_rep_v \[ot_die_repeaters (.*)\]$} $line -> expression]} {
        uplevel #0 "set cfg $expression"
        incr found
    }
}
close $f
if {$found != 1} {error "missing/ambiguous original repeater configuration"}
# Evaluate only the original default/config merge, ending before its first functional work.
set body [info body ot_die_repeaters]
set marker {  dict with d {}}
set end [string first $marker $body]
if {$end < 0} {error "original configuration prefix changed"}
set prefix [string range $body 0 [expr {$end+[string length $marker]-1}]]
eval $prefix
# Preserve the original cfg projection rather than silently skipping post-GRT resizing.
set start [string first {  set ::ot_die_rep_cfg } $body]
set stop [string first {  set ::ot_die_rep_pre $pre} $body]
if {$start < 0 || $stop <= $start} {error "original post-GRT state contract changed"}
eval [string range $body $start [expr {$stop-1}]]
set ::ot_die_rep_pre [ot_die_rep_inst_map [ord::get_db_block]]
set f [open /baseline/die_repeaters.json];set original_report [read $f];close $f
if {![regexp {"instances_pre"\s*:\s*([0-9]+)} $original_report -> expected_pre] || [dict size $::ot_die_rep_pre] != $expected_pre} {error "original preexisting instance count mismatch"}
set f [open /baseline/die_repeaters.skip_nets.txt]
set ::ot_die_rep_skip [dict create]
foreach n [split [string trim [read $f]] "\n"] {if {$n ne ""} {dict set ::ot_die_rep_skip $n original_persisted}}
close $f
if {![regexp {"skip_nets"\s*:\s*([0-9]+)} $original_report -> expected_skip] || [dict size $::ot_die_rep_skip] != $expected_skip} {error "original persisted skip count mismatch"}
# These are the SAME original obstacles used by the first spread, before new repeaters existed.
set blk [ord::get_db_block]
set obs {}; array set ob {}; set cb 200000
foreach inst [$blk getInsts] {
    if {![$inst isPlaced]} continue
    set bb [$inst getBBox]
    set box [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    set k [llength $obs]; lappend obs $box
    for {set i [expr {[lindex $box 0]/$cb}]} {$i <= [lindex $box 2]/$cb} {incr i} {
        for {set j [expr {[lindex $box 1]/$cb}]} {$j <= [lindex $box 3]/$cb} {incr j} {lappend ob($i,$j) $k}
    }
}
foreach bk [$blk getBlockages] {
    if {[$bk isSoft]} continue
    set bb [$bk getBBox]
    set box [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    set k [llength $obs]; lappend obs $box
    for {set i [expr {[lindex $box 0]/$cb}]} {$i <= [lindex $box 2]/$cb} {incr i} {
        for {set j [expr {[lindex $box 1]/$cb}]} {$j <= [lindex $box 3]/$cb} {incr j} {lappend ob($i,$j) $k}
    }
}
set f [open /baseline/die_repeaters.spread1.json]
set raw [read $f]; close $f
if {![regexp {"slot_width_um"\s*:\s*([0-9.eE+-]+)} $raw -> slot_um]} {error "missing original spread slot width"}
set slw [expr {round($slot_um*[$blk getDbUnitsPerMicron])}]
if {$slw <= 0} {error "invalid original spread slot width"}
set f [open /work/resume_state.tcl w]
foreach name {ot_die_rep_cfg ot_die_rep_pre ot_die_rep_skip} {puts $f [list set ::$name [set ::$name]]}
puts $f [list set ::ot_die_rep_slw $slw]
puts $f [list set ::ot_die_rep_obs $obs]
puts $f [list array set ::ot_die_rep_ob [array get ob]]
close $f
puts "HEAD_RESUME_STATE pre=[dict size $::ot_die_rep_pre] skip=[dict size $::ot_die_rep_skip] obstacles=[llength $obs] slot_dbu=$slw cfg=$::ot_die_rep_cfg"

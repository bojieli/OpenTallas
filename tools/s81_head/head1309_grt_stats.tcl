set C $::env(OT_CORNER)
set c $C
source /work/postcts_gate.tcl
if {$ot_pg_mode ne "global_routing"} {error "HEAD GRT diagnostic refuses placement fallback"}
set blk [ord::get_db_block];set dbu [$blk getDbUnitsPerMicron]
set groups {};set ck {}
set f [open /work/grt_clock_${c}.tsv w];puts $f "name\tx_um\ty_um\tclock_ps\tleaf"
foreach p [all_registers -clock_pins] {
 set it [sta::sta_to_db_pin $p];if {$it eq "NULL" || $it eq ""} continue
 set i [$it getInst];set raw [$i getName];set nm [string map [list "\\" ""] $raw]
 set a [get_property $p arrival_max_rise];if {$a eq "" || $a eq "INF"} continue
 set a [expr {double($a)}];dict set ck $raw $a
 set tag all
 if {[[$i getMaster] isBlock]} {set tag macro:$nm
 } elseif {[regexp {u_m[./]cap([01])\[} $nm -> b]} {set tag cap$b
 } elseif {[regexp {u_m[./]u_rom_addr([01])[./](?:addr|q)\[} $nm -> b]} {set tag addr$b
 } elseif {[string match *u_c* $nm]} {set tag chain}
 dict lappend groups $tag $a
 set bb [$i getBBox];set x [expr {([$bb xMin]+[$bb xMax])/2.0/$dbu}];set y [expr {([$bb yMin]+[$bb yMax])/2.0/$dbu}]
 puts $f "$raw\t$x\t$y\t$a\t[[$it getNet] getName]"
}
close $f
proc stats {v} {
 set v [lsort -real $v];set n [llength $v];set s 0.0;foreach a $v {set s [expr {$s+$a}]}
 return "n $n min [lindex $v 0] mean [expr {$s/$n}] max [lindex $v end]"
}
dict for {tag v} $groups {puts "HEAD_CLOCK $c $tag [stats $v]"}
puts "HEAD_STA $c basis GLOBAL_ROUTING_DIAGNOSTIC setup [sta::time_sta_ui [sta::worst_slack_cmd max]] hold [sta::time_sta_ui [sta::worst_slack_cmd min]]"
set classes {};set raw_worst {}
foreach p [find_timing_paths -path_delay min -group_path_count 100000 -endpoint_path_count 1 -slack_max 0] {
 set start [get_full_name [get_property $p startpoint]];set end [get_full_name [get_property $p endpoint]]
 set tag r2r
 if {![string match */* $start]} {set tag input}
 if {$start eq "rst_n"} {set tag reset}
 if {[string match *u_c* $start] && [string match *u_c* $end]} {set tag chain}
 if {[string match *cap* $start]} {set tag cap_transport}
 set slack [get_property $p slack]
 dict lappend classes $tag $slack
}
dict for {tag v} $classes {puts "HEAD_HOLD $c $tag [stats $v]"}

set ::env(OT_PS_OUT) /work/grt_pairs_${c}.tsv
set ::env(CORNER) $c
source /work/pair_skew.tcl

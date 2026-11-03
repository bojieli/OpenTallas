# Three existing DATA buffer poses only. This is not a routed/timed checkpoint.
read_db /work/input.odb
source /work/sc_guard.tcl
source /work/pg_connect.tcl
set b [ord::get_db_block];set u [expr {double([$b getDbUnitsPerMicron])}]
set before_cells [sc_cells];set expected $before_cells;set before_inc [sc_inc];set before_terms [sc_terms];set before_nets [sc_nets]
set row_orient {};foreach row [$b getRows] {dict set row_orient [lindex [$row getOrigin] 1] [$row getOrient]}
set f [open /work/moves.tsv];set rows [split [string trim [read $f]] \n];close $f
if {[llength $rows]!=3} {error SC_BUFFER_ALLOWLIST_COUNT}
foreach row $rows {
 lassign [split $row \t] name master ox0 oy0 ox1 oy1 nx0 ny0 nx1 ny1 orient
 set i [$b findInst $name]
 if {$i eq "NULL" || [[$i getMaster] getName] ne $master || $master ne "BUFx6f_ASAP7_75t_R"} {error "SC_BUFFER_IDENTITY $name"}
 set q [$i getBBox]
 if {[list [$q xMin] [$q yMin] [$q xMax] [$q yMax]] ne [list $ox0 $oy0 $ox1 $oy1]} {error "SC_BUFFER_OLD_POSE $name"}
 if {![dict exists $row_orient $ny0] || [dict get $row_orient $ny0] ne $orient} {error "SC_BUFFER_ROW_ORIENT $name"}
 foreach t [$i getITerms] {set n [$t getNet];if {$n ne "NULL" && [$n getSigType] eq "CLOCK"} {error "SC_BUFFER_NOT_DATA $name"}}
 set flag [$i isDoNotTouch];set status [$i getPlacementStatus]
 if {$flag} {$i setDoNotTouch 0}
 try {
  if {$status in {FIRM LOCKED COVER}} {$i setPlacementStatus PLACED}
  $i setOrient $orient;$i setLocation $nx0 $ny0
 } finally {$i setPlacementStatus $status;$i setDoNotTouch $flag}
 set q [$i getBBox]
 if {[list [$q xMin] [$q yMin] [$q xMax] [$q yMax]] ne [list $nx0 $ny0 $nx1 $ny1]} {error "SC_BUFFER_NEW_POSE $name"}
 dict set expected $name [list $master [$i getLocation] [$i getOrient] $status $flag]
}
check_placement -verbose
if {[sc_cells] ne $expected || [sc_inc] ne $before_inc || [sc_terms] ne $before_terms || [sc_nets] ne $before_nets} {error SC_BUFFER_SOURCE_OR_NONALLOWLIST_MUTATION}
ot_pg_require_bound sc_three_buffer_import
set chain {
 {u.g_sc_shared_rst_1.u_pin/Q$_DFF_P_ QN u.g_sc_shared_rst_1.u_pin/place27112 A}
 {u.g_sc_shared_rst_1.u_pin/place27112 Y u.g_sc_shared_rst_1.u_pin/place27111 A}
 {u.g_sc_shared_rst_1.u_pin/place27111 Y u.g_sc_shared_rst_1.u_pin/place27110 A}
 {u.g_sc_shared_rst_1.u_pin/place27110 Y u.g_sc_shared_rst_1.u_pin/_1_ A}
}
set f [open /work/actual_chain.tsv w];puts $f "driver\tsink\tfanout\tactual_pin_l1_um";set mx 0
foreach edge $chain {
 lassign $edge di dp si sp;set dt [[ $b findInst $di] findITerm $dp];set st [[ $b findInst $si] findITerm $sp];set n [$dt getNet]
 if {$n eq "NULL" || $n ne [$st getNet] || [$n getSigType] ne "SIGNAL"} {error SC_BUFFER_CHAIN_GRAPH}
 set sinks {};foreach t [$n getITerms] {if {[[$t getMTerm] getIoType] eq "INPUT"} {lappend sinks $t}}
 if {[llength $sinks]!=1 || [lindex $sinks 0] ne $st} {error SC_BUFFER_CHAIN_FANOUT}
 set a [$dt getBBox];set z [$st getBBox]
 set d [expr {(abs(([$a xMin]+[$a xMax])-([$z xMin]+[$z xMax]))+abs(([$a yMin]+[$a yMax])-([$z yMin]+[$z yMax])))/(2*$u)}]
 set mx [expr {max($mx,$d)}];puts $f "$di/$dp\t$si/$sp\t1\t$d"
};close $f
write_db /work/SC_DATA_GEOMETRY_CHECKPOINT.odb
puts "SC_BUFFER_IMPORT_PASS only3DATAposes all_other_cells_FF_CLOCK_pins_graph_flags_preserved max_actual_pin_hop=$mx no_route_or_RC_credit"
set ::env(OT_GEOM_OUT) /work/sc_buffer_geometry.tsv
source /work/geom_dump.tcl

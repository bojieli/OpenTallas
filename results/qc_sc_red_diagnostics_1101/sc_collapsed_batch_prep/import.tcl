# Forty-nine existing DATA buffer poses only. This is not a routed/timed checkpoint.
read_db /work/input.odb
source /work/sc_guard.tcl
source /work/pg_connect.tcl
set b [ord::get_db_block];set u [expr {double([$b getDbUnitsPerMicron])}]
set before_cells [sc_cells];set expected $before_cells;set before_inc [sc_inc];set before_terms [sc_terms];set before_nets [sc_nets]
set row_orient {};foreach row [$b getRows] {dict set row_orient [lindex [$row getOrigin] 1] [$row getOrient]}
set f [open /work/moves.tsv];set rows [split [string trim [read $f]] \n];close $f
if {[llength $rows]!=49} {error SC_BUFFER_ALLOWLIST_COUNT}
set seen_targets {}
foreach row $rows {
 lassign [split $row \t] name master ox0 oy0 ox1 oy1 nx0 ny0 nx1 ny1 orient
 if {[dict exists $seen_targets $name]} {error SC_BATCH_DUPLICATE_ALLOWLIST_TARGET}
 dict set seen_targets $name 1
 set i [$b findInst $name]
 if {$i eq "NULL" || [[$i getMaster] getName] ne $master || $master ni {BUFx3_ASAP7_75t_R BUFx6f_ASAP7_75t_R BUFx16f_ASAP7_75t_R}} {error "SC_BUFFER_IDENTITY $name"}
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
ot_pg_require_bound sc_49_buffer_import
set chain {
 {u.u_15645/Q$_DFF_P_ QN u.u_15645/place27055 A}
 {u.u_15645/place27055 Y u.u_15645/place27054 A}
 {u.u_15645/place27054 Y u.u_15645/_1_ A}
 {u.u_15647/Q$_DFF_P_ QN u.u_15647/place27052 A}
 {u.u_15647/place27052 Y u.u_15647/place27051 A}
 {u.u_15647/place27051 Y u.u_15647/_1_ A}
 {u.u_15635/Q$_DFF_P_ QN u.u_15635/place27067 A}
 {u.u_15635/place27067 Y u.u_15635/place27066 A}
 {u.u_15635/place27066 Y u.u_15635/_1_ A}
 {u.u_15633/Q$_DFF_P_ QN u.u_15633/place27070 A}
 {u.u_15633/place27070 Y u.u_15633/place27069 A}
 {u.u_15633/place27069 Y u.u_15633/_1_ A}
 {u.u_15628/Q$_DFF_P_ QN u.u_15628/place27079 A}
 {u.u_15628/place27079 Y u.u_15628/place27078 A}
 {u.u_15628/place27078 Y u.u_15628/_1_ A}
 {u.u_15627/Q$_DFF_P_ QN u.u_15627/place27081 A}
 {u.u_15627/place27081 Y u.u_15627/place27080 A}
 {u.u_15627/place27080 Y u.u_15627/_1_ A}
 {u.u_208277/Q$_DFF_P_ QN u.u_208277/place26866 A}
 {u.u_208277/place26866 Y u.u_208277/place26865 A}
 {u.u_208277/place26865 Y u.u_208277/_1_ A}
 {u.u_208279/Q$_DFF_P_ QN u.u_208279/place26864 A}
 {u.u_208279/place26864 Y u.u_208279/place26863 A}
 {u.u_208279/place26863 Y u.u_208279/_1_ A}
 {u.u_208281/Q$_DFF_P_ QN u.u_208281/place26862 A}
 {u.u_208281/place26862 Y u.u_208281/place26861 A}
 {u.u_208281/place26861 Y u.u_208281/_1_ A}
 {u.u_209840/Q$_DFF_P_ QN u.u_209840/place26852 A}
 {u.u_209840/place26852 Y u.u_209840/place26851 A}
 {u.u_209840/place26851 Y u.u_209840/_1_ A}
 {u.u_15629/Q$_DFF_P_ QN u.u_15629/place27077 A}
 {u.u_15629/place27077 Y u.u_15629/place27076 A}
 {u.u_15629/place27076 Y u.u_15629/_1_ A}
 {u.u_15630/Q$_DFF_P_ QN u.u_15630/place27075 A}
 {u.u_15630/place27075 Y u.u_15630/place27074 A}
 {u.u_15630/place27074 Y u.u_15630/wire27142 A}
 {u.u_15630/wire27142 Y u.u_15630/_1_ A}
 {u.u_208276/Q$_DFF_P_ QN u.u_208276/place26867 A}
 {u.u_208276/place26867 Y u.u_208276/wire27156 A}
 {u.u_208276/wire27156 Y u.u_208276/_1_ A}
 {u.u_15631/Q$_DFF_P_ QN u.u_15631/place27073 A}
 {u.u_15631/place27073 Y u.u_15631/place27072 A}
 {u.u_15631/place27072 Y u.u_15631/_1_ A}
 {u.u_208283/Q$_DFF_P_ QN u.u_208283/place26860 A}
 {u.u_208283/place26860 Y u.u_208283/place26859 A}
 {u.u_208283/place26859 Y u.u_208283/_1_ A}
 {u.u_15636/Q$_DFF_P_ QN u.u_15636/place27065 A}
 {u.u_15636/place27065 Y u.u_15636/place27064 A}
 {u.u_15636/place27064 Y u.u_15636/_1_ A}
 {u.u_215771/Q$_DFF_P_ QN u.u_215771/place26798 A}
 {u.u_215771/place26798 Y u.u_215771/wire27155 A}
 {u.u_215771/wire27155 Y u.u_215771/_1_ A}
 {u.u_215773/Q$_DFF_P_ QN u.u_215773/place26797 A}
 {u.u_215773/place26797 Y u.u_215773/wire27154 A}
 {u.u_215773/wire27154 Y u.u_215773/_1_ A}
 {u.u_15637/Q$_DFF_P_ QN u.u_15637/place27063 A}
 {u.u_15637/place27063 Y u.u_15637/place27062 A}
 {u.u_15637/place27062 Y u.u_15637/_1_ A}
 {u.u_16292/Q$_DFF_P_ QN u.u_16292/place26984 A}
 {u.u_16292/place26984 Y u.u_16292/place26983 A}
 {u.u_16292/place26983 Y u.u_16292/_1_ A}
 {u.u_210624/Q$_DFF_P_ QN u.u_210624/place26843 A}
 {u.u_210624/place26843 Y u.u_210624/place26842 A}
 {u.u_210624/place26842 Y u.u_210624/_1_ A}
 {u.u_210626/Q$_DFF_P_ QN u.u_210626/place26840 A}
 {u.u_210626/place26840 Y u.u_210626/place26839 A}
 {u.u_210626/place26839 Y u.u_210626/_1_ A}
 {u.u_210628/Q$_DFF_P_ QN u.u_210628/place26836 A}
 {u.u_210628/place26836 Y u.u_210628/place26835 A}
 {u.u_210628/place26835 Y u.u_210628/_1_ A}
 {u.u_210627/Q$_DFF_P_ QN u.u_210627/place26838 A}
 {u.u_210627/place26838 Y u.u_210627/place26837 A}
 {u.u_210627/place26837 Y u.u_210627/_1_ A}
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
write_db /work/SC_BATCH_DATA_GEOMETRY_CHECKPOINT.odb
puts "SC_BUFFER_IMPORT_PASS only49DATAposes all_other_cells_FF_CLOCK_pins_graph_flags_preserved max_actual_pin_hop=$mx no_route_or_RC_credit"
set ::env(OT_GEOM_OUT) /work/sc_batch_buffer_geometry.tsv
source /work/geom_dump.tcl

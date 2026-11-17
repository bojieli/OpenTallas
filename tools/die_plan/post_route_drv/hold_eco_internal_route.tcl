# HOLD-FLOW-R 11-16: standalone incremental route of a routed DB after hold_eco_internal_insert.tcl (the prd hook does the
# same inside its ECO session; this form is for a routed DB that has no prd kit, e.g. a copy of a finished type).
# Environment: OT_HEI_IN (odb with the inserted cells), OT_HEI_CELLS (hold_eco_internal_cells.tsv: capture stage name ...),
# OT_HEI_OUT (output dir), OT_HEI_LIBS (file, one TT liberty path per line), OT_HEI_PG_DIR (optional kit dir with
# pg_track_truth.tcl / pg_pair_cap.tcl, replayed around the global route like the kit), OT_HEI_THREADS (default 4).
# Only the nets of the new HB4 cells are ripped and re-routed; every other wire is kept.  Fails closed on a count mismatch.
foreach v {OT_HEI_IN OT_HEI_CELLS OT_HEI_OUT OT_HEI_LIBS} { if {![info exists ::env($v)]} { error "OT_HEI_ROUTE: $v unset" } }
set fh [open $::env(OT_HEI_LIBS) r]
foreach f [split [read $fh] \n] { if {$f ne ""} { read_liberty $f } }
close $fh
read_db $::env(OT_HEI_IN)
set blk [ord::get_db_block]
set_thread_count [expr {[info exists ::env(OT_HEI_THREADS)] ? $::env(OT_HEI_THREADS) : 4}]
set_routing_layers -signal M2-M8 -clock M2-M8
set_global_routing_layer_adjustment M2-M8 0.25
set fh [open $::env(OT_HEI_CELLS) r]; set names {}
foreach ln [lrange [split [read $fh] \n] 1 end] { if {$ln ne ""} { lappend names [lindex [split $ln \t] 2] } }
close $fh
set selected [dict create]
foreach name $names {
  set inst [$blk findInst $name]
  if {$inst eq "NULL"} { error "OT_HEI_ROUTE missing inserted cell $name" }
  foreach it [$inst getITerms] {
    if {[[$it getMTerm] getSigType] ne "SIGNAL"} continue
    dict set selected [[$it getNet] getName] [$it getNet]
  }
}
set out $::env(OT_HEI_OUT)
set f [open $out/selected_nets.txt w]; set deleted 0
dict for {name net} $selected {
  puts $f $name
  set wire [$net getWire]
  if {$wire ne "NULL"} { odb::dbWire_destroy $wire; incr deleted }
  foreach guide [$net getGuides] { odb::dbGuide_destroy $guide }
}
close $f
puts "OT_HEI_ROUTE cells [llength $names] nets [dict size $selected] ripped_original_wires $deleted"
set pg [expr {[info exists ::env(OT_HEI_PG_DIR)] ? $::env(OT_HEI_PG_DIR) : ""}]
if {$pg ne "" && [file exists $pg/pg_track_truth.tcl] && [file exists $pg/pg_pair_cap.tcl]} {
  source $pg/pg_track_truth.tcl; ot_pgtt_add
  source $pg/pg_pair_cap.tcl; ot_pgcap_add
}
dict for {name net} $selected { grt::add_net_to_route $net }
pin_access
global_route -guide_file $out/route.guide -congestion_report_file $out/grt_congestion.rpt -congestion_iterations 30 -verbose
if {[llength [info commands ot_pgtt_remove]]} { ot_pgtt_remove }
write_db $out/hei_grt.odb
detailed_route -output_drc $out/hei_drc.rpt -output_maze $out/hei_maze.log -verbose 1
write_db $out/hei_routed.odb
puts "OT_HEI_ROUTE_DONE nets [dict size $selected]"
exit

# QC-SU-F4D probe: does read_guides put the rewritten (tree-only M5/M6) guides into the ODB that DRT uses?
set_thread_count 16
read_db $::env(ODB)
proc census {tag} {
  set c [dict create]
  foreach n [[ord::get_db_block] getNets] {
    set t [expr {[string match ot_ms_*_n [$n getName]] ? "tree" : "other"}]
    foreach g [$n getGuides] { dict incr c "$t:[[$g getLayer] getName]" }
  }
  puts "GUIDES $tag [lsort [dict keys $c]] :: $c"
}
census before
read_guides $::env(GUIDE)
census after
if {[info exists ::env(DRT)]} {
  set_routing_layers -signal M2-M6
  detailed_route -output_drc /out/drc.rpt -verbose 0 -droute_end_iter 6
  write_db /out/5_2_route_probe.odb
}

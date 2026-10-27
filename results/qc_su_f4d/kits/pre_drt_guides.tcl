# QC-SU-F4D PRE_DETAIL_ROUTE_TCL: load the tree-net-only rewritten guides into the ODB (DRT uses dbGuides, not the file)
if {[info exists ::env(OT_TREE_GUIDE)] && $::env(OT_TREE_GUIDE) ne ""} {
  read_guides $::env(OT_TREE_GUIDE)
  set c [dict create]
  foreach n [[ord::get_db_block] getNets] {
    set t [expr {[string match ot_ms_*_n [$n getName]] ? "tree" : "other"}]
    foreach g [$n getGuides] { dict incr c "$t:[[$g getLayer] getName]" }
  }
  puts "OT_TREE_GUIDE loaded $::env(OT_TREE_GUIDE) :: $c"
  if {[dict exists $c other:M6]} { error "OT_TREE_GUIDE: non-tree net has an M6 guide" }
}

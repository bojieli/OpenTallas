# DIE-QC-33 A0 NK graph homes (PRE_GLOBAL_PLACE, sourced at the end of face_flops.tcl) -- same mechanism as
# kit_istations.py: every non-face sequential cell + every ICG FIRM at its analytic graph home, name appended to
# ot_face_flops.txt so face_flops_release.tcl hands it to DPL as PLACED. Replaces the post-GPL NL-reset6 anchor list.
set gh_b [ord::get_db_block]
set gh_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set gh_in [open /work/nk_graph_homes.tsv r]
set gh_out [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
set gh_n 0; set gh_miss {}
while {[gets $gh_in ln] >= 0} {
  set a [split $ln "\t"]
  set i [$gh_b findInst [lindex $a 0]]
  if {$i eq "NULL"} { lappend gh_miss [lindex $a 0]; continue }
  set m [$i getMaster]
  $i setPlacementStatus PLACED
  $i setLocation [expr {round([lindex $a 1]*$gh_dbu - [$m getWidth]/2.0)}] [expr {round([lindex $a 2]*$gh_dbu - [$m getHeight]/2.0)}]
  $i setPlacementStatus FIRM
  puts $gh_out "[lindex $a 0]\tH\t[lindex $a 1]\t[lindex $a 2]\t-"
  incr gh_n
}
close $gh_in; close $gh_out
if {[llength $gh_miss]} { error "GRAPH_HOMES missing [llength $gh_miss]: [lrange $gh_miss 0 4]" }
puts "GRAPH_HOMES placed $gh_n cells FIRM"

# S81-COL-PRD-OBS 11-17 (FABLE-PD-S81-0720 B1): the post-route ECO (prd) path replaces the kit's POST_GLOBAL_ROUTE hook (grt_post.tcl, which
# removes the PG-track-truth GRT obstructions) with eco_post.tcl, so 5_1_grt.odb kept 3,967 temporary obstructions (col pg3: M5 2897 /
# M6 740 / M7 331) and detail route saw 15,736 static spacing violations and crashed (DRT-1231).  Two guards:
#   ot_prd_obs_seed   at the very top of eco_grt_pre.tcl (before any PG-track / keepout add): per-layer obstruction counts of the seed DB.
#   ot_prd_obs_check  in eco_post.tcl after the temporary ones are removed, BEFORE 5_1_grt.odb is written: the per-layer count must equal the
#                     seed's, else error (the GRT step fails, detail route never starts).
# OT_PRD_OBS_ALLOW="M5=1 M6=2" names deliberate extra obstructions a recipe adds on purpose (e.g. a temporary M5 block); OT_PRD_OBS_CHECK=0 = off.
proc ot_prd_obs_count {} {
  set cnt [dict create]
  foreach o [[ord::get_db_block] getObstructions] {
    set ly [[[$o getBBox] getTechLayer] getName]
    dict incr cnt $ly
  }
  return $cnt
}
proc ot_prd_obs_fmt {d} {
  set out {}
  foreach k [lsort [dict keys $d]] { lappend out "$k=[dict get $d $k]" }
  return [join $out " "]
}
proc ot_prd_obs_seed {} {
  set ::ot_prd_obs_seed_counts [ot_prd_obs_count]
  puts "OT_PRD_OBS seed [ot_prd_obs_fmt $::ot_prd_obs_seed_counts]"
}
proc ot_prd_obs_check {} {
  if {[info exists ::env(OT_PRD_OBS_CHECK)] && $::env(OT_PRD_OBS_CHECK) eq "0"} { puts "OT_PRD_OBS check skipped (OT_PRD_OBS_CHECK=0)"; return }
  if {![info exists ::ot_prd_obs_seed_counts]} { puts "OT_PRD_OBS check: no seed recorded (eco_grt_pre.tcl did not run): FAIL"; error "OT_PRD_OBS_CHECK no seed" }
  set allow [dict create]
  if {[info exists ::env(OT_PRD_OBS_ALLOW)]} {
    foreach t [split $::env(OT_PRD_OBS_ALLOW) " ,"] { if {[regexp {^([A-Za-z0-9]+)=([0-9]+)$} $t -> l n]} { dict set allow $l $n } }
  }
  set now [ot_prd_obs_count]
  set bad {}
  foreach ly [lsort -unique [concat [dict keys $::ot_prd_obs_seed_counts] [dict keys $now]]] {
    set s [expr {[dict exists $::ot_prd_obs_seed_counts $ly] ? [dict get $::ot_prd_obs_seed_counts $ly] : 0}]
    set n [expr {[dict exists $now $ly] ? [dict get $now $ly] : 0}]
    set a [expr {[dict exists $allow $ly] ? [dict get $allow $ly] : 0}]
    if {$n != $s + $a} { lappend bad "$ly seed $s allowed +$a now $n" }
  }
  if {[llength $bad]} {
    puts "OT_PRD_OBS_CHECK FAIL before 5_1_grt.odb is written: [join $bad {; }]"
    error "OT_PRD_OBS_CHECK FAIL: [join $bad {; }]"
  }
  puts "OT_PRD_OBS_CHECK PASS per-layer obstruction counts equal the seed ([ot_prd_obs_fmt $now])"
}

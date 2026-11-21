# Recreate the kit's opted-in PG routing constraints in a fresh incremental-GRT scene.
# Region adjustments live in GlobalRouter, not the ODB. Temporary track obstructions and
# cell keepouts were deliberately removed before that ODB was written. Replaying the
# generated config once is therefore necessary after read_db; sourcing grt_pre.tcl as a
# whole would also repeat unrelated repair/clock hooks. No PG metal or clock is edited.
set ::ot_grt_pg_replay_dir [file dirname [file normalize [info script]]]

proc ot_grt_pg_replay_config {kit} {
  set cfg [file join $kit config.mk]
  if {![file exists $cfg]} { error "OT_GRT_PG_REPLAY missing kit config: $cfg" }
  set fh [open $cfg]; set text [read $fh]; close $fh
  foreach line [split $text \n] {
    if {![regexp {^export[ \t]+([A-Z0-9_]+)[ \t]*(\?=|:=|=)[ \t]*(.*)$} $line -> key op value]} continue
    if {![regexp {^(OT_PGCAP|OT_PG_TRACK_TRUTH|OT_PG_CELL_KEEPOUT)($|_)} $key]} continue
    regsub {[ \t]+#.*$} $value {} value
    set value [string trim $value]
    # gen_phys emits literal values for these keys. Never silently use an unevaluated
    # make expression as a capacity setting in a standalone OpenROAD session.
    if {[string first {$} $value] >= 0} { error "OT_GRT_PG_REPLAY nonliteral generated value: $key=$value" }
    if {$op eq "?=" && [info exists ::env($key)]} continue
    set ::env($key) $value
  }
}

proc ot_grt_pg_replay_begin {{kit ""}} {
  if {[info exists ::ot_grt_pg_replay_active]} {
    puts "OT_GRT_PG_REPLAY already restored in this scene"
    return
  }
  if {$kit eq ""} { set kit $::ot_grt_pg_replay_dir }
  set kit [file normalize $kit]
  ot_grt_pg_replay_config $kit
  set applied {}
  foreach {key helper add} {
    OT_PG_CELL_KEEPOUT pg_cell_keepout.tcl ot_pgcko_add
    OT_PG_TRACK_TRUTH pg_track_truth.tcl ot_pgtt_add
    OT_OBS_GCELL_CAP obs_gcell_cap.tcl ot_obsgc_add
    OT_PGCAP pg_pair_cap.tcl ot_pgcap_add
  } {
    set path [file join $kit $helper]
    # FLOW-OBS-GCELL-1121: the obstruction sliver cap is default on (not a config.mk key); kits generated before it
    # have no helper and keep their old replay
    if {$key eq "OT_OBS_GCELL_CAP"} {
      if {([info exists ::env($key)] && $::env($key) eq "0") || ![file exists $path]} continue
    } elseif {![info exists ::env($key)] || $::env($key) ne "1"} continue
    if {![file exists $path]} { error "OT_GRT_PG_REPLAY $key=1 but helper missing: $path" }
    source $path
    $add
    lappend applied $key
  }
  set ::ot_grt_pg_replay_active $applied
  puts "OT_GRT_PG_REPLAY restored $applied from $kit/config.mk"
}

proc ot_grt_pg_replay_end {} {
  if {![info exists ::ot_grt_pg_replay_active]} return
  if {[info exists ::ot_grt_pg_replay_cleaned]} return
  # Keep router-internal region cuts for the rest of this scene, but do not write
  # temporary GRT-only geometry into the checkpoint used by detail route or STA.
  if {"OT_PG_TRACK_TRUTH" in $::ot_grt_pg_replay_active} { ot_pgtt_remove }
  if {"OT_PG_CELL_KEEPOUT" in $::ot_grt_pg_replay_active} { ot_pgcko_remove }
  set ::ot_grt_pg_replay_cleaned 1
  puts "OT_GRT_PG_REPLAY temporary geometry removed"
}

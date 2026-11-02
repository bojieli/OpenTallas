# Shared checked CLOCK-only restore. Call AFTER native RC estimation and BEFORE
# timing consumers. Explicit native dataset map; caller owns scene/stage selection.
# The original clock-only SPEF and immutable identity must be prequalified together.
# Explicit opt-in for a prequalified unloaded BUFFER-output clock branch.
# It remains in the full immutable graph comparison; no PORT alias or RC is made.
proc ::ot_clock_rc_check_empty_driver {name spec} {
  if {[lsort [dict keys $spec]] ne [lsort {instance master input output root source_net}]} {
    error "OT_MM_FROZEN_CLOCK_RC: malformed empty-driver profile: $name"
  }
  foreach key {instance master input output root source_net} {
    if {[dict get $spec $key] eq ""} {error "OT_MM_FROZEN_CLOCK_RC: empty profile field $key: $name"}
  }
  set block [::ord::get_db_block]
  set net [$block findNet $name]; set inst [$block findInst [dict get $spec instance]]
  if {$net in {NULL ""} || $inst in {NULL ""} || [$net getSigType] ne "CLOCK" ||
      [llength [$net getBTerms]] || [llength [$net getITerms]]!=1 ||
      ([$net getWire] ni {NULL ""} && [[$net getWire] count]!=0)} {
    error "OT_MM_FROZEN_CLOCK_RC: empty-driver native shape differs: $name"
  }
  # This scoped profile is the selected noninverting BUFx24 family only.
  if {[dict get $spec master] ne "BUFx24_ASAP7_75t_R" ||
      [[$inst getMaster] getName] ne [dict get $spec master] ||
      [dict get $spec input] ne "A" || [dict get $spec output] ne "Y"} {
    error "OT_MM_FROZEN_CLOCK_RC: unsupported empty-driver master/pins: $name"
  }
  set output [lindex [$net getITerms] 0]
  set input [$inst findITerm A]
  if {[$output getInst] ne $inst || [[$output getMTerm] getName] ne "Y" ||
      [[$output getMTerm] getIoType] ne "OUTPUT" || $input in {NULL ""} ||
      [[$input getMTerm] getIoType] ne "INPUT" || [$input getNet] in {NULL ""} ||
      [[$input getNet] getName] ne [dict get $spec source_net]} {
    error "OT_MM_FROZEN_CLOCK_RC: empty-driver pin/source join differs: $name"
  }
  set root [$block findBTerm [dict get $spec root]]
  if {$root in {NULL ""} || [$root getIoType] ne "INPUT"} {
    error "OT_MM_FROZEN_CLOCK_RC: empty-driver root is not a native input: $name"
  }
  set clock_sources {}
  foreach clock [::all_clocks] {
    foreach source [::get_property $clock sources] {lappend clock_sources [::get_full_name $source]}
  }
  if {[dict get $spec root] ni $clock_sources} {
    error "OT_MM_FROZEN_CLOCK_RC: empty-driver root is not a real clock source: $name"
  }
  set pins [::get_pins -quiet "[dict get $spec instance]/A"]
  if {[llength $pins]!=1} {error "OT_MM_FROZEN_CLOCK_RC: ambiguous native driver input: $name"}
  set roots {}
  foreach point [::get_fanin -to $pins -flat -startpoints_only -trace_arcs all] {
    lappend roots [::get_full_name $point]
  }
  if {[lsort -unique $roots] ne [list [dict get $spec root]]} {
    error "OT_MM_FROZEN_CLOCK_RC: empty-driver native root fanin differs: $name"
  }
  puts "OT_MM_FROZEN_CLOCK_EMPTY_DRIVER $name [dict get $spec instance]/Y root=[dict get $spec root]"
}

proc ::ot_clock_rc_restore_checked {maps baseline checker stem tag} {
  set ::ot_clock_rc_restore_verified 0
  foreach command {::ot_clk_freeze_assert ::ot_clk_dump ::ot_clk_restore_parasitics} {
    if {![llength [info commands $command]]} { error "OT_MM_FROZEN_CLOCK_RC: caller must stage the approved clock helper ($command absent)" }
  }
  if {![info exists ::ot_clk_frozen] || !$::ot_clk_frozen ||
      ![info exists ::ot_clk_frozen_nets] || ![llength $::ot_clk_frozen_nets]} {
    error "OT_MM_FROZEN_CLOCK_RC: original routed clock must already have a nonempty active freeze"
  }
  if {![file readable $baseline]} {
    error "OT_MM_FROZEN_CLOCK_RC: immutable original clock graph identity is required"
  }
  if {![file readable $checker]} { error "OT_MM_FROZEN_CLOCK_RC: existing clock geometry checker absent: $checker" }
  set expected {};set routed {};set unwired {};set pins {};set f [open $baseline r]
  while {[gets $f line] >= 0} {
    set fields [split $line \t]
    set kind [lindex $fields 0];set name [lindex $fields 1]
    if {$kind eq "PIN"} {dict set pins $name [lindex $fields 2];continue}
    if {$kind ne "NET"} continue
    set count [lindex $fields 3]
    if {![string is integer -strict $count] || $count<0} {close $f;error "OT_MM_FROZEN_CLOCK_RC: invalid original wire count: $name"}
    if {$count==0} {
      if {[lindex $fields 2] ne "CLOCK" || [lindex $fields 4] ne "" || [lindex $fields 5] ne ""} {
        close $f;error "OT_MM_FROZEN_CLOCK_RC: malformed unwired clock: $name"
      }
      lappend unwired $name
    } else {lappend routed $name}
    lappend expected $name
  }
  close $f
  set driver_profiles {}
  if {[info exists ::env(OT_POSTCTS_FROZEN_CLOCK_EMPTY_DRIVERS)]} {
    set driver_profiles $::env(OT_POSTCTS_FROZEN_CLOCK_EMPTY_DRIVERS)
    if {[catch {dict size $driver_profiles}]} {error "OT_MM_FROZEN_CLOCK_RC: malformed empty-driver dictionary"}
  }
  set used_profiles {}
  foreach name $unwired {
    if {[dict exists $driver_profiles $name]} {
      ::ot_clock_rc_check_empty_driver $name [dict get $driver_profiles $name]
      lappend used_profiles $name
    } elseif {![dict exists $pins $name] || [llength [dict get $pins $name]]!=1 ||
        ![string match {PORT:?*} [lindex [dict get $pins $name] 0]]} {
      error "OT_MM_FROZEN_CLOCK_RC: original loaded clock has no routed wire: $name"
    }
  }
  if {[lsort $used_profiles] ne [lsort [dict keys $driver_profiles]]} {
    error "OT_MM_FROZEN_CLOCK_RC: unused/wired/unknown empty-driver profile"
  }
  # ot_clk_freeze stores only nets with nonempty wire ops; the immutable
  # graph inventory additionally includes the unloaded aliases checked above.
  if {![llength $routed] || [lsort $routed] ne [lsort $::ot_clk_frozen_nets]} {
    error "OT_MM_FROZEN_CLOCK_RC: original routed identity and active frozen clock net sets differ"
  }
  # Existing freeze restores any destroyed clock wire byte-identically; the
  # existing graph checker also guards connectivity, masters and physical homes.
  ::ot_clk_freeze_assert "clock_rc_$tag"
  set f [open ${stem}.nets w];puts $f [join $expected \n];close $f
  ::ot_clk_dump ${stem}.tsv "clock_rc_$tag" ${stem}.nets
  if {[catch {exec python3 -I $checker $baseline ${stem}.tsv} result]} {
    error "OT_MM_FROZEN_CLOCK_RC: original clock graph/wire identity failed: $result"
  }
  # Approved -name helper reuses the EXISTING native datasets, replacing only
  # clock-net annotations. Its preflight refuses an absent/misspelled dataset.
  ::ot_clk_restore_parasitics $maps
  set ::ot_clock_rc_restore_verified 1
}

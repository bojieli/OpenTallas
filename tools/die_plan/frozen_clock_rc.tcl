# Shared checked CLOCK-only restore. Call AFTER native RC estimation and BEFORE
# timing consumers. Explicit native dataset map; caller owns scene/stage selection.
# The original clock-only SPEF and immutable identity must be prequalified together.
proc ::ot_clock_rc_restore_checked {maps baseline checker stem tag} {
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
  foreach name $unwired {
    # A historical clock alias can be only an unloaded port. It has no
    # instance timing endpoint or RC to restore. Keep it in the FULL identity
    # dump/graph check: acquiring a load, wire or changed port still fails.
    if {![dict exists $pins $name] || [llength [dict get $pins $name]]!=1 ||
        ![string match {PORT:?*} [lindex [dict get $pins $name] 0]]} {
      error "OT_MM_FROZEN_CLOCK_RC: original loaded clock has no routed wire: $name"
    }
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
}

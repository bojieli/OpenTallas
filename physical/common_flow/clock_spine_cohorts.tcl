# Explicit, default-off source/reset-consumer cohorts for clock_spine.tcl.
# Each dict is {name NAME source INST_PATTERN receivers {INST_PATTERN ...}}.
# A cohort changes physical leaf membership only, preserving clock and RTL edges.
proc ot_sp_cohort_match {pattern name} {
  expr {$pattern eq $name || [string match $pattern $name]}
}
proc ot_sp_cohort_bins {blk net0 u lmax} {
  set result [dict create]
  if {![info exists ::ot_sp_cohorts] || ![llength $::ot_sp_cohorts]} {return $result}
  set clock [dict create]
  foreach it [$net0 getITerms] {
    if {[$it getIoType] eq "INPUT"} {
      set name [[$it getInst] getName]
      if {[dict exists $clock $name]} {error "OT_SPINE cohort: multiple clock inputs for $name"}
      dict set clock $name $it
    }
  }
  set used [dict create]; set names [dict create]
  foreach item $::ot_sp_cohorts {
    foreach key {name source receivers} {
      if {![dict exists $item $key]} {error "OT_SPINE cohort: missing $key"}
    }
    set label [dict get $item name]
    if {$label eq "" || [dict exists $names $label]} {error "OT_SPINE cohort: empty/duplicate name $label"}
    dict set names $label 1
    set source {}; set receivers {}
    foreach inst [$blk getInsts] {
      if {[ot_sp_cohort_match [dict get $item source] [$inst getName]]} {lappend source $inst}
    }
    if {[llength $source] != 1} {error "OT_SPINE cohort $label: source must match exactly one instance"}
    set source [lindex $source 0]
    if {![llength [dict get $item receivers]]} {error "OT_SPINE cohort $label: empty receivers"}
    foreach pat [dict get $item receivers] {
      set found 0
      foreach inst [$blk getInsts] {
        if {[ot_sp_cohort_match $pat [$inst getName]]} {
          incr found
          if {[lsearch -exact $receivers $inst] >= 0} {error "OT_SPINE cohort $label: overlapping receiver patterns"}
          lappend receivers $inst
        }
      }
      if {!$found} {error "OT_SPINE cohort $label: missing receiver $pat"}
    }
    set members [linsert $receivers 0 $source]
    if {[llength $members] > $lmax} {error "OT_SPINE cohort $label: [llength $members] sinks exceed LEAF_N $lmax"}
    # Verify the declared receivers really are direct async-reset consumers of
    # a source output. Arbitrary data fanout cannot qualify as a reset cohort.
    set output_nets {}
    foreach it [$source getITerms] {
      if {[$it getIoType] eq "OUTPUT" && [$it getNet] ne "NULL"} {lappend output_nets [$it getNet]}
    }
    # No immediate asynchronous-reset consumer may silently remain outside the
    # atomic leaf. Also preserve the native dynamic-fanout bound on source Q.
    set declared {}
    foreach inst $receivers {lappend declared [$inst getName]}
    foreach net $output_nets {
      set loads 0
      foreach it [$net getITerms] {
        if {[$it getIoType] ne "INPUT"} continue
        incr loads
        if {[[$it getMTerm] getName] in {RESETN RESETB RESET_B RN RB CLR CLRN CDN RESET SETN} &&
            [lsearch -exact $declared [[$it getInst] getName]] < 0} {
          error "OT_SPINE cohort $label: undeclared immediate reset receiver [[$it getInst] getName]"
        }
      }
      if {$loads > 32} {error "OT_SPINE cohort $label: source output exceeds 32 dynamic loads"}
    }
    foreach inst $receivers {
      set connected 0
      foreach it [$inst getITerms] {
        if {[$it getIoType] eq "INPUT" &&
            [[$it getMTerm] getName] in {RESETN RESETB RESET_B RN RB CLR CLRN CDN RESET SETN} &&
            [lsearch -exact $output_nets [$it getNet]] >= 0} {set connected 1}
      }
      if {!$connected} {error "OT_SPINE cohort $label: [$inst getName] is not a direct async-reset consumer"}
    }
    set entries {}
    foreach inst $members {
      set name [$inst getName]
      if {[dict exists $used $name]} {error "OT_SPINE cohort $label: overlapping member $name"}
      if {![dict exists $clock $name]} {error "OT_SPINE cohort $label: missing/cross-root clock member $name"}
      if {[[$inst getMaster] isBlock]} {error "OT_SPINE cohort $label: hard macro member $name"}
      set it [dict get $clock $name]
      lassign [$it getAvgXY] ok x y
      if {!$ok} {error "OT_SPINE cohort $label: unplaced clock member $name"}
      foreach entry $entries {
        lassign $entry other ox oy
        if {abs($x-$ox)+abs($y-$oy) > 405*$u} {error "OT_SPINE cohort $label: pair exceeds 405um reach"}
      }
      dict set used $name 1
      lappend entries [list $it $x $y]
    }
    dict set result "C:$label" $entries
    puts "OT_SPINE cohort $label: [llength $entries] connected same-clock sinks, atomic leaf"
  }
  return $result
}

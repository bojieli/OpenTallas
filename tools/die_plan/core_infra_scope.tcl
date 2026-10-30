# Explicit one-root planned clock ownership. Included only by opt-in kits.
# Ordinary-root editors may run only on declared roots; their actual effects
# are checked on the rooted clock graphs, including pin bindings and geometry.
proc ot_ci_scope_cone {root {frontiers {}}} {
  set blk [ord::get_db_block]
  set bt [$blk findBTerm $root]
  if {$bt eq "NULL" || [$bt getIoType] ne "INPUT" || [$bt getNet] eq "NULL"} {
    error "OT_CORE_SCOPE_ROOT missing input clock root $root"
  }
  set todo [list [$bt getNet]]; set seen {}; set records {}; set insts {}
  while {[llength $todo]} {
    set net [lindex $todo end]; set todo [lrange $todo 0 end-1]
    set nm [$net getName]
    if {[dict exists $seen $nm]} continue
    dict set seen $nm 1
    set terms {}; set stop [expr {[lsearch -exact $frontiers $nm] >= 0}]
    foreach it [$net getITerms] {
      set inst [$it getInst]; set master [$inst getMaster]
      set pin [$it getMTerm]; set ip [$pin getName]
      if {!$stop || [$pin getIoType] eq "OUTPUT"} {
        lappend terms [list [$inst getName] [$master getName] $ip [$pin getIoType]]
      }
      if {$stop || [$pin getIoType] ne "INPUT"} continue
      set iname [$inst getName]
      set mn [$master getName]
      set propagates [expr {![$master isBlock] && ([regexp {^(BUF|INV|CK|HB)} $mn] ||
          ([string match ICG* $mn] && $ip eq "CLK"))}]
      if {![dict exists $insts $iname]} {
        dict set insts $iname 1
        set binds {}
        foreach jt [$inst getITerms] {
          # A terminal FF/macro contributes only the clock pin reached by
          # this root. Ordinary data hold repair is not a clock-graph edit.
          # Clock buffers/gates include every pin, including gate enables.
          if {!$propagates && $jt ne $it} continue
          set nn [$jt getNet]
          lappend binds [list [[$jt getMTerm] getName] [expr {$nn eq "NULL" ? "NULL" : [$nn getName]}]]
        }
        lappend records [list I $iname [$master getName] [$inst getLocation] [$inst getOrient] \
                         [$inst getPlacementStatus] [$inst isDoNotTouch] [lsort $binds]]
      }
      # Clock propagation cells only. Unknown inserted logic changes the rooted
      # graph immediately and is rejected by the before/after comparison.
      if {$propagates} {
        foreach out [$inst getITerms] {
          if {[[$out getMTerm] getIoType] eq "OUTPUT" && [$out getNet] ne "NULL"} {
            lappend todo [$out getNet]
          }
        }
      }
    }
    set ports {}; foreach b [$net getBTerms] {lappend ports [list [$b getName] [$b getIoType]]}
    lappend records [list N $nm [$net getSigType] [$net isDoNotTouch] [lsort $ports] [lsort $terms]]
  }
  return [dict create nets [lsort [dict keys $seen]] graph [lsort $records]]
}
proc ot_ci_scope_disjoint {} {
  set owners {}; set cones {}
  foreach root $::ot_ci_scope_roots {
    set cone [ot_ci_scope_cone $root]; dict set cones $root $cone
    foreach net [dict get $cone nets] {
      if {[dict exists $owners $net]} {
        error "OT_CORE_SCOPE_OVERLAP roots $root and [dict get $owners $net] share net $net"
      }
      dict set owners $net $root
    }
  }
  return $cones
}
proc ot_ci_scope_snapshot {roots {frontiers {}}} {
  set out {}
  foreach root $roots {dict set out $root [dict get [ot_ci_scope_cone $root $frontiers] graph]}
  return $out
}
proc ot_ci_scope_hook {path} {
  # Protect the complete generator hook too: direct Tcl edits outside the
  # known sourced editor files must not bypass the selected-root guard.
  set allowed {}
  dict for {script roots} $::ot_ci_scope_editors {set allowed [concat $allowed $roots]}
  set protected {};foreach root $::ot_ci_scope_roots {
    if {[lsearch -exact $allowed $root] < 0} {lappend protected $root}
  }
  ot_ci_scope_disjoint
  set before [ot_ci_scope_snapshot $protected]
  try {
    set result [uplevel 1 [list ::source $path]]
  } finally {
    ot_ci_scope_disjoint
    if {[ot_ci_scope_snapshot $protected] ne $before} {
      error "OT_CORE_SCOPE_HOOK_CHANGED $path changed a root outside its declared ordinary editor roots ($protected)"
    }
  }
  return $result
}
if {![llength [info commands ::ot_ci_scope_source]]} {
  rename ::source ::ot_ci_scope_source
  proc ::source {args} {
    set name [file tail [lindex $args end]]
    if {![info exists ::ot_ci_scope_known] || [lsearch -exact $::ot_ci_scope_known $name] < 0} {
      return [uplevel 1 [list ::ot_ci_scope_source {*}$args]]
    }
    set allowed {}; if {[dict exists $::ot_ci_scope_editors $name]} {set allowed [dict get $::ot_ci_scope_editors $name]}
    set protected {}; foreach root $::ot_ci_scope_roots {
      if {[lsearch -exact $allowed $root] < 0} {lappend protected $root}
    }
    ot_ci_scope_disjoint
    set before [ot_ci_scope_snapshot $protected]
    try {
      set result [uplevel 1 [list ::ot_ci_scope_source {*}$args]]
    } finally {
      ot_ci_scope_disjoint
      if {[ot_ci_scope_snapshot $protected] ne $before} {
        error "OT_CORE_SCOPE_EDITOR_CHANGED $name changed a protected root ($protected); declared roots are $allowed"
      }
    }
    puts "OT_CORE_SCOPE_EDITOR $name preserved roots {$protected}; ordinary roots {$allowed} checked"
    return $result
  }
}

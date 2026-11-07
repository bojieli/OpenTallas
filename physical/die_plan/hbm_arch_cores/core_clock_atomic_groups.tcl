# Optional atomic native-clock branches for short register chains. This planner is
# pure Tcl; core_density_taps owns real BUFx24 branches and local CTS as before.
# Points are exact OpenDB instance names -> {x y clock_iterm}. Groups are a Tcl
# list of {group_name {exact_instance_name ...}} records, read as data, never eval.
proc dt_atomic_plan {points groups max_sinks max_radius} {
  if {![string is integer -strict $max_sinks] || $max_sinks < 2 || $max_sinks > 64} {error "ATOMIC_CLOCK sink cap must be 2..64"}
  if {![string is double -strict $max_radius] || $max_radius <= 0} {error "ATOMIC_CLOCK radius must be positive"}
  if {![llength $groups]} {error "ATOMIC_CLOCK empty manifest"}
  set used {}; set ids {}; set sets {}; set med {}
  foreach record $groups {
    if {[llength $record] != 2} {error "ATOMIC_CLOCK malformed group"}
    lassign $record id members
    if {$id eq "" || [dict exists $ids $id]} {error "ATOMIC_CLOCK duplicate/empty group $id"}
    dict set ids $id 1
    if {[llength $members] < 2 || [llength $members] > $max_sinks} {error "ATOMIC_CLOCK group $id exceeds sink budget or is a singleton"}
    set S {}; set cx 0.0; set cy 0.0
    foreach name $members {
      if {[dict exists $used $name]} {error "ATOMIC_CLOCK overlapping member $name"}
      if {![dict exists $points $name]} {error "ATOMIC_CLOCK missing native-root clock sink $name"}
      dict set used $name $id
      set p [dict get $points $name]; lappend S $p
      set cx [expr {$cx + [lindex $p 0]}]; set cy [expr {$cy + [lindex $p 1]}]
    }
    set cx [expr {$cx / [llength $S]}]; set cy [expr {$cy / [llength $S]}]
    set best {}; set bd Inf
    foreach p $S {
      set d [expr {abs([lindex $p 0]-$cx)+abs([lindex $p 1]-$cy)}]
      if {$d < $bd} {set bd $d; set best $p}
    }
    lassign $best x y
    foreach p $S {
      if {abs([lindex $p 0]-$x)+abs([lindex $p 1]-$y) > $max_radius} {error "ATOMIC_CLOCK group $id outside reviewed radius"}
    }
    lappend sets $S; lappend med [list $x $y]
  }
  set rest {}
  dict for {name point} $points {if {![dict exists $used $name]} {lappend rest $point}}
  return [dict create sets $sets med $med pinned $used rest $rest]
}

# Non-inverting ancestry receipt: a grouped branch must still reach the exact
# declared native BTerm through buffers only, with no gating or root crossing.
proc dt_atomic_root {net native} {
  set seen {}
  for {set depth 0} {$depth < 128} {incr depth} {
    if {[dict exists $seen $net]} {error "ATOMIC_CLOCK clock ancestry cycle"}
    dict set seen $net 1
    set ports {}
    foreach port [$net getBTerms] {if {[$port getIoType] eq "INPUT"} {lappend ports [$port getName]}}
    if {[llength $ports]} {
      if {[llength $ports] != 1 || [lindex $ports 0] ne $native} {error "ATOMIC_CLOCK wrong native clock root"}
      return $native
    }
    set drivers {}
    foreach pin [$net getITerms] {if {[$pin isOutputSignal]} {lappend drivers [$pin getInst]}}
    if {[llength $drivers] != 1} {error "ATOMIC_CLOCK missing/multiple clock ancestry drivers"}
    set driver [lindex $drivers 0]
    if {![string match BUF* [[$driver getMaster] getName]]} {error "ATOMIC_CLOCK inverted/gated clock ancestry"}
    set inputs {}
    foreach pin [$driver getITerms] {if {[$pin isInputSignal]} {lappend inputs [$pin getNet]}}
    if {[llength $inputs] != 1 || [lindex $inputs 0] eq "NULL"} {error "ATOMIC_CLOCK malformed clock buffer"}
    set net [lindex $inputs 0]
  }
  error "ATOMIC_CLOCK clock ancestry exceeds depth bound"
}

# Called after CTS on the real database. A common density tap alone is not
# sufficient: CTS must have kept every chain on one actual local leaf.
proc dt_atomic_check {block groups max_sinks max_radius native} {
  set checked 0
  foreach record $groups {
    lassign $record id members
    set common ""; set points {}
    foreach name $members {
      set inst [$block findInst $name]
      if {$inst eq "NULL" || $inst eq ""} {error "ATOMIC_CLOCK missing post-CTS register $name"}
      set pin [$inst findITerm CLK]
      if {$pin eq "NULL" || $pin eq ""} {set pin [$inst findITerm CK]}
      if {$pin eq "NULL" || $pin eq ""} {error "ATOMIC_CLOCK no clock pin on $name"}
      set net [$pin getNet]
      if {$net eq "NULL" || $net eq ""} {error "ATOMIC_CLOCK disconnected register $name"}
      if {$common eq ""} {set common $net} elseif {$common ne $net} {error "ATOMIC_CLOCK group $id split across actual CTS leaves"}
      lappend points [$inst getLocation]
    }
    set load 0; set driver ""
    foreach pin [$common getITerms] {
      if {[[ $pin getMTerm] getIoType] eq "INPUT" && [[ $pin getMTerm] getSigType] ni {POWER GROUND}} {incr load}
      if {[$pin isOutputSignal]} {
        if {$driver ne ""} {error "ATOMIC_CLOCK multiple leaf drivers $id"}
        set driver [$pin getInst]
      }
    }
    if {$driver eq "" || ![string match BUF* [[$driver getMaster] getName]] || $load > $max_sinks} {error "ATOMIC_CLOCK invalid driver/sink budget $id load=$load"}
    dt_atomic_root $common $native
    lassign [$driver getLocation] x y
    foreach p $points {
      if {abs([lindex $p 0]-$x)+abs([lindex $p 1]-$y) > $max_radius} {error "ATOMIC_CLOCK actual leaf wire exceeds reviewed radius $id"}
    }
    incr checked
  }
  puts "OT_DTAP_ATOMIC_CTS checked_groups $checked common_leaf PASS"
  return $checked
}

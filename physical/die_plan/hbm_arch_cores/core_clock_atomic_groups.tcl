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

# DIE-HEAD-84/85 11-07 (HEAD TX vE CTS, class fix): TritonCTS builds an H-tree under every atomic density-tap net, and a
# 9-10 sink net gets a Level-1 split (two sibling leaf buffers + a dummy load), so every group lands on two leaves by
# construction and dt_atomic_check can never pass ("split across actual CTS leaves", TX vE attempt 1).  Collapse: for a
# group whose members sit on more than one leaf net, re-hang every member on the leaf net holding most of them; both
# leaves must be BUF-driven siblings of one parent net.  An emptied sibling leaf buffer, its CTS dummy loads (no
# connected output) and its net are deleted.  Fail-closed: a sibling that still drives a non-dummy load is an error,
# never deleted.  dt_atomic_check runs afterwards and stays the receipt (sink cap, radius, native root).
proc dt_atomic_ck {inst} {
  set p [$inst findITerm CLK]
  if {$p eq "NULL" || $p eq ""} {set p [$inst findITerm CK]}
  if {$p eq "NULL" || $p eq ""} {error "ATOMIC_COLLAPSE no clock pin on [$inst getName]"}
  return $p
}
proc dt_atomic_driver {net} {
  foreach t [$net getITerms] {if {[$t isOutputSignal]} {return [$t getInst]}}
  return ""
}
proc dt_atomic_buf_parent {inst what} {
  if {$inst eq "" || ![string match BUF* [[$inst getMaster] getName]]} {error "ATOMIC_COLLAPSE $what not BUF-driven"}
  set ins {}
  foreach t [$inst getITerms] {if {[$t isInputSignal]} {lappend ins [$t getNet]}}
  if {[llength $ins] != 1 || [lindex $ins 0] eq "NULL" || [lindex $ins 0] eq ""} {error "ATOMIC_COLLAPSE $what malformed buffer"}
  return [[lindex $ins 0] getName]
}
proc dt_atomic_is_dummy {inst} {
  if {[string match *DFF* [[$inst getMaster] getName]]} {return 0}
  foreach t [$inst getITerms] {
    if {[$t isOutputSignal]} {set n [$t getNet]; if {$n ne "NULL" && $n ne ""} {return 0}}
  }
  return 1
}
proc dt_atomic_collapse {block groups} {
  set split 0; set moved 0; set del_buf 0; set del_dummy 0
  foreach record $groups {
    lassign $record id members
    set cnt [dict create]; set order {}; set pins {}
    foreach name $members {
      set inst [$block findInst $name]
      if {$inst eq "NULL" || $inst eq ""} {error "ATOMIC_COLLAPSE missing post-CTS register $name"}
      set p [dt_atomic_ck $inst]; set n [$p getNet]
      if {$n eq "NULL" || $n eq ""} {error "ATOMIC_COLLAPSE disconnected register $name"}
      set nn [$n getName]
      if {![dict exists $cnt $nn]} {lappend order $nn}
      dict incr cnt $nn; lappend pins [list $p $nn]
    }
    if {[dict size $cnt] < 2} continue
    incr split
    set keep ""; set best -1
    foreach nn $order {if {[dict get $cnt $nn] > $best} {set best [dict get $cnt $nn]; set keep $nn}}
    set knet [$block findNet $keep]
    set kpar [dt_atomic_buf_parent [dt_atomic_driver $knet] "$id keep leaf $keep"]
    set others {}
    foreach pn $pins {
      lassign $pn p nn
      if {$nn eq $keep} continue
      if {![dict exists $others $nn]} {
        set opar [dt_atomic_buf_parent [dt_atomic_driver [$block findNet $nn]] "$id sibling leaf $nn"]
        if {$opar ne $kpar} {error "ATOMIC_COLLAPSE $id leaves $nn and $keep are not siblings ($opar vs $kpar)"}
        dict set others $nn 1
      }
      $p disconnect; $p connect $knet; incr moved
    }
    foreach on [dict keys $others] {
      set n [$block findNet $on]; set odrv [dt_atomic_driver $n]
      set loads {}
      foreach t [$n getITerms] {if {![$t isOutputSignal]} {lappend loads [$t getInst]}}
      foreach li $loads {if {![dt_atomic_is_dummy $li]} {error "ATOMIC_COLLAPSE $id sibling $on still drives [$li getName]: not deleted"}}
      foreach li $loads {odb::dbInst_destroy $li; incr del_dummy}
      odb::dbInst_destroy $odrv; incr del_buf
      odb::dbNet_destroy $n
    }
  }
  puts "OT_ATOMIC_COLLAPSE groups_split $split members_moved $moved leaf_bufs_deleted $del_buf dummies_deleted $del_dummy"
  return [list $split $moved $del_buf $del_dummy]
}

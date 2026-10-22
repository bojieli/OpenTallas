# forwarded_soft_tap.tcl (STW-S81c-DIE3-FRAME 2026-10-22): a post-CTS clock delay tap in front of the SOFT sinks of a
# forwarded clock input (ref_tile spec "forwarded_soft_tap"; needs "forwarded_soft_clocks").
#
# Why (S81 frame flat gates h9 vg / h9 vgc / h10 vg @56c0699a4, 4_1_cts): the forwarded xk[k] drives two hard children
# (u_cf/xk[k] R 100.9..119.6 ps, the u_xo<k> relay ck R 106.6 ps) and the two flops of the xk-domain reset synchroniser
# u_xrl<k>.  GPL put the synchroniser beside the relay (soft wire 272.8 vs relay pin 274.9 ps), but a bare flop has no
# internal insertion, so the child-flop spread = hard (arrival + R) - soft arrival = 122.6..126.3 ps > 80 (owner clock rule,
# TT and FF).  Placement cannot remove a missing ~110 ps; the soft group needs the same latency as the children's flops.
#
# What: per declared forwarded port bit, ONE chain of clock buffers is inserted between the port's net and the declared
# soft clock pins (all of them move together, so they stay one group), placed at the soft centroid, grown greedily with a
# step ladder (OT_FST_BUFS, default BUFx4 -> BUFx2 -> HB1xp67, the child_centre_tap.tcl ladder): a step is kept only when it
# lowers the WORST child-flop spread over every scene with propagated arrivals (setup scene + BC) by >= OT_FST_GAIN
# (0.5 ps), else it is removed and the next smaller master is tried.  Spread per scene = max(hard a + R_max, soft) -
# min(hard a + R_min, soft), R from ::ot_ce_refs (the children's insertion.json boundary ranges, the same numbers the
# gate's OT_LANDED FORWARDED_CLOCK check uses).  Nothing else changes: no SDC latency, no netlist function, no hard pin,
# no port; the chain is dont_touch and its nets are CLOCK; the gate still judges the real arrivals.  Fails closed when a
# declared cell, its clock pin, a hard sink, a reference range or an arrival is missing.
if {![llength [info procs ot_pg_standard_bind]]} {
  set ot_fst_pg_helper [file join [file dirname [info script]] native_pg_binding.tcl]
  if {[info exists ::env(OT_PG_HELPER)]} {set ot_fst_pg_helper $::env(OT_PG_HELPER)} elseif {![file exists $ot_fst_pg_helper]} {set ot_fst_pg_helper /src/physical/common_flow/native_pg_binding.tcl}
  source $ot_fst_pg_helper
}
proc ot_fst_arr {pin clock scene} {
  # latest propagated arrival of ONE clock at a pin in one scene (rising pin transition, else falling)
  sta::worst_slack_cmd max
  set best ""
  foreach transition {rise fall} marker {^ v} {
    foreach vertex [$pin vertices] {
      if {$vertex eq "NULL"} continue
      set paths [$vertex path_iterator $transition max]
      while {[$paths has_next]} {
        set path [$paths next]
        set tag [$path tag]
        if {[lindex $tag 1] ne $scene || [lindex $tag 2] ne "${marker}max" || [lindex $tag 3] ne $clock
            || [string first "(clock prop)" $tag] < 0} continue
        set a [sta::time_sta_ui [$path arrival]]
        if {[string is double -strict $a] && ![regexp -nocase {inf|nan} $a] && ($best eq "" || $a > $best)} { set best $a }
      }
      $paths finish
    }
    if {$best ne ""} break
  }
  return $best
}
proc ot_fst_root_port {pin} {
  # = clock_entry ot_ce_net_root_port: the port a pin's net reaches through single-input non-child cells, else ""
  set net [get_nets -quiet -of_objects $pin]
  for {set i 0} {$i < 256 && [llength $net] == 1} {incr i} {
    set ports [get_ports -quiet -of_objects $net]
    if {[llength $ports] == 1} { return [get_full_name [lindex $ports 0]] }
    if {[llength $ports]} { return "" }
    set drv [get_pins -quiet -of_objects $net -filter "direction == output"]
    if {[llength $drv] != 1} { return "" }
    set cell [get_cells -quiet -of_objects $drv]
    if {[llength $cell] != 1 || [dict exists $::ot_ce_counts [get_property $cell ref_name]]} { return "" }
    set ins [get_pins -quiet -of_objects $cell -filter "direction == input"]
    if {[llength $ins] != 1} { return "" }
    set net [get_nets -quiet -of_objects $ins]
  }
  return ""
}
proc ot_fst_scenes {pin clock} {
  sta::worst_slack_cmd max
  set out {}
  foreach transition {rise fall} {
    foreach vertex [$pin vertices] {
      if {$vertex eq "NULL"} continue
      set paths [$vertex path_iterator $transition max]
      while {[$paths has_next]} {
        set tag [[$paths next] tag]
        if {[lindex $tag 3] ne $clock || [string first "(clock prop)" $tag] < 0} continue
        set s [lindex $tag 1]
        if {[lsearch -exact $out $s] < 0} { lappend out $s }
      }
      $paths finish
    }
  }
  return $out
}
proc ot_fst_corner {cell scene} {
  # as child_centre_tap ot_cct_corner: BC/FF named = ff; TT/TC = tt; a WC/SS setup scene is TT when the hard child's
  # loaded Liberty set has a _tt and no _ss library (OT_ORFS_CORNER_OVERRIDE=TC gate sessions)
  set sc [string tolower $scene]
  if {[regexp {^(bc|ff|fast|min)} $sc]} { return ff }
  if {[regexp {^(tt|tc|typ)} $sc]} { return tt }
  set have {}
  foreach lc [get_lib_cells -quiet -of_objects $cell] {
    if {[regexp -nocase {_(tt|ff|ss)(?:[/_.]|$)} [get_full_name $lc] -> c]} { dict set have [string tolower $c] 1 }
  }
  if {[regexp {^(wc|ss|slow|max)} $sc]} {
    if {[dict exists $have ss]} { return ss }
    if {[dict exists $have tt]} { return tt }
    error "OT_FST: setup scene $scene has neither a _tt nor an _ss library"
  }
  set ks [dict keys $have]
  if {[llength $ks] == 1} { return [lindex $ks 0] }
  if {[dict exists $have tt] && ![dict exists $have ss]} { return tt }
  error "OT_FST: no unique corner for scene $scene (libraries: $ks)"
}
proc ot_fst_measure {r} {
  # per scene: {spread hard_lo hard_hi soft_lo soft_hi}; the record keeps the worst spread in w
  set clock [dict get $r clock]
  set w ""
  set per {}
  foreach s [dict get $r scenes] {
    set lo ""; set hi ""
    foreach h [dict get $r hard] {
      lassign $h pin cell key
      set a [ot_fst_arr $pin $clock $s]
      if {$a eq ""} { error "OT_FST: [get_full_name $pin] lost its $clock arrival in scene $s" }
      set corner [ot_fst_corner $cell $s]
      if {![dict exists $::ot_ce_refs $key $corner]} { error "OT_FST: no $corner reference range for $key" }
      lassign [dict get $::ot_ce_refs $key $corner] clo cmean chi
      set l [expr {$a + $clo}]; set u [expr {$a + $chi}]
      if {$lo eq "" || $l < $lo} { set lo $l }
      if {$hi eq "" || $u > $hi} { set hi $u }
    }
    set slo ""; set shi ""
    foreach sp [dict get $r softpins] {
      set a [ot_fst_arr $sp $clock $s]
      if {$a eq ""} { error "OT_FST: [get_full_name $sp] lost its $clock arrival in scene $s" }
      if {$slo eq "" || $a < $slo} { set slo $a }
      if {$shi eq "" || $a > $shi} { set shi $a }
    }
    set sp [expr {max($hi, $shi) - min($lo, $slo)}]
    dict set per $s [list $sp $lo $hi $slo $shi]
    if {$w eq "" || $sp > $w} { set w $sp }
  }
  dict set r per $per
  dict set r wnow $w
  return $r
}
proc ot_fst_insert {block bm ain aout at r} {
  dict with r {
    if {$at eq "port"} { set x $px; set y $py }
    set old [[lindex $softits 0] getNet]
    set b [odb::dbInst_create $block $bm "ot_fst_${tag}_$n"]
    if {$b eq "NULL"} { error "OT_FST: cannot create tap buffer" }
    $b setLocation [expr {int($x)}] [expr {int($y)}]
    $b setPlacementStatus PLACED
    set nn [odb::dbNet_create $block "ot_fst_n_${tag}_$n"]
    $nn setSigType CLOCK
    set dt [$old isDoNotTouch]
    if {$dt} { $old setDoNotTouch 0 }
    foreach it $softits { $it disconnect }
    [$b findITerm $ain] connect $old
    [$b findITerm $aout] connect $nn
    foreach it $softits { $it connect $nn }
    if {$dt} { $old setDoNotTouch 1; $nn setDoNotTouch 1 }
    set last [list $b $nn $old]
    lappend made $b $nn
    incr n
  }
  return $r
}
proc ot_fst_remove_last {r} {
  dict with r {
    lassign $last b nn old
    set made [lrange $made 0 end-2]
    set dt [$old isDoNotTouch]
    if {$dt} { $old setDoNotTouch 0 }
    $nn setDoNotTouch 0
    foreach it $softits { $it disconnect }
    odb::dbInst_destroy $b
    odb::dbNet_destroy $nn
    foreach it $softits { $it connect $old }
    if {$dt} { $old setDoNotTouch 1 }
    incr n -1
    set last {}
  }
  return $r
}
proc ot_fst_propagate_modes {} {
  set original [sta::cmd_mode_name]
  set changed {}
  foreach mode [get_modes *] {
    set name [get_property $mode name]
    set_mode $name
    set ideal {}
    foreach c [all_clocks] { if {![get_property $c is_propagated]} { lappend ideal $c } }
    if {[llength $ideal]} { set_propagated_clock $ideal; dict set changed $name $ideal }
  }
  set_mode $original
  return $changed
}
proc ot_fst_restore_modes {changed} {
  set original [sta::cmd_mode_name]
  dict for {mode clocks} $changed { set_mode $mode; unset_propagated_clock $clocks }
  set_mode $original
}
proc ot_fst_tap {} {
  if {![info exists ::ot_ce_fwd_soft] || ![dict size $::ot_ce_fwd_soft]} { error "OT_FST: no forwarded_soft_clocks (::ot_ce_fwd_soft)" }
  if {![info exists ::ot_ce_refs] || ![info exists ::ot_ce_counts]} { error "OT_FST: no hard-child reference ranges (::ot_ce_refs)" }
  set block [ord::get_db_block]
  set lim [expr {[info exists ::env(OT_FST_MAX)] ? $::env(OT_FST_MAX) : 16}]
  set gain [expr {[info exists ::env(OT_FST_GAIN)] ? $::env(OT_FST_GAIN) : 0.5}]
  set names [expr {[info exists ::env(OT_FST_BUFS)] ? $::env(OT_FST_BUFS) : "BUFx4_ASAP7_75t_R BUFx2_ASAP7_75t_R HB1xp67_ASAP7_75t_R"}]
  set ladder {}
  foreach nm $names {
    set bm [[ord::get_db] findMaster $nm]
    if {$bm eq "NULL"} { error "OT_FST: buffer master $nm missing" }
    set ain ""; set aout ""
    foreach mt [$bm getMTerms] {
      if {[$mt getSigType] in {POWER GROUND}} continue
      if {[$mt getIoType] eq "INPUT"} { set ain [$mt getName] } elseif {[$mt getIoType] eq "OUTPUT"} { set aout [$mt getName] }
    }
    foreach at {soft port} { lappend ladder [list $nm $bm $ain $aout $at] }
  }
  # declared soft cells by exact (unescaped) name
  set want {}
  dict for {port info} $::ot_ce_fwd_soft { foreach c [dict get $info cells] { dict set want $c $port } }
  set found {}
  foreach i [$block getInsts] {
    set nm [string map {\\ {}} [$i getName]]
    if {[dict exists $want $nm]} { dict set found $nm $i }
  }
  # hard sinks per forwarded port bit: every bound hard-child pin with a reference range whose net walks back (through
  # single-input soft buffers) to that port, exactly as ot_ce_forwarded_visit selects them for the gate's check
  set hardby {}
  foreach i [$block getInsts] {
    set m [$i getMaster]
    if {![$m isBlock] || ![dict exists $::ot_ce_counts [$m getName]]} continue
    foreach it [$i getITerms] {
      if {[$it getNet] eq "NULL"} continue
      set key "[$m getName]/[[$it getMTerm] getName]"
      if {![dict exists $::ot_ce_refs $key]} continue
      set pin [get_pins -quiet "[$i getName]/[[$it getMTerm] getName]"]
      if {[llength $pin] != 1} continue
      set port [ot_fst_root_port $pin]
      if {$port eq "" || ![dict exists $::ot_ce_fwd_soft $port]} continue
      dict lappend hardby $port [list $pin [get_cells -of_objects $pin] $key]
    }
  }
  set changes [ot_fst_propagate_modes]
  estimate_parasitics -placement
  # Repeat the forwarded port nets first (OT_FST_REPAIR, default 1).  TritonCTS -repair_clock_nets repairs EVERY clock net,
  # so a TritonCTS frame got repeaters on xk[k]; a spine frame never runs TritonCTS, and the vgy spine test (10-22) left the
  # xk[k] nets unrepeated: 300-660 ps of RC with a slow slew at the sinks, where one tap buffer added 50-450 ps.  Same
  # resizer net repair as the clock_entries selected-root repair; a no-op on an already repeated net.
  if {![info exists ::env(OT_FST_REPAIR)] || $::env(OT_FST_REPAIR) ne "0"} {
    est::check_parasitics
    set mw [rsz::check_max_wire_length 0 true]
    set nrep 0
    dict for {port info} $::ot_ce_fwd_soft {
      set bt [$block findBTerm $port]
      if {$bt eq "NULL" || $bt eq ""} { error "OT_FST: no port $port in the block" }
      set pn [$bt getNet]
      set dt [$pn isDoNotTouch]
      if {$dt} { $pn setDoNotTouch 0 }
      rsz::repair_net_cmd [sta::db_net_to_sta $pn] $mw 0 0
      if {$dt} { $pn setDoNotTouch 1 }
      incr nrep
    }
    estimate_parasitics -placement
    puts "OT_FST repaired $nrep forwarded port nets (max wire [expr {$mw}] dbu)"
  }
  set recs {}
  set k 0
  dict for {port info} $::ot_ce_fwd_soft {
    set clock [dict get $info clock]
    set softits {}; set softpins {}; set sx 0.0; set sy 0.0
    foreach c [dict get $info cells] {
      if {![dict exists $found $c]} { error "OT_FST: declared soft cell $c ($port) not in the design" }
      set inst [dict get $found $c]
      set cit {}
      foreach it [$inst getITerms] { if {[[$it getMTerm] getSigType] eq "CLOCK" && [$it getNet] ne "NULL"} { lappend cit $it } }
      if {[llength $cit] != 1} { error "OT_FST: $c has [llength $cit] connected clock pins (one expected)" }
      set it [lindex $cit 0]
      lappend softits $it
      set p [get_pins -quiet "[$inst getName]/[[$it getMTerm] getName]"]
      if {[llength $p] != 1} { error "OT_FST: $c clock pin not unique in STA" }
      lappend softpins $p
      set l [$inst getLocation]; set sx [expr {$sx + [lindex $l 0]}]; set sy [expr {$sy + [lindex $l 1]}]
    }
    set nets {}
    foreach it $softits { set nn [[$it getNet] getName]; if {$nn ni $nets} { lappend nets $nn } }
    if {[llength $nets] != 1} { error "OT_FST: soft clock pins of $port sit on [llength $nets] nets ($nets): one group expected" }
    # hard sinks of the same port bit: bound child clock pins with a reference range (as ot_ce_forwarded_visit)
    set hard [expr {[dict exists $hardby $port] ? [dict get $hardby $port] : {}}]
    if {![llength $hard]} { error "OT_FST: forwarded $port reaches no hard child clock pin with a reference range" }
    set scenes [ot_fst_scenes [lindex $softpins 0] $clock]
    if {![llength $scenes]} { error "OT_FST: $port soft pins have no propagated $clock arrival" }
    # the port pin (clamped into the core): a tap there sees the port's sharp slew, not the slow slew at the end of the
    # forwarded wire (vgy spine test 10-22: one BUFx4 at the soft centroid added ~117 ps at the end of a 680-ps wire)
    set bt [$block findBTerm $port]
    if {$bt eq "NULL" || $bt eq ""} { error "OT_FST: no port $port in the block" }
    set bb [$bt getBBox]
    set core [$block getCoreArea]
    set px [expr {min(max(([$bb xMin] + [$bb xMax]) / 2, [$core xMin]), [$core xMax] - 2000)}]
    set py [expr {min(max(([$bb yMin] + [$bb yMax]) / 2, [$core yMin]), [$core yMax] - 2000)}]
    set n [llength $softits]
    set r [dict create px $px py $py port $port clock $clock tag [regsub -all {[^A-Za-z0-9]} $port _] softits $softits softpins $softpins \
      hard $hard scenes $scenes x [expr {$sx / $n}] y [expr {$sy / $n}] n 0 last {} made {} rung 0 active 1 steps {}]
    set r [ot_fst_measure $r]
    dict set r w [dict get $r wnow]; dict set r w0 [dict get $r wnow]
    dict for {s v} [dict get $r per] {
      puts [format "OT_FST %s %s %s hard %.1f..%.1f soft %.1f..%.1f spread %.1f" $port $s $clock {*}[lrange $v 1 end] [lindex $v 0]]
    }
    lappend recs $r
    incr k
  }
  set nr [llength $recs]
  set round 0
  while 1 {
    set any 0
    for {set i 0} {$i < $nr} {incr i} {
      set r [lindex $recs $i]
      if {![dict get $r active]} continue
      if {[dict get $r n] >= $lim} { dict set r active 0; lset recs $i $r; continue }
      set any 1
      lassign [lindex $ladder [dict get $r rung]] nm bm ain aout at
      set sx0 [dict get $r x]; set sy0 [dict get $r y]
      set r [ot_fst_insert $block $bm $ain $aout $at $r]
      dict set r x $sx0; dict set r y $sy0
      lset recs $i $r
    }
    if {!$any} break
    estimate_parasitics -placement
    incr round
    set redo 0
    for {set i 0} {$i < $nr} {incr i} {
      set r [lindex $recs $i]
      if {![dict get $r active] || ![llength [dict get $r last]]} continue
      set r [ot_fst_measure $r]
      set w [dict get $r wnow]
      set nm [join [lrange [lindex $ladder [dict get $r rung]] 0 0] ""]@[lindex [lindex $ladder [dict get $r rung]] 4]
      if {$w <= [dict get $r w] - $gain} {
        dict set r w $w
        dict lappend r steps $nm
        puts [format "OT_FST %s keep %s n=%d worst spread %.1f" [dict get $r port] $nm [dict get $r n] $w]
      } else {
        puts [format "OT_FST %s drop %s (worst spread %.1f vs %.1f)" [dict get $r port] $nm $w [dict get $r w]]
        set r [ot_fst_remove_last $r]
        dict set r rung [expr {[dict get $r rung] + 1}]
        if {[dict get $r rung] >= [llength $ladder]} { dict set r active 0 }
        set redo 1
      }
      dict set r last {}
      lset recs $i $r
    }
    if {$redo} { estimate_parasitics -placement }
  }
  set tapped 0
  for {set i 0} {$i < $nr} {incr i} {
    set r [ot_fst_measure [lindex $recs $i]]
    lset recs $i $r
    dict with r {
      if {[llength $made]} {
        if {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"} {
          set pg_instances {}
          foreach o $made {if {[$o getObjectType] eq "dbInst"} {lappend pg_instances $o}}
          set pg_mapping [ot_pg_prepare_targets [ord::get_db_block] $pg_instances]
          foreach o $pg_instances {ot_pg_bind_before_protect $pg_mapping $o}
        } elseif {[llength [info procs ot_pg_standard_bind]]} {
          ot_pg_standard_bind forwarded_soft_tap
        }
        foreach o $made { $o setDoNotTouch 1 }
        incr tapped
      }
      set txt {}
      dict for {s v} $per { lappend txt [format "%s hard %.1f..%.1f soft %.1f..%.1f spread %.1f" $s {*}[lrange $v 1 end] [lindex $v 0]] }
      puts [format "OT_FST DONE %s buffers=%d steps={%s} worst %.1f -> %.1f | %s" $port $n $steps $w0 $wnow [join $txt " | "]]
    }
  }
  if {$tapped} { detailed_placement }
  estimate_parasitics -placement
  ot_fst_restore_modes $changes
  puts "OT_FST tapped $tapped of $nr forwarded soft groups ($round parasitics rounds, minimax over scenes)"
}
if {[info procs clock_tree_synthesis] ne "" && [info procs ot_fst_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_fst_cts_orig
  proc clock_tree_synthesis {args} {
    ot_fst_cts_orig {*}$args
    ot_fst_tap
  }
}

# Opt-in PRE_CTS install of a plan core tree (core_tree.install_stage = "pre_cts", DIE-QC-36 A0).
# Sourced after core_infra_impl.tcl by master_core_infra_late.tcl, itself sourced from the kit PRE_CTS hook before
# core_infra_cts.tcl. The design is already placed and legal: no re-place. Planned tree BUFs are created at their plan
# xy (row/site quantised), then ONE incremental detailed_placement legalizes only them (every other instance is held
# FIRM for that call and its status restored). Existing RTL clock gates keep their placed xy; the plan xy is only
# reported. No timing input, no search, no clock trim.
set ::ot_ci_late_cells {}
proc ot_ci_late_cell {name master x y rect} {
  set m [[ord::get_db] findMaster $master]
  if {$m eq "NULL"} {error "OT_CORE_INFRA_MISSING_MASTER $master"}
  set i [$::ot_ci_b findInst $name]
  if {$i eq "NULL"} {set i [odb::dbInst_create $::ot_ci_b $m $name]} elseif {[$i getMaster] ne $m} {
    error "OT_CORE_INFRA_STALE_MASTER $name"
  }
  foreach pin {A Y} {if {[$i findITerm $pin] eq "NULL"} {error "OT_CORE_INFRA_BUFFER_PIN $name/$pin"}}
  set w [$m getWidth]; set h [$m getHeight]
  set row ""; set best 1e99
  foreach r [$::ot_ci_b getRows] {
    lassign [$r getOrigin] rx ry
    set d [expr {abs($ry + $h / 2.0 - $y * $::ot_ci_u)}]
    if {$d < $best} {set best $d; set row $r}
  }
  if {$row eq ""} {error "OT_CORE_INFRA_NO_ROWS $name"}
  lassign [$row getOrigin] rx ry
  set sw [[$row getSite] getWidth]
  set xx [expr {$rx + int(round(($x * $::ot_ci_u - $w / 2.0 - $rx) / $sw)) * $sw}]
  $i setOrient [$row getOrient]; $i setLocation $xx $ry; $i setPlacementStatus PLACED
  lappend ::ot_ci_cells $i
  lappend ::ot_ci_late_cells [list $i $x $y $rect]
}
proc ot_ci_late_gate {inst master parent clk_pin out_pin x y rect} {
  set i [$::ot_ci_b findInst $inst]
  if {$i eq "NULL"} {error "OT_CORE_INFRA_GATE_INSTANCE $inst"}
  if {[[$i getMaster] getName] ne $master} {error "OT_CORE_INFRA_GATE_MASTER $inst [[$i getMaster] getName] != $master"}
  if {![$i isPlaced]} {error "OT_CORE_INFRA_LATE_GATE_UNPLACED $inst"}
  set ck [$i findITerm $clk_pin]; set go [$i findITerm $out_pin]
  if {$ck eq "NULL" || $go eq "NULL"} {error "OT_CORE_INFRA_GATE_PIN $inst"}
  set target [dict get $::ot_ci_tree_out $parent]
  if {[$ck getNet] ne $target} {
    if {[lsearch -exact $::ot_ci_tree_expected $ck] < 0} {error "OT_CORE_INFRA_GATE_NOT_ON_CORE_CLOCK $inst"}
    set protected [$i isDoNotTouch]
    if {$protected} {$i setDoNotTouch 0}
    try {$ck disconnect; $ck connect $target} finally {if {$protected} {$i setDoNotTouch 1}}
  }
  lappend ::ot_ci_tree_seen $ck
  set n [$go getNet]
  if {$n eq "NULL"} {error "OT_CORE_INFRA_GATE_NO_DOMAIN $inst"}
  $n setSigType CLOCK
  set b [$i getBBox]
  set cx [expr {([$b xMin] + [$b xMax]) / 2.0 / $::ot_ci_u}]; set cy [expr {([$b yMin] + [$b yMax]) / 2.0 / $::ot_ci_u}]
  puts [format "OT_CORE_INFRA_LATE_GATE %s kept placed (%.3f, %.3f) plan (%.3f, %.3f) d=%.3f" $inst $cx $cy $x $y \
          [expr {abs($cx - $x) + abs($cy - $y)}]]
  lappend ::ot_ci_fixed $i
  dict set ::ot_ci_tree_out $inst $n
}
proc ot_ci_late_legalize {max_um} {
  if {![info exists ::ot_ci_late_cells] || ![llength $::ot_ci_late_cells]} {error "OT_CORE_INFRA_LATE_NO_CELLS"}
  set mine [dict create]
  foreach rec $::ot_ci_late_cells {dict set mine [lindex $rec 0] 1}
  set held {}
  foreach i [$::ot_ci_b getInsts] {
    if {[dict exists $mine $i]} continue
    if {[$i getPlacementStatus] eq "PLACED"} {$i setPlacementStatus FIRM; lappend held $i}
  }
  try {
    detailed_placement
  } finally {
    foreach i $held {$i setPlacementStatus PLACED}
  }
  set worst 0.0
  foreach rec $::ot_ci_late_cells {
    lassign $rec i x y rect
    set b [$i getBBox]
    set cx [expr {([$b xMin] + [$b xMax]) / 2.0 / $::ot_ci_u}]; set cy [expr {([$b yMin] + [$b yMax]) / 2.0 / $::ot_ci_u}]
    set d [expr {abs($cx - $x) + abs($cy - $y)}]
    if {$d > $worst} {set worst $d}
    lassign $rect x0 y0 x1 y1
    if {$d > $max_um || [$b xMin] < $x0*$::ot_ci_u || [$b yMin] < $y0*$::ot_ci_u || [$b xMax] > $x1*$::ot_ci_u ||
        [$b yMax] > $y1*$::ot_ci_u} {
      error [format "OT_CORE_INFRA_LATE_DPL %s at (%.3f, %.3f) plan (%.3f, %.3f) d=%.3f max %g rect {%s}" \
               [$i getName] $cx $cy $x $y $d $max_um $rect]
    }
    $i setPlacementStatus FIRM
  }
  puts [format "OT_CORE_INFRA_LATE_DPL cells=%d held=%d max_disp_um=%.3f (bound %g)" \
          [llength $::ot_ci_late_cells] [llength $held] $worst $max_um]
}
# The plan owns every stage above the CTS-open nets (equal total stages incl. macro early taps, 12.7c/12.8b), so
# TritonCTS's own latency balancer must not insert delay buffers upstream of the hop ICGs: that is a second balancing
# method on the planned (dont_touch) tree. This file
# is installed only for install_stage pre_cts, before core_infra_cts.tcl wraps clock_tree_synthesis in turn.
# TritonCTS (26Q3) clones a high-fanout / spread ICG of a CTS-open gated domain (clone_<n>_<gate>, same enables) and
# hangs the clone's CLK on the gate's planned parent net (A0 diag, ODB-0373 on mp_a0_t7_out). Such a clone is one more
# gate at the SAME planned depth. For the TritonCTS call only, dont_touch is lifted on those parent nets; afterwards the
# only accepted edit is added CLK pins of ICG clones of a gate already on that net (fail-closed otherwise).
proc ot_ci_late_gate_parents {} {
  set out [dict create]
  foreach net $::ot_ci_tree_open {
    set drv [$net getFirstOutput]
    if {$drv eq "NULL" || $drv eq ""} continue
    set g [$drv getInst]
    if {![string match ICG* [[$g getMaster] getName]]} continue
    set ck [$g findITerm CLK]
    if {$ck eq "NULL"} continue
    set pn [$ck getNet]
    if {$pn eq "NULL" || ![$pn isDoNotTouch]} continue
    dict lappend out $pn [$g getName]
  }
  return $out
}
if {![llength [info commands ::ot_ci_late_tritoncts]]} {
  rename ::clock_tree_synthesis ::ot_ci_late_tritoncts
  proc ::clock_tree_synthesis {args} {
    if {[lsearch -exact $args -no_insertion_delay] < 0} {lappend args -no_insertion_delay}
    # -repair_clock_nets buffers planned nets (A0 diag: RSZ-3006 on mp_a0_t2_out): plan identities, so not passed
    set k [lsearch -exact $args -repair_clock_nets]
    if {$k >= 0} {set args [lreplace $args $k $k]}
    puts "OT_CORE_INFRA_LATE_CTS plan-owned balancing: clock_tree_synthesis $args"
    set parents [ot_ci_late_gate_parents]
    set before [dict create]
    dict for {pn gates} $parents {
      dict set before $pn [lmap it [$pn getITerms] {set it}]
      $pn setDoNotTouch 0
    }
    try {
      ::ot_ci_late_tritoncts {*}$args
    } finally {
      dict for {pn gates} $parents {$pn setDoNotTouch 1}
    }
    set clones 0
    dict for {pn gates} $parents {
      set old [dict get $before $pn]
      foreach it $old {if {[$it getNet] ne $pn} {error "OT_CORE_INFRA_LATE_CTS_PLANNED_NET_EDIT [$pn getName] lost [[$it getInst] getName]"}}
      foreach it [$pn getITerms] {
        if {[lsearch -exact $old $it] >= 0} continue
        set i [$it getInst]; set n [$i getName]
        set ok [expr {[string match ICG* [[$i getMaster] getName]] && [$it getMTerm] ne "NULL" && [[$it getMTerm] getName] eq "CLK"}]
        if {$ok} {
          set ok 0
          foreach g $gates {if {[regexp {^clone_[0-9]+_} $n m] && [string range $n [string length $m] end] eq $g} {set ok 1}}
        }
        if {!$ok} {error "OT_CORE_INFRA_LATE_CTS_PLANNED_NET_EDIT [$pn getName] gained [$n]/[[$it getMTerm] getName]"}
        $i setDoNotTouch 1; incr clones
        puts "OT_CORE_INFRA_LATE_CTS_GATE_CLONE $n on [$pn getName] (TritonCTS ICG clone; same planned depth; kit LEC covers it)"
      }
    }
    puts "OT_CORE_INFRA_LATE_CTS planned parent nets=[dict size $parents] tritoncts_icg_clones=$clones"
  }
}

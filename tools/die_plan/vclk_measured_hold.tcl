# tools/die_plan/vclk_measured_hold.tcl (S81-ECO-2 10-27; OPT-IN form, FLOW-SHARED-4 10-27 rebase of 2f4c07767 + 9891c5f4e7).
# Measured FF boundary reference for the coupled two-mode (orfs_hold_mm.tcl) GRT repair: in ot_mm_sync, mode ff, the IO
# virtual clock is bound to the FF IO-boundary pin-register clock-arrival mean measured on the session's GRT parasitics
# (same selection as signoff.py FF_VCLK_TCL), band-checked against the bound FF insertion +- tol (fail closed), BEFORE
# setup/hold repair.  ONLY when the kit opts in (config.mk OT_MM_MEASURED_HOLD = 1, kit_modes.py stage --measured-hold,
# 'rebind' kits only); no default flow (grt_post.tcl, gen_phys.py, core_flow.py) sources this file.
# Frame note (FLOW-SHARED-4, COORD ruling 3): the bound mean is measured in the SAME RC model the repair times the
# registers in; IO hold slack = in_min + data - (arr_i - mean) - hold (output: (arr_i - mean) + data - out_min), so an
# absolute offset of the whole clock between GRT and RCX (S81 VQ: GRT 226.36 vs routed 211.64 ps FF) cancels exactly;
# binding the routed 211.64 while timing the registers at GRT RC would instead INJECT a 15 ps frame error.  The residual
# risk is the per-register deviation (arr_i - mean) error between GRT RC and RCX (rc_cal fit FF hold-slack error p5 -9.3 /
# p95 +11.4 ps), covered by the hold margin; it is not a binding optimism.
set ::ot_vmh_dir [file dirname [file normalize [info script]]]

proc ot_vmh_reference {} {
  set py [file join $::ot_vmh_dir vclk_ref.py]
  if {![file isfile $py]} { error "OT_VCLK_MEASURED_HOLD: missing $py (kit predates the measured-frame hold step)" }
  if {[catch {exec python3 -I $py $::ot_vmh_dir} out]} { error "OT_VCLK_MEASURED_HOLD: vclk_ref.py failed: $out" }
  set out [string trim $out]
  if {[llength $out] != 3} { error "OT_VCLK_MEASURED_HOLD: bad vclk_ref.py output '$out'" }
  return $out
}

# IO-boundary pin-register clock-arrival mean (SDC units) -> {mean n bad nclocks}
proc ot_vmh_pinreg_mean {} {
  if {![llength [info commands ot_cf_wire]]} {
    foreach f [list [file join $::ot_vmh_dir clock_family.tcl]] { if {[file isfile $f]} { uplevel #0 [list source $f] } }
  }
  set ck_ports {}
  foreach c [all_clocks] { foreach s [get_property $c sources] { lappend ck_ports [get_full_name $s] } }
  set din {}
  foreach p [all_inputs] { if {[get_full_name $p] ni $ck_ports} { lappend din $p } }
  set regs {}
  # The golden SDC declares the source-forwarded ring families explicitly.
  # Their writer flops have their own input-delay/window contract and cannot
  # contribute to the local IO virtual-clock insertion reference (HEAD-36).
  # Without those declarations the legacy census is unchanged. Keep every
  # declared core root in multi-root kits; never infer ownership from names.
  set fwd_roots {}
  set sdcp [file join $::ot_vmh_dir constraint.sdc]
  if {[file isfile $sdcp]} {
    set fh [open $sdcp]; set sdct [read $fh]; close $fh
    foreach line [split $sdct "\n"] {
      if {![string match {# OT_FWD_RING_INPUTS *} $line]} continue
      if {![regexp {^# OT_FWD_RING_INPUTS\s+(\S+)\s+\S+} $line -> name]} {
        error "OT_VCLK_MEASURED_HOLD: malformed forwarded-ring declaration"
      }
      set clock [get_clocks -quiet $name]
      if {[llength $clock] != 1} { error "OT_VCLK_MEASURED_HOLD: missing unique forwarded clock $name" }
      if {[llength [info commands ot_cf_refresh]]} { ot_cf_refresh }
      set root [expr {[llength [info commands ot_cf_root]] ? [ot_cf_root $name] : $name}]
      dict set fwd_roots $root 1
    }
  }
  foreach p [all_registers -clock_pins] {
    if {[dict size $fwd_roots]} {
      set owners [get_property $p clocks]
      if {[llength $owners] == 1} {
        set name [get_full_name [lindex $owners 0]]
        set root [expr {[llength [info commands ot_cf_root]] ? [ot_cf_root $name] : $name}]
        if {[dict exists $fwd_roots $root]} continue
      }
    }
    dict set regs [regsub {/[^/]+$} [get_full_name $p] {}] $p
  }
  set async {}
  foreach p [all_registers -async_pins] { dict set async [get_full_name $p] 1 }
  set data {}
  foreach p [all_registers -data_pins] { set n [get_full_name $p]; if {![dict exists $async $n]} { dict set data $n 1 } }
  set bnd {}
  if {[llength $din]} {
    foreach p [get_fanout -from $din -flat -endpoints_only -trace_arcs all] {
      set n [get_full_name $p]
      if {![dict exists $data $n]} continue
      set i [regsub {/[^/]+$} $n {}]
      if {[dict exists $regs $i]} { dict set bnd $i 1 }
    }
  }
  if {[llength [all_outputs]]} {
    foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
      set i [regsub {/[^/]+$} [get_full_name $p] {}]
      if {[dict exists $regs $i]} { dict set bnd $i 1 }
    }
  }
  set sum 0.0; set n 0; set bad 0; set clocks {}
  if {[llength [info commands ot_cf_refresh]]} { catch {ot_cf_refresh} }
  dict for {i unused} $bnd {
    set p [dict get $regs $i]
    set cl [get_property $p clocks]
    set a ""
    if {[llength $cl] == 1} {
      set name [get_full_name [lindex $cl 0]]
      if {[dict size $fwd_roots] && [llength [info commands ot_cf_root]]} { set name [ot_cf_root $name] }
      dict set clocks $name 1
      if {[llength [info commands ot_cf_wire]]} { catch {set a [ot_cf_wire $p [lindex $cl 0] [expr {[info exists ::ot_ioref_scene] ? $::ot_ioref_scene : ""}]]} }
      if {$a eq ""} { catch {set a [get_property $p arrival_max_rise]} }
    }
    if {![string is double -strict $a] || [regexp -nocase {inf|nan} $a]} { incr bad; continue }
    set sum [expr {$sum + $a}]; incr n
  }
  return [list [expr {$n ? $sum / $n : "nan"}] $n $bad [dict size $clocks]]
}

proc ot_vclk_measured_bind {} {
  lassign [ot_vmh_reference] ref ffb tol
  if {$ref ne "rebind"} { puts "OT_VCLK_MEASURED_HOLD skip ref $ref (sign-off frame = bound / sdc, already repaired)"; return }
  set vc {}
  foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend vc $c } }
  if {[llength $vc] != 1} { error "OT_VCLK_MEASURED_HOLD: expected exactly one IO virtual clock, found [llength $vc]" }
  estimate_parasitics -global_routing
  lassign [ot_vmh_pinreg_mean] mean n bad ncl
  if {$n == 0 || $bad != 0 || $ncl != 1} {
    error "OT_VCLK_MEASURED_HOLD: pin-register mean unavailable (samples $n missing $bad clocks $ncl) -- sign-off would be NOT RUN"
  }
  if {abs($mean - $ffb) > $tol} {
    error "OT_VCLK_MEASURED_HOLD: FF pin-register mean [format %.3f $mean] outside bound $ffb +- $tol (sign-off band FAIL; fix the clock, not the hold)"
  }
  set_clock_latency -source $mean [lindex $vc 0]
  puts "OT_VCLK_MEASURED_BIND clock [get_full_name [lindex $vc 0]] measured [format %.6f $mean] bound $ffb tol $tol samples $n"
  return $mean
}

proc ot_vclk_measured_hold {} {
  set mean [ot_vclk_measured_bind]
  if {$mean eq ""} { return }
  set hm 0
  foreach k {OT_HOLD_FF_MARGIN HOLD_SLACK_MARGIN} { if {[info exists ::env($k)] && [string is double -strict $::env($k)]} { set hm $::env($k); break } }
  puts "OT_VCLK_MEASURED_HOLD ref rebind measured $mean hold_margin $hm"
  set before [llength [get_cells -quiet -hierarchical hold*]]
  global_route -start_incremental
  repair_timing -hold -hold_margin $hm -max_buffer_percent 100
  detailed_placement
  check_placement -verbose
  global_route -end_incremental
  estimate_parasitics -global_routing
  puts "OT_VCLK_MEASURED_HOLD done hold_cells_before $before after [llength [get_cells -quiet -hierarchical hold*]]"
  report_worst_slack -min -digits 3
}

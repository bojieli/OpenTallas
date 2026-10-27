# GENERATED-COPY of tools/die_plan/vclk_measured_hold.tcl (S81-ECO-2 10-27, FLOW): repair FF hold in the frame the
# kit is SIGNED OFF in.  Sourced by grt_post.tcl in the FF-only GRT step (OT_VCLK_CORNER=ff), on the global-route
# parasitics, before the vclk goes back to TT; in the two-scene GRT step (grt_scenes.sh) grt_ff_scene.sdc calls
# ot_vmh_scene_bind instead (FF scene vclk measured before the stage repair; FLOW-MCMM-GRT 10-27).
#
# Die-plan kits sign off FF IO hold against the routed FF pin-register mean ('rebind', ruling 9.7 / 5e, COORD REBIND
# 10-27, band-checked vs the bound FF insertion +- tol).  The in-flow repair used the fixed bound (OT_VCLK_FF): on
# qbank_S / sstn_base566 c18 the measured mean was 12.8 / 11.5 ps below the bound -> FF hold -6.19 / -6.32 ps at
# sign-off after a clean in-flow repair (CHECKED).  This step measures the mean with the same selection as
# signoff.py FF_VCLK_TCL (IO-boundary registers: data-pin fanout of the non-clock inputs + startpoints of the
# outputs; one clock each; ot_cf_wire else arrival_max_rise), band-checks it (fail closed), binds it and repairs
# hold (async removal arcs included: repair_timing -hold works on every min-check endpoint).  Kits whose sign-off
# reference is not 'rebind' (hard-core 'bound-ff', plain 'sdc') are untouched.  No margin change, no pad.
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
  foreach p [all_registers -clock_pins] { dict set regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
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
      dict set clocks [get_full_name [lindex $cl 0]] 1
      if {[llength [info commands ot_cf_wire]]} { catch {set a [ot_cf_wire $p [lindex $cl 0]]} }
      if {$a eq ""} { catch {set a [get_property $p arrival_max_rise]} }
    }
    if {![string is double -strict $a] || [regexp -nocase {inf|nan} $a]} { incr bad; continue }
    set sum [expr {$sum + $a}]; incr n
  }
  return [list [expr {$n ? $sum / $n : "nan"}] $n $bad [dict size $clocks]]
}

# the IO virtual clock + its band-checked measured FF pin-register mean (fail closed) -> {vclk mean n ffb tol}
proc ot_vmh_measured {ffb tol} {
  set vc {}
  foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend vc $c } }
  if {[llength $vc] != 1} { error "OT_VCLK_MEASURED_HOLD: expected exactly one IO virtual clock, found [llength $vc]" }
  lassign [ot_vmh_pinreg_mean] mean n bad ncl
  if {$n == 0 || $bad != 0 || $ncl != 1} {
    error "OT_VCLK_MEASURED_HOLD: pin-register mean unavailable (samples $n missing $bad clocks $ncl) -- sign-off would be NOT RUN"
  }
  if {abs($mean - $ffb) > $tol} {
    error "OT_VCLK_MEASURED_HOLD: FF pin-register mean [format %.3f $mean] outside bound $ffb +- $tol (sign-off band FAIL; fix the clock, not the hold)"
  }
  return [list [lindex $vc 0] $mean $n]
}

# FLOW-MCMM-GRT 10-27: FF scene binding of the two-scene GRT repair (grt_ff_scene.sdc, read in mode ff by
# orfs_hold_mm.tcl ot_mm_sync on GRT parasitics, arrivals from scene BC).  vclk = OT_VCLK_FF (+ core-tap FF overlay);
# 'rebind' kits: then the measured mean (same selection / band as signoff.py).  No repair here: the stage's own
# repair_timing repairs TT setup (scene tc) and FF hold (scene BC) together.
proc ot_vmh_scene_bind {} {
  ot_vclk_bind ff
  lassign [ot_vmh_reference] ref ffb tol
  if {$ref ne "rebind"} { puts "OT_GRT_SCENES ff vclk = bound OT_VCLK_FF (sign-off ref $ref)"; return }
  lassign [ot_vmh_measured $ffb $tol] vc mean n
  set_clock_latency -source $mean $vc
  puts "OT_GRT_SCENES ff vclk = measured FF pin-register mean [format %.6f $mean] (bound $ffb tol $tol samples $n, ref rebind)"
}

proc ot_vclk_measured_hold {} {
  lassign [ot_vmh_reference] ref ffb tol
  if {$ref ne "rebind"} { puts "OT_VCLK_MEASURED_HOLD skip ref $ref (sign-off frame = bound / sdc, already repaired)"; return }
  estimate_parasitics -global_routing
  lassign [ot_vmh_measured $ffb $tol] vc mean n
  set_clock_latency -source $mean $vc
  set hm 0
  foreach k {OT_HOLD_FF_MARGIN HOLD_SLACK_MARGIN} { if {[info exists ::env($k)] && [string is double -strict $::env($k)]} { set hm $::env($k); break } }
  puts "OT_VCLK_MEASURED_HOLD ref rebind clock [get_full_name $vc] measured [format %.6f $mean] bound $ffb tol $tol samples $n hold_margin $hm"
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

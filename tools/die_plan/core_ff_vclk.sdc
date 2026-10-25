# Opt-in core clock contract for the REAL FF mode of the route-time MM flow.
# Read LAST through OT_MM_FF_SDC, inside ot_mm_sync's BC scene shim.  Enable:
# OT_FF_VCLK_MODE=pin_flop_mean, OT_FF_VCLK_CONTRACT=<measured source@sha>.
# Does not change periods, uncertainties, input/output delays or the TT mode.
# The shared virtual clock moves BOTH IO directions to the measured BC boundary
# reference. Missing / mixed / non-BC measurements are errors, never a fallback.
proc ot_core_ff_vclk_apply {} {
  if {![info exists ::env(OT_FF_VCLK_MODE)] || $::env(OT_FF_VCLK_MODE) in {"" sdc off}} { return }
  if {$::env(OT_FF_VCLK_MODE) ne "pin_flop_mean"} { error "CORE_FF_VCLK: unsupported reference mode" }
  if {![info exists ::env(OT_FF_VCLK_CONTRACT)] || [string trim $::env(OT_FF_VCLK_CONTRACT)] eq ""} {
    error "CORE_FF_VCLK: explicit source-pinned measured core clock contract required"
  }
  if {![info exists ::ot_mm_active] || !$::ot_mm_active ||
      ![info exists ::ot_ioref_scene] || $::ot_ioref_scene ne "BC" ||
      ![llength [info commands ot_mm_arrival_bc]]} {
    error "CORE_FF_VCLK: real BC scene during ot_mm_sync required; refusing a global TT clock shift"
  }
  set vc {}; set ck_ports {}
  foreach c [all_clocks] {
    set sources [get_property $c sources]
    if {![llength $sources]} { lappend vc $c } else {
      foreach p $sources { lappend ck_ports [get_full_name $p] }
    }
    if {abs([get_property $c period] - 833.0) > 0.001} { error "CORE_FF_VCLK: 833 ps core clock contract required" }
  }
  if {[llength $vc] != 1} { error "CORE_FF_VCLK: exactly one shared IO virtual clock required" }
  set din {}
  foreach p [all_inputs] { if {[get_full_name $p] ni $ck_ports} { lappend din $p } }
  set regs {}; set async {}; set data {}; set boundary {}
  foreach p [all_registers -clock_pins] { dict set regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
  foreach p [all_registers -async_pins] { dict set async [get_full_name $p] 1 }
  foreach p [all_registers -data_pins] {
    set n [get_full_name $p]
    if {![dict exists $async $n]} { dict set data $n 1 }
  }
  if {[llength $din]} {
    foreach p [get_fanout -from $din -flat -endpoints_only -trace_arcs all] {
      set n [get_full_name $p]
      if {![dict exists $data $n]} continue
      set i [regsub {/[^/]+$} $n {}]
      if {[dict exists $regs $i]} { dict set boundary $i 1 }
    }
  }
  if {[llength [all_outputs]]} {
    foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
      set i [regsub {/[^/]+$} [get_full_name $p] {}]
      if {[dict exists $regs $i]} { dict set boundary $i 1 }
    }
  }
  set total 0.0; set n 0; set missing 0; set families {}
  dict for {i unused} $boundary {
    set p [dict get $regs $i]; set cl [get_property $p clocks]; set a ""
    if {[llength $cl] == 1} {
      dict set families [get_full_name [lindex $cl 0]] 1
      # The existing MM helper reads report_arrival -scene BC explicitly.
      # get_property arrival_* without this is the TT/FF extreme, not FF.
      catch {set a [ot_mm_arrival_bc $p arrival_max_rise]}
    }
    if {![string is double -strict $a] || [regexp -nocase {inf|nan} $a]} { incr missing; continue }
    set total [expr {$total + $a}]; incr n
  }
  if {$n == 0 || $missing || [dict size $families] != 1} {
    error "CORE_FF_VCLK: unavailable boundary measurement samples=$n missing=$missing clock_families=[dict size $families]"
  }
  set mean [expr {$total / $n}]
  set before [ot_mm_ws min BC]
  set_clock_latency -source $mean [lindex $vc 0]
  set after [ot_mm_ws min BC]
  set ::ot_core_ff_vclk_record [dict create mode pin_flop_mean scene BC virtual_clock [get_full_name [lindex $vc 0]] \
    latency_ps $mean samples $n contract $::env(OT_FF_VCLK_CONTRACT) raw_hold_ps $before referenced_hold_ps $after]
  puts "CORE_FF_VCLK [list $::ot_core_ff_vclk_record]"
}
ot_core_ff_vclk_apply

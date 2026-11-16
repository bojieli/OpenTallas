# Opt-in GRT-only nonport hold repair. Source this file literally at the END of
# PRE_GLOBAL_ROUTE_TCL, after any existing repair_timing_helper/HB4 wrapper.
# No change unless OT_GRT_NONPORT_HOLD=1. Normal sign-off still sees every path.
if {![info exists ::env(OT_GRT_NONPORT_HOLD)] || $::env(OT_GRT_NONPORT_HOLD) in {"" 0 false}} { return }
if {$::env(OT_GRT_NONPORT_HOLD) ne "1"} { error "OT_GRT_NONPORT_HOLD requires 0 or 1" }
if {[info exists ::ot_grt_nonport_installed]} { return }

# advisory residue of the output-port hold that the GRT repair no longer pads: PORT_SEAM out N ws X (die STA owns it)
proc ot_grt_port_seam {outs} {
  set n 0; set ws 0.0
  if {[llength $outs] && ![catch {find_timing_paths -path_delay min -to $outs -group_path_count 3000000 -endpoint_path_count 1 -slack_max 0} ps]} {
    foreach pe $ps { set s [sta::time_sta_ui [$pe slack]]; incr n; if {$s < $ws} { set ws $s } }
  }
  puts [format "OT_GRT_NONPORT PORT_SEAM out %d ws %.2f (advisory: output-port hold is not repaired at GRT)" $n $ws]
}
# Native FF scope follows ot_prd_hold_scope's full-precision SDC restoration.
# Input DATA starts and output-port endpoints are excluded; no internal/macro exception.
proc ot_grt_nonport_native_scope {body} {
  set dir [expr {[info exists ::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : [pwd]}]
  set stem [file join $dir ot_grt_nonport_[pid]_[clock clicks]]
  set before ${stem}_before.sdc
  set after ${stem}_after.sdc
  write_sdc -digits 17 -no_timestamp $before
  set clock_sources [dict create]
  foreach clock [all_clocks] {
    foreach source [get_property $clock sources] { dict set clock_sources [get_full_name $source] 1 }
  }
  set inputs {}
  foreach port [all_inputs] {
    if {![dict exists $clock_sources [get_full_name $port]]} { lappend inputs $port }
  }
  # QC-SRC-CLOSE-1115 (COORD r211, FABLE-PD-QCHOLD-1915 F2): output-port endpoints leave the GRT hold scope; the residue is one
  # advisory line for die STA.  (Output-port padding at 11-15 s per buffer was the measured QC GRT hold stall.)
  set outputs [all_outputs]
  puts "OT_GRT_NONPORT begin native_ff input_ports=[llength $inputs] excluded_output_ports=[llength $outputs]"
  ot_grt_port_seam $outputs
  try {
    if {[llength $inputs]} { set_false_path -hold -from $inputs }
    if {[llength $outputs]} { set_false_path -hold -to $outputs }
    return [uplevel 1 $body]
  } finally {
    if {[llength $inputs]} { unset_path_exceptions -hold -from $inputs }
    if {[llength $outputs]} { unset_path_exceptions -hold -to $outputs }
    # Replay the complete original SDC: removing an overlapping temporary
    # exception may split an original one, and clock/IO precision must survive.
    read_sdc $before
    write_sdc -digits 17 -no_timestamp $after
    set fb [open $before r]; set tb [read $fb]; close $fb
    set fa [open $after r]; set ta [read $fa]; close $fa
    if {$tb ne $ta} { error "OT_GRT_NONPORT restore differs: retained $before $after" }
    puts "OT_GRT_NONPORT restored exact FF SDC (port hold remains visible)"
    if {![info exists ::env(OT_HOLD_SCOPE_KEEP_SDC)] || $::env(OT_HOLD_SCOPE_KEEP_SDC) ne "1"} {
      file delete $before $after
    }
  }
}
proc ot_grt_nonport_mm_call {args} {
  if {![info exists ::ot_mm_synced] || ![info exists ::ot_mm_stage] || $::ot_mm_stage ne "4_cts.sdc"} {
    error "OT_GRT_NONPORT requires a synced GRT 4_cts.sdc FF repair session"
  }
  set had [info exists ::env(OT_HOLD_REPAIR_SCOPE)]
  if {$had} { set previous $::env(OT_HOLD_REPAIR_SCOPE) }
  set ::env(OT_HOLD_REPAIR_SCOPE) nonport
  try {
    # Existing ot_repair_timing separates untouched TT setup from scoped FF
    # hold and uses ot_hold_repair_scope's exact FF SDC/mode restoration.
    return [uplevel 1 [list ::ot_grt_nonport_mm_original {*}$args]]
  } finally {
    if {$had} { set ::env(OT_HOLD_REPAIR_SCOPE) $previous } else { unset ::env(OT_HOLD_REPAIR_SCOPE) }
  }
}
if {[info exists ::ot_mm_active] && $::ot_mm_active} {
  if {![llength [info procs ::ot_repair_timing]] || ![llength [info procs ::ot_hold_repair_scope]] ||
      ![info exists ::ot_hold_scope_supported_modes] || "nonport" ni $::ot_hold_scope_supported_modes} {
    error "OT_GRT_NONPORT requires matching nonport-capable orfs_hold_mm.tcl"
  }
  rename ::ot_repair_timing ::ot_grt_nonport_mm_original
  proc ::ot_repair_timing {args} { return [uplevel 1 [list ot_grt_nonport_mm_call {*}$args]] }
  set ::ot_grt_nonport_installed mm
} else {
  if {![info exists ::env(OT_VCLK_CORNER)] || [string tolower $::env(OT_VCLK_CORNER)] ne "ff" ||
      ([info exists ::env(CORNER)] && [string toupper $::env(CORNER)] ni {BC FF})} {
    error "OT_GRT_NONPORT native session must explicitly select FF (OT_VCLK_CORNER=ff, CORNER=BC)"
  }
  if {![llength [info procs ::repair_timing_helper]]} {
    error "OT_GRT_NONPORT PRE_GLOBAL_ROUTE requires existing repair_timing_helper"
  }
  rename ::repair_timing_helper ::ot_grt_nonport_helper_original
  proc ::repair_timing_helper {args} {
    return [ot_grt_nonport_native_scope [list ::ot_grt_nonport_helper_original {*}$args]]
  }
  set ::ot_grt_nonport_installed native_ff
}
puts "OT_GRT_NONPORT installed $::ot_grt_nonport_installed; hold input starts and output endpoints out of scope; reg2reg/internal/macro retained"


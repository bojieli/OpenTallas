# GRT183-RESUME (ROOT 2026-10-15): sourced by hooks/pre_grt_ot_grt183.tcl (tools/run_abi3_physical.py) at ORFS PRE
# GLOBAL_ROUTE, after the block's own PRE_GLOBAL_ROUTE hook.
#
# Defect: GRT-0183 ("3D maze router ran out of legal paths (heap underflow)") raised by the INCREMENTAL global route that
# repair_design / repair_timing run inside stage 5_1_grt kills the stage although the full global route of the same
# design has zero overflow.  Measured on qfd_tt_scale_leaf-tg1-b123d97bd (ot-epyc1tb:/srv/opentallas/claude/
# tt-boundary-2116): initial full GRT 8.99 % usage, 0 overflow; repair_design up-sized scale_addr[166] DFFHQNx1->x2 at
# an unchanged location and the incremental reroute of _04241_ hit GRT-0183.  In the same process neither
# global_route -end_incremental (SIGSEGV in GlobalRouter::endIncremental) nor a new full global_route (GRT-0171) recovers;
# a FRESH process that full-global-routes the saved resized design and runs the complete repair_design passes
# (0 overflow, 137 slew violations repaired, RECOVERY_PASS_C).
#
# This hook only SAVES the resized design ($RESULTS_DIR/5_1_grt.grt183_resume.odb) and re-raises the error, so the stage
# still fails; tools/run_abi3_physical.py then re-runs the whole 5_1_grt stage ONCE, in a fresh process, from that
# design (every repair re-runs: no mutation discarded, no repair skipped, no guard or limit changed).  A second GRT-0183
# (marker 5_1_grt.grt183_recovered.json present) saves a distinct diagnostic-only terminal DB with all current
# hook shapes intact, then fails with the original Tcl error/options. It is never used for another resume.
#
# Sourced BEFORE the block's own PRE_GLOBAL_ROUTE hook: it records the routing obstructions and placement blockages the
# stage started with; the saved design drops the ones the block's hook added (keepouts / macro edge guards, which the
# re-run's PRE hook re-creates from unchanged pins and macros -- macro_edge_via_guard.tcl refuses a second add), so the
# re-run starts from exactly the stage's input state plus the repair mutations.
namespace eval ot_g183 {
  variable hook_source [info script]
  proc json_string {value} {
    set out "\""
    foreach char [split $value ""] {
      scan $char %c code
      switch -- $char {
        "\\" { append out "\\\\" }
        "\"" { append out "\\\"" }
        default {
          if {$code < 32} { append out [format {\u%04x} $code] } else { append out $char }
        }
      }
    }
    return "${out}\""
  }
  proc save_terminal {helper message options} {
    variable hook_source
    set stem [file join $::env(RESULTS_DIR) "5_1_grt.grt183_terminal.${helper}.[pid].[clock clicks]"]
    # This is diagnostic evidence, never a resume input: keep every actual shape.
    set failed [catch {write_db ${stem}.odb} detail]
    set fields [dict create stage 5_1_grt helper $helper source $hook_source \
      error $message error_options $options odb ${stem}.odb \
      db_status [expr {$failed ? "WRITE_FAILED" : "SAVED"}] db_detail $detail \
      scope DIAGNOSTIC_ONLY_NO_RETRY captured_at [clock format [clock seconds] -gmt 1 -format {%Y-%m-%dT%H:%M:%SZ}]]
    set pairs {}
    dict for {key value} $fields { lappend pairs "[json_string $key]: [json_string $value]" }
    set channel [open ${stem}.json {WRONLY CREAT EXCL}]
    try { puts $channel "\{[join $pairs ,]\}" } finally { close $channel }
    puts "OT_GRT183_TERMINAL_SAVED helper=$helper metadata=${stem}.json db_status=[dict get $fields db_status]; diagnostic only, no retry"
  }
  proc keys {} {
    set b [ord::get_db_block]; set out {}
    foreach o [$b getObstructions] {
      set x [$o getBBox]; set l [$x getTechLayer]
      lappend out [list O [expr {$l eq "NULL" ? "-" : [$l getName]}] [$x xMin] [$x yMin] [$x xMax] [$x yMax]] $o
    }
    foreach o [$b getBlockages] {
      set x [$o getBBox]
      lappend out [list B - [$x xMin] [$x yMin] [$x xMax] [$x yMax]] $o
    }
    return $out
  }
  # QC fw 11-11 (RSZ-3006 class, slw_fw_v3 a20, COORD 11-11): the in-flow hold repair (repair_timing -hold inside 5_1_grt)
  # buffers a net before its loads; a dont_touch HB4 hold-pad load (u_hdly_<bus>.g_b[].g_k[].u_hb) makes ODB-1211
  # "InsertBufferBeforeLoads: Load pin ... is dont_touch" and RSZ-3006 kills the stage (3 h 18 min lost).  The pads are the
  # planned hold fix, so the nets feeding them must not be buffered: set them dont_touch for the repair call only (the
  # instances stay dont_touch; no other cell, clock net or power net is touched).  OT_HB4_PAD_NETS_DNT=0 restores the old flow.
  proc protect_pad_nets {} {
    if {[info exists ::env(OT_HB4_PAD_NETS_DNT)] && $::env(OT_HB4_PAD_NETS_DNT) eq "0"} { return 0 }
    set n 0
    foreach inst [[ord::get_db_block] getInsts] {
      if {![$inst isDoNotTouch] || [string first "u_hdly_" [$inst getName]] < 0} continue
      foreach it [$inst getITerms] {
        if {![$it isInputSignal]} continue
        set net [$it getNet]
        if {$net eq "NULL" || $net eq "" || [$net getSigType] ne "SIGNAL" || [$net isDoNotTouch]} continue
        $net setDoNotTouch 1
        incr n
      }
    }
    puts "OT_HB4_PAD_NETS_DNT nets=$n: dont_touch on nets feeding dont_touch u_hdly_ pad loads for repair_timing (RSZ-3006 class)"
    return $n
  }
  variable start {}
  foreach {k o} [keys] { dict incr start $k }
  proc strip_hook_shapes {} {
    variable start; set seen {}; set n 0
    foreach {k o} [keys] {
      dict incr seen $k
      if {[dict get $seen $k] > ([dict exists $start $k] ? [dict get $start $k] : 0)} {
        if {[lindex $k 0] eq "O"} { odb::dbObstruction_destroy $o } else { odb::dbBlockage_destroy $o }
        incr n
      }
    }
    return $n
  }
}
foreach ot_g183_helper {repair_design_helper repair_timing_helper} {
  if {[llength [info commands $ot_g183_helper]] && ![llength [info commands ot_g183_orig_$ot_g183_helper]]} {
    rename $ot_g183_helper ot_g183_orig_$ot_g183_helper
    proc $ot_g183_helper {args} [string map [list @H@ $ot_g183_helper] {
      if {"@H@" eq "repair_timing_helper"} { catch {ot_g183::protect_pad_nets} ot_pn_err; if {$ot_pn_err ne "" && ![string is integer -strict $ot_pn_err]} { puts "OT_HB4_PAD_NETS_DNT_FAILED: $ot_pn_err" } }
      set rc [catch {uplevel 1 [linsert $args 0 ot_g183_orig_@H@]} msg opts]
      if {$rc == 0} { return $msg }
      set dir $::env(RESULTS_DIR)
      if {[string match "*GRT-0183*" $msg] && ![file exists $dir/5_1_grt.grt183_recovered.json]} {
        set ot_n [ot_g183::strip_hook_shapes]
        write_db $dir/5_1_grt.grt183_resume.odb
        puts "OT_GRT183_RESUME_SAVED helper=@H@ odb=$dir/5_1_grt.grt183_resume.odb hook_shapes_dropped=$ot_n: incremental GRT-0183 inside @H@; the runner re-runs 5_1_grt once in a fresh process from this resized design"
      } elseif {[string match "*GRT-0183*" $msg]} {
        if {[catch {ot_g183::save_terminal @H@ $msg $opts} ot_save_error]} {
          puts "OT_GRT183_TERMINAL_SAVE_FAILED helper=@H@: $ot_save_error"
        }
        puts "OT_GRT183_RESUME_REFUSED helper=@H@: GRT-0183 again after one fresh-process resume; not retried"
      }
      return -options $opts $msg
    }]
  }
}
unset ot_g183_helper

# PRE_RESIZE hook (KW-FIX-44 PLACE-NOCONVERGE, COORD 11-10): end the run at place when global placement did not converge.
# OpenROAD stops the Nesterov loop at its built-in iteration limit (GPL-1010, 5,000 here) and the flow then goes on:
# HBM kv_line vC left GPL at overflow 0.370, resize added 459k buffers and DPL-0038 hit 153% utilisation, hours later.
# The verdict is gp_noconverge.py --gate on the finished 3_3_place_gp.log (same parser as the fleet no-progress report):
# GPL-1010 and last overflow > OT_GPL_NOCONV_OVERFLOW (default 0.1) -> FAIL_PLACE_NOCONVERGE marker + Tcl error, so make
# stops at 3_4 before repair_design.  No log, or the checker itself failing, leaves the flow unchanged (reported, no stop).
# OT_GPL_NOCONV=0 turns the gate off.
# KW-FIX-45 PLACE-FANOUT (COORD 11-12): OT_PLACE_MAX_FANOUT (kit config.mk, gen_phys.place_max_fanout) = the fanout
# limit of the place-stage repair_design that runs right after this hook; independent of the gate below (also with
# OT_GPL_NOCONV=0).  Unset / empty = unchanged.
if {[info exists ::env(OT_PLACE_MAX_FANOUT)] && [string is integer -strict $::env(OT_PLACE_MAX_FANOUT)] && $::env(OT_PLACE_MAX_FANOUT) > 1} {
  set_max_fanout $::env(OT_PLACE_MAX_FANOUT) [current_design]
  puts "PLACE-FANOUT set_max_fanout $::env(OT_PLACE_MAX_FANOUT) on design [current_design] (place repair_design)"
}
# PLACE-SLEW (CORE-LIB-LIMITS-1330): OT_PLACE_MAX_TRANSITION (ps, kit config.mk, gen_phys.place_max_transition) = design
# max_transition for the same repair_design.  The hard-core view libs carry no max_transition, so nets into core pins
# had no slew limit; the stdcell libs' own 320 ps limit is the tighter one elsewhere.  Unset / empty / 0 = unchanged.
if {[info exists ::env(OT_PLACE_MAX_TRANSITION)] && [string is double -strict $::env(OT_PLACE_MAX_TRANSITION)] && $::env(OT_PLACE_MAX_TRANSITION) > 0} {
  set_max_transition $::env(OT_PLACE_MAX_TRANSITION) [current_design]
  puts "PLACE-SLEW set_max_transition $::env(OT_PLACE_MAX_TRANSITION) on design [current_design] (place repair_design; core pins have no liberty limit)"
}
set gpnc_dir [file dirname [file normalize [info script]]]
set gpnc_log [file join $::env(LOG_DIR) 3_3_place_gp.log]
set gpnc_ovf 0.1
if {[info exists ::env(OT_GPL_NOCONV_OVERFLOW)] && $::env(OT_GPL_NOCONV_OVERFLOW) ne ""} { set gpnc_ovf $::env(OT_GPL_NOCONV_OVERFLOW) }
if {[info exists ::env(OT_GPL_NOCONV)] && $::env(OT_GPL_NOCONV) eq "0"} {
  puts "PLACE-NOCONVERGE gate off (OT_GPL_NOCONV=0)"
} elseif {![file exists $gpnc_log]} {
  puts "PLACE-NOCONVERGE gate NOT RUN: no $gpnc_log"
} else {
  set gpnc_marker [file join [file dirname $gpnc_dir] [file tail $gpnc_dir] FAIL_PLACE_NOCONVERGE]
  set gpnc_rc [catch {exec python3 -I [file join $gpnc_dir gp_noconverge.py] --gate $gpnc_log --overflow $gpnc_ovf \
                        --marker $gpnc_marker} gpnc_out]
  if {$gpnc_rc == 0} {
    puts $gpnc_out
  } elseif {[lindex $::errorCode 0] eq "CHILDSTATUS" && [lindex $::errorCode 2] == 3} {
    puts $gpnc_out
    error $gpnc_out
  } else {
    puts "PLACE-NOCONVERGE gate NOT RUN (checker failed, flow unchanged): $gpnc_out"
  }
}

# PLACE-HPWL (FABLE-PD-S81-STRIP 11-16): OT_GPL_HPWL_RATIO (kit config.mk; unset, empty or 0 = off) ends the run here when
# the GPL result's measured HPWL (all signal nets, pin centres, ports) exceeds that multiple of the lowest HPWL the same
# run printed in its Nesterov table (gp_noconverge.py --hpwl-gate): a placement that converged and then diverged
# (S81 t47 2.36 x, t75 1.91 x, t8fix 1.81 x after the non-virtual timing-driven pass; good leaves 1.01-1.05).
# Marker FAIL_PLACE_HPWL, Tcl error -> make stops before resize.  Checker failure leaves the flow unchanged (reported).
if {[info exists ::env(OT_GPL_HPWL_RATIO)] && [string is double -strict $::env(OT_GPL_HPWL_RATIO)] && $::env(OT_GPL_HPWL_RATIO) > 0} {
  if {![file exists $gpnc_log]} {
    puts "PLACE-HPWL gate NOT RUN: no $gpnc_log"
  } else {
    set gphw_blk [ord::get_db_block]
    set gphw_u [expr {double([$gphw_blk getDbUnitsPerMicron])}]
    set gphw_h 0.0
    foreach gphw_net [$gphw_blk getNets] {
      if {[$gphw_net getSigType] in {POWER GROUND}} continue
      set gphw_x {}; set gphw_y {}
      foreach gphw_it [$gphw_net getITerms] {
        set gphw_r [$gphw_it getAvgXY]
        if {[lindex $gphw_r 0]} { lappend gphw_x [lindex $gphw_r 1]; lappend gphw_y [lindex $gphw_r 2] } else {
          set gphw_b [[$gphw_it getInst] getBBox]
          lappend gphw_x [expr {([$gphw_b xMin] + [$gphw_b xMax]) / 2}]; lappend gphw_y [expr {([$gphw_b yMin] + [$gphw_b yMax]) / 2}] }
      }
      foreach gphw_bt [$gphw_net getBTerms] { set gphw_b [$gphw_bt getBBox]; lappend gphw_x [$gphw_b xMin]; lappend gphw_y [$gphw_b yMin] }
      if {[llength $gphw_x] < 2} continue
      set gphw_x [lsort -real $gphw_x]; set gphw_y [lsort -real $gphw_y]
      set gphw_h [expr {$gphw_h + [lindex $gphw_x end] - [lindex $gphw_x 0] + [lindex $gphw_y end] - [lindex $gphw_y 0]}]
    }
    set gphw_um [expr {$gphw_h / $gphw_u}]
    set gphw_marker [file join [file dirname $gpnc_dir] [file tail $gpnc_dir] FAIL_PLACE_HPWL]
    set gphw_rc [catch {exec python3 -I [file join $gpnc_dir gp_noconverge.py] --hpwl-gate $gpnc_log --exit-hpwl $gphw_um \
                          --ratio $::env(OT_GPL_HPWL_RATIO) --marker $gphw_marker} gphw_out]
    if {$gphw_rc == 0} {
      puts $gphw_out
    } elseif {[lindex $::errorCode 0] eq "CHILDSTATUS" && [lindex $::errorCode 2] == 3} {
      puts $gphw_out
      error $gphw_out
    } else {
      puts "PLACE-HPWL gate NOT RUN (checker failed, flow unchanged): $gphw_out"
    }
  }
}

# POST-PLACE built-wire check of zero-logic register-to-register paths (lever 7, HOLD-FLOW-R 11-17): place_wire_ratio.tcl, report-only
# unless OT_PLACE_WIRE_RATIO = fail (0 = off).  Runs last so a gate above that already stopped the run is not delayed by it.
# (a kit that carries core_input_chain.tcl runs it from the end of that file instead: after the chain spread, not before)
if {[file exists [file join $gpnc_dir place_wire_ratio.tcl]] && ![file exists [file join $gpnc_dir core_input_chain.tcl]]} { source [file join $gpnc_dir place_wire_ratio.tcl] }

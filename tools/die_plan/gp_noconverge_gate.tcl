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
  puts "PLACE-FANOUT set_max_fanout $::env(OT_PLACE_MAX_FANOUT) on [get_full_name [current_design]] (place repair_design)"
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

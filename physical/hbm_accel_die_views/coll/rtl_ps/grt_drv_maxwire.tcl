# PRE_GLOBAL_ROUTE hook (el1011-hbm-coll 2026-10-11, route_ps.sh MAXWIRE=<um>): repeater pitch for the hcoll tile.
# Why: tiles g5a/b/c (87566e93a) routed DRC 0 / TT +62.57 but failed independent_electrical_zero on 120 / ~130 /
# ~170 max-slew pins (limit 320 ps, worst 481 ps).  Probe of g5a 6_final.odb: every violator is ONE wire segment of
# 130-215 um (u_wtx/net16644 BUFx6f 215.7 um, u_wrx/net19160 BUFx16f 192.5 um, u_qr din_p[151] DFFHQNx1 130.3 um):
# the post-GRT repair_design buffered to the GRT estimate at 20% margin, detailed routing then put the long hops on
# the high-R M2/M3 layers of this pin-dense tile and the segment slew went 50% over.  Industry practice: a max-length
# (repeater pitch) rule on every signal net, so slew is set by repeater spacing, not by the layer DRT happens to use.
# This keeps the flow's own repair_design (same slew/cap margins) and adds -max_wire_length; it also keeps the
# v41x_karb_repair_buffer_cap.tcl repair_timing override that route_ps.sh passes at this hook.
source /src/physical/abi3/v41x_karb_repair_buffer_cap.tcl
# el1011-hbm-coll 2026-10-11 (child_lint check f, before the hfd_coll cluster): with OT_PK_FRAC set, the face-pin
# access keepout (stn_pin_keepout.tcl; the same file runs as POST_DETAIL_ROUTE and removes it) = pin_access_pregrt.tcl.
if {[info exists ::env(OT_PK_FRAC)]} {
  # WAVE-FLOW-R2 11-17: the kit carries stn_pin_keepout.tcl (kit_common_files); /src has it only in a full checkout (a sparse lane clone failed GRT here: 6 svc cores).
  # Kit copy first, then /src; with neither the keepout is skipped LOUDLY (no stations to protect), never a silent half run.
  set ot_pk_done 0
  foreach ot_pk_f [list [file join [file dirname [info script]] stn_pin_keepout.tcl] /work/stn_pin_keepout.tcl /src/physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl] {
    if {[file exists $ot_pk_f]} { source $ot_pk_f; set ot_pk_done 1; break }
  }
  if {!$ot_pk_done} { puts "OT_PK WARNING: OT_PK_FRAC is set but stn_pin_keepout.tcl is in neither the kit nor /src: the face-pin keepout is skipped" }
}
if {[info procs repair_design_helper] ne "" && [info procs ot_orig_repair_design_helper] eq ""} {
  rename repair_design_helper ot_orig_repair_design_helper
  proc repair_design_helper {} {
    set args [list -verbose -max_wire_length $::env(OT_MAXWIRE_UM)]
    if {[info exists ::env(CAP_MARGIN)]} { lappend args -cap_margin $::env(CAP_MARGIN) }
    if {[info exists ::env(SLEW_MARGIN)]} { lappend args -slew_margin $::env(SLEW_MARGIN) }
    puts "OT_MAXWIRE repair_design $args"
    log_cmd repair_design {*}$args
  }
}

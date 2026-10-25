# Copied into every kit by tools/die_plan/gen.py phys (PRE_SYNTH_TCL hook, CP1-R10 10-24): ORFS synth_odb.tcl runs
# eliminate_dead_logic after this hook; it deleted the planned face registers whose q the leaf leaves unused (CP1 r10b:
# 120 frame_int_i1 in-bus flops + their inverters, 248 instances), after Yosys kept them.  Every boundary / ft station cell
# (u_bin_* / u_bout_* / u_ft_* hierarchy, kept by the ot_dp_* keep_hierarchy cells) is dont_touch for that step only;
# RESET 10-24: the reset tree's entry stage and relays (u_rst_in / u_rst_root / u_rrl_<k>) too: a tap with no RTL
# load kept no relay chain (CP1 reach405P: 125 of 175 relays deleted), so reset_taps.tcl could not re-point FIRM flops
# to it and the placed-hop gate saw missing relays.
# face_keep_release.tcl (POST_SYNTH_TCL) releases them so repair / resizing work on them as before.
set fk_c {}
foreach i [get_cells -hierarchical *] {
  if {[regexp {(^|[/.])(u_(bin|bout|ft)_[^/]*|u_rst_in|u_rst_root|u_rrl_[0-9]+)[/.]} [get_full_name $i]]} { lappend fk_c $i }
}
if {[llength $fk_c]} { set_dont_touch $fk_c }
puts "OT_FACE_KEEP dont_touch [llength $fk_c] boundary cells before eliminate_dead_logic"
# S81/FTHOLD 10-25: the plan's ft input hold cells (u_ftd_<slot>, tools/die_plan/ft_hold.py) are dont_touch for the
# WHOLE flow (face_keep_release.tcl does not match them): remove_buffers / repair_design / repair_timing must neither
# delete nor resize the deterministic delay (it is budgeted in the kit SDC ft share).
set fk_h {}
foreach i [get_cells -hierarchical *] {
  if {[regexp {(^|[/.])u_ftd_[^/.]*[/.]} [get_full_name $i]]} { lappend fk_h $i }
}
if {[llength $fk_h]} { set_dont_touch $fk_h }
puts "OT_FACE_KEEP dont_touch [llength $fk_h] ft input hold cells (kept for the whole flow)"

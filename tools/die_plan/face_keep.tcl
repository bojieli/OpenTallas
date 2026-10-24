# Copied into every kit by tools/die_plan/gen.py phys (PRE_SYNTH_TCL hook, CP1-R10 10-24): ORFS synth_odb.tcl runs
# eliminate_dead_logic after this hook; it deleted the planned face registers whose q the leaf leaves unused (CP1 r10b:
# 120 frame_int_i1 in-bus flops + their inverters, 248 instances), after Yosys kept them.  Every boundary / ft station cell
# (u_bin_* / u_bout_* / u_ft_* hierarchy, kept by the ot_dp_* keep_hierarchy cells) is dont_touch for that step only;
# face_keep_release.tcl (POST_SYNTH_TCL) releases them so repair / resizing work on them as before.
set fk_c {}
foreach i [get_cells -hierarchical *] {
  if {[regexp {(^|[/.])u_(bin|bout|ft)_[^/]*[/.]} [get_full_name $i]]} { lappend fk_c $i }
}
if {[llength $fk_c]} { set_dont_touch $fk_c }
puts "OT_FACE_KEEP dont_touch [llength $fk_c] boundary cells before eliminate_dead_logic"

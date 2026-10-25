# Copied into every kit by tools/die_plan/gen.py phys (POST_SYNTH_TCL hook, CP1-R10 10-24): release face_keep.tcl's dont_touch.
set fk_c {}
foreach i [get_cells -hierarchical *] {
  if {[regexp {(^|[/.])(u_(bin|bout|ft)_[^/]*|u_rst_in|u_rst_root|u_rrl_[0-9]+)[/.]} [get_full_name $i]]} { lappend fk_c $i }
}
if {[llength $fk_c]} { unset_dont_touch $fk_c }
puts "OT_FACE_KEEP released [llength $fk_c] boundary cells"

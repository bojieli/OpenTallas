# RING retained capture bits: the source already declares each cap_* register keep/dont_touch.
# Yosys preserves them; OpenROAD eliminate_dead_logic needs physical-cell dont_touch too.
# Place before eliminate_dead_logic through PRE_SYNTH_TCL, after normal face_keep.tcl.
set rk_cells {}
foreach rk_cell [get_cells -hierarchical *] {
  if {[regexp {(^|[/.])u_ring[/.]g_lane\[[0-7]\][/.]u_state[/.]cap_[A-Za-z0-9_]+\[[0-9]+\]\$_DFF_} [get_full_name $rk_cell]]} {
    lappend rk_cells $rk_cell
  }
}
if {![llength $rk_cells]} { error "RING_CAPTURE_RELEASE: no capture cells found" }
unset_dont_touch $rk_cells
puts "RING_CAPTURE_RELEASE [llength $rk_cells] source-declared capture cells released for data repair"

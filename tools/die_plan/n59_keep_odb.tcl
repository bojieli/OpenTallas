# Native59 physical state retention. Use STA cell objects directly: passing
# escaped OpenDB names to get_cells treats bracketed array names as patterns.
source /work/face_keep.tcl
set n59k_regs {}
foreach cell [get_cells -hierarchical *] {
 if {[regexp {(^|[/.])u_core[/.]} [get_full_name $cell]] && [regexp {DFF|SDF} [get_property $cell ref_name]]} {
  lappend n59k_regs $cell
 }
}
if {![llength $n59k_regs]} {error "N59_KEEP no actual body register objects in selected native59 netlist"}
set_dont_touch $n59k_regs
puts "N59_KEEP retained [llength $n59k_regs] actual selected body FF objects"

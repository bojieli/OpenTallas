# Keep the selected native59 state through OpenROAD's pre-floorplan dead-logic
# cleanup as well as Yosys. Wire attributes are absent after Liberty mapping;
# the physical type therefore retains its selected body FF population here.
# Release before physical optimisation; no data, clock or reset pin changes.
source /work/face_keep.tcl
set n59k_regs {}
foreach inst [[ord::get_db_block] getInsts] {
 if {[regexp {(^|[/.])u_core[/.]} [$inst getName]] && [regexp {DFF|SDF} [[$inst getMaster] getName]]} {
  lappend n59k_regs [$inst getName]
 }
}
if {![llength $n59k_regs]} {error "N59_KEEP no body registers in selected native59 netlist"}
set_dont_touch [get_cells $n59k_regs]
puts "N59_KEEP retained [llength $n59k_regs] selected body FFs through eliminate_dead_logic"

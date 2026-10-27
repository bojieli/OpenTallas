source /work/face_keep_release.tcl
set n59k_regs {}
foreach inst [[ord::get_db_block] getInsts] {
 if {[regexp {(^|[/.])u_core[/.]} [$inst getName]] && [regexp {DFF|SDF} [[$inst getMaster] getName]]} {
  lappend n59k_regs [$inst getName]
 }
}
if {[llength $n59k_regs]} {unset_dont_touch [get_cells $n59k_regs]}
puts "N59_KEEP released [llength $n59k_regs] selected body FFs after eliminate_dead_logic"

# s81-vm-1011 2026-10-11: dsfd_vm_bgq28 (537.6 x 500.04): copy of place_macros_vmsys.tcl with the macro column fixed at the W edge.
# redesign-ds 2026-10-09: macro rows for the SYSTOLIC VM tile (rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv, instance
# names g_s[s].g_bank[b].g_m[c].g_sram.u_m).  Bank row r = s * SR + b counts from the NORTH face (requests and read data
# flow N -> S, stage 0 sits under the input pins), x 39.744 (bgq, one 174.12-um column) as place_macros_vms.tcl, rows
# evenly spread between y0 = 10.8 and the north edge - 10.8 (macro-edge clearance >= 10 um, checked); for the 500.04
# outline the pitch is 61.56 (the vm_bg grid), for a taller outline the channels between rows grow.
set ot_blk [ord::get_db_block]
set ot_u [$ot_blk getDbUnitsPerMicron]
set ot_die [$ot_blk getDieArea]
set ot_w [expr {[$ot_die dx] / double($ot_u)}]
set ot_h [expr {[$ot_die dy] / double($ot_u)}]
set ot_m {}
set ot_smax 0; set ot_bmax 0
foreach ot_i [$ot_blk getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_s\\?\[(\d+)\\?\]\.g_bank\\?\[(\d+)\\?\]\.g_m\\?\[(\d)\\?\]\..*u_m$} $ot_nm -> ot_s ot_b ot_c]} { continue }
  lappend ot_m [list $ot_nm $ot_s $ot_b $ot_c]
  if {$ot_s > $ot_smax} { set ot_smax $ot_s }
  if {$ot_b > $ot_bmax} { set ot_bmax $ot_b }
}
set ot_sr [expr {$ot_bmax + 1}]
set ot_rows [expr {($ot_smax + 1) * $ot_sr}]
if {[llength $ot_m] < 8 || $ot_rows != 8} { error "place_macros_vm28: [llength $ot_m] macros / $ot_rows rows" }
set ot_mh 29.736
set ot_y0 32.4   ;# el1011-ds-vm/bgq28: >= 32 um N / S pin-face channels (the f_d / i_d pin registers and IO buffers sit between the pins and the end macros; at 10.8 the S-face f_d buffers were pushed ~500 ps of wire away) -> pitch 57.24, inter-macro channels 27.5 um
# pitch on the 1.08-um row grid
set ot_p [expr {floor(($ot_h - 2 * $ot_y0 - $ot_mh) / ($ot_rows - 1) / 1.08) * 1.08}]
foreach e $ot_m {
  lassign $e ot_nm ot_s ot_b ot_c
  set ot_r [expr {$ot_s * $ot_sr + $ot_b}]
  set ot_y [expr {$ot_y0 + ($ot_rows - 1 - $ot_r) * $ot_p}]
  set ot_x 39.744   ;# one 174.12-um macro column at the W edge; the E channel carries the 24-port bus
  place_macro -macro_name $ot_nm -location [list $ot_x $ot_y] -orientation R0
}
foreach ot_i [$ot_blk getInsts] {
  if {![[$ot_i getMaster] isBlock]} { continue }
  set ot_bb [$ot_i getBBox]
  set ot_c [expr {min(([$ot_bb xMin] - [$ot_die xMin]), ([$ot_die xMax] - [$ot_bb xMax]), ([$ot_bb yMin] - [$ot_die yMin]), ([$ot_die yMax] - [$ot_bb yMax])) / double($ot_u)}]
  if {$ot_c < 20.0} { error "place_macros_vm28: [$ot_i getName] only $ot_c um from a die edge (< 20 um macro-edge clearance)" }
}
puts "place_macros_vm28: [llength $ot_m] macros, $ot_rows rows, pitch $ot_p (die $ot_w x $ot_h)"

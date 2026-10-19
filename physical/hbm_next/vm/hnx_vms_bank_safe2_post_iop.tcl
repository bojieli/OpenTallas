# HBM-NEXT-UNITS-VM 2026-10-19: copy of physical/ref_tile_specs/smh/vm_q0_faces_g313_post_iop.tcl for hnx_vms_bank (pin file swapped)
source /src/physical/hbm_next/vm/hnx_vms_bank_safe2_pins.tcl

set vb [ord::get_db_block]
set vu [$vb getDbUnitsPerMicron]
set vt [ord::get_db_tech]
set vm_pg {}
foreach bt [$vb getBTerms] {
 if {[$bt getSigType] ni {POWER GROUND}} continue
 foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {
  lappend vm_pg [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
 }}
}
set vm_bad 0
set vm_rows [open [file join $::env(RESULTS_DIR) identity_actual_pins.tsv] w]
puts $vm_rows "port\tface\tlayer\texpected_um\tactual_um\ttrack_ok\tPG_projection_clear"
foreach item $vm_expected {
 lassign $item name face layer expected
 set bt [$vb findBTerm $name]
 if {$bt eq "NULL" || $bt eq "" || [llength [$bt getBPins]] != 1} {
  puts "VM_ID_PIN_ERROR missing/duplicate pin $name";incr vm_bad;continue
 }
 set boxes [[lindex [$bt getBPins] 0] getBoxes]
 if {[llength $boxes] != 1} {puts "VM_ID_PIN_ERROR rectangle count $name";incr vm_bad;continue}
 set box [lindex $boxes 0]
 set actual [expr {$face in {N S}?([$box xMin]+[$box xMax])/2.0:([$box yMin]+[$box yMax])/2.0}]
 set tl [$vt findLayer $layer]
 set grid [$vb findTrackGrid $tl]
 set tracks [expr {$face in {N S}?[$grid getGridX]:[$grid getGridY]}]
 set track_ok [expr {[lsearch -exact $tracks [expr {int(round($actual))}]] >= 0}]
 set pg_clear 1
 set half [expr {$face in {N S}?([$box xMax]-[$box xMin])/2.0:([$box yMax]-[$box yMin])/2.0}]
 set space [$tl getSpacing]
 foreach rect $vm_pg {
  lassign $rect pl ax ay bx by
  if {$pl ne $layer} continue
  set lo [expr {$face in {N S}?$ax:$ay}]
  set hi [expr {$face in {N S}?$bx:$by}]
  if {$actual+$half+$space>$lo && $actual-$half-$space<$hi} {set pg_clear 0;break}
 }
 set actual_um [expr {$actual/double($vu)}]
 if {abs($actual_um-$expected)>0.0001 || [[$box getTechLayer] getName] ne $layer || !$track_ok || !$pg_clear} {
  puts "VM_ID_PIN_ERROR $name expected=$expected actual=$actual_um track=$track_ok PG_clear=$pg_clear"
  incr vm_bad
 }
 puts $vm_rows "$name\t$face\t$layer\t$expected\t$actual_um\t$track_ok\t$pg_clear"
}
close $vm_rows
set vm_actual_signal 0
foreach bt [$vb getBTerms] {if {[$bt getSigType] ni {POWER GROUND}} {incr vm_actual_signal}}
if {$vm_actual_signal != [llength $vm_expected]} {incr vm_bad;puts "VM_ID_PIN_ERROR signal inventory $vm_actual_signal expected [llength $vm_expected]"}
# abutted SRAM stack (pitch = height + .024 on the M4 lattice): block the .024 um slivers (textbook util_channel)
set ot_sliver_um 20.0
source /src/physical/common_flow/macro_channel_block.tcl

# Safe2: one connected full-width cell band. Macros remain fixed outside the cell rows.
set vm_ylo [expr {round(129.6*$vu)}]
set vm_yhi [expr {round(151.2*$vu)}]
set vm_rows_removed 0
foreach vm_row [$vb getRows] {
 set vm_bb [$vm_row getBBox]
 if {[$vm_bb yMin] < $vm_ylo || [$vm_bb yMax] > $vm_yhi} {odb::dbRow_destroy $vm_row;incr vm_rows_removed}
}
set vm_phys_removed 0
foreach vm_i [$vb getInsts] {
 set vm_ty [[$vm_i getMaster] getType]
 if {![string match CORE_WELLTAP $vm_ty] && ![string match ENDCAP* $vm_ty] && ![string match TAP_* [$vm_i getName]] && ![string match PHY_EDGE_* [$vm_i getName]]} continue
 set vm_bb [$vm_i getBBox]
 if {[$vm_bb yMin] < $vm_ylo || [$vm_bb yMax] > $vm_yhi} {odb::dbInst_destroy $vm_i;incr vm_phys_removed}
}
puts "HNX_VM_SINGLE_BAND rows_removed=$vm_rows_removed phys_removed=$vm_phys_removed y129.6..151.2"

source /src/tools/fp_margin_lint.tcl
ot_fp_lint_dump [file join $::env(RESULTS_DIR) identity_actual_pin_pg.json]
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
puts "VM_ID_PIN_READBACK checked=[llength $vm_expected] PG_shapes=[llength $vm_pg] violations=$vm_bad"
if {$vm_bad} {error "VM_ID_PIN_READBACK failed: $vm_bad actual coordinate/track/PG errors"}

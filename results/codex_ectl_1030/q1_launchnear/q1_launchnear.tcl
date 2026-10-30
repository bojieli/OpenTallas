foreach l $::env(OT_LIBS) {read_liberty $l}
read_db /work/run/results/asap7/hc_qkd_ectlk_q1__233_28x172_8/base/6_final.odb
read_sdc /work/constraint.sdc
# Final DB physical-only fillers must be cleared before any legal ECO growth.
remove_fillers
set_propagated_clock [get_clocks clk]
set ::env(RESULTS_DIR) /out
source /work/clk_freeze.tcl
ot_clk_freeze
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron]
set f [open /work/targets.tsv r];set lines [split [string trim [read $f]] \n];close $f
set moved 0;set sized 0
foreach line $lines {
 lassign [split $line \t] nm old new move src tx ty
 set i [$b findInst $nm]
 if {$i eq "NULL" || $i eq "" || [[$i getMaster] getName] ne $old} {error "Q1_LAUNCH source identity mismatch $nm"}
 if {[string match DFF* $old]} {error "Q1_LAUNCH refuses FF changes"}
 if {$new ne $old} {
  set lc [get_lib_cells -quiet */$new]
  if {[llength $lc]!=1} {error "Q1_LAUNCH unavailable exact driver $new"}
  replace_cell [get_cells -quiet $nm] [lindex $lc 0]
  incr sized
 }
 if {$move} {
  set driver [$b findInst $src]
  if {$driver eq "NULL" || $driver eq ""} {error "Q1_LAUNCH missing source $src"}
  $i setOrient [$driver getOrient]
  $i setLocation [expr {int(round($tx*$u))}] [expr {int(round($ty*$u))}]
  $i setPlacementStatus PLACED
  incr moved
 }
}
puts "Q1_LAUNCH moved $moved sized $sized combinational drivers; before DPL"
detailed_placement
check_placement -verbose
ot_clk_freeze_assert q1_launchnear_placed
write_db /out/q1_launchnear_placed.odb
set f [open /out/actual_moves.tsv w]
foreach line $lines {
 lassign [split $line \t] nm old new move src tx ty
 if {!$move} continue
 set i [$b findInst $nm];set driver [$b findInst $src];lassign [$i getLocation] x y;lassign [$driver getLocation] dx dy
 puts $f "$nm\t$src\t[expr {double(abs($x-$dx)+abs($y-$dy))/$u}]"
}
close $f
puts "Q1_LAUNCH PLACED ONLY; routed timing invalid until fresh GRT; no DRT performed"
exit

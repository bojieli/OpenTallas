read_db /work/work/orfs/results/asap7/opentallas_ot_attn_registered_parent_phys_asap7_codex_h16_registered_parent_r1/base/4_1_cts.odb
set b [ord::get_db_block]
foreach i [$b getInsts] {
 if {[[$i getMaster] isBlock]} {
  lassign [$i getLocation] x y
  set nx [expr {round(double($x)/48)*48}];set ny [expr {round(double($y)/48)*48}]
  puts "ACCESS_ONLY_ALIGN [$i getName] OLD $x $y NEW $nx $ny"
  $i setPlacementStatus PLACED
  $i setLocation $nx $ny
  $i setPlacementStatus FIRM
 }
}
# In-memory access diagnostic only. No saved routed/PG geometry is qualified or overwritten.
set_thread_count 1
set_routing_layers -signal M2-M9
pin_access
puts "ALIGNED_NATIVE_ACCESS_PASS"

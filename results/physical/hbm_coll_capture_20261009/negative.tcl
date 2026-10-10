foreach lib [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*.lib.gz] {read_liberty $lib}
read_liberty /source/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
read_db /input/3_2_place_iop.odb
set injected 0
foreach mac [[ord::get_db_block] getInsts] {
 if {![regexp {^ot_sram_1r1w_128x256_m1_r2c2$} [[$mac getMaster] getName]]} continue
 foreach pin [$mac getITerms] {
  if {![regexp {^rd_out\[} [[$pin getMTerm] getName]]} continue
  set net [$pin getNet]; if {$net eq "NULL"} continue
  foreach load [$net getITerms] {
   if {[[$load getMTerm] getName] ne "D"} continue
   foreach wrong [[$load getInst] getITerms] {
    if {![$wrong isInputSignal] || [[$wrong getMTerm] getName] eq "D"} continue
    $wrong connect $net;set injected 1;break
   }
   if {$injected} break
  }
  if {$injected} break
 }
 if {$injected} break
}
if {!$injected} {error "NEGATIVE_INJECTION_MISSING"}
source /gate/src/physical/hbm_accel_die_views/coll/rtl_ps/capture_adjacent_place.tcl
error "NEGATIVE_NOT_REJECTED"

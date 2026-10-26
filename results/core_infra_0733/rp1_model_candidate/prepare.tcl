set P /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [glob $P/*_RVT_TT_*] {read_liberty $f}
read_liberty /work/macros/ot_sram_1r1w_1024x256_m2_r2c2_tt.lib
read_db /work/source.odb
set f [open /work/source.sdc r];set constraint [read $f];close $f
foreach required {{create_clock -name clk -period 833.0000} {set_clock_uncertainty -setup 60.0000 clk} {set_clock_uncertainty -hold 25.0000 clk}} {
 if {[string first $required $constraint]<0} {error "DIAGNOSTIC_CONSTRAINT_MISMATCH $required"}
}
read_sdc /work/source.sdc
proc original_data_connections {} {
 set lines {}
 foreach i [[ord::get_db_block] getInsts] {
  set name [$i getName]
  if {[string match ot_ms_* $name] || [string match ot_isl_* $name] || [string match mp_core_* $name] || [string match mp_isl* $name]} continue
  foreach it [$i getITerms] {
   set mt [$it getMTerm]
   if {[$mt getSigType] in {POWER GROUND CLOCK} || [$mt getName] in {CLK clk}} continue
   set net [$it getNet];set nn NULL;if {$net ne "NULL"} {set nn [$net getName]}
   lappend lines [list $name [$mt getName] $nn [$i isDoNotTouch]]
  }
 }
 return [lsort $lines]
}
set data_before [original_data_connections]
source /work/restore_clock.tcl
source /work/master_core_infra.tcl
# Every planned clock cell is FIRM; only displaced original data cells legalize.
detailed_placement
check_placement -verbose
source /work/master_core_infra.tcl
if {$data_before ne [original_data_connections]} {error ORIGINAL_NONCLOCK_CONNECTIVITY_OR_PROTECTION_CHANGED}
set b [ord::get_db_block];set census [ot_pg_collect_all_native $b [ot_pg_prepare $b]]
if {[dict get $census failure_count]} {error "NATIVE_PG_FAIL $census"}
set ndr [$b findNonDefaultRule mp_core_clock_4w4s];set nc 0
dict for {node net} $::ot_ci_tree_out {if {[$net getNonDefaultRule] ne $ndr} {error "NDR_ASSIGNMENT_FAIL $node"};incr nc}
puts "PRE_ROUTE_GATES period833 uncertainty60_25 PG=$census nonclock_connectivity_protection_IDENTICAL ndr_clock_nets=$nc FT_ARC_QUALIFICATION_NOT_RUN"
write_db /work/prepared.odb
write_sdc /work/prepared.sdc
write_verilog /work/prepared.v
puts "PLAN_CTS_PREPARED exact_named_tree=1 automatic_CTS=0 no_data_cycles_added=1"

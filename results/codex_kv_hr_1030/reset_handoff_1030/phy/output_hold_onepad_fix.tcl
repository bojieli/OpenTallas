define_corners tc
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc /work/macros/ot_sram_1r1w_512x128_m1_r2c2_tt.lib
read_db /work/output_hold1/4_cts_outputhold.odb
read_sdc /work/run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base/4_cts.sdc
source /work/output_hold_guard_procs.tcl
source /work/output_hold1/original_physical_reference.tcl
set ::env(RESULTS_DIR) /work/output_hold1_fixed
file mkdir $::env(RESULTS_DIR)
source /work/clk_freeze.tcl
source /work/pg_connect.tcl
ot_clk_freeze
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron]
set i [$b findInst phy_outhp_6_0__1260]
if {$i eq "NULL" || [[$i getMaster] getName] ne "HB4xp67_ASAP7_75t_R" || [$i getLocation] ne [list 4320 48330]} {error "onepad identity/site mismatch"}
$i setOrient R0;$i setLocation 10152 48600
# Onealready-appliedDATApad relocated; noadd/delete, alloldhomes unchanged.
ot_pg_connect_all phy_output_hold_onepadfix
ot_pg_require_bound phy_output_hold_onepadfix
write_db /work/output_hold1_fixed/4_cts_outputhold.odb
write_def /work/output_hold1_fixed/4_cts_outputhold.def
write_verilog /work/output_hold1_fixed/after.v
write_sdc /work/output_hold1_fixed/4_cts_outputhold.sdc
check_placement -verbose
ot_clk_freeze_assert post_onepadfix
set new 0
foreach i [$b getInsts] {
 set n [$i getName]
 if {[dict exists $oh_orig $n]} {
  if {[list [[$i getMaster] getName] [$i getOrient] [$i getLocation]] ne [dict get $oh_orig $n]} {error "oldmaster/home changed $n"}
 } else {
  if {[[$i getMaster] getName] ne "HB4xp67_ASAP7_75t_R"} {error "nonHB4newcell"}
  incr new
 }
}
if {$new!=488} {error "newcellcount not488"}
if {[oh_pins] ne $oh_orig_pins || [oh_pg_wires] ne $oh_orig_pg} {error "publicpin/PGwire changed"}
ot_clk_dump /work/output_hold1_fixed/clock_final.tsv final /work/output_hold1/clk_freeze_nets.txt
puts "PHY_OUTPUT_HOLD_FIXED_GUARD_PASS oldcells[dict size $oh_orig] newHB4$new alloldmaster_home_orient_publicpin_PGwireEXACT"
puts PHY_OUTPUT_HOLD_ONEPAD_CORRECTION_DONE_NO_GRT_NO_STA_QUALIFICATION

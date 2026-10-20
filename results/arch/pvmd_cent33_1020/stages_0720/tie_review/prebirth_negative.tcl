read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir.lef
foreach pat {asap7sc7p5t_AO_RVT_TT* asap7sc7p5t_INVBUF_RVT_TT* asap7sc7p5t_OA_RVT_TT* asap7sc7p5t_SEQ_RVT_TT* asap7sc7p5t_SIMPLE_RVT_TT*} {
 foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$pat] {read_liberty $f}
}
read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir_tt.lib
read_verilog $::env(IMPORT_V)
link_design ot_hbm_sm_pv_merge_distributed
read_sdc /audit/work/results/asap7/opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate/base/1_2_yosys.sdc
source /audit/prebirth_kernel_rewire/graph_guard.tcl
set b [ord::get_db_block];set nd 0;set nc 0
foreach i [pvm_bf_cells $b] {incr nc;if {[$i isDoNotTouch]} {incr nd}}
if {$nc != 56000 || $nd != 0} {error "PREBIRTH_NEGATIVE_WRONG_FLAGS cells=$nc protected=$nd"}
puts "PREBIRTH_NEGATIVE_SOURCE cells=$nc protected=$nd noDNTclear"
pvm_bf_guard prebirth_kernel_rewire
error PREBIRTH_KERNEL_NEGATIVE_UNEXPECTED_PASS

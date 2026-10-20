read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir.lef
foreach pat {asap7sc7p5t_AO_RVT_TT* asap7sc7p5t_INVBUF_RVT_TT* asap7sc7p5t_OA_RVT_TT* asap7sc7p5t_SEQ_RVT_TT* asap7sc7p5t_SIMPLE_RVT_TT*} {
 foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/$pat] {read_liberty $f}
}
read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir_tt.lib
read_verilog $::env(IMPORT_V)
link_design ot_hbm_sm_pv_merge_distributed
set b [ord::get_db_block];set nc 0;set nd 0;set np 0
foreach i [$b getInsts] {
 if {[string first {.g_native7.u_native.} [$i getName]]<0} {continue}
 incr nc
 if {[$i isDoNotTouch]} {incr nd}
 foreach t [$i getITerms] {if {[$t getSigType] in {POWER GROUND} && [$t getNet] eq "NULL"} {incr np}}
}
set f [open $::env(IMPORT_OUT) {WRONLY CREAT EXCL}]
puts $f "{\"stage\":\"fresh_read_verilog_then_link_design_BEFORE_anySDC_orPG\",\"cells\":$nc,\"protected\":$nd,\"unboundPG\":$np}"
close $f
puts "IMPORT_PROBE $::env(IMPORT_V) cells=$nc protected=$nd unboundPG=$np"
exit
